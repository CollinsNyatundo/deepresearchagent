import base64
import json
import logging
import os

from supabase import Client, create_client

logger = logging.getLogger(__name__)

_supabase_client: Client | None = None


def _detect_key_role(key: str) -> str:
    """Decode the JWT payload to detect whether this is an anon or service_role key."""
    try:
        # JWT = header.payload.signature — decode the payload part
        parts = key.split(".")
        if len(parts) >= 2:
            # Add padding for base64 decoding
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            payload = json.loads(base64.b64decode(payload_b64).decode("utf-8"))
            return payload.get("role", "unknown")
    except Exception:
        pass
    return "unknown"


def get_supabase_client() -> Client:
    """Singleton getter for the Supabase Client.

    IMPORTANT: SUPABASE_KEY must be the ``service_role`` key, not the ``anon``
    key. The backend validates user identity independently via JWT; using the
    anon key causes Supabase RLS to block all workspace_members / notes /
    documents queries because ``auth.uid()`` is NULL for service calls, which
    produces 500 errors on every authenticated endpoint.

    Find the service_role key at:
      Supabase Dashboard → Settings → API → service_role (secret)
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error(
            "SUPABASE_URL or SUPABASE_KEY not set in environment. "
            "All database operations will fail. "
            "Set them in config.toml under [supabase] or as environment variables."
        )
        # Fallback placeholders so the app starts (will fail on first DB call)
        supabase_url = supabase_url or "https://placeholder-project.supabase.co"
        supabase_key = supabase_key or "placeholder-key"
    else:
        # Detect key role — anon key causes RLS to block all backend queries
        role = _detect_key_role(supabase_key)
        if role == "anon":
            logger.error(
                "SUPABASE_KEY is the ANON key — this will cause 403/500 errors on all "
                "workspace-scoped endpoints (notes, documents, runs) because Supabase RLS "
                "uses auth.uid() which is NULL for backend service calls. "
                "ACTION: Replace SUPABASE_KEY with the service_role key from "
                "Supabase Dashboard → Settings → API → service_role (secret)."
            )
        elif role == "service_role":
            logger.info("Supabase client initialized with service_role key. RLS bypass active.")
        else:
            logger.warning(
                f"SUPABASE_KEY role is '{role}' (expected 'service_role'). "
                "If you see 403 or 500 errors, check that the key is the service_role key."
            )

    try:
        _supabase_client = create_client(supabase_url, supabase_key)
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        raise

