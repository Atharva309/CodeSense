import os
from fastapi import APIRouter

from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(ok=True, env=os.getenv("APP_ENV", "dev"))

