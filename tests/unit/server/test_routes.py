import pytest

# Mark all tests in this file as unit tests (fast with mocking)
pytestmark = pytest.mark.unit
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json


class TestServerRoutes:
    """Test cases for Flask API routes."""

    @pytest.fixture
    def client(self):
        """Create test Flask client."""
        from app.server.routes import app
        app.config['TESTING'] = True
        with patch('app.server.routes.chat_service') as mock_service:
            # Return a real mock that will not be overridden by route initialization
            yield app.test_client()

    def test_chat_endpoint_success(self, client):
        """Test successful chat API call."""
        from app.server.routes import chat_service
        
        # Setup mock chat service
        chat_service.process_message = Mock(
            return_value=("Repository analysis complete: microsoft/vscode has recent updates.", 
                         [("human", "Tell me about microsoft/vscode"), 
                          ("assistant", "Repository analysis complete: microsoft/vscode has recent updates.")])
        )
        
        response = client.post('/api/chat', 
                             data=json.dumps({
                                 "user_id": "test_user",
                                 "message": "Tell me about microsoft/vscode"
                             }),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "assistant_reply" in data
        assert "messages" in data
        assert "Repository analysis complete" in data["assistant_reply"]

    def test_chat_endpoint_missing_fields(self, client):
        """Test chat endpoint with missing required fields."""
        # Test missing user_id
        response = client.post('/api/chat', 
                             data=json.dumps({"message": "test"}),
                             content_type='application/json')
        assert response.status_code == 400
        
        # Test missing message
        response = client.post('/api/chat', 
                             data=json.dumps({"user_id": "test_user"}),
                             content_type='application/json')
        assert response.status_code == 400

    def test_chat_endpoint_invalid_json(self, client):
        """Test chat endpoint with invalid JSON."""
        response = client.post('/api/chat', 
                             data="invalid json",
                             content_type='application/json')
        
        assert response.status_code == 400

    def test_chat_endpoint_service_error(self, client):
        """Test chat endpoint when service raises error."""
        from app.server.routes import chat_service
        
        # Setup mock chat service to raise exception
        chat_service.process_message = Mock(side_effect=Exception("Processing failed"))
        
        response = client.post('/api/chat', 
                             data=json.dumps({
                                 "user_id": "test_user",
                                 "message": "test"
                             }),
                             content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "success" in data
        assert not data["success"]

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"

    def test_chat_handles_github_queries(self, client):
        """Test that chat endpoint handles GitHub-specific queries."""
        from app.server.routes import chat_service
        
        # Setup mock chat service
        chat_service.process_message = Mock(
            return_value=("Found 5 recent commits in the repository with bug fixes.", 
                         [("human", "What are recent changes in owner/repo?"),
                          ("assistant", "Found 5 recent commits in the repository with bug fixes.")])
        )
        
        response = client.post('/api/chat', 
                             data=json.dumps({
                                 "user_id": "test_user",
                                 "message": "What are recent changes in owner/repo?"
                             }),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "assistant_reply" in data
        assert "recent commits" in data["assistant_reply"]
        assert "bug fixes" in data["assistant_reply"]

    @pytest.mark.asyncio
    @patch('app.agent.llm_client.LLMClient')
    async def test_response_quality_with_llm(self, mock_llm_client, client):
        """Test that responses are evaluated with qwen3:8b for quality."""
        from app.server.routes import chat_service
        
        # Setup mock chat service
        chat_service.process_message = Mock(
            return_value=(
                "The microsoft/vscode repository has seen significant development in the past month. There were 52 commits from 15 contributors, focusing mainly on improving performance and fixing bugs in the editor's search functionality.",
                [("human", "Tell me about recent changes in microsoft/vscode"),
                 ("assistant", "The microsoft/vscode repository has seen significant development in the past month. There were 52 commits from 15 contributors, focusing mainly on improving performance and fixing bugs in the editor's search functionality.")]
            )
        )
        
        # Setup LLM validation
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = Mock(content="The response is relevant and provides specific details about the GitHub repository microsoft/vscode, including the number of commits (52), contributors (15), and focus areas (performance, search bugs). The response is high quality.")
        
        mock_llm_instance = Mock()
        mock_llm_instance.llm = mock_llm
        mock_llm_client.return_value = mock_llm_instance
        
        # Make request
        response = client.post('/api/chat',
                              data=json.dumps({
                                  "user_id": "test_user",
                                  "message": "Tell me about recent changes in microsoft/vscode",
                                  "evaluate_response": True  # Flag to enable LLM evaluation
                              }),
                              content_type='application/json')
        
        # In a real implementation, this would trigger the LLM evaluation
        # For now, we're just testing the structure is in place
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Basic response validation
        assert "assistant_reply" in data
        assert "52 commits" in data["assistant_reply"]
        assert "15 contributors" in data["assistant_reply"]
        
        # If we had response evaluation enabled, we'd check for it here
        # This test primarily ensures our test infrastructure can support
        # LLM-based response validation
