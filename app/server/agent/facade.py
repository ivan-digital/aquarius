# app/server/agent/facade.py
from app.server.agent.tools.code.python import executePython
from app.server.agent.tools.search.arxiv import ArxivSearch
from app.server.agent.tools.search.github import GithubSearch
from app.server.agent.tools.search.google import googleSearcher
from app.server.agent.tools.search.reddit import redditSearcher


class ToolsFacade:
    def __init__(self):
        self.search_tools = [
            # redditSearcher,
            googleSearcher,
            # ArxivSearch.search
        ]
        self.code_tools = [
            executePython,
            GithubSearch.search_and_enrich,
        ]

    @property
    def available_tools(self):
        return self.search_tools + self.code_tools
