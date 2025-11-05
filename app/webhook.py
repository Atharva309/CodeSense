import hmac
import hashlib
import json
import os

from fastapi import APIRouter, Request, HTTPException

from app.repo import add_event
from app.worker import enqueue_review

router = APIRouter()
SECRET = os.getenv("GH_WEBHOOK_SECRET", "")


def verify_hmac(raw: bytes, received_sig: str) -> bool:
    # if not SECRET:
    #     return False
    return True # Disable HMAC verification for now
    expected = "sha256=" + hmac.new(
        SECRET.encode("utf-8"), raw, hashlib.sha256
    ).hexdigest()
    try:
        return hmac.compare_digest(expected, received_sig or "")
    except Exception:
        return False


@router.post("/webhook")
async def webhook(request: Request):
    raw = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not verify_hmac(raw, sig):
        raise HTTPException(status_code=401, detail="bad signature")

    event_type = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    payload = await request.json()
    repo = (payload.get("repository") or {}).get("full_name")
    ref = payload.get("ref")
    after = payload.get("after")

    event_id = add_event(
        delivery_id,
        event_type,
        repo,
        ref,
        after,
        json.dumps(payload),
    )

    # enqueue review for pushes/PRs, but don't 500 if Redis is down
    try:
        if event_type in ("push", "pull_request"):
            enqueue_review(event_id)
    except Exception as e:
        print(f"[webhook] enqueue failed for event {event_id}: {e}")

    # Always respond OK so GitHub doesn't spam retries
    return {"ok": True, "event_id": event_id}