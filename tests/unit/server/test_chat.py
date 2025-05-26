import pytest

# Mark all tests in this file as unit tests (fast with mocking)
pytestmark = pytest.mark.unit
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.server.chat import ChatService
from app.server.models import AgentResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


class TestChatService:
    """Test cases for ChatService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chat_service = ChatService()

    def test_chat_service_initialization(self):
        """Test that ChatService initializes correctly."""
        assert self.chat_service.agent_facade is not None
        assert hasattr(self.chat_service.agent_facade, 'config_manager')

    def test_serialize_messages_from_tuples(self):
        """Test serializing messages from tuples to dicts."""
        messages_tuples = [
            ("user", "Hello"),
            ("assistant", "Hi there!"),
            ("user", "How are you?")
        ]
        
        result = self.chat_service._serialize_messages_from_tuples(messages_tuples)
        
        expected = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        assert result == expected

    def test_serialize_messages_from_langchain_objects(self):
        """Test serializing Langchain message objects to dicts."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            SystemMessage(content="You are a helpful assistant")
        ]
        
        result = self.chat_service._serialize_messages(messages)
        
        expected = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "system", "content": "You are a helpful assistant"}
        ]
        
        assert result == expected

    def test_process_message_success(self):
        """Test successful message processing."""
        # Setup mock agent response
        mock_response = AgentResponse(
            success=True,
            message="Repository analysis complete",
            history=[("user", "Tell me about repo"), ("assistant", "Repository analysis complete")]
        )
        
        # Create a real event loop for the test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Patch the instance's agent_facade attribute
            self.chat_service.agent_facade = Mock()
            self.chat_service.agent_facade.invoke = AsyncMock(return_value=mock_response)
            
            reply, history = self.chat_service.process_message("test_user", "Tell me about repo")
            
            assert reply == "Repository analysis complete"
            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert history[1]["role"] == "assistant"
            assert history[1]["content"] == "Repository analysis complete"
        finally:
            loop.close()

    def test_process_message_agent_failure(self):
        """Test message processing when agent fails."""
        # Setup mock agent response for failure
        mock_response = AgentResponse(
            success=False,
            message="I had trouble processing your request",
            history=[("user", "Tell me about repo"), ("assistant", "I had trouble processing your request")]
        )
        
        # Create a real event loop for the test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Patch the instance's agent_facade attribute
            self.chat_service.agent_facade = Mock()
            self.chat_service.agent_facade.invoke = AsyncMock(return_value=mock_response)
            
            reply, history = self.chat_service.process_message("test_user", "Tell me about repo")
            
            assert "trouble processing" in reply
            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert history[1]["role"] == "assistant"
        finally:
            loop.close()

    def test_process_message_timeout(self):
        """Test message processing timeout handling."""
        # Create a real event loop for the test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Patch the instance's agent_facade attribute
            self.chat_service.agent_facade = Mock()
            self.chat_service.agent_facade.invoke = AsyncMock(side_effect=asyncio.TimeoutError())
            
            reply, history = self.chat_service.process_message("test_user", "Tell me about repo")
            
            assert "timed out" in reply.lower()
            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert history[1]["role"] == "assistant"
        finally:
            loop.close()

    def test_process_message_exception(self):
        """Test message processing when unexpected exception occurs."""
        # Create a real event loop for the test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Patch the instance's agent_facade attribute
            self.chat_service.agent_facade = Mock()
            self.chat_service.agent_facade.invoke = AsyncMock(side_effect=RuntimeError("Unexpected error"))
            
            reply, history = self.chat_service.process_message("test_user", "Tell me about repo")
            
            assert "trouble processing" in reply.lower()
            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert history[1]["role"] == "assistant"
        finally:
            loop.close()

    def test_get_history_placeholder(self):
        """Test that get_history returns empty list (placeholder implementation)."""
        result = self.chat_service.get_history("test_user")
        
        assert result == []

    @pytest.mark.asyncio
    async def test_close_agent_resources(self):
        """Test closing agent resources."""
        with patch.object(self.chat_service.agent_facade, 'stop', new_callable=AsyncMock) as mock_stop:
            await self.chat_service.close_agent_resources()
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_error_response(self):
        """Test error response generation."""
        with patch('app.agent.llm_client.LLMClient') as mock_llm_client:
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = "Generated error response"
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_client.return_value.llm = mock_llm
            
            result = await self.chat_service._generate_error_response("Test error", "Test message")
            
            assert result == "Generated error response"
            mock_llm.ainvoke.assert_called_once()

    def test_cleanup_preserves_event_loop(self):
        """Test that cleanup preserves the persistent event loop."""
        # Mock event loop
        mock_loop = Mock()
        mock_loop.is_closed.return_value = False
        self.chat_service._event_loop = mock_loop
        
        with patch.object(self.chat_service.agent_facade, 'close_resources', new_callable=AsyncMock):
            self.chat_service.cleanup()
            
            # Event loop should still be available
            assert hasattr(self.chat_service, '_event_loop')
            assert self.chat_service._event_loop == mock_loop

    def test_shutdown_closes_event_loop(self):
        """Test that shutdown closes the persistent event loop."""
        # Mock event loop
        mock_loop = Mock()
        mock_loop.is_closed.return_value = False
        self.chat_service._event_loop = mock_loop
        
        with patch.object(self.chat_service.agent_facade, 'close_resources', new_callable=AsyncMock):
            self.chat_service.shutdown()
            
            # Event loop should be closed
            mock_loop.close.assert_called_once()
