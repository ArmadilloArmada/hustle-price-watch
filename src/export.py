"""Human-approve alerts → free delivery export (email draft + mailto). Never sends mail."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

# Soft cap so mailto: links stay usable in common mail clients / browsers.
_MAILTO_BODY_MAX = 1800


def _date_from_alerts_path(path: Path) -> str:
    m = re.search(r"alerts-(\d{4}-\d{2}-\d{2})\.md$", path.name)
    if m:
        return m.group(1)
    return date.today().isoformat()


def _extract_alert_headings(markdown: str) -> list[str]:
    """Pull ### item names under the Alerts section when present."""
    in_alerts = False
    names: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## Alerts"):
            in_alerts = True
            continue
        if in_alerts and line.startswith("## "):
            break
        if in_alerts and line.startswith("### "):
            names.append(line[4:].strip())
    return names


def render_email_draft(
    *,
    alerts_markdown: str,
    source_path: Path,
    to_addr: str,
    subject: str,
    run_date: str,
) -> str:
    alert_names = _extract_alert_headings(alerts_markdown)
    summary = (
        f"{len(alert_names)} threshold alert(s): " + ", ".join(alert_names)
        if alert_names
        else "No threshold alerts in this approved report (full status still attached)."
    )
    to_line = to_addr if to_addr else "(fill in recipient)"
    lines = [
        f"# Email draft — price watch {run_date}",
        "",
        "_Human-approved export. This file is for copy/paste into your mail client._",
        "_This tool never sends email automatically._",
        "",
        f"- **To:** {to_line}",
        f"- **Subject:** {subject}",
        f"- **Source (approved):** `{source_path.as_posix()}`",
        "",
        "## Suggested body",
        "",
        f"Price watch update for {run_date}.",
        "",
        summary,
        "",
        "---",
        "",
        "Full approved report:",
        "",
        alerts_markdown.strip(),
        "",
        "---",
        "",
        "## Compliance reminder",
        "",
        "- Public pages only; no login/CAPTCHA bypass.",
        "- Before affiliate monetization: add an FTC affiliate disclosure near links.",
        "",
    ]
    return "\n".join(lines)


def render_mailto_url(*, to_addr: str, subject: str, body: str) -> str:
    """Build a mailto URL. Body is truncated to keep the link openable."""
    clipped = body
    if len(clipped) > _MAILTO_BODY_MAX:
        clipped = (
            clipped[: _MAILTO_BODY_MAX].rstrip()
            + "\n\n[…truncated — paste the full email-draft file for the rest…]"
        )
    addr = to_addr.strip()
    query = f"subject={quote(subject)}&body={quote(clipped)}"
    if addr:
        return f"mailto:{addr}?{query}"
    return f"mailto:?{query}"


def mailto_body_from_draft(draft: str, run_date: str) -> str:
    """Shorter body for mailto — summary + pointer, not the whole report."""
    names = _extract_alert_headings(draft)
    if names:
        bullets = "\n".join(f"- {n}" for n in names)
        return (
            f"Price watch alerts for {run_date} (human-approved).\n\n"
            f"Threshold hits:\n{bullets}\n\n"
            "Open the matching email-draft-*.md under out/export/ for the full report.\n"
            "This link was generated locally — nothing was auto-sent.\n"
        )
    return (
        f"Price watch report for {run_date} (human-approved).\n\n"
        "No threshold alerts; see email-draft-*.md under out/export/ for full status.\n"
        "This link was generated locally — nothing was auto-sent.\n"
    )


def write_exports(
    *,
    alerts_path: Path,
    export_dir: Path,
    to_addr: str,
    subject: str | None,
    dry_run: bool = False,
) -> tuple[Path, Path, str]:
    if not alerts_path.is_file():
        raise FileNotFoundError(f"alerts file not found: {alerts_path}")
    if not re.match(r"alerts-\d{4}-\d{2}-\d{2}\.md$", alerts_path.name):
        raise ValueError(
            f"expected alerts-YYYY-MM-DD.md (got {alerts_path.name}); "
            "pass the human-reviewed file from out/"
        )

    markdown = alerts_path.read_text(encoding="utf-8")
    run_date = _date_from_alerts_path(alerts_path)
    subj = subject or f"Price watch alerts — {run_date}"

    draft = render_email_draft(
        alerts_markdown=markdown,
        source_path=alerts_path,
        to_addr=to_addr,
        subject=subj,
        run_date=run_date,
    )
    mailto_body = mailto_body_from_draft(markdown, run_date)
    mailto = render_mailto_url(to_addr=to_addr, subject=subj, body=mailto_body)

    draft_path = export_dir / f"email-draft-{run_date}.md"
    mailto_path = export_dir / f"mailto-{run_date}.txt"

    if dry_run:
        return draft_path, mailto_path, mailto

    export_dir.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(draft, encoding="utf-8")
    mailto_path.write_text(
        "\n".join(
            [
                "# Mailto (open in your mail client — nothing was sent)",
                "",
                mailto,
                "",
                "# Tip: if the link is too long for your OS, paste email-draft-*.md instead.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return draft_path, mailto_path, mailto


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="price-watch-export",
        description=(
            "After you review out/alerts-*.md, export a free email draft + mailto link "
            "under out/export/. Never sends email."
        ),
    )
    p.add_argument(
        "--approve",
        type=Path,
        required=True,
        metavar="ALERTS_MD",
        help="Path to the human-reviewed alerts-YYYY-MM-DD.md (required gate)",
    )
    p.add_argument(
        "--export-dir",
        type=Path,
        default=Path("out/export"),
        help="Directory for email-draft-*.md and mailto-*.txt (default: out/export)",
    )
    p.add_argument(
        "--to",
        default="",
        help="Optional recipient for To: / mailto (you still send manually)",
    )
    p.add_argument(
        "--subject",
        default=None,
        help="Optional email subject (default: Price watch alerts — YYYY-MM-DD)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print paths and mailto preview; write nothing",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        draft_path, mailto_path, mailto = write_exports(
            alerts_path=args.approve,
            export_dir=args.export_dir,
            to_addr=args.to,
            subject=args.subject,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("Human approve gate: OK (you passed --approve).", file=sys.stderr)
    print("Delivery mode: export only — never auto-emails.", file=sys.stderr)
    if args.dry_run:
        print(f"dry-run would write {draft_path}", file=sys.stderr)
        print(f"dry-run would write {mailto_path}", file=sys.stderr)
        print(mailto)
        return 0

    print(f"wrote {draft_path}", file=sys.stderr)
    print(f"wrote {mailto_path}", file=sys.stderr)
    print(draft_path)
    print(mailto_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
