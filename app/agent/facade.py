import logging

from langchain.tools import tool
from pydantic import BaseModel
from typing import Dict, Any, List

from app.agent.tools.search.reddit import redditSearcher
from app.agent.tools.search.google import googleSearcher
from app.agent.tools.search.arxiv import ArxivSearch
from app.agent.tools.search.github import GithubSearch
from app.agent.tools.code.python import executePython

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SearchInput(BaseModel):
    """Pydantic schema for any generic search tool."""
    query: str

@tool(
    "redditSearcher",
    description="Searches Reddit for the given query and returns relevant results."
)
def reddit_searcher(input: SearchInput) -> Dict[str, Any]:
    """
    Calls the underlying redditSearcher function, returning a dictionary of results.
    """
    logger.info("reddit_searcher called with query: %s", input.query)
    result = redditSearcher(query={"query": input.query})
    logger.info("reddit_searcher result count: %d", len(result.get('data', [])) if isinstance(result, dict) else 0)
    return result

@tool(
    "googleSearcher",
    description="Performs a Google search for the given query."
)
def google_searcher(input: SearchInput) -> str:
    """
    Calls the underlying googleSearcher function, returning a dictionary of results.
    """
    logger.info("google_searcher called with query: %s", input.query)
    result = googleSearcher(query=input.query)
    logger.info("google_searcher result length: %d characters", len(str(result)))
    return result

@tool(
    "arxivSearch",
    description="Performs an Arxiv.org search for academic papers matching the query."
)
def arxiv_search(input: SearchInput) -> List[Any]:
    """
    Calls the underlying ArxivSearch.search function, returning a list of results.
    """
    logger.info("arxiv_search called with query: %s", input.query)
    result = ArxivSearch.search(query=input.query)
    logger.info("arxiv_search found %d entries", len(result))
    return result

@tool(
    "githubSearchEnrich",
    description="Searches GitHub repos for the given query and enriches results with additional data."
)
def github_search_enrich(input: SearchInput) -> Dict[str, Any]:
    """
    Calls the underlying GithubSearch.search_and_enrich function, returning a dictionary of results.
    """
    logger.info("github_search_enrich called with query=%s",
                input.query)
    # build exactly the dict that search_and_enrich expects
    payload = {
        "query": input.query
    }
    # instantiate your service and pass the dict
    service = GithubSearch()
    result = service.search_and_enrich(payload)
    logger.info("github_search_enrich result count: %d repos", len(result.get('repos', [])) if isinstance(result, dict) else 0)
    return result

class PythonCodeInput(BaseModel):
    """Schema for code execution tool."""
    code: str

@tool(
    "executePython",
    description="Executes the given Python code in a sandboxed environment, returning stdout/stderr."
)
def execute_python(code: PythonCodeInput) -> Dict[str, Any]:
    """
    Calls the underlying executePython function, returning a dictionary with execution results.
    """
    logger.info("execute_python called with code length: %d characters", len(code.code))
    result = executePython(code=code.code)
    logger.info("execute_python execution success: %s", 'success' if result.get('stdout') else 'no output')
    return result

class ToolsFacade:
    """
    A lightweight facade that returns lists of search or code tools
    so you can manage them easily.
    """
    def __init__(self):
        self._search_tools = [
            reddit_searcher,
            google_searcher,
            arxiv_search,
            github_search_enrich
        ]
        self._code_tools = [execute_python,github_search_enrich]
        logger.info(
            "ToolsFacade initialized with %d search tools and %d code tools",
            len(self._search_tools), len(self._code_tools)
        )

    @property
    def search_tools(self) -> List:
        return self._search_tools

    @property
    def code_tools(self) -> List:
        return self._code_tools

    @property
    def all_tools(self) -> List:
        return self._search_tools + self._code_tools
