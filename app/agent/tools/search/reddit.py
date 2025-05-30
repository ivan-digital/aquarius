import praw
import datetime
import os

from app.config_manager import configManager


def format_results_as_markdown(results: list) -> str:
    """
    Format the search results as Markdown to provide context for an LLM.

    Parameters:
        results (list): A list of dictionaries containing post details.

    Returns:
        str: A markdown formatted string representation of the search results.
    """
    md = "# Reddit Search Results\n\n"
    for post in results:
        created_str = datetime.datetime.utcfromtimestamp(
            post['created_utc']
        ).strftime('%Y-%m-%d %H:%M:%S UTC')
        md += f"## {post['title']}\n"
        md += f"- **Subreddit:** {post['subreddit']}\n"
        md += f"- **Score:** {post['score']}\n"
        md += f"- **Created:** {created_str}\n"
        md += f"- **URL:** [Link]({post['url']})\n\n"
    return md


class RedditSearch:
    """
    A service to search Reddit posts using the Reddit API.
    """

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize the Reddit client.

        Parameters:
            client_id (str): Your Reddit application's client ID.
            client_secret (str): Your Reddit application's client secret.
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
        )

    def search(self, query: str, subreddit: str = 'all'):
        """
        Search for posts on Reddit matching the query.

        Parameters:
            query (str): The search query.
            subreddit (str): The subreddit to search in. Default is 'all'.

        Returns:
            list: A list of dictionaries containing post details.
        """
        results = []
        try:
            for submission in self.reddit.subreddit(subreddit).search(query, limit=10):
                results.append({
                    'id': submission.id,
                    'title': submission.title,
                    'url': submission.url,
                    'score': submission.score,
                    'subreddit': submission.subreddit.display_name,
                    'created_utc': submission.created_utc
                })
        except Exception as e:
            print("Error while searching Reddit:", e)
        return results


# Conditionally initialize the RedditSearch service
app_component = os.environ.get("APP_COMPONENT")
redditSearcherService = None
if app_component == "api":
    reddit_app_id = configManager.get("reddit_app_id")
    reddit_secret = configManager.get("reddit_secret")
    if reddit_app_id and reddit_secret:
        redditSearcherService = RedditSearch(
            client_id=reddit_app_id,
            client_secret=reddit_secret
        )
    else:
        print("Reddit API credentials not found. Reddit search tool will not be available.")
else:
    print(f"Skipping RedditSearch initialization for APP_COMPONENT='{app_component}'.")


def redditSearcher(query, subreddit="all"):
    """
    Search for posts on Reddit matching the query.
    """
    if redditSearcherService:
        return redditSearcherService.search(query, subreddit)
    return "Reddit search tool is not available in this component."
