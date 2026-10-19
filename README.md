# hustle-price-watch

Tier-0 MVP: **price / stock watch alerts** for **public pages only**.

Submit URLs + target prices in a CSV. The CLI politely fetches public HTML/JSON, extracts a price via optional CSS or JSON-path selectors, and writes a Markdown status report under `out/`.

No login, cookies, CAPTCHA bypass, or credentialed access. Optional LLM is **not** required — alerts are templated.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Dry-run with demo watchlist
python -m src.main
```

Output (always written, even when nothing alerts or fetches fail):

```text
out/alerts-YYYY-MM-DD.md
```

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

## Layout

```text
watchlist.csv          # demo rows
config.example.yaml    # optional knobs (documented; CLI flags are enough for MVP)
requirements.txt
pyproject.toml
src/
  main.py              # CLI entry
  fetch.py             # polite public GET
  parse.py             # CSS / JSON price extract
  alerts.py            # Markdown template report
out/
  .gitkeep
  alerts-YYYY-MM-DD.md # generated
```

## Compliance & affiliate disclosure

- **Public sources only.** Respect `robots.txt` / site Terms of Service. Prefer official public JSON/APIs when available.
- **No anti-bot bypass.** If a page blocks automated access, the run logs `fetch_failed` and continues — fix selectors or drop the URL.
- **FTC affiliate disclosure (for later monetization):** If you add affiliate links or earn commission from referred purchases, disclose that clearly near the links and in the product/README (e.g. “As an Amazon Associate I earn from qualifying purchases”). Required under FTC endorsement guides; do this before any affiliate monetization.

## License

MIT — see [`LICENSE`](LICENSE).
