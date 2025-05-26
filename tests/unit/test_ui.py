import pytest

# Mark all tests in this file as unit tests (fast with mocking)
pytestmark = pytest.mark.unit
from unittest.mock import Mock, patch, MagicMock
import requests
from app.ui import AquariusUI


class TestAquariusUI:
    """Test cases for AquariusUI."""

    def test_is_processing_message_true(self):
        """Test detection of processing messages."""
        processing_content = "Processing your request..."
        
        result = AquariusUI._is_processing_message(processing_content)
        
        assert result is True

    def test_is_processing_message_false(self):
        """Test detection of non-processing messages."""
        regular_content = "Here's your repository analysis"
        
        result = AquariusUI._is_processing_message(regular_content)
        
        assert result is False

    def test_is_processing_message_empty(self):
        """Test detection with empty content."""
        result = AquariusUI._is_processing_message("")
        
        assert result is False

    def test_add_user_message(self):
        """Test adding user message to chat history."""
        chat_history = [
            {"role": "assistant", "content": "Hello! How can I help?"}
        ]
        message = "Tell me about microsoft/vscode"
        
        updated_history, updated_ui, cleared_input = AquariusUI.add_user_message(message, chat_history)
        
        assert len(updated_history) == 2
        assert updated_history[-1]["role"] == "user"
        assert updated_history[-1]["content"] == message
        assert updated_ui == updated_history
        assert cleared_input == ""

    def test_show_processing(self):
        """Test showing processing indicator."""
        chat_history = [
            {"role": "user", "content": "Tell me about repo"}
        ]
        
        updated_history = AquariusUI.show_processing(chat_history)
        
        assert len(updated_history) == 2
        assert updated_history[-1]["role"] == "assistant"
        assert "Processing your request" in updated_history[-1]["content"]
        assert "processing-spinner" in updated_history[-1]["content"]

    def test_clean_assistant_response_with_thinking_tags(self):
        """Test cleaning assistant response by removing thinking tags."""
        response_with_thinking = """<think>
        Let me analyze this repository...
        I need to check the commits
        </think>
        
        Based on my analysis, the repository has recent updates with bug fixes."""
        
        cleaned = AquariusUI._clean_assistant_response(response_with_thinking)
        
        assert "<think>" not in cleaned
        assert "</think>" not in cleaned
        assert "Based on my analysis" in cleaned
        assert "bug fixes" in cleaned

    def test_clean_assistant_response_without_thinking_tags(self):
        """Test cleaning assistant response without thinking tags."""
        response = "The repository has recent commits with new features."
        
        cleaned = AquariusUI._clean_assistant_response(response)
        
        assert cleaned == response

    def test_clean_assistant_response_empty(self):
        """Test cleaning empty response."""
        result = AquariusUI._clean_assistant_response("")
        
        assert result == ""

    def test_clean_assistant_response_multiple_newlines(self):
        """Test cleaning response with multiple newlines."""
        response = "Line 1\n\n\n\nLine 2\n\n\n\nLine 3"
        
        cleaned = AquariusUI._clean_assistant_response(response)
        
        # Should reduce multiple newlines to double newlines
        assert "\n\n\n" not in cleaned
        assert "Line 1\n\nLine 2\n\nLine 3" == cleaned.strip()

    @patch('app.ui.requests.post')
    def test_get_assistant_response_success(self, mock_post):
        """Test successful assistant response."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "assistant_reply": "Repository analysis complete",
            "messages": [
                {"role": "user", "content": "Tell me about repo"},
                {"role": "assistant", "content": "Repository analysis complete"}
            ]
        }
        mock_post.return_value = mock_response
        
        # Only include the user message - the processing message is removed in the UI component 
        # when response returns, not in the get_assistant_response function
        chat_history = [
            {"role": "user", "content": "Tell me about repo"}
        ]
        
        result = AquariusUI.get_assistant_response(chat_history)
        
        assert len(result) == 2
        assert result[-1]["role"] == "assistant"
        assert result[-1]["content"] == "Repository analysis complete"

    @patch('app.ui.requests.post')
    def test_get_assistant_response_api_error(self, mock_post):
        """Test assistant response with API error."""
        # Setup mock response with error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response
        
        # Only include the user message
        chat_history = [
            {"role": "user", "content": "Tell me about repo"}
        ]
        
        result = AquariusUI.get_assistant_response(chat_history)
        
        assert len(result) == 2
        assert result[-1]["role"] == "assistant"
        assert "API Error 500" in result[-1]["content"]

    @patch('app.ui.requests.post')
    def test_get_assistant_response_request_exception(self, mock_post):
        """Test assistant response with request exception."""
        # Setup mock to raise exception
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        
        # Only include the user message
        chat_history = [
            {"role": "user", "content": "Tell me about repo"}
        ]
        
        result = AquariusUI.get_assistant_response(chat_history)
        
        assert len(result) == 2
        assert result[-1]["role"] == "assistant"
        assert "Request Error" in result[-1]["content"]

    def test_get_assistant_response_no_user_message(self):
        """Test assistant response when no user message found."""
        chat_history = [
            {"role": "assistant", "content": "Hello"}
        ]
        
        result = AquariusUI.get_assistant_response(chat_history)
        
        # Should return unchanged history when no user message
        assert result == chat_history

    def test_final_sync_debug(self):
        """Test final sync debug method."""
        state = [
            {"role": "user", "content": "Test message"},
            {"role": "assistant", "content": "Test response"}
        ]
        
        result_state, result_ui = AquariusUI.final_sync_debug(state)
        
        assert result_state == state
        assert result_ui == state

    @patch('app.ui.gr.Blocks')
    def test_ui_creation(self, mock_blocks):
        """Test UI creation with Gradio blocks."""
        mock_demo = Mock()
        mock_blocks.return_value.__enter__.return_value = mock_demo
        
        # Mock gradio components
        with patch('app.ui.gr.Markdown') as mock_markdown, \
             patch('app.ui.gr.Tabs') as mock_tabs, \
             patch('app.ui.gr.Tab') as mock_tab, \
             patch('app.ui.gr.Chatbot') as mock_chatbot, \
             patch('app.ui.gr.Textbox') as mock_textbox, \
             patch('app.ui.gr.State') as mock_state:
            
            result = AquariusUI.ui()
            
            # Verify that gradio components were called
            mock_markdown.assert_called()
            mock_tabs.assert_called()
            mock_tab.assert_called()
            mock_chatbot.assert_called()
            mock_textbox.assert_called()
            mock_state.assert_called()

    @patch('app.ui.AquariusUI.ui')
    def test_launch_ui(self, mock_ui):
        """Test launching the UI."""
        mock_demo = Mock()
        mock_ui.return_value = mock_demo
        
        AquariusUI.launch_ui(server_name="127.0.0.1", server_port=7861)
        
        mock_demo.queue.assert_called_once()
        mock_demo.launch.assert_called_once_with(server_name="127.0.0.1", server_port=7861)

    def test_chat_api_url_configuration(self):
        """Test that CHAT_API_URL can be configured."""
        original_url = AquariusUI.CHAT_API_URL
        
        try:
            # Test default URL
            assert "http://127.0.0.1:5000/api/chat" in AquariusUI.CHAT_API_URL
            
            # Test URL override
            AquariusUI.CHAT_API_URL = "http://localhost:8000/api/chat"
            assert AquariusUI.CHAT_API_URL == "http://localhost:8000/api/chat"
            
        finally:
            # Restore original URL
            AquariusUI.CHAT_API_URL = original_url
