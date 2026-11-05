import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from valuation import evaluate, apply

class ValuationTests(unittest.TestCase):
    def setUp(self):
        self.today=date(2026,11,5)
        self.company={"ticker":"TEST","fundamentals":{
            "net_income":{"value":100,"period_end":"2025-12-31","filed":"2026-02-01"},
            "operating_cash":{"value":200,"period_end":"2025-12-31","filed":"2026-02-01"},
            "capex":{"value":50,"period_end":"2025-12-31","filed":"2026-02-01"}}}
        self.cap={"market_cap_usd":2000,"asof":"2026-11-04","source":"Licensed fixture"}
    def test_annual_pe_and_fcf_yield(self):
        result,reason=evaluate(self.company,self.cap,self.today)
        self.assertIsNone(reason)
        self.assertEqual(result["pe_annual"],20)
        self.assertEqual(result["fcf_yield_annual"],7.5)
    def test_missing_cap_is_not_estimated(self):
        result,reason=evaluate(self.company,None,self.today)
        self.assertIsNone(result)
    def test_profit_loss_has_no_pe(self):
        self.company["fundamentals"]["net_income"]["value"]=-5
        result,_=evaluate(self.company,self.cap,self.today)
        self.assertIsNone(result["pe_annual"])
    def test_no_false_fcf_with_mismatched_period(self):
        self.company["fundamentals"]["capex"]["period_end"]="2024-12-31"
        result,_=evaluate(self.company,self.cap,self.today)
        self.assertIsNone(result["fcf_yield_annual"])
    def test_no_buy_signals(self):
        d=apply({"companies":[self.company]},{"TEST":self.cap},self.today)
        self.assertEqual(d["companies"][0]["status"],"unknown")
        self.assertIsNone(d["companies"][0]["valuation"])
if __name__=="__main__":unittest.main()
