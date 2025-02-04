import os
import time

import gradio as gr

# Import from new services
from services.token_service import store_token
from services.github_service import list_repos, clone_repo
from services.local_repo_service import list_local_cloned_repos

from app.settings import get_github_token

current_status = "Idle"


def get_token_placeholder():
    return "*****" if get_github_token() else ""


def on_save_token(token: str):
    global current_status
    txt = token.strip()
    if not txt:
        current_status = "No new token entered; keeping the current token."
        return current_status
    if txt == "*****":
        current_status = "Token unchanged."
        return current_status
    current_status = store_token(txt)
    return current_status


def on_list_repos():
    # Example: Keep track of status messages
    global current_status
    current_status = "Fetching repos..."

    # Call your existing function that returns repos or an error
    result = list_repos("")  # empty => uses saved token

    # If there's an error, return an empty dropdown + status text
    if "error" in result:
        current_status = result["error"]
        return (
            gr.update(choices=[], value=None),
            f"**Status**: {current_status}"
        )

    # Otherwise, populate the dropdown with repo full_names
    repos = result["repos"]
    current_status = f"Found {len(repos)} repos"
    repo_names = [r["full_name"] for r in repos]

    return (
        gr.update(choices=repo_names, value=None),
        f"**Status**: {current_status}"
    )


def on_clone_repo(selected_repo: str):
    global current_status
    if not selected_repo:
        current_status = "Error: No repo selected."
        return f"**Status**: {current_status}"

    current_status = f"Cloning {selected_repo}..."
    result = clone_repo("", selected_repo)
    current_status = result
    return f"**Status**: {current_status}"


def on_list_local_repos():
    repos = list_local_cloned_repos()
    return gr.update(choices=repos)


