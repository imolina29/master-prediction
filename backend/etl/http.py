import logging
import time

import httpx

logger = logging.getLogger(__name__)

RETRYABLE = (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError)


def get_with_retry(
    url: str,
    *,
    max_retries: int = 3,
    backoff: float = 5.0,
    timeout: float = 30.0,
    **kwargs,
) -> httpx.Response:
    for attempt in range(1, max_retries + 1):
        try:
            resp = httpx.get(url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except RETRYABLE as exc:
            if attempt == max_retries:
                raise
            wait = backoff * attempt
            logger.warning(
                "Request to %s failed (attempt %d/%d): %s. Retrying in %.0fs",
                url,
                attempt,
                max_retries,
                exc,
                wait,
            )
            time.sleep(wait)
    raise RuntimeError("unreachable")
