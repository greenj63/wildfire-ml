"""Small HTTP helpers (standard library only) shared by every live data source."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "wildfire-ml-live/0.1 (class project)"


class ApiError(RuntimeError):
    """A live data source failed or returned something unusable."""


def get_text(url: str, params: dict | None = None, timeout: int = 60, retries: int = 3):
    """GET a URL and return the body as text. Retries on network and server errors."""
    if params:
        url = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode(params)}"
    last_error = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code < 500:  # retrying a bad request won't help
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            last_error = error
        time.sleep(2 * (attempt + 1))
    raise ApiError(f"Request failed ({last_error}): {url[:200]}")


def get_json(url: str, params: dict | None = None, **kwargs) -> dict:
    """GET JSON. ArcGIS reports errors inside a 200 response, so check for that."""
    try:
        data = json.loads(get_text(url, params, **kwargs))
    except json.JSONDecodeError as error:
        raise ApiError(f"Not JSON: {url[:200]}") from error
    if isinstance(data, dict) and "error" in data:
        raise ApiError(f"{url[:120]} returned error: {data['error']}")
    return data
