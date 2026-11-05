#!/usr/bin/env python3
"""Import attributed IEX-only reference prices from HF Data Library.
Reference-only. Adjusted, single-venue historical prices MUST NOT be multiplied by
SEC share counts to fabricate market cap or PE.
Requires HF_DATA_API_KEY secret; never store key or original bulk history in Git.
"""
import csv
import io
import json
import os
import time
import urllib.request
import urllib.error
from datetime import date,datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"companies.json"
API="https://api.hfdatalibrary.com/v1"
ATTRIBUTION=("Elkassabgi, A. (2026), HF Data Library, DOI:10.5281/zenodo.19501604. "
             "Data provided for free by IEX. By accessing or using IEX Historical Data, "
             "you agree to the IEX Historical Data Terms of Use.")
def get(url,key=None):
    headers={"User-Agent":"MOAT-Radar research open-source","Accept":"application/json"}
    if key: headers["X-API-Key"]=key
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=60) as r:
        return r.read()
def allowed_symbols():
    x=json.loads(get(API+"/symbols"))
    return {str(item.get("ticker","")).upper() for item in x.get("symbols",[]) if isinstance(item,dict)}
def validated_download_url(url,ticker):
    """Reject any signed URL outside the provider's exact host and ticker path."""
    p=urlsplit(url)
    if p.scheme!="https" or p.netloc!="api.hfdatalibrary.com":
        raise ValueError("Untrusted signed download URL")
    if p.path!=f"/v1/download/{ticker}" or not p.query:
        raise ValueError("Unexpected signed download path or missing token")
    return url

def latest_row(body,today):
    reader=csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    if not reader.fieldnames: return None
    lower={x.lower():x for x in reader.fieldnames}
    pricecol=lower.get("close")
    datecol=lower.get("date") or lower.get("datetime")
    volcol=lower.get("volume")
    if not (pricecol and datecol): return None
    latest=None
    for row in reader:
        try:
            raw=row[datecol].strip()
            try:dt=date.fromisoformat(raw[:10])
            except ValueError:dt=datetime.strptime(raw[:10],"%m/%d/%Y").date()
            px=float(row[pricecol])
            volume=int(float(row[volcol])) if volcol and row.get(volcol) else None
            if px<=0 or px>1000000 or (today-dt).days not in range(0,8):continue
            if volume is not None and volume<=0:continue
            if latest is None or dt>date.fromisoformat(latest["date"]):
                latest={"date":dt.isoformat(),"price_usd":round(px,6)}
        except (ValueError,TypeError,KeyError):continue
    return latest

def main():
    key=os.getenv("HF_DATA_API_KEY","").strip()
    if not key:
        print("HF_DATA_API_KEY missing: skip price references, no change.")
        return
    data=json.loads(DATA.read_text(encoding="utf-8"))
    available=allowed_symbols()
    max_tickers=min(max(int(os.getenv("HF_PRICE_BATCH","60")),1),100)
    candidates=[c for c in data["companies"] if c.get("ticker") in available]
    candidates.sort(key=lambda c: (c.get("iex_reference") or {}).get("checked_at",""))
    completed=0
    today=date.today()
    errors=[]
    for c in candidates[:max_tickers]:
        ticker=c["ticker"]
        try:
            params=f"?timeframe=daily&format=csv&version=clean"
            token=json.loads(get(API+"/download-token/"+ticker+params,key))
            url=token["url"]
            url=validated_download_url(url,ticker)
            record=latest_row(get(url),today)
            if record:
                c["iex_reference"]={**record,"checked_at":today.isoformat(),
                   "source":"HF Data Library / IEX-only", "split_adjusted":True, "dividend_adjusted":False,
                   "license":"CC BY 4.0 + IEX HIST terms",
                   "reference_only":True,"not_consolidated":True}
                completed+=1
            else:
                errors.append(ticker+": no recent observed trades")
        except (urllib.error.URLError,TimeoutError,ValueError,KeyError) as e:
            errors.append(ticker+": "+str(e)[:100])
        time.sleep(0.8)
    data["iex_reference_count"]=sum(bool(c.get("iex_reference")) for c in data["companies"])
    data["iex_reference_last_run"]=today.isoformat()
    data["iex_reference_attribution"]=ATTRIBUTION
    data["iex_reference_errors"]=errors[:20]
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"IEX-only reference data updated: {completed}; total: {data['iex_reference_count']}; errors {len(errors)}")
if __name__=="__main__":main()
