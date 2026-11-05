#!/usr/bin/env python3
"""MOAT Radar financial screening v2.
Exploratory, sector-aware financial *partial* indicators, not a moat or valuation rating.
Missing or non-comparable facts are never imputed.
"""
import argparse
import json
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "companies.json"
MODEL = "quality-financial-v2"
# Transparent heuristic ranges, NOT statistically calibrated percentiles.
RULES = {
    "standard": {"net_margin":(-0.05,0.25), "operating_cash_margin":(-0.05,0.30),
                 "fcf_margin":(-0.05,0.25), "cash_conversion":(0.2,1.6),
                 "return_on_assets":(-0.03,0.18), "equity_ratio":(0.05,0.65)},
    "Utilities": {"net_margin":(-0.05,0.20), "operating_cash_margin":(0.00,0.35),
                  "fcf_margin":(-0.20,0.15), "cash_conversion":(0.2,2.2),
                  "return_on_assets":(-0.02,0.08), "equity_ratio":(0.05,0.50)}
}
# Do not misuse industrial ratios for financial intermediaries or REITs.
EXCLUDED = {"Financials", "Real Estate"}
CORE = ("net_margin", "operating_cash_margin", "return_on_assets", "equity_ratio")
MAX_AGE_DAYS = 540

def valid_fact(fact, today):
    if not isinstance(fact,dict): return False
    try:
        observed=date.fromisoformat(fact["period_end"])
        filed=date.fromisoformat(fact["filed"])
        val=fact["value"]
        return (isinstance(val,(float,int)) and not isinstance(val,bool)
                and 0 <= (today-observed).days <= MAX_AGE_DAYS
                and observed <= filed <= today and abs(val)<1e18)
    except (KeyError, ValueError, OverflowError, TypeError): return False

def normalize(value,low,high):
    return round(max(0.,min(100.,100*(value-low)/(high-low))),1)

def candidate(company,today=None):
    today=today or date.today()
    sector=company.get("sector","")
    if sector in EXCLUDED:
        return None,"Secteur nécessitant un modèle spécialisé (banques, assurances ou immobilier coté)."
    f=company.get("fundamentals") or {}
    f={k:v if valid_fact(v,today) else None for k,v in f.items()}
    metrics={}
    dates={}
    notes=[]
    def put(key,value,objects):
        if value is not None and abs(value)<100:
            metrics[key]=value
            dates[key]=sorted({x["period_end"] for x in objects})
    revenue=f.get("revenue")
    profit=f.get("net_income")
    cash=f.get("operating_cash")
    capex=f.get("capex")
    assets=f.get("assets")
    liabilities=f.get("liabilities")
    if revenue and revenue["value"]>0:
        rv=revenue["value"]
        if profit and revenue["period_end"]==profit["period_end"]:
            put("net_margin",profit["value"]/rv,[revenue,profit])
        if cash and revenue["period_end"]==cash["period_end"]:
            put("operating_cash_margin",cash["value"]/rv,[revenue,cash])
        if cash and capex and revenue["period_end"]==cash["period_end"]==capex["period_end"] and capex["value"]>=0:
            put("fcf_margin",(cash["value"]-capex["value"])/rv,[revenue,cash,capex])
        if profit and cash and profit["period_end"]==cash["period_end"] and profit["value"]>0:
            put("cash_conversion",cash["value"]/profit["value"],[cash,profit])
    if profit and assets and assets["value"]>0:
        if abs((date.fromisoformat(profit["period_end"])-date.fromisoformat(assets["period_end"])).days)<=460:
            put("return_on_assets",profit["value"]/assets["value"],[profit,assets])
    if assets and liabilities and assets["period_end"]==liabilities["period_end"] and assets["value"]>0:
        if 0<=liabilities["value"]<=assets["value"]*2:
            put("equity_ratio",(assets["value"]-liabilities["value"])/assets["value"],[assets,liabilities])
    # Require two independent metrics from profitability, cash flow and balance sheet.
    # Cash conversion and FCF margin can supplement, but cannot make two independent pillars alone.
    supported=[k for k in CORE if k in metrics]
    if len(supported)<2:
        return None, "Moins de deux indicateurs fondamentaux indépendants disponibles et comparables."
    rules=RULES.get(sector,RULES["standard"])
    # Use core pillars equally; supplementary signals appear in breakdown but do not double-count cash flow.
    parts={k:normalize(metrics[k],*rules[k]) for k in supported}
    score=round(sum(parts.values())/len(parts))
    coverage=len(supported)/len(CORE)
    confidence="élevée" if len(supported)==4 else ("intermédiaire" if len(supported)==3 else "faible")
    if len(supported)<4: notes.append("Score partiel : métriques fondamentales manquantes.")
    if sector=="Utilities": notes.append("Barèmes exploratoires spécifiques aux utilities ; comparer avec prudence.")
    notes.append("Pas de score de moat ni de valorisation ; ce n'est pas un signal d'achat.")
    return {
        "score":score,"model":MODEL,"coverage":round(coverage,2),"confidence":confidence,
        "metrics":{k:round(v,6) for k,v in metrics.items()},
        "components":parts,"metric_dates":dates,
        "pillars":supported,"notes":notes,
        "interpretation":"Indice comptable exploratoire, non comparable entre secteurs sans validation."
    },None

def apply(data,today=None):
    count=0;full=0;partial=0;reasons={}
    for company in data.get("companies",[]):
        item,reason=candidate(company,today)
        company["quality_financial"]=item["score"] if item else None
        company["quality_details"]=item
        company["quality_reason"]=reason
        company["quality_coverage"]=item["coverage"] if item else None
        company["quality_confidence"]=item["confidence"] if item else None
        # These fields remain deliberately unscored.
        company["quality"]=None
        company["moat"]=None
        company["valuation"]=None
        company["status"]="unknown"
        if item:
            count+=1
            if item["coverage"]==1: full+=1
            else: partial+=1
        else: reasons[reason]=reasons.get(reason,0)+1
    data["scoring_version"]=MODEL
    data["financial_scores_count"]=count
    data["financial_full_count"]=full
    data["financial_partial_count"]=partial
    data["financial_missing_reasons"]=reasons
    data["notice"]=(f"{count} indices comptables exploratoires ({full} complets, {partial} partiels). "
                    "Aucun moat ou prix de marché analysé. Ne pas interpréter comme recommandation.")
    return data

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,default=DATA)
    parser.add_argument("--output",type=Path)
    a=parser.parse_args()
    d=json.loads(a.input.read_text(encoding="utf-8"))
    apply(d)
    (a.output or a.input).write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Financial indices: {d['financial_scores_count']} / {len(d['companies'])}; "
          f"full {d['financial_full_count']}, partial {d['financial_partial_count']}")
if __name__=="__main__":main()
