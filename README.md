> **Architecture decision (2026-11-06):** MOAT Radar production must run indefinitely without monthly API-key renewal. The HF Data Library / IEX importer is retained as an optional experimental script, but is no longer called by the scheduled GitHub Actions workflow. Its data must not be used to issue investment signals. The supported unattended production data source remains SEC EDGAR. For valuation, assess SEC public quarterly Form 13F holdings as a *lagged historical reference* subject to security-identifier reconciliation, splits, 13F coverage gaps and filing accuracy. This is not a live price feed and cannot be marketed as a current PER or buy signal. No market data supplier has yet been identified that is simultaneously free, legally redistributable, complete and current.\n\n# MOAT Radar

Open-source experimental investment research dashboard, hosted on GitHub Pages.

## Status

- Responsive interface: available in `index.html`.
- Four statuses: opportunity verified / quality-price watch / risk or overpriced / insufficient data.
- **Only 'insufficient data' is emitted by the current collector.** No financial score, moat, PER or buy signal is invented.
- S&P 500 universe (roughly 500 companies/share classes), fetched from the Wikipedia components table with exact SEC CIKs; this is not an official or real-time index constituent feed.
- Fundamental facts: SEC EDGAR companyfacts XBRL API. Initial full backfill completed; daily SEC refresh rotates through issuers. Financial V2 indices are preliminary.
- **Not a live trading system.** US financial statements only; no reliable free market-price feed or European coverage yet.

## Enable the daily free collector (one-time step)

