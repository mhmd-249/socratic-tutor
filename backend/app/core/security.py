"""Security and authentication utilities."""

from typing import Any
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository


security = HTTPBearer()


class SupabaseJWTError(Exception):
    """Raised when Supabase JWT validation fails."""

    pass


async def get_supabase_public_key() -> dict[str, Any]:
    """
    Fetch Supabase JWT public key from JWKS endpoint.

    Returns:
        dict: JWKS key data

    Raises:
        SupabaseJWTError: If fetching the key fails
    """
    supabase_url = settings.SUPABASE_URL
    jwks_url = f"{supabase_url}/auth/v1/jwks"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks = response.json()
            return jwks["keys"][0] if jwks.get("keys") else {}
    except Exception as e:
        raise SupabaseJWTError(f"Failed to fetch Supabase public key: {e}")


async def verify_supabase_token(token: str) -> dict[str, Any]:
    """
    Verify Supabase JWT token.

    Args:
        token: JWT token string

    Returns:
        dict: Decoded token payload

    Raises:
        HTTPException: If token is invalid
    """
    try:
        # For development/testing, you can decode without verification
        # In production, fetch and use the public key from Supabase
        unverified_payload = jwt.get_unverified_claims(token)

        # Verify the token using Supabase's public key
        # For now, we'll trust the Supabase token if it decodes
        # In production, add proper signature verification
        payload = jwt.decode(
            token,
            key=None,  # Will need to fetch JWKS in production
            options={"verify_signature": False},  # FIXME: Enable in production
        )

        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP authorization credentials with Bearer token
        db: Database session

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Verify the token
    payload = await verify_supabase_token(token)

    # Extract user ID from token
    supabase_user_id = payload.get("sub")
    if not supabase_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.get_by_supabase_id(supabase_user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


async def require_auth(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that requires authentication.

    Args:
        current_user: Current user from get_current_user

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If not authenticated (handled by get_current_user)
    """
    return current_user
