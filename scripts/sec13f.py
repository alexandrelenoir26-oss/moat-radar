#!/usr/bin/env python3
"""SEC 13F historical diagnostics, not trading prices or current valuations.

Parse official SEC quarterly TSV files SUBMISSION.tsv and INFOTABLE.tsv from
https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets

CUSIP->ticker matching requires an independently verified mapping; none is guessed.
No output is considered a real-time quote, PER or buy signal.
"""
import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

def parse_date(value):
    value=(value or "").strip()
    for fmt in ("%Y-%m-%d","%d-%b-%Y","%d-%B-%Y"):
        try: return datetime.strptime(value,fmt).date()
        except ValueError: pass
    raise ValueError("Invalid SEC date: "+value[:30])

def import_rows(submission_file, holdings_file, cusip_map_file, quarter, unit="thousands"):
    """Explicit unit must come from the source dataset documentation.
    SEC older 13F information tables represent USD thousands; some newer forms
    use actual dollars. Never silently assume a scale.
    """
    if unit not in ("thousands","dollars"):
        raise ValueError("unit must be 'thousands' or 'dollars'")
    scale=1000 if unit=="thousands" else 1
    target=parse_date(quarter)
    if (target.month,target.day) not in ((3,31),(6,30),(9,30),(12,31)):
        raise ValueError("Quarter must end on Mar 31, Jun 30, Sep 30 or Dec 31.")
    with open(cusip_map_file,encoding="utf-8-sig",newline="") as file:
        reader=csv.DictReader(file)
        if not {"cusip","ticker","verified"}.issubset(reader.fieldnames or []):
            raise ValueError("CUSIP mapping must include cusip,ticker,verified.")
        mapping={}
        for row in reader:
            if str(row["verified"]).lower() not in ("yes","true","1"):continue
            cusip=row["cusip"].strip().upper()
            ticker=row["ticker"].strip().upper()
            if len(cusip)==9 and ticker and cusip not in mapping:
                mapping[cusip]=ticker
    submissions={}
    with open(submission_file,encoding="utf-8-sig",newline="") as file:
        reader=csv.DictReader(file,delimiter="\t")
        required={"ACCESSION_NUMBER","PERIODOFREPORT","SUBMISSIONTYPE","FILING_DATE"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Official SUBMISSION.tsv fields missing.")
        for row in reader:
            if row["SUBMISSIONTYPE"].strip().upper()!="13F-HR":continue # amendments need separate reconciliation
            try:
                period=parse_date(row["PERIODOFREPORT"])
                filed=parse_date(row["FILING_DATE"])
            except ValueError:continue
            if period!=target or filed<period or filed>date.today():continue
            submissions[row["ACCESSION_NUMBER"]]={"filed":filed.isoformat()}
    values=defaultdict(list)
    with open(holdings_file,encoding="utf-8-sig",newline="") as file:
        reader=csv.DictReader(file,delimiter="\t")
        required={"ACCESSION_NUMBER","CUSIP","VALUE","SSHPRNAMT","SSHPRNAMTTYPE","PUTCALL"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Official INFOTABLE.tsv fields missing.")
        for row in reader:
            acc=row["ACCESSION_NUMBER"]
            if acc not in submissions:continue
            if row["SSHPRNAMTTYPE"].strip().upper()!="SH" or row["PUTCALL"].strip():continue
            ticker=mapping.get(row["CUSIP"].strip().upper())
            if not ticker:continue
            try:
                shares=float(row["SSHPRNAMT"].replace(",",""))
                val=float(row["VALUE"].replace(",",""))*scale
                if not (math.isfinite(shares) and math.isfinite(val)) or shares<1000 or val<=0:continue
                implied=val/shares
                # guard obvious unit errors, tiny positions and transformed claims
                if not 0.10<=implied<=100000:continue
                values[ticker].append({"price":implied,"accession":acc})
            except (ValueError,TypeError,ZeroDivisionError):continue
    result=[]
    for ticker, observations in sorted(values.items()):
        # multiple independent manager filings needed for even a historical diagnostic
        by_manager={}
        for row in observations:by_manager.setdefault(row["accession"],row["price"])
        prices=list(by_manager.values())
        if len(prices)<3:continue
        median=statistics.median(prices)
        within=[p for p in prices if abs(p/median-1)<=.05]
        if len(within)<3 or len(within)/len(prices)<.8:continue
        result.append({"ticker":ticker,"period_end":target.isoformat(),
            "historical_implied_price_usd":round(statistics.median(within),4),
            "number_of_filings":len(within),"unit_assumption":unit,
            "purpose":"13F quarter-end research estimate ONLY; NOT a current trading quote",
            "source":"SEC EDGAR official Form 13F data sets",
            "source_url":"https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets",
            "note":"Reported valuations and share counts may be erroneous; adjusted instruments and issuer actions not fully verified."})
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--submission",type=Path,required=True)
    p.add_argument("--infotable",type=Path,required=True)
    p.add_argument("--cusip-map",type=Path,required=True)
    p.add_argument("--quarter",required=True)
    p.add_argument("--value-unit",choices=["thousands","dollars"],required=True)
    p.add_argument("--output",type=Path,default=Path("data/13f_diagnostics.json"))
    a=p.parse_args()
    out=import_rows(a.submission,a.infotable,a.cusip_map,a.quarter,a.value_unit)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({"source":"SEC 13F official historical datasets","results":out,
        "warning":"Historical research only. Never use for current PER, market cap, or buy signal."},
        indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Historical diagnostics produced: {len(out)}")
if __name__=="__main__":main()
