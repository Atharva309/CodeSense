import os
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.auth import get_current_user
from app.repo import (
    create_repository,
    get_repositories_by_user,
    get_repository_by_id,
    deactivate_repository,
)

router = APIRouter()


class CreateRepositoryRequest(BaseModel):
    repo_full_name: str  # e.g., "username/repo-name"
    github_token: Optional[str] = None  # Optional, for private repos


class RepositoryResponse(BaseModel):
    id: int
    user_id: int
    repo_full_name: str
    webhook_secret: str
    webhook_url: str
    is_active: bool
    created_at: str


@router.get("/repositories", response_model=list[RepositoryResponse])
def list_repositories(current_user: dict = Depends(get_current_user)):
    """List all repositories for the current user."""
    repos = get_repositories_by_user(current_user["id"])
    return [
        RepositoryResponse(
            id=r["id"],
            user_id=r["user_id"],
            repo_full_name=r["repo_full_name"],
            webhook_secret=r["webhook_secret"],
            webhook_url=r["webhook_url"],
            is_active=bool(r.get("is_active", 1)),
            created_at=r.get("created_at", ""),
        )
        for r in repos
    ]


@router.post("/repositories", response_model=RepositoryResponse, status_code=201)
def create_repository_endpoint(
    request: CreateRepositoryRequest,
    current_user: dict = Depends(get_current_user),
):
    """Connect a new repository."""
    # Generate unique webhook secret
    webhook_secret = str(uuid.uuid4())
    
    # Generate webhook URL
    base_url = os.getenv("PUBLIC_WEBHOOK_BASE", "http://localhost:8000")
    webhook_url = f"{base_url}/webhook/{webhook_secret}"
    
    # Create repository
    repo_id = create_repository(
        user_id=current_user["id"],
        repo_full_name=request.repo_full_name,
        webhook_secret=webhook_secret,
        webhook_url=webhook_url,
        github_token=request.github_token,
    )
    
    if not repo_id:
        raise HTTPException(
            status_code=400,
            detail="Repository already connected or invalid"
        )
    
    # Get created repository
    repo = get_repository_by_id(repo_id, current_user["id"])
    if not repo:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve created repository"
        )
    
    return RepositoryResponse(
        id=repo["id"],
        user_id=repo["user_id"],
        repo_full_name=repo["repo_full_name"],
        webhook_secret=repo["webhook_secret"],
        webhook_url=repo["webhook_url"],
        is_active=bool(repo.get("is_active", 1)),
        created_at=repo.get("created_at", ""),
    )


@router.get("/repositories/{repo_id}", response_model=RepositoryResponse)
def get_repository(
    repo_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get repository details."""
    repo = get_repository_by_id(repo_id, current_user["id"])
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return RepositoryResponse(
        id=repo["id"],
        user_id=repo["user_id"],
        repo_full_name=repo["repo_full_name"],
        webhook_secret=repo["webhook_secret"],
        webhook_url=repo["webhook_url"],
        is_active=bool(repo.get("is_active", 1)),
        created_at=repo.get("created_at", ""),
    )


@router.delete("/repositories/{repo_id}")
def disconnect_repository(
    repo_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Disconnect (deactivate) a repository."""
    success = deactivate_repository(repo_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return {"message": "Repository disconnected successfully"}

