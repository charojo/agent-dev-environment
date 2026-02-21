import subprocess
from pathlib import Path
import functools

@functools.lru_cache(maxsize=1)
def get_gh_user():
    try:
        user = subprocess.check_output(
            ["gh", "api", "user", "-q", ".login"], 
            stderr=subprocess.DEVNULL, universal_newlines=True
        ).strip()
        return user
    except Exception:
        return None

@functools.lru_cache(maxsize=128)
def is_repo_owned_by_current_user(filepath_str):
    """Check if the git repository containing this filepath is owned by the current github user."""
    gh_user = get_gh_user()
    if not gh_user:
        # If we can't determine the user, default to safe (True) so we don't break functionality, 
        # or False? Local repos might just be safe to process.
        return True
        
    path = Path(filepath_str).resolve()
    if path.is_file():
        parent_dir = path.parent
    else:
        parent_dir = path

    try:
        # Find the git root for this file
        repo_root_str = subprocess.check_output(
            ["git", "-C", str(parent_dir), "rev-parse", "--show-toplevel"],
            universal_newlines=True,
            stderr=subprocess.DEVNULL
        ).strip()
        
        # Get the remote origin URL
        remote_url = subprocess.check_output(
            ["git", "-C", repo_root_str, "remote", "get-url", "origin"],
            universal_newlines=True,
            stderr=subprocess.DEVNULL
        ).strip()
        
        # Check if the github user is in the remote URL
        if f"github.com/{gh_user}/" in remote_url or f"github.com:{gh_user}/" in remote_url:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        # Not in a git repo, so we probably own it locally (e.g. project root if not git init'd)
        return True
