"""Security and authentication utilities."""

import logging
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwk, jwt, JWTError
from jose.utils import base64url_decode
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Supabase JWT configuration
SUPABASE_JWT_AUDIENCE = "authenticated"
# Supabase uses ES256 (ECDSA) for newer projects, HS256 for older ones
SUPABASE_JWT_ALGORITHMS = ["ES256", "HS256"]

# Cache for JWKS public keys
_jwks_cache: dict[str, Any] | None = None


class SupabaseJWTError(Exception):
    """Raised when Supabase JWT validation fails."""

    pass


async def get_supabase_jwks() -> dict[str, Any]:
    """
    Fetch Supabase JWKS (JSON Web Key Set) from endpoint.
    Caches the result to avoid repeated network calls.

    Returns:
        dict: JWKS data with keys

    Raises:
        SupabaseJWTError: If fetching fails
    """
    global _jwks_cache

    if _jwks_cache is not None:
        return _jwks_cache

    supabase_url = settings.SUPABASE_URL

    # Debug: Log the SUPABASE_URL value
    logger.info(f"SUPABASE_URL value: '{supabase_url}' (length: {len(supabase_url) if supabase_url else 0})")

    if not supabase_url:
        raise SupabaseJWTError(
            "SUPABASE_URL is not set. Check your .env file and ensure "
            "docker-compose.yml has env_file: ./backend/.env"
        )

    if not supabase_url.startswith(("http://", "https://")):
        raise SupabaseJWTError(
            f"SUPABASE_URL must start with http:// or https://, got: '{supabase_url}'"
        )

    jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"

    try:
        logger.info(f"Fetching JWKS from {jwks_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
            logger.info(f"Fetched JWKS with {len(_jwks_cache.get('keys', []))} keys")
            return _jwks_cache
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise SupabaseJWTError(f"Failed to fetch Supabase JWKS: {e}")


def get_signing_key_from_jwks(jwks: dict[str, Any], kid: str | None) -> Any:
    """
    Get the signing key from JWKS matching the key ID.

    Args:
        jwks: JWKS response from Supabase
        kid: Key ID from JWT header

    Returns:
        The signing key for verification
    """
    keys = jwks.get("keys", [])

    if not keys:
        raise SupabaseJWTError("No keys found in JWKS")

    # If kid is provided, find matching key
    if kid:
        for key_data in keys:
            if key_data.get("kid") == kid:
                return jwk.construct(key_data)

    # Fallback to first key
    return jwk.construct(keys[0])


async def verify_supabase_token(token: str) -> dict[str, Any]:
    """
    Verify Supabase JWT token.

    Supports both ES256 (newer Supabase projects) and HS256 (older projects).
    For ES256: Uses public key from JWKS endpoint.
    For HS256: Uses SUPABASE_JWT_SECRET from environment.

    Args:
        token: JWT token string

    Returns:
        dict: Decoded token payload

    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Get unverified header to determine algorithm and key ID
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg")
        kid = unverified_header.get("kid")

        logger.debug(f"JWT algorithm: {alg}, kid: {kid}")

        if alg == "ES256":
            # ES256 uses asymmetric keys - fetch public key from JWKS
            logger.debug("Using ES256 - fetching public key from JWKS")
            jwks_data = await get_supabase_jwks()
            signing_key = get_signing_key_from_jwks(jwks_data, kid)

            payload = jwt.decode(
                token,
                key=signing_key,
                algorithms=["ES256"],
                audience=SUPABASE_JWT_AUDIENCE,
            )

        elif alg == "HS256":
            # HS256 uses symmetric key (JWT secret)
            if not settings.SUPABASE_JWT_SECRET:
                logger.warning(
                    "HS256 token but SUPABASE_JWT_SECRET not set - "
                    "skipping signature verification"
                )
                payload = jwt.decode(
                    token,
                    key="",
                    algorithms=["HS256"],
                    audience=SUPABASE_JWT_AUDIENCE,
                    options={"verify_signature": False},
                )
            else:
                logger.debug("Using HS256 with JWT secret")
                payload = jwt.decode(
                    token,
                    key=settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience=SUPABASE_JWT_AUDIENCE,
                )

        else:
            raise JWTError(f"Unsupported algorithm: {alg}")

        logger.debug(f"JWT verified successfully for user: {payload.get('sub')}")
        return payload

    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
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
