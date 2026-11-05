# MOAT Radar

Open-source experimental investment research dashboard, hosted on GitHub Pages.

## Status

- Responsive interface: available in `index.html`.
- Four statuses: opportunity verified / quality-price watch / risk or overpriced / insufficient data.
- **Only 'insufficient data' is emitted by the current collector.** No financial score, moat, PER or buy signal is invented.
- S&P 500 universe (roughly 500 companies/share classes), fetched from the Wikipedia components table with exact SEC CIKs; this is not an official or real-time index constituent feed.
- Fundamental facts: SEC EDGAR companyfacts XBRL API. Incremental batches of 75 filings per daily run.
- **Not a live trading system.** US financial statements only; no reliable free market-price feed or European coverage yet.

## Enable the daily free collector (one-time step)

1. Open [Actions settings](https://github.com/alexandrelenoir26-oss/moat-radar/settings/variables/actions).
2. Create a repository variable named `SEC_CONTACT` with a real, contactable email address preceded by an identifier, for example `MOAT-Radar analyst contact@example.com` (replace the example address). **Do not put any password or API key in this variable**. It is a public contact string sent to SEC.
3. In GitHub repo Settings → Actions → General, ensure Actions are enabled and workflow permissions permit `Read and write permissions` where available. The workflow explicitly asks for `contents: write`, but organization policies may override it.
4. Run Actions → **Collect SEC fundamentals** → Run workflow, or wait for the daily UTC schedule.
5. GitHub Pages: Settings → Pages → Source → **GitHub Actions**. The deployment workflow is in `.github/workflows/pages.yml`.

The SEC requires an identified User-Agent and asks automated clients not to exceed ten requests per second. Collection uses a conservative ~2.5 req/s plus retry backoff, 75 companies each run. About seven successful daily runs are required for initial full coverage, assuming no blocking or changes. GitHub scheduled tasks can be delayed or skipped.

## Sources and licensing

- [SEC EDGAR companyfacts API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) — public US issuer filings.
- [Wikipedia S&P 500 constituents](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies) — CC BY-SA; attribution and license [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/). Content may change and is not guaranteed official.
- GitHub Actions / Pages — free for eligible public repositories, subject to provider limits and policies.

## Data principles

`data/companies.json` stores source URLs, fiscal periods, filing dates, and coverage. Annual financial measurements are not automatically comparable across all issuers (banks, insurance, fiscal-year variation and taxonomy differences). Absent or stale values stay null. A valid price/valuation model and sector-specific moat review are prerequisites for non-unknown status.

## Run locally

```sh
python -m pip install 'beautifulsoup4>=4.12,<5'
SEC_CONTACT='MOAT-Radar your-real-address@example.com' BATCH_SIZE=10 python scripts/collect.py
```

Replace the placeholder with a valid email you control. Do not publish personal addresses unless you're comfortable with them appearing in process logs or public contexts.

## Disclaimer

Experimental informational software, not personalized investment advice. No warranty of accuracy, completeness, price timeliness, or investment return.
