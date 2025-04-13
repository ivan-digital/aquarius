import requests
from pydantic import BaseModel

from app.config_manager import configManager
from app.server.web_driver import webDriverService


class GoogleSearch:
    def __init__(self, configManager, webDriver):
        self.api_key = configManager.config["google_key"]
        self.cse_id = configManager.config["google_cx"]
        self.service_url = "https://www.googleapis.com/customsearch/v1"
        self.webDriver = webDriver;

    def search(self, query):
        """
        Performs a search using the Google Custom Search JSON API.
        """
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query
        }
        try:
            response = requests.get(self.service_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"Other error occurred: {err}")
        return None

    def format_results(self, search_response, query):
        """
        Formats the search results into a markdown string. If an enrichment function is provided,
        it is called for each result link to append additional content.
        """
        md = f"# Google Search Results for \"{query}\"\n\n"
        if search_response is None:
            md += "No results found."
            return md

        search_info = search_response.get("searchInformation", {})
        formatted_total = search_info.get("formattedTotalResults", "N/A")
        formatted_time = search_info.get("formattedSearchTime", "N/A")
        md += f"**Total Results:** {formatted_total}  •  **Search Time:** {formatted_time} seconds\n\n"

        items = search_response.get("items", [])
        if not items:
            md += "No results found."
            return md

        for item in items:
            title = item.get("title", "No Title")
            snippet = item.get("snippet", "No description available.")
            link = item.get("link", "#")
            md += f"### [{title}]({link})\n\n"
            md += f"{snippet}\n\n"

            if self.webDriver is not None:
                try:
                    enriched_content = self.webDriver.query(link)
                    md += enriched_content
                except Exception as e:
                    md += f"**Page Content:** Unable to retrieve page content. Error: {e}\n\n"

            md += "---\n\n"
        return md

    def search_formatted(self, query):
        """
        Performs a search and returns a formatted markdown string. An optional enrichment function
        can be provided to add content from each result link.
        """
        search_response = self.search(query)
        return self.format_results(search_response, query)


googleSearcherService = GoogleSearch(configManager=configManager, webDriver=webDriverService)


class GoogleSearchInput(BaseModel):
    query: str


def googleSearcher(input_data: GoogleSearchInput) -> str:
    """
    Using structured input with a 'query' field.
    """
    return googleSearcherService.search(input_data.query)
