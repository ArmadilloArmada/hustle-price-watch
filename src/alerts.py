"""Template alert report writer (no LLM required)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path


@dataclass
class WatchItemResult:
    name: str
    url: str
    target_price: float
    status: str  # alert | below_target | no_price | fetch_failed | parse_failed
    observed_price: float | None = None
    raw_value: str | None = None
    message: str = ""
    notes: str = ""


@dataclass
class RunReport:
    run_date: date
    results: list[WatchItemResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def alert_count(self) -> int:
        return sum(1 for r in self.results if r.status == "alert")

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if r.status in ("fetch_failed", "parse_failed"))


def _fmt_price(value: float) -> str:
    """Format money-like numbers without scientific notation or float noise."""
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if text else "0"


def render_markdown(report: RunReport) -> str:
    lines: list[str] = [
        f"# Price watch alerts — {report.run_date.isoformat()}",
        "",
        f"_Generated at {report.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}_",
        "",
        "## Summary",
        "",
        f"- Watched: **{len(report.results)}**",
        f"- Threshold met (alert): **{report.alert_count}**",
        f"- Fetch/parse issues: **{report.failure_count}**",
        "",
    ]

    alerts = [r for r in report.results if r.status == "alert"]
    if alerts:
        lines.extend(["## Alerts (at or below target)", ""])
        for r in alerts:
            price = _fmt_price(r.observed_price) if r.observed_price is not None else "?"
            lines.append(f"### {r.name}")
            lines.append("")
            lines.append(f"- URL: {r.url}")
            lines.append(f"- Observed: **{price}** ≤ target **{_fmt_price(r.target_price)}**")
            if r.raw_value:
                lines.append(f"- Raw: `{r.raw_value}`")
            if r.message:
                lines.append(f"- Note: {r.message}")
            lines.append("")
    else:
        lines.extend(
            [
                "## Alerts (at or below target)",
                "",
                "_No threshold alerts this run._",
                "",
            ]
        )

    lines.extend(["## Full status", ""])
    for r in report.results:
        obs = _fmt_price(r.observed_price) if r.observed_price is not None else "—"
        lines.append(f"### {r.name}")
        lines.append("")
        lines.append(f"- Status: `{r.status}`")
        lines.append(f"- URL: {r.url}")
        lines.append(f"- Target: {_fmt_price(r.target_price)}")
        lines.append(f"- Observed: {obs}")
        if r.raw_value:
            lines.append(f"- Raw: `{r.raw_value[:120]}`")
        if r.message:
            lines.append(f"- Detail: {r.message}")
        if r.notes:
            lines.append(f"- Watchlist notes: {r.notes}")
        lines.append("")

    lines.extend(
        [
            "## Compliance",
            "",
            "- Public pages / public JSON only; polite User-Agent and request delay.",
            "- No login, cookies, CAPTCHA bypass, or credentialed access.",
            "- If you later monetize via affiliate links, include an FTC affiliate disclosure.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: RunReport, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"alerts-{report.run_date.isoformat()}.md"
    path.write_text(render_markdown(report), encoding="utf-8")
    return path
