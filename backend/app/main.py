"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Socratic Tutor API",
        description="AI-powered Socratic teaching assistant backend",
        version="0.1.0",
    )

    # Configure CORS - MUST be added before routes
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "User-Agent",
            "DNT",
            "Cache-Control",
            "X-Requested-With",
        ],
        expose_headers=[
            "Content-Length",
            "Content-Type",
            "Cache-Control",
            "X-Accel-Buffering",
        ],
        max_age=600,  # Cache preflight requests for 10 minutes
    )

    # Include API router
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_application()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
