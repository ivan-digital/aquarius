import logging
import uuid
import asyncio

from app.server.models import AgentResponse
from app.agent.llm_client import LLMClient
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage, ToolMessage
from langgraph.prebuilt.chat_agent_executor import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# Import MCP client with fallback
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError as e:
    MultiServerMCPClient = None

logger = logging.getLogger(__name__)


class AgentFacade:
    """Simplified GitHub-focused agent facade using built-in ReAct agent."""
    
    def __init__(self, config_manager=None):
        from app.config_manager import ConfigManager
        
        if config_manager is None:
            self.config_manager = ConfigManager()
            logger.info("AgentFacade initialized with a default ConfigManager instance.")
        else:
            self.config_manager = config_manager
            logger.info("AgentFacade initialized with a provided ConfigManager instance.")
        
        # Per-request clients (no longer persistent to avoid event loop issues)
        self._github_token = None
        self._initialization_lock = asyncio.Lock()
        
        logger.info("AgentFacade instance created. Both LLM and MCP clients will be created per-request.")

    async def _initialize_dependencies_if_needed(self):
        """Initialize GitHub token if needed."""
        # Store GitHub token for per-request client creation
        if self._github_token is None:
            self._github_token = self.config_manager.get("github_token")
            if self._github_token:
                logger.info("AgentFacade: GitHub token found and stored for per-request clients.")
            else:
                logger.warning("AgentFacade: GitHub token not found. GitHub tools will be unavailable.")

    async def _create_per_request_llm_client(self):
        """Create a fresh LLM client for this request to avoid event loop issues."""
        try:
            logger.info("AgentFacade: Creating fresh LLM client for this request...")
            llm_client = LLMClient(config_manager=self.config_manager)
            logger.info("AgentFacade: Fresh LLM client created successfully.")
            return llm_client
        except Exception as e:
            logger.error(f"AgentFacade: Failed to create per-request LLM client: {e}", exc_info=True)
            return None
    async def _create_per_request_mcp_client(self):
        """Create a fresh MCP client for this request to avoid event loop issues."""
        if not self._github_token or MultiServerMCPClient is None:
            logger.info("AgentFacade: No GitHub token or MCP client available, returning empty tools.")
            return None, []
        
        try:
            container_name = f"aquarius-github-mcp-{uuid.uuid4().hex[:8]}"
            
            # Use exact same config as working debug script
            mcp_servers_config = {
                "github": {
                    "command": "docker",
                    "args": [
                        "run", "-i", "--rm", "--name", container_name,
                        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                        "-e", "FASTMCP_LOG_LEVEL=DEBUG",
                        "ghcr.io/github/github-mcp-server"
                    ],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": self._github_token,
                        "FASTMCP_LOG_LEVEL": "DEBUG"
                    },
                }
            }
            
            # Create and initialize MCP client for this request
            mcp_manager = MultiServerMCPClient(mcp_servers_config)
            
            # Initialize with configurable timeout
            mcp_timeout = self.config_manager.get("timeouts", {}).get("mcp_init", 90)
            mcp_client = await asyncio.wait_for(
                mcp_manager.__aenter__(),
                timeout=float(mcp_timeout)
            )
            
            # Get tools from the fresh client
            tools = await self._get_github_tools_from_client(mcp_client)
            
            logger.info(f"AgentFacade: Created fresh MCP client with {len(tools)} tools for this request.")
            return mcp_manager, tools
                
        except asyncio.TimeoutError:
            logger.warning(f"AgentFacade: Per-request MCP client initialization timed out after {mcp_timeout} seconds.")
            return None, []
        except Exception as e:
            logger.warning(f"AgentFacade: Failed to create per-request MCP client: {e}")
            return None, []

    async def _cleanup_per_request_mcp(self, mcp_manager):
        """Clean up per-request MCP resources with proper error handling."""
        if mcp_manager:
            try:
                # Use configurable timeout to prevent hanging during cleanup
                cleanup_timeout = self.config_manager.get("timeouts", {}).get("mcp_cleanup", 20)
                # Create a new task for cleanup to avoid cancel scope issues
                cleanup_task = asyncio.create_task(
                    mcp_manager.__aexit__(None, None, None)
                )
                await asyncio.wait_for(cleanup_task, timeout=float(cleanup_timeout))
                logger.info("AgentFacade: Per-request MCP manager cleaned up successfully")
            except asyncio.TimeoutError:
                logger.warning(f"AgentFacade: Per-request MCP cleanup timed out after {cleanup_timeout} seconds")
                # Cancel the cleanup task if it timed out
                if 'cleanup_task' in locals():
                    cleanup_task.cancel()
                    try:
                        await cleanup_task
                    except asyncio.CancelledError:
                        pass
            except Exception as e:
                logger.warning(f"AgentFacade: Error cleaning up per-request MCP manager: {e}")

    async def _get_github_tools_from_client(self, mcp_client) -> list:
        """Get essential GitHub tools from the provided MCP client (filtered for performance)."""
        if not mcp_client:
            logger.info("AgentFacade: No MCP client provided, returning empty tools list.")
            return []        
        try:
            # Get all available tools
            all_tools = mcp_client.get_tools()
            if not all_tools:
                logger.info("AgentFacade: No tools available from MCP client.")
                return []
            
            # Enhanced tool selection for better repository content access
            # Based on the 51 available tools, select the most useful ones for exploration
            priority_tools = [
                # Core repository exploration
                'search_repositories', 'get_file_contents', 'search_code',
                # Commit and history access  
                'get_commit', 'list_commits',
                # Branch and structure exploration
                'list_branches', 'list_tags',
                # Issues and PRs for project understanding
                'get_issue', 'list_issues', 'get_pull_request', 'list_pull_requests',
                # Pull request details for code review context
                'get_pull_request_diff', 'get_pull_request_files',
                # User and metadata
                'get_me', 'search_users'
            ]
            
            selected_tools = []
            tool_names_selected = set()
            
            # First pass: select exact priority tools
            for tool in all_tools:
                tool_name = getattr(tool, 'name', str(tool))
                if tool_name in priority_tools:
                    selected_tools.append(tool)
                    tool_names_selected.add(tool_name)
                    logger.debug(f"AgentFacade: Selected priority tool: {tool_name}")
            
            # Second pass: add useful tools if we have room (limit to 18 total for good performance)
            additional_patterns = ['get_pull_request_', 'get_tag', 'search_']
            for tool in all_tools:
                if len(selected_tools) >= 18:
                    break
                    
                tool_name = getattr(tool, 'name', str(tool))
                if (tool_name not in tool_names_selected and 
                    any(pattern in tool_name for pattern in additional_patterns)):
                    selected_tools.append(tool)
                    tool_names_selected.add(tool_name)
                    logger.debug(f"AgentFacade: Selected additional tool: {tool_name}")
            
            logger.info(f"AgentFacade: Using {len(selected_tools)} GitHub tools for enhanced repository access (filtered from {len(all_tools)} total).")
            if selected_tools:
                tool_names = [getattr(tool, 'name', str(tool)) for tool in selected_tools]
                logger.info(f"AgentFacade: Selected tools: {', '.join(sorted(tool_names))}")
            
            return selected_tools
            
        except Exception as e:
            logger.error(f"AgentFacade: Error fetching tools from MCP client: {e}", exc_info=True)
            return []

    async def _initialize_basic_setup_if_needed(self):
        """Initialize basic setup if needed."""
        async with self._initialization_lock:
            logger.info("AgentFacade: Ensuring basic dependencies are ready...")
            await self._initialize_dependencies_if_needed()
            logger.info("AgentFacade: Basic setup completed. Per-request clients will be created as needed.")

    async def _create_per_request_agent(self, llm_client, tools: list):
        """Create a ReAct agent for this specific request with the provided LLM client and tools."""
        if llm_client is None or llm_client.llm is None:
            logger.error("AgentFacade: LLM client not available for agent creation.")
            return None

        # Create system prompt for GitHub assistant (enhanced for better tool usage)
        system_prompt = (
            "You are a GitHub repository analysis assistant with access to powerful GitHub exploration tools. "
            "You can search repositories, read files, examine commits, analyze pull requests, and explore repository structure.\n\n"
            
            "CRITICAL INSTRUCTIONS FOR TOOL USAGE:\n"
            "1. ALWAYS use available tools when asked about GitHub repositories, commits, issues, or code.\n"
            "2. When you receive data from tools, ANALYZE and SUMMARIZE it - do NOT treat it as user input.\n"
            "3. NEVER make up commit hashes, usernames, dates, or repository data - only use actual tool responses.\n"
            "4. If tools return empty results, explicitly state that no data was found.\n"
            "5. Process tool responses to provide meaningful insights, summaries, and analysis.\n\n"
            
            "RESPONSE FORMATTING:\n"
            "- When summarizing commits: Include commit hashes, authors, dates, and clear descriptions of changes\n"
            "- When analyzing repositories: Provide structure overview, recent activity, and key insights\n"
            "- When examining issues/PRs: Summarize status, key discussions, and recent updates\n"
            "- Always present information in a clear, organized manner\n\n"
            
            "EXAMPLE GOOD RESPONSES:\n"
            "✓ 'Based on the recent commits I found, here are the latest updates to PyTorch...'\n"
            "✓ 'I searched the repository and found these key files and directories...'\n"
            "✓ 'The repository has X open issues, with recent activity focused on...'\n\n"
            
            "AVOID THESE RESPONSES:\n"
            "✗ 'The data you provided shows...' (I fetched the data, not the user)\n"
            "✗ 'To analyze this JSON, you could...' (I should analyze it myself)\n"
            "✗ Generic advice without using actual GitHub data\n\n"
            
            "Remember: You are an active assistant that uses tools to gather and analyze GitHub data, "
            "not a passive helper explaining how users should analyze data themselves."
        )

        try:
            # Create ReAct agent with GitHub tools for this request
            agent = create_react_agent(
                model=llm_client.llm,
                tools=tools,
                checkpointer=MemorySaver()
            )
            logger.info(f"AgentFacade: Per-request ReAct agent created successfully with {len(tools)} tools.")
            return agent, system_prompt
        except Exception as e:
            logger.error(f"AgentFacade: Error creating per-request ReAct agent: {e}", exc_info=True)
            return None, None

    async def invoke(self, user_id: str, message: str, progress_callback=None) -> AgentResponse:
        """Process user message through the GitHub-focused ReAct agent with per-request clients."""
        import time
        start_time = time.time()
        
        logger.info(f"AgentFacade: Processing GitHub query for user {user_id}")
        
        if progress_callback:
            await progress_callback("Starting basic initialization", time.time() - start_time)
        
        try:
            await self._initialize_basic_setup_if_needed()
            if progress_callback:
                await progress_callback("Basic initialization completed", time.time() - start_time)
        except Exception as e:
            logger.error(f"AgentFacade: Critical error during basic initialization: {e}", exc_info=True)
            error_message = await self._generate_error_response(
                f"Basic initialization failed: {str(e)}", message
            )
            return AgentResponse(success=False, message=error_message, history=[('human', message)])

        # Create per-request clients
        mcp_manager = None
        llm_client = None
        try:
            if progress_callback:
                await progress_callback("Creating fresh LLM client", time.time() - start_time)
            
            # Create fresh LLM client for this request
            llm_client = await self._create_per_request_llm_client()
            if llm_client is None:
                logger.error("AgentFacade: Per-request LLM client could not be created.")
                error_message = await self._generate_error_response(
                    "LLM client could not be created for this request", message
                )
                return AgentResponse(success=False, message=error_message, history=[('human', message)])
            
            if progress_callback:
                await progress_callback("Creating MCP client for this request", time.time() - start_time)
            
            mcp_manager, tools = await self._create_per_request_mcp_client()
            
            if progress_callback:
                await progress_callback("Creating agent with tools", time.time() - start_time)
            
            # Create per-request agent with fresh LLM client and tools
            agent, system_prompt = await self._create_per_request_agent(llm_client, tools)
            
            if agent is None:
                logger.error("AgentFacade: Per-request agent could not be created.")
                error_message = await self._generate_error_response(
                    "Agent could not be created for this request", message
                )
                return AgentResponse(success=False, message=error_message, history=[('human', message)])
        
            # Configure agent execution
            config = {"configurable": {"thread_id": user_id}}
            
            if progress_callback:
                await progress_callback("Preparing agent messages", time.time() - start_time)
            
            # Create messages with system prompt included
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=message))
            
            if progress_callback:
                await progress_callback("Starting agent execution", time.time() - start_time)
            
            # Run the agent with configurable timeout for GitHub operations
            agent_timeout = self.config_manager.get("timeouts", {}).get("llm_request", 300.0)
            result = await asyncio.wait_for(
                agent.ainvoke(
                    {"messages": messages},
                    config=config
                ),
                timeout=float(agent_timeout)  # Use configurable timeout (default 5 minutes)
            )
            
            if progress_callback:
                await progress_callback("Agent execution completed", time.time() - start_time)
            
            # Extract response from agent result
            if "messages" in result and isinstance(result["messages"], list):
                messages = result["messages"]
                
                # Find the last AI message
                final_response = "I processed your request but couldn't generate a response."
                for msg in reversed(messages):
                    # Check both for actual AIMessage instances and mock messages with type="ai"
                    is_ai_message = (isinstance(msg, AIMessage) or 
                                   (hasattr(msg, 'type') and getattr(msg, 'type') == 'ai'))
                    if is_ai_message and getattr(msg, 'content', None):
                        final_response = str(msg.content)
                        break
                
                # Convert messages to history format
                history = []
                for msg in messages:
                    role = getattr(msg, 'type', 'unknown')
                    content = str(getattr(msg, 'content', ''))
                    if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                        content += f" [Used {len(msg.tool_calls)} tool(s)]"
                    history.append((role, content))
                
                return AgentResponse(
                    success=True,
                    message=final_response,
                    history=history
                )
            else:
                logger.warning("AgentFacade: Agent returned unexpected result format")
                error_message = await self._generate_error_response(
                    "Agent returned unexpected result format", message
                )
                return AgentResponse(success=False, message=error_message, history=[('human', message)])
                
        except asyncio.TimeoutError:
            logger.error(f"AgentFacade: Agent execution timed out for user {user_id}")
            # Use hardcoded timeout message to avoid potential issues with _generate_error_response
            timeout_message = "Request timed out. Please try again later or rephrase your question."
            return AgentResponse(success=False, message=timeout_message, history=[('human', message), ('assistant', timeout_message)])
            
        except Exception as e:
            logger.error(f"AgentFacade: Error during agent execution: {e}", exc_info=True)
            error_message = await self._generate_error_response(
                f"Agent execution error: {str(e)}", message
            )
            return AgentResponse(success=False, message=error_message, history=[('human', message)])
        
        finally:
            # Always clean up the per-request clients
            if mcp_manager:
                if progress_callback:
                    await progress_callback("Cleaning up MCP client", time.time() - start_time)
                await self._cleanup_per_request_mcp(mcp_manager)
            
            # LLM client cleanup is automatic through garbage collection
            if progress_callback:
                await progress_callback("Request completed", time.time() - start_time)

    async def _generate_error_response(self, error_context: str, user_message: str) -> str:
        """Generate a helpful error response using a fresh LLM client."""
        try:
            # Create a fresh LLM client for error response to avoid using potentially corrupted instance
            fresh_llm_client = await self._create_per_request_llm_client()
            if fresh_llm_client is None:
                # Fallback to hardcoded message if LLM client creation fails
                if "timeout" in error_context.lower():
                    return "Request timed out. Please try again later or rephrase your question."
                return "I encountered a technical issue. Please try rephrasing your question or try again later."
            
            system_msg = SystemMessage(content=(
                "You are a helpful assistant explaining issues to users. "
                "Provide a brief, friendly explanation and suggest what they can try next. "
                "Keep it under 2 sentences and be encouraging."
            ))
            
            human_msg = HumanMessage(content=f"Context: {error_context}. User asked: '{user_message}'. Explain what happened and suggest next steps.")
            
            response = await asyncio.wait_for(
                fresh_llm_client.llm.ainvoke([system_msg, human_msg]),
                timeout=10.0
            )
            
            return response.content.strip()
            
        except Exception as e:
            logger.warning(f"Failed to generate error response: {e}")
            if "timeout" in error_context.lower():
                return "Request timed out. Please try again later or rephrase your question."
            return "I encountered a technical issue. Please try rephrasing your question or try again later."

    async def close_resources(self):
        """Clean up resources."""
        logger.info("AgentFacade: Closing resources...")
        
        # Clear references (all clients are now per-request)
        self._github_token = None
        
        logger.info("AgentFacade: Resources closed.")

    async def start(self):
        """Initialize basic setup."""
        await self._initialize_basic_setup_if_needed()

    async def stop(self):
        """Stop the agent and clean up."""
        await self.close_resources()
