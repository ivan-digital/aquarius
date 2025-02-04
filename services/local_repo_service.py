import os

def list_local_cloned_repos():
    """
    Return a list of directories under 'cloned_repos' that appear to be Git repos.
    """
    base_dir = "cloned_repos"
    if not os.path.isdir(base_dir):
        return []

    repos = []
    for d in os.listdir(base_dir):
        full_path = os.path.join(base_dir, d)
        if os.path.isdir(full_path) and os.path.isdir(os.path.join(full_path, ".git")):
            repos.append(d)
    return repos