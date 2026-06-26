import logging
import os

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Load .env at module import time so env vars are available regardless
# of whether the caller remembered to call load_dotenv().
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely on shell env

logger = logging.getLogger(__name__)


def _is_dev_bypass() -> bool:
    """Check DEV_AUTH_BYPASS at call time (not import time) so that
    load_dotenv() in cli.py or a re-read of os.environ always wins."""
    import sys
    if "pytest" in sys.modules:
        return False
    return os.environ.get("DEV_AUTH_BYPASS", "false").lower() == "true"


# HTTPBearer with auto_error=False so the dependency runs even without
# an Authorization header; we gate on _is_dev_bypass() below.
security = HTTPBearer(auto_error=False)


def get_supabase_jwt_secret() -> str:
    """Retrieve the Supabase JWT secret from environment variables."""
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise RuntimeError("SUPABASE_JWT_SECRET is not set in the environment variables.")
    return secret


async def verify_supabase_jwt(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """FastAPI dependency to authenticate and decode a Supabase user token.

    In development (DEV_AUTH_BYPASS=true) the JWT check is skipped entirely
    and a synthetic admin payload is returned so the server starts without
    requiring Supabase credentials.
    """
    if _is_dev_bypass():
        logger.debug(
            "DEV_AUTH_BYPASS is enabled — skipping JWT validation. "
            "Do NOT use this in production."
        )
        return {
            "sub": "dev-bypass-user",
            "email": "dev@localhost",
            "role": "authenticated",
            "app_metadata": {"role": "admin"},
        }

    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = credentials.credentials
    secret = get_supabase_jwt_secret()

    try:
        # Supabase uses HS256 by default; RS256 for projects using custom JWT.
        # We try HS256 first, then RS256 if the header specifies it.
        alg = jwt.get_unverified_header(token).get("alg", "HS256")
        allowed = ["HS256", "RS256"]
        if alg not in allowed:
            raise jwt.InvalidAlgorithmError(f"Unsupported algorithm: {alg}")

        payload = jwt.decode(
            token,
            secret,
            algorithms=allowed,
            options={"verify_aud": False},  # Supabase audience varies by project
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        logger.warning(f"Supabase JWT expired: {e}")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Supabase JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as e:
        logger.error(f"Unexpected error validating token: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")
