from fastapi import APIRouter

from app.api import events, reviews, health, auth, repositories

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(repositories.router, tags=["repositories"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(reviews.router, tags=["reviews"])
api_router.include_router(health.router, tags=["health"])

