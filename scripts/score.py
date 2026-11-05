#!/usr/bin/env python3
"""Conservative, reproducible financial quality scoring from SEC XBRL snapshots.
This is NOT an economic moat or a security valuation. No action signals.
"""
import argparse
import json
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "companies.json"
EXCLUDED = {"Financials", "Real Estate", "Utilities"}
MODEL = "quality-financial-v1"
METRIC_RULES = {
    "net_margin": (0.00, 0.25),             # higher is better
    "free_cash_flow_margin": (0.00, 0.25),  # higher is better
    "cash_conversion": (0.40, 1.40),       # CFO / positive net income
    "equity_ratio": (0.10, 0.70),         # book equity / assets
}

def ratio_score(value, low, high):
    return max(0.0, min(100.0, (value - low) / (high - low) * 100.0))

def age_days(iso, today):
    return (today - date.fromisoformat(iso)).days

def candidate(company, today=None):
    today = today or date.today()
    sector = company.get("sector", "")
    if sector in EXCLUDED:
        return None, "Modèle non adapté aux secteurs financier, immobilier ou utilities."
    facts = company.get("fundamentals") or {}
    names = ("revenue", "net_income", "operating_cash", "capex", "assets", "liabilities")
    if any(not isinstance(facts.get(name), dict) for name in names):
        return None, "Au moins une des six métriques comptables requises est absente."
    try:
        rev, profit, cash, capex, assets, liab = (facts[n] for n in names)
        flows = (rev, profit, cash, capex)
        fiscal_ends = {x["period_end"] for x in flows}
        if len(fiscal_ends) != 1:
            return None, "Exercices fiscaux incompatibles pour les flux annuels."
        if assets["period_end"] != liab["period_end"]:
            return None, "Dates de bilan incompatibles."
        end = date.fromisoformat(rev["period_end"])
        balance_end = date.fromisoformat(assets["period_end"])
        if not (0 <= (today-end).days <= 540) or not (0 <= (today-balance_end).days <= 540):
            return None, "États financiers trop anciens ou datés dans le futur."
        if abs((balance_end-end).days) > 460:
            return None, "Bilans et comptes de résultat trop éloignés."
        for x in (rev, profit, cash, capex, assets, liab):
            filed = date.fromisoformat(x["filed"])
            observed = date.fromisoformat(x["period_end"])
            if filed < observed or filed > today:
                return None, "Date de dépôt incohérente."
        rv, ni, ocf, cx, a, l = [float(x["value"]) for x in (rev, profit, cash, capex, assets, liab)]
        if rv <= 0 or ni <= 0 or a <= 0 or cx < 0 or l < 0 or l > a:
            return None, "Dénominateur invalide, pertes ou bilan atypique."
        if abs(ocf) > rv*10 or cx > rv*5:
            return None, "Ordres de grandeur incompatibles : revue requise."
        metrics = {
            "net_margin": ni/rv,
            "free_cash_flow_margin": (ocf-cx)/rv,
            "cash_conversion": ocf/ni,
            "equity_ratio": (a-l)/a,
        }
        parts = {k:round(ratio_score(v,*METRIC_RULES[k]),1) for k,v in metrics.items()}
        score = round(sum(parts.values())/4)
        return {"score":score, "metrics":{k:round(v,5) for k,v in metrics.items()},
                "components":parts, "model":MODEL,
                "annual_period":end.isoformat(), "balance_period":balance_end.isoformat(),
                "interpretation":"Score financier préliminaire, sans validation du moat ou de la valorisation."},None
    except (ValueError, TypeError, KeyError, OverflowError, ZeroDivisionError):
        return None,"Dates ou valeurs SEC invalides."

def apply(data, today=None):
    count=0
    for company in data.get("companies",[]):
        item,reason=candidate(company,today)
        company["quality_financial"]=item["score"] if item else None
        company["quality_details"]=item
        company["quality_reason"]=reason
        company["quality"]=None # Reserved for audited overall quality + moat model
        company["moat"]=None
        company["valuation"]=None
        company["status"]="unknown" # Never infer a buy signal from financial data alone
        if item: count+=1
    data["scoring_version"]=MODEL
    data["financial_scores_count"]=count
    data["notice"]=(f"{count} scores financiers préliminaires calculés sur données SEC ; "
                    "aucun score de moat, aucune valorisation ni aucun signal d'achat validé. "
                    "Les secteurs financiers, immobiliers et utilities sont exclus de ce modèle.")
    return data

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,default=DATA)
    parser.add_argument("--output",type=Path)
    a=parser.parse_args()
    output=a.output or a.input
    data=json.loads(a.input.read_text(encoding="utf-8"))
    apply(data)
    output.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Scored {data['financial_scores_count']} of {len(data['companies'])} records (provisional financial only).")

if __name__=="__main__":
    main()
