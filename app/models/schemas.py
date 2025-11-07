from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EventResponse(BaseModel):
    id: int
    delivery_id: Optional[str] = None
    event_type: str
    repo: Optional[str] = None
    ref: Optional[str] = None
    after_sha: Optional[str] = None
    created_at: str
    latest_review_status: Optional[str] = None
    latest_review_id: Optional[int] = None


class ReviewResponse(BaseModel):
    id: int
    event_id: int
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    summary_json: Optional[str] = None


class FindingResponse(BaseModel):
    id: int
    review_id: int
    file_path: Optional[str] = None
    severity: str
    title: str
    rationale: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    patch: Optional[str] = None
    tool: Optional[str] = None


class EventDetailResponse(BaseModel):
    event: EventResponse
    reviews: List[ReviewResponse]


class ReviewDetailResponse(BaseModel):
    review: ReviewResponse
    event: EventResponse
    findings: List[FindingResponse]
    findings_by_file: dict[str, List[FindingResponse]]


class PaginatedEventsResponse(BaseModel):
    events: List[EventResponse]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    has_more: bool


class HealthResponse(BaseModel):
    ok: bool
    env: str


class EnqueueResponse(BaseModel):
    success: bool
    message: str
    event_id: int

