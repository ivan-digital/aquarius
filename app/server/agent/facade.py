from langchain_core.tools import StructuredTool

from app.server.agent.tools.code.python import executePython
from app.server.agent.tools.search.arxiv import ArxivSearch
from app.server.agent.tools.search.github import GithubSearch
from app.server.agent.tools.search.google import googleSearcher
from app.server.agent.tools.search.reddit import redditSearcher


def _to_structured_tool(td: dict) -> StructuredTool:
    """
    Convert our registry entry into a StructuredTool
    (with name, func, and description).
    """
    return StructuredTool.from_function(
        func=td["fn"],
        name=td["name"],
        description=td["description"]
    )


class ToolsFacade:
    """
    Example ToolsFacade that holds a registry of tool definitions,
    each with a name, category, function, and now a description.
    """

    def __init__(self):
        self._tool_registry = [
            {
                "name": "redditSearcher",
                "category": "search",
                "fn": redditSearcher,
                "description": "Searches Reddit for the given query and returns relevant results."
            },
            {
                "name": "googleSearcher",
                "category": "search",
                "fn": googleSearcher,
                "description": "Performs a Google search using a query. Provide the query as a JSON object with a single field 'query'. "
            },
            {
                "name": "arxivSearch",
                "category": "search",
                "fn": ArxivSearch.search,
                "description": "Performs an Arxiv.org search for academic papers matching the query."
            },
            {
                "name": "githubSearchEnrich",
                "category": "search",
                "fn": GithubSearch.search_and_enrich,
                "description": "Searches GitHub repos for the given keywords and enriches results with additional data."
            },
            {
                "name": "executePython",
                "category": "code",
                "fn": executePython,
                "description": "Executes the given Python code in a sandboxed environment, returning the stdout/stderr."
            },
        ]

    def get_all_tools(self) -> list[StructuredTool]:
        return [_to_structured_tool(td) for td in self._tool_registry]

    def get_tools_by_category(self, category: str) -> list[StructuredTool]:
        return [
            _to_structured_tool(td)
            for td in self._tool_registry
            if td["category"] == category
        ]

    @property
    def search_tools(self) -> list[StructuredTool]:
        return self.get_tools_by_category("search")

    @property
    def code_tools(self) -> list[StructuredTool]:
        return self.get_tools_by_category("code")

    @property
    def tools(self) -> list[StructuredTool]:
        return self.get_all_tools()