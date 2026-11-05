import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from score import candidate, apply

def f(value,end="2025-12-31",filed="2026-02-01"):
    return {"value":value,"period_end":end,"filed":filed,"tag":"fixture"}

class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.today=date(2026,11,5)
        self.company={"ticker":"TEST","sector":"Industrials","fundamentals":{
            "revenue":f(1000),"net_income":f(150),"operating_cash":f(200),
            "capex":f(50),"assets":f(2000,"2026-09-30","2026-10-15"),
            "liabilities":f(1000,"2026-09-30","2026-10-15")}}
    def test_complete(self):
        x,why=candidate(self.company,self.today)
        self.assertIsNone(why)
        self.assertEqual(x["coverage"],1.0)
        self.assertEqual(len(x["components"]),4)
        self.assertTrue(0<=x["score"]<=100)
    def test_partial_without_capex(self):
        self.company["fundamentals"]["capex"]=None
        x,why=candidate(self.company,self.today)
        self.assertIsNotNone(x)
        self.assertIsNone(why)
        self.assertEqual(x["coverage"],1.0) # capex is supplementary, not a core pillar
        self.assertNotIn("fcf_margin",x["metrics"])
    def test_unmatched_period_avoids_false_fcf(self):
        self.company["fundamentals"]["capex"]["period_end"]="2024-12-31"
        x,_=candidate(self.company,self.today)
        self.assertNotIn("fcf_margin",x["metrics"])
    def test_partial_metrics(self):
        self.company["fundamentals"]["liabilities"]=None
        x,_=candidate(self.company,self.today)
        self.assertIsNotNone(x)
        self.assertEqual(x["confidence"],"intermédiaire")
        self.assertEqual(x["coverage"],.75)
    def test_no_fake_zero_when_little_data(self):
        self.company["fundamentals"]={"revenue":f(1000)}
        x,why=candidate(self.company,self.today)
        self.assertIsNone(x)
        self.assertIn("Moins de deux",why)
    def test_sector_exclusions(self):
        for sector in ("Financials","Real Estate"):
            self.company["sector"]=sector
            x,_=candidate(self.company,self.today)
            self.assertIsNone(x)
    def test_utilities_sector_model(self):
        self.company["sector"]="Utilities"
        x,_=candidate(self.company,self.today)
        self.assertIsNotNone(x)
    def test_loss_is_not_missing(self):
        self.company["fundamentals"]["net_income"]["value"]=-100
        x,_=candidate(self.company,self.today)
        self.assertIsNotNone(x)
        self.assertEqual(x["components"]["net_margin"],0)
    def test_future_filing_is_ignored(self):
        self.company["fundamentals"]["net_income"]["filed"]="2030-02-01"
        x,_=candidate(self.company,self.today)
        self.assertNotIn("net_margin",x["metrics"])
    def test_no_investment_signal(self):
        row=apply({"companies":[self.company]},self.today)["companies"][0]
        self.assertEqual(row["status"],"unknown")
        self.assertIsNone(row["moat"])
        self.assertIsNone(row["valuation"])
        self.assertIsNone(row["quality"])
    def test_stale_not_scored(self):
        for v in self.company["fundamentals"].values():
            v["period_end"]="2022-12-31"
            v["filed"]="2023-02-01"
        x,_=candidate(self.company,self.today)
        self.assertIsNone(x)
if __name__=="__main__": unittest.main()
