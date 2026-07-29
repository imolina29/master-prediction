import os

from fastapi import Header, HTTPException

API_KEYS: dict[str, str] = {}


def _load_keys():
    global API_KEYS
    for key, val in os.environ.items():
        if key.startswith("API_KEY_") and val:
            client_name = key.replace("API_KEY_", "").lower()
            API_KEYS[val] = client_name


def verify_api_key(key: str) -> str | None:
    if not API_KEYS:
        _load_keys()
    return API_KEYS.get(key)


async def require_api_key(x_api_key: str = Header(...)):
    """FastAPI dependency: validate X-API-Key header."""
    if not API_KEYS:
        _load_keys()
    client = API_KEYS.get(x_api_key)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return client
