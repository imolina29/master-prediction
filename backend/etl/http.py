import logging
import time

import httpx

logger = logging.getLogger(__name__)

RETRYABLE = (
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
)


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
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                wait = backoff * attempt
                logger.warning(
                    "HTTP %d from %s (attempt %d/%d). Retrying in %.0fs",
                    exc.response.status_code,
                    url,
                    attempt,
                    max_retries,
                    wait,
                )
                time.sleep(wait)
                continue
            raise
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
