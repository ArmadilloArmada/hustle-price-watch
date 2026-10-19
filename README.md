# hustle-price-watch

Tier-0 MVP: **price / stock watch alerts** for **public pages only**.

Submit URLs + target prices in a CSV. The CLI politely fetches public HTML/JSON, extracts a price via optional CSS or JSON-path selectors, and writes a Markdown status report under `out/`.

**Human approve → free export.** Review `out/alerts-*.md`, then export an email draft + `mailto:` link under `out/export/`. **Nothing is ever emailed automatically.**

No login, cookies, CAPTCHA bypass, or credentialed access. Optional LLM is **not** required — alerts are templated.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Dry-run with demo watchlist (writes out/alerts-YYYY-MM-DD.md)
python -m src.main
```

## Human approve + free alert delivery

1. Open the generated report and review it yourself:

```text
out/alerts-YYYY-MM-DD.md
```

2. When you approve that file, export free delivery artifacts (still no send):

```bash
# Dry-run export (prints paths + mailto; writes nothing)
python -m src.export --approve out/alerts-YYYY-MM-DD.md --dry-run

# Write email draft + mailto under out/export/
python -m src.export --approve out/alerts-YYYY-MM-DD.md --to you@example.com
```

Export paths:

```text
out/export/email-draft-YYYY-MM-DD.md   # copy/paste into Gmail, etc.
out/export/mailto-YYYY-MM-DD.txt       # open the mailto: URL in a mail client
```

`--approve` is required: you must pass the specific `alerts-*.md` you reviewed. The exporter never calls an SMTP API, webhook, or Telegram bot.

## Watchlist CSV

Demo file: [`watchlist.csv`](watchlist.csv)

| Column | Required | Description |
|--------|----------|-------------|
| `name` | yes | Label for the alert |
| `url` | yes | Public product page or JSON URL |
| `target_price` | yes | Alert when observed price ≤ this value |
| `selector` | no | CSS selector (HTML) or dotted JSON path |
| `selector_type` | no | `css` or `json` (auto-guessed from content-type if empty) |
| `notes` | no | Free text |

Example:

```csv
name,url,target_price,selector,selector_type,notes
Widget sale,https://example.com/product,19.99,.price,css,Demo
API quote,https://api.example.com/quote,100,data.price,json,
```

## CLI options

### Watch (fetch → report)

```bash
python -m src.main --watchlist watchlist.csv --out-dir out --delay 1.0 --timeout 20
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--watchlist` | `watchlist.csv` | Input CSV |
| `--out-dir` | `out` | Alert output directory |
| `--delay` | `1.0` | Seconds between requests (be polite) |
| `--timeout` | `20` | HTTP timeout seconds |
| `--retries` | `1` | Extra attempts after a failed fetch |
| `--user-agent` | project UA | Identify the client |

### Export (approve → draft)

```bash
python -m src.export --approve out/alerts-YYYY-MM-DD.md --export-dir out/export --to you@example.com
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--approve` | _(required)_ | Human-reviewed `alerts-YYYY-MM-DD.md` |
| `--export-dir` | `out/export` | Where to write draft + mailto |
| `--to` | _(empty)_ | Optional recipient for To: / mailto |
| `--subject` | auto | Optional subject line |
| `--dry-run` | off | Preview only; write nothing |

## Layout

```text
watchlist.csv          # demo rows
config.example.yaml    # optional knobs (documented; CLI flags are enough for MVP)
requirements.txt
pyproject.toml
src/
  main.py              # watch CLI entry
  fetch.py             # polite public GET
  parse.py             # CSS / JSON price extract
  alerts.py            # Markdown template report
  export.py            # human-approve → email-draft + mailto (no send)
out/
  .gitkeep
  alerts-YYYY-MM-DD.md # generated (gitignored)
  export/
    .gitkeep
    email-draft-*.md   # generated after --approve (gitignored)
    mailto-*.txt       # generated after --approve (gitignored)
```

## Weekly schedule (GitHub Actions)

Every Monday at **14:30 UTC**, [`.github/workflows/weekly-price-watch.yml`](.github/workflows/weekly-price-watch.yml) runs a **draft-only** pipeline (`python -m src.main`) and uploads artifact **`price-watch-draft`** (no approve/export/send). Download from the Actions run → **Artifacts**, unzip into `out/`, then approve + export locally.

## Compliance & affiliate disclosure

- **Public sources only.** Respect `robots.txt` / site Terms of Service. Prefer official public JSON/APIs when available.
- **No anti-bot bypass.** If a page blocks automated access, the run logs `fetch_failed` and continues — fix selectors or drop the URL.
- **Never auto-email.** Delivery is copy/paste or a local `mailto:` open after you approve `out/alerts-*.md`.
- **FTC affiliate disclosure (for later monetization):** If you add affiliate links or earn commission from referred purchases, disclose that clearly near the links and in the product/README (e.g. “As an Amazon Associate I earn from qualifying purchases”). Required under FTC endorsement guides; do this before any affiliate monetization. Reminder only for now — no affiliate links in this MVP.

## License

MIT — see [`LICENSE`](LICENSE).
