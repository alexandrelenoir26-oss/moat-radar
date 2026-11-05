#!/usr/bin/env python3
"""MOAT Radar: free, verifiable, SEC-only fundamentals collection.
No invented price, PER, moat or investment scores.
Run from repository root: python scripts/collect.py
"""
import csv
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "companies.json"
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
SEC_BASE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
CONTACT = os.getenv("SEC_CONTACT", "moat-radar research contact moat-radar@example.org")
# Set SEC_CONTACT to a real contact email before production collection.
BATCH = min(max(int(os.getenv("BATCH_SIZE", "75")), 1), 200)
PAUSE = float(os.getenv("SEC_REQUEST_PAUSE", "0.35"))
MAX_AGE_DAYS = 540

def fetch(url, headers=None):
    h = {"User-Agent": CONTACT, "Accept-Encoding": "identity",
         "Accept": "application/json,text/html;q=0.9,*/*;q=0.7"}
    if headers: h.update(headers)
    request = urllib.request.Request(url, headers=h)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3: raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Cannot fetch " + url)

def parse_universe(html):
    # Wikipedia page includes a stable wikitable with a header containing CIK.
    # Use BeautifulSoup for robust parsing and transparent source attribution.
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    table = None
    for t in soup.select("table"):
        header = " ".join(x.get_text(" ", strip=True) for x in t.select("tr th")[:10]).lower()
        if "symbol" in header and "cik" in header and "security" in header:
            table = t
            break
    if table is None:
        raise ValueError("No S&P 500 table with CIK found; abort to preserve last good dataset")
    records = []
    for row in table.select("tr")[1:]:
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) < 7: continue
        ticker = cells[0].get_text(" ", strip=True)
        name = cells[1].get_text(" ", strip=True)
        sector = cells[2].get_text(" ", strip=True)
        digits = re.sub(r"\D", "", cells[6].get_text(" ", strip=True))
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,7}", ticker) or not digits: continue
        records.append({"ticker": ticker, "name": name, "sector": sector,
                        "cik": digits.zfill(10)})
    if len(records) < 400:
        raise ValueError(f"Universe unusually small ({len(records)}); abort")
    return records

def get_usgaap(facts, names, units="USD", duration=None):
    for name in names:
        fact = facts.get("us-gaap", {}).get(name, {})
        options = fact.get("units", {}).get(units, [])
        viable = []
        for item in options:
            try:
                filed = datetime.fromisoformat(item["filed"]).date()
                end = datetime.fromisoformat(item["end"]).date()
                val = item["val"]
                if not isinstance(val, (int, float)): continue
                if item.get("form") not in ("10-K", "10-Q"): continue
                if duration is not None:
                    if "start" not in item: continue
                    days = (end - datetime.fromisoformat(item["start"]).date()).days
                    if duration == "annual" and not 330 <= days <= 380: continue
                else:
                    if "start" in item: continue
                viable.append((end, filed, val))
            except (ValueError, KeyError, TypeError): continue
        if viable:
            viable.sort(reverse=True)
            end, filed, value = viable[0]
            return {"value": value, "period_end": end.isoformat(),
                    "filed": filed.isoformat(), "tag": name}
    return None

def record_for(company, document):
    facts = document.get("facts", {})
    revenue = get_usgaap(facts, [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"
    ], duration="annual")
    profit = get_usgaap(facts, ["NetIncomeLoss"], duration="annual")
    assets = get_usgaap(facts, ["Assets"])
    liabilities = get_usgaap(facts, ["Liabilities"])
    operating_cash = get_usgaap(facts, ["NetCashProvidedByUsedInOperatingActivities"], duration="annual")
    capex = get_usgaap(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"], duration="annual")
    values = {"revenue": revenue, "net_income": profit, "assets": assets,
              "liabilities": liabilities, "operating_cash": operating_cash, "capex": capex}
    freshest = max((x["filed"] for x in values.values() if x), default=None)
    if freshest:
        age = (datetime.now(timezone.utc).date() - datetime.fromisoformat(freshest).date()).days
        if age > MAX_AGE_DAYS: freshest = None
    return {
        **company,
        "status": "unknown",
        "quality": None,
        "valuation": None,
        "source": "SEC EDGAR / XBRL",
        "source_url": SEC_BASE.format(cik=company["cik"]),
        "asof": max((x["period_end"] for x in values.values() if x), default=None),
        "last_filing": freshest,
        "fundamentals": values,
        "coverage": sum(bool(v) for v in values.values()),
        "reason": "Cours de marché et évaluation qualitative du moat non disponibles ; aucun signal de valorisation autorisé."
    }

def main():
    if CONTACT.endswith("@example.org"):
        raise SystemExit("Set SEC_CONTACT to a genuine contact address before collecting SEC data.")
    universe = parse_universe(fetch(WIKI_URL, headers={"User-Agent": "MOAT Radar educational nonprofit data project"}))
    old = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {}
    previous = {x["ticker"]: x for x in old.get("companies", [])}
    today = datetime.now(timezone.utc).date()
    # Refresh missing filings first, then least-recently-checked records.
    candidates = sorted(universe, key=lambda c: (previous.get(c["ticker"], {}).get("checked_at") or ""))
    errors = []
    completed = 0
    for company in candidates[:BATCH]:
        ticker = company["ticker"]
        try:
            doc = json.loads(fetch(SEC_BASE.format(cik=company["cik"])))
            item = record_for(company, doc)
            item["checked_at"] = today.isoformat()
            previous[ticker] = item
            completed += 1
        except (urllib.error.URLError, ValueError, KeyError, TimeoutError) as exc:
            errors.append({"ticker": ticker, "error": str(exc)[:140]})
            # Do not fabricate company facts, retain the previous verifiable snapshot.
            if ticker not in previous:
                previous[ticker] = {**company, "status": "unknown", "quality": None,
                                    "valuation": None, "coverage": 0,
                                    "reason": "SEC data retrieval failed",
                                    "source": "SEC EDGAR (pending)", "asof": None}
            previous[ticker].update({k:company[k] for k in ("name","sector","cik")})
        time.sleep(PAUSE)
    # Keep all index members visible, even those not yet fetched.
    output = []
    for company in universe:
        item = previous.get(company["ticker"], {
            **company, "status": "unknown", "quality": None, "valuation": None,
            "coverage": 0, "reason": "Waiting for SEC filing collection",
            "source": "SEC EDGAR (pending)", "asof": None
        })
        item.update({k:company[k] for k in ("name","sector","cik")})
        item["status"] = "unknown" # fail-closed until a vetted valuation and moat model exists
        item["quality"] = None
        item["valuation"] = None
        output.append(item)
    result = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_label": "SEC EDGAR + S&P 500 (Wikipedia)",
        "notice": "Données comptables SEC publiques : collecte progressive. Le PER, le moat, le scoring et les signaux d'achat ne sont pas encore calculés. Statut « données insuffisantes » par sécurité.",
        "universe": "S&P 500",
        "universe_source": WIKI_URL,
        "universe_count": len(universe),
        "batch_attempted": min(len(candidates), BATCH),
        "batch_completed": completed,
        "batch_errors": errors,
        "companies": output
    }
    DATA.parent.mkdir(exist_ok=True, parents=True)
    temp = DATA.with_suffix(".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temp.replace(DATA)
    print(f"S&P 500: {len(output)} constituents; SEC checked: {completed}; errors: {len(errors)}")

if __name__ == "__main__":
    main()
