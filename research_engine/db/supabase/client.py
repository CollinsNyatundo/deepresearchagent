import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_supabase_client: Client | None = None

def get_supabase_client() -> Client:
    """Singleton getter for the Supabase Client."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.warning(
            "SUPABASE_URL or SUPABASE_KEY not set in environment. "
            "Supabase database integrations will fail."
        )
        # Fallback placeholders for safety in initialization
        supabase_url = "https://placeholder-project.supabase.co"
        supabase_key = "placeholder-anon-key"

    try:
        _supabase_client = create_client(supabase_url, supabase_key)
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        raise
