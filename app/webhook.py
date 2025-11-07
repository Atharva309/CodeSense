import hmac
import hashlib
import json
import os
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, HTTPException, Path, Form

from app.repo import add_event, get_repository_by_secret
from app.worker import enqueue_review

router = APIRouter()


def normalize_repo_name(repo_name: str) -> str:
    """Normalize repository name to owner/repo format.
    
    Handles both:
    - Full URLs: https://github.com/owner/repo -> owner/repo
    - Short format: owner/repo -> owner/repo
    """
    if not repo_name:
        return ""
    # Remove protocol and domain if present
    repo_name = repo_name.replace("https://github.com/", "").replace("http://github.com/", "")
    repo_name = repo_name.replace("github.com/", "")
    # Remove leading/trailing slashes
    repo_name = repo_name.strip("/")
    return repo_name


def verify_hmac(raw: bytes, received_sig: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC signature."""
    if not secret:
        return False
    try:
        expected = "sha256=" + hmac.new(
            secret.encode("utf-8"), raw, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, received_sig or "")
    except Exception:
        return False


@router.post("/webhook/{webhook_secret}")
async def webhook(
    request: Request,
    webhook_secret: str = Path(..., description="Repository webhook secret"),
):
    """Handle GitHub webhook for a specific repository."""
    # Get repository by webhook secret
    repository = get_repository_by_secret(webhook_secret)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Read request body
    raw = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    content_type = request.headers.get("Content-Type", "")
    
    # Debug logging
    if len(raw) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Empty request body. Content-Type: {content_type}, Headers: {dict(request.headers)}"
        )
    
    global_secret = os.getenv("GH_WEBHOOK_SECRET", "")
    if global_secret:
        if not verify_hmac(raw, sig, global_secret):
            raise HTTPException(status_code=401, detail="bad signature")
    
    # Parse payload based on content type
    try:
        if "application/json" in content_type:
            # Direct JSON payload
            payload = json.loads(raw.decode("utf-8"))
        elif "application/x-www-form-urlencoded" in content_type:
            # Form-encoded payload - GitHub sends JSON as form data
            form_data = raw.decode("utf-8")
            # Try to parse as form data first
            try:
                parsed = parse_qs(form_data, keep_blank_values=True)
                # GitHub sends the JSON payload in a 'payload' form field
                if "payload" in parsed and parsed["payload"]:
                    payload_str = parsed["payload"][0]
                    payload = json.loads(payload_str)
                else:
                    # If no 'payload' field, the form data might be the JSON itself
                    # Try parsing the entire form data as JSON
                    payload = json.loads(form_data)
            except (ValueError, KeyError):
                # If form parsing fails, try direct JSON
                payload = json.loads(form_data)
        else:
            # Unknown content type - try JSON first
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                # Try form-encoded as fallback
                form_data = raw.decode("utf-8")
                parsed = parse_qs(form_data, keep_blank_values=True)
                if "payload" in parsed and parsed["payload"]:
                    payload_str = parsed["payload"][0]
                    payload = json.loads(payload_str)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unable to parse payload. Content-Type: {content_type}, Body length: {len(raw)}, Body preview: {raw[:500].decode('utf-8', errors='ignore')}"
                    )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON payload: {str(e)}. Content-Type: {content_type}, Body length: {len(raw)}, Body preview: {raw[:500].decode('utf-8', errors='ignore')}"
        )
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    repo = (payload.get("repository") or {}).get("full_name")
    ref = payload.get("ref")
    after = payload.get("after")

    # Normalize repository names for comparison
    if repo:
        normalized_repo = normalize_repo_name(repo)
        normalized_expected = normalize_repo_name(repository["repo_full_name"])
        if normalized_repo != normalized_expected:
            raise HTTPException(
                status_code=400,
                detail=f"Repository mismatch: expected {repository['repo_full_name']} (normalized: {normalized_expected}), got {repo} (normalized: {normalized_repo})",
            )

    event_id = add_event(
        delivery_id=delivery_id,
        event_type=event_type,
        repo=repo or repository["repo_full_name"],
        ref=ref,
        after_sha=after,
        payload_json=json.dumps(payload),
        user_id=repository["user_id"],
        repository_id=repository["id"],
    )

    try:
        if event_type in ("push", "pull_request"):
            enqueue_review(event_id)
    except Exception as e:
        print(f"[webhook] enqueue failed for event {event_id}: {e}")

    return {"ok": True, "event_id": event_id, "repository": repository["repo_full_name"]}



# Legacy webhook endpoint for backward compatibility (optional)
@router.post("/webhook")
async def legacy_webhook(request: Request):
    """Legacy webhook endpoint (for backward compatibility)."""
    # This can be removed once all users migrate to per-repo webhooks
    raw = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    global_secret = os.getenv("GH_WEBHOOK_SECRET", "")
    
    if global_secret and not verify_hmac(raw, sig, global_secret):
        raise HTTPException(status_code=401, detail="bad signature")

    event_type = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    payload = await request.json()
    repo = (payload.get("repository") or {}).get("full_name")
    ref = payload.get("ref")
    after = payload.get("after")

    # Legacy: no user_id or repository_id (will be None)
    event_id = add_event(
        delivery_id,
        event_type,
        repo,
        ref,
        after,
        json.dumps(payload),
    )

    try:
        if event_type in ("push", "pull_request"):
            enqueue_review(event_id)
    except Exception as e:
        print(f"[webhook] enqueue failed for event {event_id}: {e}")

    return {"ok": True, "event_id": event_id}