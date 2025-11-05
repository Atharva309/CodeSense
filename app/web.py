import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from app.repo import (
    init_db,
    list_events,
    get_latest_review_for_event,
    get_reviews_for_event,
    get_findings,
    get_review_and_event,
)
from app.worker import enqueue_review
from app.webhook import router as webhook_router
from app.github import get_file_at_sha

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="CloudSense (local)", lifespan=lifespan)

app.include_router(webhook_router)


@app.get("/events", response_class=HTMLResponse)
def events():
    rows = list_events()
    items = ""
    for r in rows:
        rev = get_latest_review_for_event(r["id"])
        status = rev["status"] if rev else "-"
        review_cell = (
            f'<a href="/reviews/{rev["id"]}">{status}</a>' if rev else status
        )
        items += (
            "<tr>"
            f'<td><a href="/events/{r["id"]}">{r["id"]}</a></td>'
            f"<td>{r['event_type']}</td>"
            f"<td>{r['repo']}</td>"
            f"<td>{r['ref']}</td>"
            f"<td><code>{r['after_sha']}</code></td>"
            f"<td>{review_cell}</td>"
            f"<td>{r['created_at']}</td>"
            "</tr>"
        )

    html = f"""
    <html>
    <head>
      <title>CloudSense – Events</title>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <style>
        body {{ font-family: system-ui, Arial, sans-serif; padding: 16px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; }}
        th {{ background: #f5f5f5; text-align: left; }}
        a {{ color: #0b5ed7; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
      </style>
    </head>
    <body>
      <h2>Recent Events</h2>
      <table>
        <tr>
          <th>ID</th><th>Type</th><th>Repo</th><th>Ref</th>
          <th>After</th><th>Review</th><th>Time</th>
        </tr>
        {items or '<tr><td colspan="7">No events yet</td></tr>'}
      </table>
      <p style="margin-top:12px"><a href="/">← Home</a></p>
    </body>
    </html>
    """
    return html


