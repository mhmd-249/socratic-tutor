"""API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, conversations

api_router = APIRouter()

# Include auth endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Include conversation endpoints
api_router.include_router(conversations.router, tags=["conversations"])
