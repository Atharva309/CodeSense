from fastapi import APIRouter, HTTPException, Depends
from app.repo import get_findings, get_review_and_event, _con
from app.github import get_file_at_sha
from app.auth import get_current_user
from app.models.schemas import (
    ReviewResponse,
    ReviewDetailResponse,
    EventResponse,
    FindingResponse,
)

router = APIRouter()


@router.get("/reviews/{review_id}", response_model=ReviewDetailResponse)
async def get_review_detail(
    review_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get review details with findings grouped by file. Only if review belongs to user."""
    user_id = current_user["id"]
    review_row, event_row = get_review_and_event(review_id)
    
    if not review_row or not event_row:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Verify event belongs to user
    event_dict = dict(event_row) if hasattr(event_row, 'keys') else event_row
    if event_dict.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Convert sqlite3.Row to dict
    review_dict = dict(review_row) if hasattr(review_row, 'keys') else review_row
    event_dict = dict(event_row) if hasattr(event_row, 'keys') else event_row
    
    # Convert to response models
    review = ReviewResponse(
        id=review_dict["id"],
        event_id=review_dict["event_id"],
        status=review_dict["status"],
        started_at=review_dict.get("started_at"),
        finished_at=review_dict.get("finished_at"),
        summary_json=review_dict.get("summary_json"),
    )
    
    event = EventResponse(
        id=event_dict["id"],
        delivery_id=event_dict.get("delivery_id"),
        event_type=event_dict.get("event_type", "unknown"),
        repo=event_dict.get("repo"),
        ref=event_dict.get("ref"),
        after_sha=event_dict.get("after_sha"),
        created_at=event_dict.get("created_at", ""),
        latest_review_status=None,
        latest_review_id=None,
    )
    
    # Get findings (already returns dicts from repo.get_findings)
    findings_rows = get_findings(review_id)
    findings = [
        FindingResponse(
            id=f["id"],
            review_id=f["review_id"],
            file_path=f.get("file_path"),
            severity=f.get("severity", "info"),
            title=f.get("title", ""),
            rationale=f.get("rationale"),
            start_line=f.get("start_line"),
            end_line=f.get("end_line"),
            patch=f.get("patch"),
            tool=f.get("tool"),
        )
        for f in findings_rows
    ]
    
    # Group findings by file
    findings_by_file: dict[str, list[FindingResponse]] = {}
    for finding in findings:
        file_path = finding.file_path or "unknown"
        if file_path not in findings_by_file:
            findings_by_file[file_path] = []
        findings_by_file[file_path].append(finding)
    
    return ReviewDetailResponse(
        review=review,
        event=event,
        findings=findings,
        findings_by_file=findings_by_file,
    )


@router.get("/reviews/{review_id}/findings", response_model=list[FindingResponse])
def get_review_findings(
    review_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get all findings for a review. Only if review belongs to user."""
    user_id = current_user["id"]
    review_row, event_row = get_review_and_event(review_id)
    
    if not review_row or not event_row:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Verify event belongs to user
    event_dict = dict(event_row) if hasattr(event_row, 'keys') else event_row
    if event_dict.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    findings_rows = get_findings(review_id)  # Already returns dicts
    return [
        FindingResponse(
            id=f["id"],
            review_id=f["review_id"],
            file_path=f.get("file_path"),
            severity=f.get("severity", "info"),
            title=f.get("title", ""),
            rationale=f.get("rationale"),
            start_line=f.get("start_line"),
            end_line=f.get("end_line"),
            patch=f.get("patch"),
            tool=f.get("tool"),
        )
        for f in findings_rows
    ]

