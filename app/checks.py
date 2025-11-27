import os
import json
import shlex
import subprocess
import tempfile

MAX_FILE_CHARS = 200_000  # cap content size we lint


def _run(cmd: str, cwd: str):
    try:
        p = subprocess.run(
            shlex.split(cmd),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 1, "", str(e)


def run_python_checks(content: str, filename: str = "file.py") -> list[dict]:
    """
    Runs Ruff (lint), Black --check (format), and Bandit (security).
    Returns normalized finding dicts.
    """
    if not content or len(content) > MAX_FILE_CHARS:
        return []

    findings: list[dict] = []

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        # Ruff (lint)
        _, out, _ = _run(f"ruff {path}", cwd=tmp)
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[0].endswith(".py"):
                try:
                    ln = int(parts[1])
                except Exception:
                    ln = None
                findings.append(
                    {
                        "tool": "ruff",
                        "file": filename,
                        "severity": "low",
                        "title": line.strip(),
                        "rationale": "Ruff lint finding",
                        "start_line": ln,
                        "end_line": ln,
                    }
                )

        # Black (format)
        _, out, _ = _run(f"black --check {path}", cwd=tmp)
        if "would reformat" in out:
            findings.append(
                {
                    "tool": "black",
                    "file": filename,
                    "severity": "info",
                    "title": "Formatting differs from Black",
                    "rationale": "Run black to format",
                    "start_line": 1,
                    "end_line": 1,
                }
            )

        # Bandit (security)
        _, out, _ = _run(f"bandit -q -f json -r {path}", cwd=tmp)
        try:
            j = json.loads(out or "{}")
            for issue in j.get("results", []):
                title = issue.get("test_name", "Bandit issue")
                if title == "request_without_timeout":
                    title = "HTTP request without timeout"
                findings.append(
                    {
                        "tool": "bandit",
                        "file": filename,
                        "severity": str(issue.get("issue_severity", "LOW")).lower(),
                        "title": title,
                        "rationale": issue.get("issue_text", ""),
                        "start_line": issue.get("line_number"),
                        "end_line": issue.get("line_number"),
                    }
                )
        except Exception:
            pass

    return findings


def run_js_checks(content: str, filename: str = "file.js") -> list[dict]:
    """
    Placeholder for JS/TS checks.
    For MVP we skip ESLint (project config dependent) to keep noise low.
    Add ESLint/Prettier later when you decide configs.
    """
    if not content or len(content) > MAX_FILE_CHARS:
        return []
    return []