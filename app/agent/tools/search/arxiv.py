import re
import requests
from bs4 import BeautifulSoup


def format_results_as_markdown(results: list) -> str:
    """
    Format the arXiv search results as Markdown.

    Parameters:
        results (list): A list of dictionaries containing paper details.

    Returns:
        str: A Markdown-formatted string representation of the search results.
    """
    md = "# arXiv Search Results\n\n"
    for i, paper in enumerate(results, 1):
        md += f"## {i}. {paper['title']}\n"
        md += f"**Authors:** {paper['authors']}\n\n"
        md += f"**Abstract:** {paper['abstract']}\n\n"
        md += f"**Link:** [View Paper]({paper['link']})\n\n"
    return md


class ArxivSearch:
    """
    A service to search arXiv papers using requests and BeautifulSoup.
    """
    base_url = "https://arxiv.org/search/"
    valid_sizes = [25, 50, 100, 200]

    @staticmethod
    def search(query: str) -> list:
        """
        Search for scientific papers on arXiv matching the query.

        Parameters:
            query (str): The search query.

        Returns:
            list: A list of dictionaries containing paper details.
        """
        size = 25
        # Validate and adjust the size if necessary.
        if size not in ArxivSearch.valid_sizes:
            size = min(ArxivSearch.valid_sizes, key=lambda x: abs(x - size))
        results = []
        start = 0
        max_results = min(25, 100)

        while len(results) < max_results:
            params = {
                "searchtype": "all",
                "query": query,
                "abstracts": "show",
                "order": "",
                "size": str(size),
                "start": str(start)
            }
            try:
                response = requests.get(ArxivSearch.base_url, params=params)
                soup = BeautifulSoup(response.content, 'html.parser')
                papers = soup.find_all("li", class_="arxiv-result")
                if not papers:
                    break

                for paper in papers:
                    if len(results) >= max_results:
                        break

                    title = paper.find("p", class_="title").text.strip()
                    authors = paper.find("p", class_="authors").text.strip()
                    authors = re.sub(r'^Authors:\s*', '', authors)
                    authors = re.sub(r'\s+', ' ', authors).strip()

                    abstract = paper.find("span", class_="abstract-full").text.strip()
                    abstract = abstract.replace("△ Less", "").strip()

                    link = paper.find("p", class_="list-title").find("a")["href"]

                    results.append({
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "link": link
                    })

                start += size

            except Exception as e:
                print(f"Error during arXiv search: {e}")
                break

        return results


# Expose a tool named 'search_arxiv' for the LangGraph agent

def search_arxiv(query: str, max_results: int = 5) -> str:
    """
    Search arXiv for papers matching the query and return Markdown-formatted results.
    """
    results = ArxivSearch.search(query)
    return format_results_as_markdown(results)

# Attach a name attribute for tool discovery
search_arxiv.name = "search_arxiv"
search_arxiv.description = "Search arXiv for papers matching the query and return Markdown-formatted results."
search_arxiv.args_schema = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "max_results": {"type": "integer", "default": 5}
    },
    "required": ["query"]
}
