"""Extract prices from public HTML/JSON using optional CSS or JSON-path selectors."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup

# Common currency / number patterns
_PRICE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:USD|US\$|\$|EUR|€|GBP|£)?\s*"
    r"(\d{1,3}(?:,\d{3})*(?:\.\d{1,4})?|\d+(?:\.\d{1,4})?)"
)


@dataclass
class ParseResult:
    ok: bool
    price: float | None
    raw_value: str | None
    error: str | None = None


def _to_float(text: str) -> float | None:
    cleaned = text.strip().replace(",", "")
    cleaned = re.sub(r"^[^\d.-]+", "", cleaned)
    cleaned = re.sub(r"[^\d.-]+$", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_price_from_text(text: str) -> ParseResult:
    if not text or not text.strip():
        return ParseResult(ok=False, price=None, raw_value=None, error="empty text")
    m = _PRICE_RE.search(text)
    if not m:
        return ParseResult(
            ok=False,
            price=None,
            raw_value=text.strip()[:200],
            error="no numeric price found in text",
        )
    price = _to_float(m.group(1))
    if price is None:
        return ParseResult(
            ok=False,
            price=None,
            raw_value=m.group(0),
            error="could not parse matched number",
        )
    return ParseResult(ok=True, price=price, raw_value=m.group(0).strip(), error=None)


def _json_path_get(data: Any, path: str) -> Any:
    """Simple dotted path: a.b.0.c — keys and integer indices."""
    cur: Any = data
    for part in path.split("."):
        if part == "":
            continue
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError) as exc:
                raise KeyError(path) from exc
        elif isinstance(cur, dict):
            if part not in cur:
                raise KeyError(path)
            cur = cur[part]
        else:
            raise KeyError(path)
    return cur


def parse_json_selector(text: str, selector: str) -> ParseResult:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return ParseResult(ok=False, price=None, raw_value=None, error=f"invalid JSON: {exc}")

    if not selector.strip():
        # Whole document as string — try to find a price-like number
        return extract_price_from_text(json.dumps(data))

    try:
        value = _json_path_get(data, selector.strip())
    except KeyError:
        return ParseResult(
            ok=False,
            price=None,
            raw_value=None,
            error=f"JSON path not found: {selector}",
        )

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return ParseResult(ok=True, price=float(value), raw_value=str(value), error=None)
    if isinstance(value, str):
        return extract_price_from_text(value)
    return ParseResult(
        ok=False,
        price=None,
        raw_value=str(value)[:200],
        error=f"JSON value is not a price-like number ({type(value).__name__})",
    )


def parse_css_selector(html: str, selector: str) -> ParseResult:
    soup = BeautifulSoup(html, "lxml")
    if not selector.strip():
        return extract_price_from_text(soup.get_text(" ", strip=True))

    nodes = soup.select(selector.strip())
    if not nodes:
        return ParseResult(
            ok=False,
            price=None,
            raw_value=None,
            error=f"CSS selector matched nothing: {selector}",
        )
    # Prefer content / value attrs then text
    chunks: list[str] = []
    for node in nodes[:5]:
        for attr in ("content", "value", "data-price", "data-amount"):
            if node.has_attr(attr) and node[attr]:
                chunks.append(str(node[attr]))
        chunks.append(node.get_text(" ", strip=True))
    combined = " ".join(c for c in chunks if c)
    return extract_price_from_text(combined)


def parse_payload(
    text: str,
    *,
    content_type: str,
    selector: str,
    selector_type: str,
) -> ParseResult:
    st = (selector_type or "").strip().lower()
    if st == "json" or (not st and "json" in (content_type or "")):
        return parse_json_selector(text, selector)
    if st in ("css", "html", "") or "html" in (content_type or ""):
        # Prefer JSON if body looks like JSON and type said css but content is json
        stripped = text.lstrip()
        if st == "json" or stripped.startswith("{") or stripped.startswith("["):
            if st == "json" or "json" in (content_type or ""):
                return parse_json_selector(text, selector)
        return parse_css_selector(text, selector)
    # Fallback: try JSON then HTML
    if text.lstrip().startswith(("{", "[")):
        return parse_json_selector(text, selector)
    return parse_css_selector(text, selector)
