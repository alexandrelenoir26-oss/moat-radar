import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from score import candidate,apply

def f(v,end="2025-12-31",filed="2026-02-01"):
    return {"value":v,"period_end":end,"filed":filed,"tag":"fixture"}

class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.today=date(2026,11,5)
        self.company={"ticker":"TEST","sector":"Industrials","fundamentals":{
            "revenue":f(1000),"net_income":f(150),"operating_cash":f(200),
            "capex":f(50),"assets":f(2000,"2026-09-30","2026-10-15"),
            "liabilities":f(1000,"2026-09-30","2026-10-15")}}
    def test_valid_score(self):
        result,reason=candidate(self.company,self.today)
        self.assertIsNone(reason)
        self.assertTrue(0 <= result["score"] <= 100)
        self.assertEqual(len(result["components"]),4)
    def test_sector_exclusion(self):
        self.company["sector"]="Financials"
        score,reason=candidate(self.company,self.today)
        self.assertIsNone(score)
    def test_unmatched_period(self):
        self.company["fundamentals"]["capex"]["period_end"]="2024-12-31"
        score,reason=candidate(self.company,self.today)
        self.assertIsNone(score)
    def test_missing_capex_is_null(self):
        self.company["fundamentals"]["capex"]=None
        score,reason=candidate(self.company,self.today)
        self.assertIsNone(score)
    def test_no_investment_signals(self):
        data=apply({"companies":[self.company]},self.today)
        row=data["companies"][0]
        self.assertIsNone(row["quality"])
        self.assertIsNone(row["valuation"])
        self.assertEqual(row["status"],"unknown")
    def test_stale_data(self):
        for v in self.company["fundamentals"].values():
            v["period_end"]="2022-12-31"
            v["filed"]="2023-02-01"
        score,reason=candidate(self.company,self.today)
        self.assertIsNone(score)

if __name__=="__main__": unittest.main()
