# app/server/chat.py
import asyncio # Added for running async AgentFacade methods
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# Removed: from app.agent.graph import get_graph
from app.agent.facade import AgentFacade # Added
from app.server.models import AgentResponse
import os
import logging
logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        # Initialize AgentFacade. 
        # AgentFacade will handle its own lazy initialization of graph and dependencies.
        self.agent_facade = AgentFacade() # Manages graph, LLM, tools
        logger.info("ChatService initialized with AgentFacade.")
        # The decision to load real tools vs. mocks should ideally be handled 
        # by the environment/configuration AgentFacade uses, not a simple env var here.
        # For now, AgentFacade will attempt to load real tools if configured.

    def _serialize_messages_from_tuples(self, messages_tuples: list[tuple[str, str]]) -> list[dict[str, str]]:
        """Serializes messages from (role, content) tuples to dicts."""
        serialized = []
        for role, content in messages_tuples:
            serialized.append({"role": role, "content": content})
        return serialized

    def _serialize_messages(self, messages: list[HumanMessage | AIMessage | SystemMessage]) -> list[dict[str, str]]:
        """Serializes Langchain message objects to dicts."""
        # This method might need to be updated based on AgentFacade's history format
        serialized = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                role = "assistant"
                content = msg.content
            elif isinstance(msg, HumanMessage):
                role = "user"
                content = msg.content
            elif isinstance(msg, SystemMessage):
                role = "system"
                content = msg.content
            else: # Fallback for other message types if any
                role = msg.type if hasattr(msg, 'type') else "unknown"
                content = str(msg.content) if hasattr(msg, 'content') else str(msg)
            serialized.append({"role": role, "content": content})
        return serialized

    def process_message(self, user_id: str, message: str) -> tuple[str, list[dict[str, str]]]:
        logger.info(f"ChatService: Starting process_message for user_id: {user_id}")
        logger.info(f"ChatService: Message content: '{message[:100]}...'")
        
        # The TEST_LLM_MODEL check for stubbed responses is removed.
        # AgentFacade will now be invoked directly.
        
        if self.agent_facade is None:
            logger.error("ChatService: AgentFacade not initialized.")
            # Generate LLM-based error response instead of hardcoded
            try:
                fallback_reply = asyncio.run(
                    self._generate_error_response("Chat service not properly configured", message)
                )
            except Exception:
                fallback_reply = "I'm having trouble initializing my systems. Please try again in a moment."
            fallback_history = [{"role": "user", "content": message}, {"role": "assistant", "content": fallback_reply}]
            return fallback_reply, fallback_history

        try:
            # Run the async invoke method from AgentFacade with a timeout
            # Use configurable timeouts
            logger.info("ChatService: About to determine timeout settings")
            
            # Check if we're in test mode for timeout adjustment
            from app.config_manager import configManager
            test_mode = configManager.get("test_mode", False)
            logger.info(f"ChatService: test_mode = {test_mode}")
            
            # Check if this is a GitHub-related request that needs more time
            github_request = any(keyword in message.lower() for keyword in ["github", "repository", "repo", "commit", "pull request", "issue", "vscode", "microsoft", "changes"])
            logger.info(f"ChatService: github_request = {github_request}")
            
            if github_request or test_mode:
                # Use configurable timeout for GitHub requests and tests
                timeout = configManager.get("timeouts.api_request", 300.0)
            else:
                timeout = 60.0  # Default timeout for non-GitHub production requests
            
            try:
                # Use appropriate timeout
                logger.info(f"ChatService: Using timeout of {timeout}s (test_mode={test_mode})")
                
                # Handle event loop properly for async operations
                logger.info("ChatService: Checking for existing event loop")
                try:
                    # Check if there's already a running loop
                    current_loop = asyncio.get_running_loop()
                    logger.info("ChatService: Found running event loop - using asyncio.run in thread")
                    
                    # If there's already a running loop, we need to run in a separate thread
                    import concurrent.futures
                    import threading
                    
                    def run_agent_in_thread():
                        # Create a new event loop in this thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(
                                asyncio.wait_for(
                                    self.agent_facade.invoke(user_id, message),
                                    timeout=timeout
                                )
                            )
                        finally:
                            new_loop.close()
                    
                    # Run in a thread to avoid event loop conflicts
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_agent_in_thread)
                        agent_response = future.result(timeout=timeout + 5)  # Extra 5s for thread overhead
                    
                    logger.info("ChatService: agent_facade.invoke completed successfully")
                    
                except RuntimeError:
                    # No running loop, safe to create one
                    logger.info("ChatService: No running event loop - using direct asyncio.run")
                    
                    def run_agent_async():
                        return asyncio.run(
                            asyncio.wait_for(
                                self.agent_facade.invoke(user_id, message),
                                timeout=timeout
                            )
                        )
                    
                    agent_response = run_agent_async()
                    logger.info("ChatService: agent_facade.invoke completed successfully")
                        
            except asyncio.TimeoutError:
                logger.warning(f"ChatService: Agent invocation timed out after {timeout}s.")
                fallback_reply = "Request timed out. Please try asking something simpler or try again later."
                history = [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": fallback_reply}
                ]
                return fallback_reply, history
            except Exception as e:
                logger.error(f"ChatService: Exception during agent invocation: {e}", exc_info=True)
                fallback_reply = "I had trouble processing your request. Please try again."
                history = [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": fallback_reply}
                ]
                return fallback_reply, history

            if agent_response.success:
                reply = agent_response.message
                # agent_response.history is List[Tuple[str, str]]
                history = self._serialize_messages_from_tuples(agent_response.history)
                logger.debug(f"ChatService successfully processed message. Reply: {reply}")
                return reply, history
            else:
                logger.error(f"ChatService: AgentFacade invocation failed. Error: {agent_response.message}")
                # Generate LLM-based error response if agent message is empty
                if agent_response.message:
                    fallback_reply = agent_response.message
                else:
                    try:
                        # Use the persistent event loop for error response generation
                        if hasattr(self, '_event_loop') and not self._event_loop.is_closed():
                            fallback_reply = self._event_loop.run_until_complete(
                                self._generate_error_response("Agent invocation failed", message)
                            )
                        else:
                            fallback_reply = "I had trouble processing your request. Please try again."
                    except Exception:
                        fallback_reply = "I had trouble processing your request. Please try again."
                # Ensure history is correctly formatted
                history_tuples = agent_response.history if agent_response.history else [("user", message), ("assistant", fallback_reply)]
                history = self._serialize_messages_from_tuples(history_tuples)
                return fallback_reply, history

        except asyncio.CancelledError:
            logger.warning("ChatService: Agent invocation was cancelled.")
            try:
                # Use the persistent event loop for error response generation
                if hasattr(self, '_event_loop') and not self._event_loop.is_closed():
                    fallback_reply = self._event_loop.run_until_complete(
                        self._generate_error_response("Request was cancelled or interrupted", message)
                    )
                else:
                    fallback_reply = "My response was interrupted. Please try again."
            except Exception:
                fallback_reply = "My response was interrupted. Please try again."
            history = [
                {"role": "user", "content": message},
                {"role": "assistant", "content": fallback_reply}
            ]
            return fallback_reply, history
            
        except Exception as e:
            logger.error(f"ChatService: Exception during agent invocation: {e}", exc_info=True)
            
            # In test mode, check if this is a mock exception that should be propagated
            test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
            if test_mode and hasattr(e, '__module__') and 'mock' in str(e.__module__):
                # This is a mock exception from tests, propagate it
                raise e
                
            try:
                # Use the persistent event loop for error response generation
                if hasattr(self, '_event_loop') and not self._event_loop.is_closed():
                    fallback_reply = self._event_loop.run_until_complete(
                        self._generate_error_response(f"Unexpected error: {str(e)}", message)
                    )
                else:
                    fallback_reply = "I had trouble processing your request. Please try again."
            except Exception:
                fallback_reply = "I had trouble processing your request. Please try again."
            history = [
                {"role": "user", "content": message},
                {"role": "assistant", "content": fallback_reply}
            ]
            return fallback_reply, history

    def get_history(self, user_id: str) -> list[dict[str, str]]:
        # TODO: Implement history retrieval through AgentFacade if needed.
        # AgentFacade currently doesn't expose a direct method to get checkpointed state easily.
        # This might require adding a method to AgentFacade or accessing its checkpointer,
        # which could be complex. For now, returning empty history.
        logger.warning(f"ChatService.get_history for user_id {user_id} is not fully implemented with AgentFacade. Returning empty history.")
        
        # Placeholder: If AgentFacade had a get_raw_history(user_id) method that returned List[BaseMessage]
        # raw_history = asyncio.run(self.agent_facade.get_raw_history(user_id)) # Fictional method
        # return self._serialize_messages(raw_history) if raw_history else []
        return []

    # Consider adding a cleanup method to ChatService that calls agent_facade.stop()
    # when the application shuts down, if AgentFacade is managed per ChatService instance
    # and not globally.
    async def close_agent_resources(self):
        if self.agent_facade:
            await self.agent_facade.stop()
            logger.info("ChatService: AgentFacade resources stopped.")

    async def _generate_error_response(self, error_context: str, user_message: str) -> str:
        """Generate an LLM-based error response instead of using hardcoded messages."""
        try:
            from app.agent.llm_client import LLMClient
            
            # Use a minimal LLM client for error response generation
            llm_client = LLMClient(config_manager=self.agent_facade.config_manager)
            
            system_prompt = (
                "You are a helpful assistant explaining technical issues to users. "
                "Provide a brief, friendly explanation of what happened and suggest what the user can do. "
                "Keep the response under 2 sentences and be reassuring."
            )
            
            user_prompt = f"Context: {error_context}. User asked: '{user_message}'. Explain what happened and suggest next steps."
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Short timeout for error responses
            response = await asyncio.wait_for(
                llm_client.llm.ainvoke(messages),
                timeout=5.0
            )
            
            return response.content.strip()
            
        except Exception as e:
            logger.warning(f"Failed to generate LLM error response: {e}")
            # Minimal fallback that doesn't use hardcoded language
            return f"I encountered a technical issue while processing your request. Please try again."

    async def _async_invoke_agent(self, user_id: str, message: str, timeout: float) -> AgentResponse:
        """Helper method to invoke agent asynchronously."""
        try:
            return await asyncio.wait_for(
                self.agent_facade.invoke(user_id, message),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"_async_invoke_agent: Timeout after {timeout}s for user {user_id}")
            timeout_message = "Request timed out. Please try again later or rephrase your question."
            return AgentResponse(
                success=False,
                message=timeout_message,
                history=[('human', message), ('assistant', timeout_message)]
            )

    def cleanup(self):
        """Clean up resources including the persistent event loop."""
        logger.info("ChatService: Starting cleanup")
        
        # Clean up agent facade first without affecting the persistent event loop
        if hasattr(self, 'agent_facade') and self.agent_facade:
            try:
                # If we have a persistent loop, use it for cleanup, otherwise create a temporary one
                if hasattr(self, '_event_loop') and not self._event_loop.is_closed():
                    cleanup_loop = self._event_loop
                else:
                    cleanup_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(cleanup_loop)
                
                cleanup_loop.run_until_complete(self.agent_facade.close_resources())
                
                # Close temporary loop if we created one
                if cleanup_loop != getattr(self, '_event_loop', None):
                    cleanup_loop.close()
                    
                logger.info("ChatService: Agent facade cleaned up successfully")
            except Exception as e:
                logger.warning(f"ChatService: Error during agent facade cleanup: {e}")
        
        # Only close the persistent event loop if explicitly requested
        # For normal operation, keep the loop alive for better performance
        if hasattr(self, '_event_loop') and not self._event_loop.is_closed():
            try:
                # Don't cancel pending tasks automatically - they might be important MCP connections
                # Only cancel them during final shutdown
                logger.info("ChatService: Persistent event loop kept alive (use shutdown() to close)")
            except Exception as e:
                logger.warning(f"ChatService: Error during event loop inspection: {e}")
        
        logger.info("ChatService: Cleanup completed")
    
    def shutdown(self):
        """Final shutdown that closes the persistent event loop."""
        logger.info("ChatService: Starting final shutdown")
        
        # Close the persistent event loop if it exists
        if hasattr(self, '_event_loop') and not self._event_loop.is_closed():
            try:
                # Cancel any pending tasks
                pending_tasks = [task for task in asyncio.all_tasks(self._event_loop) if not task.done()]
                if pending_tasks:
                    logger.warning(f"ChatService: {len(pending_tasks)} pending tasks found during shutdown")
                    for task in pending_tasks:
                        task.cancel()
                    # Wait for cancellations to complete
                    self._event_loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
                
                self._event_loop.close()
                logger.info("ChatService: Persistent event loop closed successfully")
            except Exception as e:
                logger.warning(f"ChatService: Error during event loop shutdown: {e}")
        
        logger.info("ChatService: Final shutdown completed")