@app.get("/health")
def health():
    return {"ok": True, "env": os.getenv("APP_ENV", "dev")}


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html><head><title>CloudSense (local)</title></head>
    <body>
      <h1>CloudSense (local)</h1>
      <p>Status: up</p>
      <ul>
        <li><a href="/health">/health</a></li>
        <li><a href="/events">/events</a></li>
        <li><a href="/setup">/setup</a></li>
      </ul>
    </body></html>
    """


@app.get("/events/{event_id}", response_class=HTMLResponse)
def event_detail(event_id: int):
    revs = get_reviews_for_event(event_id)
    latest = revs[0] if revs else None

    review_list = "".join(
        f'<li><a href="/reviews/{r["id"]}">Review #{r["id"]} – {r["status"]}</a></li>'
        for r in revs
    ) or "<li>No reviews yet.</li>"

    enqueue_form = f"""
      <form method="post" action="/events/{event_id}/enqueue">
        <button type="submit">Run review</button>
      </form>
    """

    return f"""
    <html><head><title>Event {event_id}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <style>body{{font-family:system-ui,Arial,sans-serif;padding:16px}}</style>
    </head><body>
      <h2>Event {event_id}</h2>
      <p>Status: {latest['status'] if latest else '-'}</p>
      {enqueue_form}
      <h3>All reviews</h3>
      <ul>{review_list}</ul>
      <p><a href="/events">← Back to events</a></p>
    </body></html>
    """


@app.post("/events/{event_id}/enqueue", response_class=HTMLResponse)
def enqueue_event_review(event_id: int):
    enqueue_review(event_id)
    return f"""
      <p>Enqueued review for event {event_id}.</p>
      <p><a href="/events/{event_id}">Back to event</a></p>
    """


def _badge(sev: str) -> str:
    colors = {
        "high": "#b91c1c",
        "medium": "#ca8a04",
        "low": "#2563eb",
        "info": "#6b7280",
    }
    return f"<span style='background:{colors.get(sev, '#6b7280')};color:white;padding:2px 8px;border-radius:999px;font-size:12px'>{sev}</span>"


def _make_snippet(text: str, max_chars: int = 8000, max_lines: int = 200) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    lines = lines[:max_lines]
    snippet = "\n".join(lines)
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars] + "\n... [truncated]"
    # add 1-based line numbers for readability
    numbered = []
    for i, line in enumerate(snippet.splitlines(), start=1):
        numbered.append(f"{i:4d} | {line}")
    return "\n".join(numbered)


@app.get("/reviews/{review_id}", response_class=HTMLResponse)
async def review_detail(review_id: int):
    rows = get_findings(review_id)
    review, event = get_review_and_event(review_id)
    if not review or not event:
        return f"<h2>Review {review_id}</h2><p>Not found.</p><p><a href='/events'>Back</a></p>"

    repo = event["repo"]
    sha = event["after_sha"]

    if not rows:
        return f"<h2>Review {review_id}</h2><p>No findings 🎉</p><p><a href='/events'>Back</a></p>"

    # group findings by file
    by_file: dict[str, list] = {}
    for f in rows:
        by_file.setdefault(f["file_path"], []).append(f)

    sections = ""

    for path, findings in by_file.items():
        # fetch file content from GitHub at this commit
        try:
            content = await get_file_at_sha(repo, path, sha)
        except Exception as e:
            print(f"[review_detail] failed to fetch {repo}@{sha}:{path}: {e}")
            content = None

        code_block = ""
        if content:
            code_block = _make_snippet(content)

        # separate static vs AI
        static_findings = [f for f in findings if f.get("tool") != "ai"]
        ai_findings = [f for f in findings if f.get("tool") == "ai"]

        # sort static by severity
        order = {"high": 0, "medium": 1, "low": 2, "info": 3}
        static_findings.sort(key=lambda f: order.get(f.get("severity", "info"), 3))

        static_rows = ""
        for f in static_findings:
            static_rows += (
                "<tr>"
                f"<td>{_badge(f.get('severity','info'))}</td>"
                f"<td>{f.get('title','')}</td>"
                f"<td><div style='white-space:pre-wrap'>{(f.get('rationale') or '')}</div></td>"
                "</tr>"
            )

        if not static_rows:
            static_rows = "<tr><td colspan='3'><i>No static findings for this file.</i></td></tr>"

        ai_rows = ""
        for f in ai_findings:
            patch_html = ""
            patch = f.get("patch") or ""
            if patch.strip():
                patch_html = f"<pre style='background:#0f172a;color:#e5e7eb;padding:8px;border-radius:4px;white-space:pre-wrap;margin-top:4px'>{patch}</pre>"
            ai_rows += (
                "<tr>"
                f"<td>{_badge(f.get('severity','info'))}</td>"
                f"<td>{f.get('title','')}</td>"
                f"<td><div style='white-space:pre-wrap'>{(f.get('rationale') or '')}</div>{patch_html}</td>"
                "</tr>"
            )

        if not ai_rows:
            ai_rows = "<tr><td colspan='3'><i>No AI suggestions for this file.</i></td></tr>"

        code_html = (
            f"<pre style='background:#0f172a;color:#e5e7eb;padding:8px;border-radius:4px;overflow:auto'>{code_block}</pre>"
            if code_block
            else "<p><i>Could not fetch file contents from GitHub.</i></p>"
        )

        sections += f"""
          <section style="margin-top:32px">
            <h3>{path}</h3>
            <h4>Code at {sha[:7]}</h4>
            {code_html}
            <div style="display:flex;flex-wrap:wrap;gap:24px;margin-top:12px">
              <div style="flex:1;min-width:280px">
                <h4>Static analysis</h4>
                <table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
                  <tr><th>Severity</th><th>Title</th><th>Details</th></tr>
                  {static_rows}
                </table>
              </div>
              <div style="flex:1;min-width:280px">
                <h4>AI suggestions</h4>
                <table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
                  <tr><th>Severity</th><th>Title</th><th>Details + Patch</th></tr>
                  {ai_rows}
                </table>
              </div>
            </div>
          </section>
        """

    html = f"""
      <html><head><title>Review {review_id}</title>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <style>body{{font-family:system-ui,Arial,sans-serif;padding:16px}}</style>
      </head><body>
        <h2>Review {review_id}</h2>
        <p>Repo: <code>{repo}</code> @ <code>{sha}</code></p>
        {sections}
        <p style="margin-top:16px"><a href="/events">← Back to events</a></p>
      </body></html>
    """
    return html


@app.get("/setup", response_class=HTMLResponse)
def setup():
    url = os.getenv("PUBLIC_WEBHOOK_BASE", "http://localhost:8000") + "/webhook"
    secret = os.getenv("GH_WEBHOOK_SECRET", "<set GH_WEBHOOK_SECRET>")
    return f"""
    <h2>Connect your repo</h2>
    <ol>
      <li>Payload URL: <code>{url}</code></li>
      <li>Content type: <code>application/json</code></li>
      <li>Secret: <code>{secret}</code></li>
      <li>Events: <b>Just the push event</b></li>
    </ol>
    <p>After saving, push a commit and watch <a href="/events">Events</a>.</p>
    """