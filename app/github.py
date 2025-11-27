import os
import base64
import httpx

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if GITHUB_TOKEN:
    HEADERS = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
else:
    # No token: rely on public / unauthenticated access
    HEADERS = {
        "Accept": "application/vnd.github+json",
    }


async def compare_commits(repo_full: str, before: str, after: str):
    """
    Uses the GitHub compare API to list changed files between two SHAs.
    Returns a list of file dicts with keys like filename, status, patch, etc.
    """
    url = f"https://api.github.com/repos/{repo_full}/compare/{before}...{after}"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return data.get("files", [])


async def get_file_at_sha(repo_full: str, path: str, sha: str):
    """
    Fetches file contents at a specific commit SHA.
    Returns decoded text or None on failure.
    """
    url = f"https://api.github.com/repos/{repo_full}/contents/{path}"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, headers=HEADERS, params={"ref": sha})

    if r.status_code != 200:
        # helpful logging while debugging
        print(
            f"[get_file_at_sha] {repo_full}@{sha}:{path} -> "
            f"{r.status_code} {r.text[:200]}"
        )
        return None

    j = r.json()
    if j.get("encoding") == "base64":
        return base64.b64decode(j["content"]).decode("utf-8", errors="replace")
    return j.get("content")