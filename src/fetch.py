"""Polite HTTP fetch for public HTML/JSON pages only."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_UA = (
    "hustle-price-watch/0.1 "
    "(+https://github.com/ArmadilloArmada/hustle-price-watch; polite public fetch)"
)


@dataclass
class FetchResult:
    url: str
    ok: bool
    status_code: int | None
    content_type: str
    text: str
    error: str | None = None


def fetch_url(
    url: str,
    *,
    user_agent: str = DEFAULT_UA,
    timeout: float = 20.0,
    retries: int = 1,
) -> FetchResult:
    """GET a public URL. No cookies, auth, or anti-bot bypass."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/json,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    }
    last_error: str | None = None
    attempts = max(1, retries + 1)

    for attempt in range(attempts):
        try:
            with httpx.Client(
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                resp = client.get(url)
                ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
                if resp.status_code >= 400:
                    last_error = f"HTTP {resp.status_code}"
                    if attempt + 1 < attempts:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    return FetchResult(
                        url=url,
                        ok=False,
                        status_code=resp.status_code,
                        content_type=ctype,
                        text="",
                        error=last_error,
                    )
                return FetchResult(
                    url=str(resp.url),
                    ok=True,
                    status_code=resp.status_code,
                    content_type=ctype,
                    text=resp.text,
                    error=None,
                )
        except httpx.HTTPError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt + 1 < attempts:
                time.sleep(0.5 * (attempt + 1))
                continue

    return FetchResult(
        url=url,
        ok=False,
        status_code=None,
        content_type="",
        text="",
        error=last_error or "unknown fetch error",
    )


def sleep_polite(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)
