import requests
import base64
import time
import html2text

from app.config_manager import configManager


def flatten_enriched_repos_to_string(repos):
    """
    Converts a list of enriched repository dictionaries into a single formatted string.
    """
    flattened = ""
    for repo in repos:
        flattened += f"Repository: {repo.get('full_name', 'N/A')} {repo.get('description', '')}\n"
        flattened += f"HTML URL: {repo.get('html_url', 'N/A')}\n"
        flattened += (f"Stars: {repo.get('stargazers_count', 'N/A')}, "
                      f"Forks: {repo.get('forks_count', 'N/A')}\n")
        readme = repo.get("readme_preview", "No README available")
        if readme is None:
            readme = ""
        flattened += "README Preview:\n" + readme + "\n"
        flattened += "-" * 40 + "\n"
    return flattened


class GithubSearch:

    headers = {"User-Agent": "GithubSearch-App"}
    token = configManager.config.get("github_token")
    if token:
        headers["Authorization"] = f"token {token}"

    def _get(self, url, params=None):
        """
        Helper method to perform GET requests and wait if rate limited.
        """
        while True:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                return response
            elif response.status_code == 403:
                remaining = response.headers.get("X-Ratelimit-Remaining")
                if remaining == "0":
                    reset_time = int(response.headers.get("X-Ratelimit-Reset", 0))
                    wait_seconds = max(0, reset_time - int(time.time()))
                    print(f"Rate limit exceeded. Waiting for {wait_seconds + 1} seconds...")
                    time.sleep(wait_seconds + 1)  # Wait an extra second to be safe.
                    continue
            raise Exception(f"GitHub API returned status code {response.status_code}: {response.text}")

    def search_repositories(self, query, per_page=10, page=1):
        """
        Searches for repositories using the GitHub Search API.
        :param query: The search query string.
        :param per_page: Number of results per page.
        :param page: Page number.
        :return: List of repository objects.
        """
        url = "https://api.github.com/search/repositories"
        params = {"q": query, "per_page": per_page, "page": page}
        response = self._get(url, params)
        data = response.json()
        return data.get("items", [])

    def get_repository_details(self, repo_api_url):
        """
        Retrieves full repository details from its API URL.
        :param repo_api_url: The repository's API endpoint URL.
        :return: Repository details as a JSON dictionary.
        """
        response = self._get(repo_api_url)
        return response.json()

    def get_readme(self, full_name):
        """
        Retrieves and decodes the repository's README.
        :param full_name: The repository full name in 'owner/repo' format.
        :return: Decoded README text or a default message if not available.
        """
        url = f"https://api.github.com/repos/{full_name}/readme"
        try:
            response = self._get(url)
            data = response.json()
            encoded_content = data.get("content", "")
            decoded = base64.b64decode(encoded_content).decode('utf-8')
            h = html2text.HTML2Text()
            h.ignore_links = False
            cleaned = h.handle(decoded)
            return cleaned
        except Exception as e:
            if "404" in str(e):
                return "No README available"
            else:
                return f"Error decoding README: {e}"

    def enrich_repository(self, repo):
        """
        Enriches a single repository object with extra details and a README preview.
        :param repo: The base repository object from search results.
        :return: An enriched repository object.
        """
        full_name = repo.get("full_name")
        details = self.get_repository_details(repo.get("url"))
        enriched_repo = repo.copy()
        if details:
            enriched_repo["stargazers_count"] = details.get("stargazers_count")
            enriched_repo["forks_count"] = details.get("forks_count")
            enriched_repo["open_issues_count"] = details.get("open_issues_count")
        readme = self.get_readme(full_name)
        if readme:
            enriched_repo["readme_preview"] = readme[:2000]
        else:
            enriched_repo["readme_preview"] = None
        enriched_repo["readme"] = readme
        return enriched_repo

    def search_and_enrich(self, input):
        """
            Tool entry point: expects input dict with:
               - 'query' (str)
               - optional 'per_page' (int)
              - optional 'page' (int)
        """

        query = input.get("query")
        per_page = input.get("per_page", 10)
        page = input.get("page", 1)

        repos = self.search_repositories(query=query, per_page=per_page, page=page)
        enriched = [self.enrich_repository(r) for r in repos]

        return flatten_enriched_repos_to_string(enriched)