1. Open [Actions settings](https://github.com/alexandrelenoir26-oss/moat-radar/settings/variables/actions).
2. Create a repository variable named `SEC_CONTACT` with a real, contactable email address preceded by an identifier, for example `MOAT-Radar analyst contact@example.com` (replace the example address). **Do not put any password or API key in this variable**. It is a public contact string sent to SEC.
3. In GitHub repo Settings → Actions → General, ensure Actions are enabled and workflow permissions permit `Read and write permissions` where available. The workflow explicitly asks for `contents: write`, but organization policies may override it.
4. Run Actions → **Collect SEC fundamentals** → Run workflow, or wait for the daily UTC schedule.
5. GitHub Pages: Settings → Pages → Source → **GitHub Actions**. The deployment workflow is in `.github/workflows/pages.yml`.

The SEC requires an identified User-Agent and asks automated clients not to exceed ten requests per second. Collection rate-limits requests and refreshes issuers in rolling batches. GitHub schedules can be delayed. GitHub scheduled tasks can be delayed or skipped.

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

## Annual valuation metrics (optional, guarded)

The new `scripts/valuation.py` computes **annual P/E (PER)** and **annual FCF yield**, not a proprietary undervaluation rating. It requires **recent market capitalization** from a source that **explicitly allows redistribution on a public website**. There is **no price feed configured yet**, so the dashboard correctly displays dashes rather than fictitious ratios.

Import format for an authorized source: `data/market_caps.csv` (optional; do not add it unless redistribution permission is confirmed):

```csv
ticker,market_cap_usd,asof,source,redistribution_allowed
```

Amounts are USD. `asof` is YYYY-MM-DD, must be <= 10 days old; `source` must name the licensed origin; `redistribution_allowed` must be `true`. CSV rows without explicit permission are skipped. Never commit a personal-only quote feed here.

Formulae: `annual P/E = market cap / positive annual net income`, `annual FCF yield (%) = 100 * (annual operating cash flow - annual capex) / market cap`. Each annual cash-flow pair must have the same SEC financial year end. Older or incompatible statements are rejected. Neither metric is a valuation score, intrinsic-value estimate, or trading signal.

**Zero-budget licensing constraint:** providers may offer free API *access* while forbidding public *display* or redistribution. Quote widgets may allow display with branding but do not automatically authorize extracting and storing quotes. We will not bypass these terms to fill thousands of scores.

## Financial scoring V2

The public interface uses exploratory financial-only indicators with partial coverage and sector-specific handling. These are **not validated moat scores**, and cross-sector rankings are not calibrated. Banks, insurers and listed real estate need dedicated models.

## Zero-cost US price references: HF Data Library / IEX HIST

A legitimate, **free and redistributable** reference price source has been identified:
[HF Data Library](https://hfdatalibrary.com/pages/api), with [CC BY 4.0 terms](https://hfdatalibrary.com/pages/data) and required [IEX historical data attribution](https://www.iex.io/legal/hist-data-terms).

- Covers a fixed universe of **1,253 tickers** (stocks + ETFs, some delisted), not all S&P 500 names or all listed US companies.
- Since March 2022, observations come from **IEX only**, not the consolidated US market tape; may omit trades and differ from official closing quotes.
- Prices in its processed files are **split-adjusted (not dividend-adjusted)**, so they are **not suitable as direct inputs to SEC-shares × price market capitalization or investment valuation**.
- The service requires an individual **free API key that expires every 30 days**. Automatic collection is therefore conditional on keeping the key current. The key must remain a GitHub Actions *secret*, never a committed file.
- This is a research reference price, not a trade execution quote or validated market cap. Provider labels its content as academic research rather than investment/trading use; do not employ it to generate or advertise investment recommendations.

### One-time activation

1. [Register for a free HF Data Library account](https://hfdatalibrary.com/pages/download); obtain your `X-API-Key` per the [API documentation](https://hfdatalibrary.com/pages/api).
2. In [this repo's GitHub Actions secrets](https://github.com/alexandrelenoir26-oss/moat-radar/settings/secrets/actions), create a secret `HF_DATA_API_KEY` with the key value. **Never post the key in chat or publish it.**
3. The HF importer is deliberately **not scheduled** in production: its 30-day key lifetime is incompatible with the permanent unattended workflow. It can be run manually only as an experiment with a valid key, subject to provider terms.
4. The importer processes up to 60 available tickers per daily workflow. It imports only recent observations with trades, flags them as adjusted and IEX-only, and includes source/attribution and observation dates. The site displays them as **Référence IEX**, not as market cap, intrinsic value or verified closing price.

IEX historical data legal attribution: **Data provided for free by IEX. By accessing or using IEX Historical Data, you agree to the [IEX Historical Data Terms of Use](https://www.iex.io/legal/hist-data-terms).**

HF Data Library citation: Elkassabgi, A. (2026). *HF Data Library: Free 1-Minute Intraday U.S. Equity Data.* Zenodo, DOI: [10.5281/zenodo.19501604](https://doi.org/10.5281/zenodo.19501604).

**Honest limitation:** This solves access to an attributed, free historic price reference, *not* the complete automated PER/valuation problem. For accurate current market cap and reliable cross-company valuation we still need a suitable unadjusted, company-matched, redistribution-permitted market price plus current share counts and corporate-action controls.

### Operational caveat (November 2026)
HF's published API documents the signed URL as a **full absolute https:// URL**, not a relative path. The importer validates the exact provider domain and ticker path. Free keys expire every 30 days, so this integration is **not fully unattended indefinitely**. The source says *for academic research only* and prices cover IEX's single trading venue (~2–3% of consolidated volume). It is therefore used only for attributed research context, not for financial decision signals. Latest documentation states **1,253** tickers and split (not dividend) adjustments; the public availability endpoint remains the authority for exact current coverage.


## SEC Form 13F — durable, key-free historical price diagnostics (experimental)

Official government data: [SEC Form 13F data sets](https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets), quarterly ZIP downloads containing `SUBMISSION.tsv` and `INFOTABLE.tsv`. The accompanying [SEC 13F FAQ](https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f) explains the holdings and reported market values.

`scripts/sec13f.py` implements a strictly *offline* importer for those official TSVs. It requires a separately verified **CUSIP→ticker mapping**, a confirmed value denomination (`--value-unit dollars|thousands`) and an explicit quarter. Only common-share positions from three or more consistent institutional filings are considered. Options, principals, inconsistent implied prices, and unverified identities are rejected.

Example after downloading the official quarterly SEC ZIP and separately verifying the mapping:

```sh
python scripts/sec13f.py --submission SUBMISSION.tsv --infotable INFOTABLE.tsv \
  --cusip-map verified_cusips.csv --quarter 2026-06-30 --value-unit dollars \
  --output data/13f_diagnostics.json
```

The unit shown is only an **example**: confirm the exact SEC archive schema before running. Do not create an unverified CUSIP mapping or assume the same units hold across vintages.

**Important:** 13F reports are delayed, may contain errors and do not constitute a consolidated quote feed. The prototype is not wired to live daily collection or current valuation; it cannot compute a current PER or support GO / NO GO signals. This is deliberately separate from the reliable SEC XBRL collector and public ranking.

To ship it unattended requires automated discovery/download of the official SEC archive, licensed CUSIP reconciliation, validation of value-unit changes across filing formats, corporate-action adjustments, historical quality checks and a publication audit. Until those steps are implemented and tested, no 13F-derived figures are presented as current prices.
