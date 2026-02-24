import hashlib
import os
import re
import subprocess
from typing import Optional


_GIT_URL_RE = re.compile(r"^(https?://|git@|ssh://|git://)")


def is_git_url(value: str) -> bool:
    return bool(value and _GIT_URL_RE.match(value.strip()))


def _run_git(args: list, cwd: Optional[str] = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "git command failed").strip())
    return (result.stdout or "").strip()


def cache_dir_for_url(cache_root: str, repo_url: str) -> str:
    url = repo_url.strip()
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return os.path.join(cache_root, f"repo_{h}")


def clone_or_update_repo(repo_url: str, cache_root: str) -> str:
    """Ensure a local clone exists for the given repo URL.

    Returns the local path to the repo.
    """
    if not is_git_url(repo_url):
        raise ValueError(f"Expected a git repo URL, got: {repo_url}")

    os.makedirs(cache_root, exist_ok=True)
    repo_dir = cache_dir_for_url(cache_root, repo_url)

    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        if os.path.exists(repo_dir):
            raise RuntimeError(
                f"Cache path exists but is not a git repository: {repo_dir}. "
                "Please remove it manually."
            )
        _run_git(["clone", "--depth", "1", repo_url, repo_dir])
    else:
        try:
            _run_git(["remote", "set-url", "origin", repo_url], cwd=repo_dir)
        except RuntimeError:
            pass
        _run_git(["fetch", "--prune", "origin"], cwd=repo_dir)

    return repo_dir


def get_remote_head_sha(repo_url: str) -> str:
    """Return the SHA for the remote HEAD."""
    out = _run_git(["ls-remote", repo_url, "HEAD"])
    return out.split()[0] if out else ""


def pull_repo(repo_dir: str) -> None:
    _run_git(["pull", "--ff-only"], cwd=repo_dir)
