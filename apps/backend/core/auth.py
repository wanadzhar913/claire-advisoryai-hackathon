"""Clerk JWT authentication module for FastAPI."""

import time
from typing import Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Try to import settings and models, with fallback for when running as script
try:
    from backend.config import settings
    from backend.models.user import User
    from backend.services.db.postgres_connector import database_service
except ImportError:
    import sys
    from pathlib import Path
    apps_dir = Path(__file__).parent.parent.parent
    if str(apps_dir) not in sys.path:
        sys.path.insert(0, str(apps_dir))
    from backend.config import settings
    from backend.models.user import User
    from backend.services.db.postgres_connector import database_service


# Security scheme for Bearer token
security = HTTPBearer()

# Cache for JWKS (JSON Web Key Set)
_jwks_cache: dict = {}
_jwks_cache_time: float = 0
JWKS_CACHE_TTL = 3600  # Cache JWKS for 1 hour


async def get_jwks() -> dict:
    """Fetch and cache Clerk's JWKS (JSON Web Key Set).
    
    Returns:
        dict: The JWKS containing public keys for JWT verification.
    """
    global _jwks_cache, _jwks_cache_time
    
    current_time = time.time()
    
    # Return cached JWKS if still valid
    if _jwks_cache and (current_time - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache
    
    # Fetch fresh JWKS from Clerk
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.CLERK_JWKS_URL)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = current_time
        
    return _jwks_cache


def get_public_key_from_jwks(jwks: dict, kid: str) -> Optional[jwt.algorithms.RSAAlgorithm]:
    """Extract the public key matching the given key ID from JWKS.
    
    Args:
        jwks: The JWKS containing public keys.
        kid: The key ID to look for.
        
    Returns:
        The RSA public key if found, None otherwise.
    """
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)
    return None


async def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT token and return the decoded payload.
    
    Args:
        token: The JWT token to verify.
        
    Returns:
        dict: The decoded token payload containing user information.
        
    Raises:
        HTTPException: If token verification fails.
    """
    try:
        # Decode header to get key ID (kid)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing key ID",
            )
        
        # Get JWKS and find matching public key
        jwks = await get_jwks()
        public_key = get_public_key_from_jwks(jwks, kid)
        
        if not public_key:
            # Key not found, try refreshing JWKS cache
            global _jwks_cache_time
            _jwks_cache_time = 0  # Force refresh
            jwks = await get_jwks()
            public_key = get_public_key_from_jwks(jwks, kid)
            
            if not public_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: key not found",
                )
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            # Clerk doesn't always set audience; also allow small clock skew for iat/nbf/exp.
            options={"verify_aud": False},
            leeway=60,
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


async def get_or_create_user_from_clerk(clerk_id: str, email: Optional[str] = None) -> User:
    """Get existing user by Clerk ID or create a new one.
    
    Args:
        clerk_id: The Clerk user ID (sub claim from JWT).
        email: Optional email address from the token.
        
    Returns:
        User: The existing or newly created user.
    """
    # Try to find existing user by clerk_id
    user = await database_service.get_user_by_clerk_id(clerk_id)
    
    if user:
        return user
    
    # Create new user with Clerk ID
    # Use email from token or generate a placeholder
    user_email = email or f"{clerk_id}@clerk.user"
    
    user = await database_service.create_user_from_clerk(
        clerk_id=clerk_id,
        email=user_email,
    )
    
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """FastAPI dependency to get the current authenticated user.
    
    This dependency:
    1. Extracts the Bearer token from the Authorization header
    2. Verifies the token with Clerk's public keys
    3. Gets or creates a local user based on the Clerk user ID
    
    Args:
        credentials: The HTTP Authorization credentials containing the Bearer token.
        
    Returns:
        User: The authenticated user.
        
    Raises:
        HTTPException: If authentication fails.
    """
    token = credentials.credentials
    
    # Verify the token and get payload
    payload = await verify_clerk_token(token)
    
    # Extract user info from token
    clerk_id = payload.get("sub")  # Clerk user ID
    email = payload.get("email")
    
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
        )
    
    # Get or create local user
    user = await get_or_create_user_from_clerk(clerk_id, email)
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> Optional[User]:
    """FastAPI dependency to optionally get the current authenticated user.
    
    Similar to get_current_user but returns None instead of raising an exception
    if no valid token is provided. Useful for endpoints that work with or without auth.
    
    Args:
        credentials: Optional HTTP Authorization credentials.
        
    Returns:
        Optional[User]: The authenticated user or None.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
