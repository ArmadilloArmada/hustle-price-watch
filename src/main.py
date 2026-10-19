"""CLI: watchlist.csv → polite fetch → out/alerts-YYYY-MM-DD.md."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.alerts import RunReport, WatchItemResult, write_report
from src.fetch import DEFAULT_UA, fetch_url, sleep_polite
from src.parse import parse_payload


@dataclass
class WatchRow:
    name: str
    url: str
    target_price: float
    selector: str
    selector_type: str
    notes: str


def load_watchlist(path: Path) -> list[WatchRow]:
    rows: list[WatchRow] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"name", "url", "target_price"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise SystemExit(
                f"{path}: CSV must include columns name, url, target_price "
                "(optional: selector, selector_type, notes)"
            )
        for i, raw in enumerate(reader, start=2):
            name = (raw.get("name") or "").strip()
            url = (raw.get("url") or "").strip()
            tp_raw = (raw.get("target_price") or "").strip()
            if not name or not url or not tp_raw:
                print(f"skip line {i}: missing name/url/target_price", file=sys.stderr)
                continue
            try:
                target = float(tp_raw)
            except ValueError:
                print(f"skip line {i}: bad target_price {tp_raw!r}", file=sys.stderr)
                continue
            rows.append(
                WatchRow(
                    name=name,
                    url=url,
                    target_price=target,
                    selector=(raw.get("selector") or "").strip(),
                    selector_type=(raw.get("selector_type") or "").strip().lower(),
                    notes=(raw.get("notes") or "").strip(),
                )
            )
    return rows


def evaluate_row(
    row: WatchRow,
    *,
    user_agent: str,
    timeout: float,
    retries: int,
) -> WatchItemResult:
    fetched = fetch_url(
        row.url,
        user_agent=user_agent,
        timeout=timeout,
        retries=retries,
    )
    if not fetched.ok:
        return WatchItemResult(
            name=row.name,
            url=row.url,
            target_price=row.target_price,
            status="fetch_failed",
            message=fetched.error or "fetch failed",
            notes=row.notes,
        )

    parsed = parse_payload(
        fetched.text,
        content_type=fetched.content_type,
        selector=row.selector,
        selector_type=row.selector_type,
    )
    if not parsed.ok or parsed.price is None:
        return WatchItemResult(
            name=row.name,
            url=row.url,
            target_price=row.target_price,
            status="parse_failed" if parsed.error else "no_price",
            raw_value=parsed.raw_value,
            message=parsed.error or "no price extracted",
            notes=row.notes,
        )

    if parsed.price <= row.target_price:
        status = "alert"
        message = "at or below target"
    else:
        status = "above_target"
        message = "still above target"

    return WatchItemResult(
        name=row.name,
        url=row.url,
        target_price=row.target_price,
        status=status,
        observed_price=parsed.price,
        raw_value=parsed.raw_value,
        message=message,
        notes=row.notes,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="price-watch",
        description="Monitor public product/JSON pages against a CSV watchlist; write Markdown alerts.",
    )
    p.add_argument(
        "--watchlist",
        type=Path,
        default=Path("watchlist.csv"),
        help="CSV with name,url,target_price[,selector,selector_type,notes]",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="Directory for alerts-YYYY-MM-DD.md",
    )
    p.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout seconds")
    p.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    p.add_argument("--retries", type=int, default=1, help="Retries after a failed fetch")
    p.add_argument("--user-agent", default=DEFAULT_UA, help="User-Agent for polite fetches")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.watchlist.is_file():
        print(f"watchlist not found: {args.watchlist}", file=sys.stderr)
        return 1

    rows = load_watchlist(args.watchlist)
    if not rows:
        print("watchlist is empty", file=sys.stderr)
        return 1

    report = RunReport(run_date=date.today())
    for i, row in enumerate(rows):
        if i > 0:
            sleep_polite(args.delay)
        print(f"fetch {row.name}: {row.url}", file=sys.stderr)
        result = evaluate_row(
            row,
            user_agent=args.user_agent,
            timeout=args.timeout,
            retries=args.retries,
        )
        print(f"  → {result.status}" + (f" ({result.message})" if result.message else ""), file=sys.stderr)
        report.results.append(result)

    out_path = write_report(report, args.out_dir)
    print(f"wrote {out_path}", file=sys.stderr)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
