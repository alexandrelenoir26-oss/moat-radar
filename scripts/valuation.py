#!/usr/bin/env python3
"""Optional valuation metrics from independently licensed market capitalization inputs.
No quote scraping, no fictitious prices, no opaque valuation scores.
CSV columns: ticker,market_cap_usd,asof,source,redistribution_allowed
Only rows explicitly permitted for redistribution are persisted to public output.
"""
import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"companies.json"
INPUT=ROOT/"data"/"market_caps.csv"
MODEL="valuation-metrics-v1"
MAX_MARKET_AGE=10
MAX_FUNDAMENTAL_AGE=540

def market_inputs(path, today):
    if not path.exists(): return {},[]
    results={}
    errors=[]
    with path.open(encoding="utf-8-sig",newline="") as file:
        reader=csv.DictReader(file)
        required={"ticker","market_cap_usd","asof","source","redistribution_allowed"}
        if not required.issubset(reader.fieldnames or []):
            return {},["Colonnes manquantes dans market_caps.csv."]
        for i,row in enumerate(reader,2):
            ticker=(row.get("ticker") or "").strip().upper()
            try:
                amount=float(row["market_cap_usd"])
                asof=date.fromisoformat(row["asof"].strip())
                source=(row.get("source") or "").strip()
                permitted=(row.get("redistribution_allowed") or "").strip().lower() in ("true","yes","1")
                if not permitted:
                    errors.append(f"line {i}: redistribution not authorized")
                    continue
                if not ticker or not source or not math.isfinite(amount) or not (1e5<amount<1e15):
                    raise ValueError("missing source or invalid cap")
                if not (0 <= (today-asof).days <= MAX_MARKET_AGE):
                    raise ValueError("market value too old or in future")
                results[ticker]={"market_cap_usd":amount,"asof":asof.isoformat(),"source":source}
            except (ValueError, TypeError, KeyError) as exc:
                errors.append(f"line {i}: {str(exc)[:80]}")
    return results,errors

def annual_value(company, key, today):
    fact=(company.get("fundamentals") or {}).get(key)
    if not isinstance(fact,dict): return None
    try:
        end=date.fromisoformat(fact["period_end"])
        filed=date.fromisoformat(fact["filed"])
        value=float(fact["value"])
        if not math.isfinite(value) or not (0 <= (today-end).days<=MAX_FUNDAMENTAL_AGE):
            return None
        if not end<=filed<=today: return None
        return value, end.isoformat()
    except (ValueError,KeyError,TypeError): return None

def evaluate(company, cap, today):
    if not cap: return None,"Capitalisation boursière sous licence de redistribution indisponible."
    result={"market_cap_usd":cap["market_cap_usd"],"market_asof":cap["asof"],
            "market_source":cap["source"],"model":MODEL,
            "basis":"Données annuelles historiques, non TTM",
            "pe_annual":None,"fcf_yield_annual":None,"earnings_yield_annual":None,
            "fiscal_period":None,"warnings":[]}
    earning=annual_value(company,"net_income",today)
    cash=annual_value(company,"operating_cash",today)
    capex=annual_value(company,"capex",today)
    if earning:
        income,period=earning
        result["fiscal_period"]=period
        if income>0:
            result["pe_annual"]=round(cap["market_cap_usd"]/income,2)
            result["earnings_yield_annual"]=round(100*income/cap["market_cap_usd"],2)
        else: result["warnings"].append("Bénéfice annuel nul ou négatif : PER non pertinent.")
    if cash and capex and cash[1]==capex[1] and capex[0]>=0:
        fcf=cash[0]-capex[0]
        result["fcf_yield_annual"]=round(100*fcf/cap["market_cap_usd"],2)
        if result["fiscal_period"] and result["fiscal_period"]!=cash[1]:
            result["warnings"].append("PER et rendement FCF issus d'exercices différents.")
        if not result["fiscal_period"]: result["fiscal_period"]=cash[1]
    if result["pe_annual"] is None and result["fcf_yield_annual"] is None:
        return None,"Données annuelles comparables insuffisantes pour PER ou rendement FCF."
    result["warnings"].append("La capitalisation n'est pas synchronisée aux états financiers ; ne pas interpréter comme décote ou recommandation.")
    return result,None

def apply(data, caps, today=None):
    today=today or date.today()
    n=0
    for c in data.get("companies",[]):
        result,reason=evaluate(c,caps.get(c.get("ticker","")),today)
        c["valuation_metrics"]=result
        c["valuation_reason"]=reason
        c["valuation"]=None
        c["status"]="unknown"
        if result: n+=1
    data["valuation_metrics_count"]=n
    data["valuation_model"]=MODEL
    data["market_cap_coverage"]=len(caps)
    return data

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",type=Path,default=DATA)
    p.add_argument("--market",type=Path,default=INPUT)
    a=p.parse_args()
    data=json.loads(a.data.read_text(encoding="utf-8"))
    caps,errors=market_inputs(a.market,date.today())
    apply(data,caps)
    data["market_data_errors"]=errors[:50]
    a.data.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Valuation metrics: {data['valuation_metrics_count']}; licensed market caps: {len(caps)}; rejected rows: {len(errors)}")
if __name__=="__main__":main()
