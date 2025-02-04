import os
import subprocess
import requests
from app.settings import get_github_token

def list_repos(token: str):
    """
    Use the provided token (or fallback) to call GitHub and list repos.
    Return a dict:
      { "repos": [...list of repos...] } or { "error": "msg" }
    """
    if not token:
        token = get_github_token()
        if not token:
            return {"error": "No GitHub token found."}

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}"
    }
    url = "https://api.github.com/user/repos"
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return {"error": f"GitHub API error: {resp.status_code} {resp.text}"}
        data = resp.json()
        return {"repos": data}
    except Exception as e:
        return {"error": str(e)}


def clone_repo(token: str, repo_full_name: str):
    """
    Clone a repo by its 'owner/repo' name into 'cloned_repos' directory.
    Return a status string for display.
    """
    if not token:
        token = get_github_token()
        if not token:
            return "No GitHub token found; cannot clone."

    if not repo_full_name:
        return "No repo name provided."

    clone_url = f"https://{token}:x-oauth-basic@github.com/{repo_full_name}.git"
    local_path = os.path.join("cloned_repos", repo_full_name.replace("/", "_"))
    os.makedirs("cloned_repos", exist_ok=True)

    if os.path.exists(local_path):
        return f"'{repo_full_name}' is already cloned at {local_path}."

    try:
        subprocess.run(["git", "clone", clone_url, local_path], check=True)
        return f"Cloned '{repo_full_name}' into {local_path}"
    except subprocess.CalledProcessError as e:
        return f"Error cloning: {str(e)}"