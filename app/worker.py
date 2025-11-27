import os
import json
import pathlib
import asyncio

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnError
from rq import Queue

from app.repo import _con, init_db
from app.github import compare_commits, get_file_at_sha
from app.checks import run_python_checks, run_js_checks
from app.providers.ai import review_file_ai

# Ensure DB exists when worker imports
init_db()

redis = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)
q = Queue("reviews", connection=redis)


def enqueue_review(event_id: int):
    try:
        q.enqueue(run_review, event_id)
    except RedisConnError as e:
        print(f"[enqueue] Redis unavailable for event_id={event_id}: {e}")
        # For dev you *could* fall back to sync:
        # run_review(event_id)


def _ext(path: str) -> str:
    return pathlib.Path(path).suffix.lower()


def _is_text_ok(s) -> bool:
    return bool(s) and isinstance(s, str) and len(s) <= 200_000


def _sev_rank(sev: str) -> int:
    return {"info": 0, "low": 1, "medium": 2, "high": 3}.get(sev or "low", 0)


def _dedupe_findings(findings: list[dict]) -> list[dict]:
    """
    Keep a single best finding per (source/tool, file, title, start_line, end_line).
    Prefer higher severity when duplicates collide.
    """
    seen = {}
    for f in findings or []:
        key = (
            f.get("tool") or f.get("source") or "ai",
            f.get("file"),
            f.get("title"),
            f.get("start_line"),
            f.get("end_line"),
        )
        cur = seen.get(key)
        if cur is None or _sev_rank(f.get("severity")) > _sev_rank(
            cur.get("severity")
        ):
            seen[key] = f
    return list(seen.values())


def _store_results(con, event_id: int, findings: list[dict]) -> int:
    cur = con.cursor()
    cur.execute(
        "INSERT INTO reviews(event_id, status, started_at) VALUES (?, 'running', datetime('now'))",
        (event_id,),
    )
    review_id = cur.lastrowid
    for f in findings or []:
        cur.execute(
            """
            INSERT INTO findings
            (review_id, file_path, severity, title, rationale, start_line, end_line, patch, tool)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                f.get("file"),
                f.get("severity", "low"),
                f.get("title", ""),
                f.get("rationale", ""),
                f.get("start_line"),
                f.get("end_line"),
                f.get("patch", ""),
                f.get("tool", "static"),  # <— default label
            ),
        )
    cur.execute(
        "UPDATE reviews SET status='done', finished_at=datetime('now'), summary_json=? WHERE id=?",
        (json.dumps({"count": len(findings or [])}), review_id),
    )
    con.commit()
    return review_id


def run_review(event_id: int):
    # Load event + raw payload
    with _con() as con:
        ev = con.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if not ev:
            return
        payload = json.loads(ev["raw_json"])

    repo = ev["repo"]
    after = ev["after_sha"]
    before = payload.get("before")  # present on push events

    # If refs missing, still create empty review for UI continuity
    if not (repo and after and before):
        with _con() as con:
            return _store_results(con, event_id, [])

    # Fetch changed files via compare API
    files = asyncio.run(compare_commits(repo, before, after))
    findings_all: list[dict] = []

    for f in files[:20]:  # cap for MVP
        path = f.get("filename")
        if not path:
            continue

        content = asyncio.run(get_file_at_sha(repo, path, after))
        if not _is_text_ok(content):
            continue

        ext = _ext(path)
        lints: list[dict] = []
        if ext in {".py"}:
            lints = run_python_checks(content, filename=path)
        elif ext in {".js", ".jsx", ".ts", ".tsx"}:
            lints = run_js_checks(content, filename=path)

        ai = review_file_ai(repo, path, content, lints, diff_snippet=f.get("patch"))

        for item in (lints or []):
            item.setdefault("file", path)
        for item in (ai or []):
            item.setdefault("file", path)

        findings_all.extend((lints or []) + (ai or []))

    findings_all = _dedupe_findings(findings_all)
    with _con() as con:
        _store_results(con, event_id, findings_all)