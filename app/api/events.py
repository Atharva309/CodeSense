from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from app.repo import (
    list_events,
    get_latest_review_for_event,
    get_reviews_for_event,
    _con,
)
from app.worker import enqueue_review
from app.auth import get_current_user
from app.models.schemas import (
    EventResponse,
    EventDetailResponse,
    ReviewResponse,
    PaginatedEventsResponse,
    EnqueueResponse,
)

router = APIRouter()


def _event_to_response(event_row, latest_review=None):
    """Convert database row to EventResponse."""
    # Convert sqlite3.Row to dict if needed
    if hasattr(event_row, 'keys'):
        event_dict = dict(event_row)
    else:
        event_dict = event_row
    
    return EventResponse(
        id=event_dict["id"],
        delivery_id=event_dict.get("delivery_id"),
        event_type=event_dict.get("event_type", "unknown"),
        repo=event_dict.get("repo"),
        ref=event_dict.get("ref"),
        after_sha=event_dict.get("after_sha"),
        created_at=event_dict.get("created_at", ""),
        latest_review_status=latest_review["status"] if latest_review else None,
        latest_review_id=latest_review["id"] if latest_review else None,
    )


@router.get("/events", response_model=PaginatedEventsResponse)
def list_events_api(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    repo: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    """List events with pagination and optional filtering. Only returns user's events."""
    user_id = current_user["id"]
    
    # Get events filtered by user_id
    with _con() as con:
        query = "SELECT * FROM events WHERE user_id = ?"
        params = [user_id]
        
        if repo:
            query += " AND repo = ?"
            params.append(repo)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY id DESC LIMIT ?"
        params.append(1000)  # Get more than we need for pagination
        
        all_events = con.execute(query, params).fetchall()
    
    # Convert sqlite3.Row objects to dicts for easier access
    all_events = [dict(e) if hasattr(e, 'keys') else e for e in all_events]
    
    # Calculate pagination
    total = len(all_events)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_events = all_events[start:end]
    
    # Convert to response models
    event_responses = []
    for event_row in paginated_events:
        latest_review = get_latest_review_for_event(event_row["id"])
        event_responses.append(_event_to_response(event_row, latest_review))
    
    return PaginatedEventsResponse(
        events=event_responses,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
    )


@router.get("/events/{event_id}", response_model=EventDetailResponse)
def get_event_detail(
    event_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get event details with associated reviews. Only if event belongs to user."""
    user_id = current_user["id"]
    
    with _con() as con:
        event_row = con.execute(
            "SELECT * FROM events WHERE id=? AND user_id=?", (event_id, user_id)
        ).fetchone()
        
        if not event_row:
            raise HTTPException(status_code=404, detail="Event not found")
    
    # Get reviews for this event
    review_rows = get_reviews_for_event(event_id)
    reviews = [
        ReviewResponse(
            id=r["id"],
            event_id=r["event_id"],
            status=r["status"],
            started_at=dict(r).get("started_at") if hasattr(r, 'keys') else r.get("started_at"),
            finished_at=dict(r).get("finished_at") if hasattr(r, 'keys') else r.get("finished_at"),
            summary_json=dict(r).get("summary_json") if hasattr(r, 'keys') else r.get("summary_json"),
        )
        for r in review_rows
    ]
    
    latest_review = get_latest_review_for_event(event_id)
    event_response = _event_to_response(dict(event_row), latest_review)
    
    return EventDetailResponse(event=event_response, reviews=reviews)


@router.post("/events/{event_id}/enqueue", response_model=EnqueueResponse)
def enqueue_event_review(
    event_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Trigger a review for an event. Only if event belongs to user."""
    user_id = current_user["id"]
    
    # Verify event exists and belongs to user
    with _con() as con:
        event_row = con.execute(
            "SELECT id FROM events WHERE id=? AND user_id=?", (event_id, user_id)
        ).fetchone()
        
        if not event_row:
            raise HTTPException(status_code=404, detail="Event not found")
    
    try:
        enqueue_review(event_id)
        return EnqueueResponse(
            success=True,
            message=f"Review enqueued for event {event_id}",
            event_id=event_id,
        )
    except Exception as e:
        return EnqueueResponse(
            success=False,
            message=f"Failed to enqueue review: {str(e)}",
            event_id=event_id,
        )

