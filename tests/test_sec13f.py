import csv
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sec13f import import_rows

class Sec13FTests(unittest.TestCase):
 def test_three_consistent_filings_and_reject_options(self):
  with tempfile.TemporaryDirectory() as tmp:
   t=Path(tmp)
   (t/"map.csv").write_text("cusip,ticker,verified\n037833100,AAPL,yes\n",encoding="utf-8")
   (t/"SUBMISSION.tsv").write_text(
    "ACCESSION_NUMBER\tPERIODOFREPORT\tSUBMISSIONTYPE\tFILING_DATE\n"+
    "".join(f"000{i}\t30-JUN-2026\t13F-HR\t10-AUG-2026\n" for i in range(1,5)),encoding="utf-8")
   (t/"INFOTABLE.tsv").write_text(
    "ACCESSION_NUMBER\tCUSIP\tVALUE\tSSHPRNAMT\tSSHPRNAMTTYPE\tPUTCALL\n"+
    "0001\t037833100\t200\t1000\tSH\t\n"+
    "0002\t037833100\t402\t2000\tSH\t\n"+
    "0003\t037833100\t600\t3000\tSH\t\n"+
    "0004\t037833100\t500\t1000\tSH\tPUT\n",encoding="utf-8")
   rows=import_rows(t/"SUBMISSION.tsv",t/"INFOTABLE.tsv",t/"map.csv","2026-06-30","thousands")
   self.assertEqual(len(rows),1)
   self.assertEqual(rows[0]["number_of_filings"],3)
   self.assertEqual(rows[0]["historical_implied_price_usd"],200)
 def test_invalid_quarter(self):
  with self.assertRaises(ValueError):
   import_rows("a","b","c","2026-11-06","thousands")
if __name__=="__main__":unittest.main()
