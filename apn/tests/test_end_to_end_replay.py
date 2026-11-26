import json
import unittest
from pathlib import Path

from apn.core import HashChainedLedger


ROOT=Path(__file__).resolve().parents[1]


class EndToEndReplayTests(unittest.TestCase):
 def test_real_footage_reaches_ranked_handoffs_case_and_evidence(self):
  observations=json.loads((ROOT/"output/phase2_yolo/observations.json").read_text())
  state=json.loads((ROOT/"output/scenario/state.json").read_text())
  self.assertGreater(len(observations),600)
  self.assertEqual(len(state["handoffs"]),3)
  self.assertTrue(all(x["candidate_count"]>0 for x in state["handoffs"]))
  self.assertTrue(all(x["state"]=="ambiguous" for x in state["handoffs"]))
  self.assertTrue(all(x["state"] in {"accepted","ambiguous","rejected"} for x in state["handoffs"]))
  case=state["cases"][0]
  self.assertGreater(case["evidence_bundle"]["observation_count"],0)
  self.assertGreaterEqual(len(case["evidence_bundle"]["crops"]),3)
  ids={message["id"] for message in state["messages"]}
  self.assertTrue(set(case["trace"]).issubset(ids))
  ledger=HashChainedLedger(ROOT/"output/phase2_yolo/ledger.sqlite3")
  try:self.assertEqual(ledger.verify_chain(),(True,None))
  finally:ledger.close()

if __name__=="__main__":unittest.main()
