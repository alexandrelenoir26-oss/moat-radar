import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from hf_prices import latest_row,validated_download_url
class HFPriceTests(unittest.TestCase):
 def test_latest_csv_with_us_date(self):
  body=b"Date,Open,High,Low,Close,Volume\n11/03/2026,100,102,99,101,55\n11/04/2026,102,105,101,104,99\n"
  self.assertEqual(latest_row(body,date(2026,11,5)),{"date":"2026-11-04","price_usd":104.0})
 def test_old_data_rejected(self):
  self.assertIsNone(latest_row(b"Date,Close,Volume\n10/01/2026,40,50\n",date(2026,11,5)))
 def test_empty_no_observed_volume(self):
  self.assertIsNone(latest_row(b"Date,Close,Volume\n11/04/2026,40,0\n",date(2026,11,5)))
 def test_signed_url(self):
  good="https://api.hfdatalibrary.com/v1/download/AAPL?token=abc"
  self.assertEqual(validated_download_url(good,"AAPL"),good)
  with self.assertRaises(ValueError):
   validated_download_url("https://external.invalid/steal?token=abc","AAPL")
  with self.assertRaises(ValueError):
   validated_download_url("https://api.hfdatalibrary.com/v1/download/MSFT?token=abc","AAPL")
if __name__=="__main__": unittest.main()
