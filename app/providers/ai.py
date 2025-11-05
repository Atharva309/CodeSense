import os
import json
from openai import OpenAI, BadRequestError

MODEL = os.getenv("OPENAI_MODEL", "gpt-5-2025-08-07")
_API_KEY = os.getenv("OPENAI_API_KEY")
_client = OpenAI(api_key=_API_KEY) if _API_KEY else None

SYSTEM = (
    "You are a precise code reviewer. "
    "Return ONLY valid JSON with key 'findings' as an array. "
    "Each finding: {file, severity in [info,low,medium,high], title, rationale, start_line, end_line, patch(optional)}. "
    "If nothing to add, return {\"findings\": []}."
)

# Models that don't allow custom temperature
NO_TEMPERATURE = {"gpt-5-2025-08-07"}


def _make_messages(repo, path, content_snippet, linter_findings, diff_snippet):
    user = f"""Repository: {repo}
File: {path}

Changed code (snippet):
<<<CODE
{(content_snippet or '')[:8000]}
>>>

Existing findings to consider:
{json.dumps(linter_findings or [])[:4000]}

If you propose a change, add a minimal unified diff in 'patch'. Keep it small and accurate.
"""
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]


def _call_openai(messages, allow_temperature: bool):
    kwargs = dict(model=MODEL, messages=messages)
    if allow_temperature:
        kwargs["temperature"] = 0.2
    return _client.chat.completions.create(**kwargs)


def review_file_ai(repo, path, content_snippet, linter_findings, diff_snippet=None):
    """Call the model and normalize findings as tool='ai'."""
    if _client is None:
        return []  # no key set; skip AI gracefully

    allow_temp = MODEL not in NO_TEMPERATURE
    messages = _make_messages(repo, path, content_snippet, linter_findings, diff_snippet)

    try:
        resp = _call_openai(messages, allow_temp)
    except BadRequestError as e:
        msg = str(e).lower()
        if "temperature" in msg:
            try:
                resp = _call_openai(messages, allow_temperature=False)
            except Exception:
                return []
        else:
            return []
    except Exception:
        return []

    try:
        content = resp.choices[0].message.content
        data = json.loads(content) if content else {"findings": []}
        if "findings" not in data:
            data = {"findings": []}
    except Exception:
        data = {"findings": []}

    normalized = []
    for f in data["findings"]:
        f = dict(f or {})
        f.setdefault("file", path)
        f.setdefault("severity", "info")
        f.setdefault("title", "AI suggestion")
        f.setdefault("rationale", "")
        f.setdefault("start_line", None)
        f.setdefault("end_line", None)
        f.setdefault("patch", "")
        f["tool"] = "ai"
        normalized.append(f)

    return normalized