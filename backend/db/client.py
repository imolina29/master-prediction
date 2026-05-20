from supabase import Client, create_client

from backend.config import Settings

_client: Client | None = None


def get_supabase(settings: Settings | None = None) -> Client:
    global _client
    if _client is None:
        if settings is None:
            settings = Settings()
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def reset_client():
    global _client
    _client = None
