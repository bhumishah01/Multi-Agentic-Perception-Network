import unittest,os,tempfile
from pathlib import Path
from fastapi.testclient import TestClient
os.environ["APN_RUNTIME_DB"]=str(Path(tempfile.gettempdir())/f"apn-api-test-{os.getpid()}.sqlite3")
from apn.api.main import app,TOKEN


class APITests(unittest.TestCase):
 def setUp(self):self.client=TestClient(app);self.auth={"Authorization":f"Bearer {TOKEN}"}
 def test_openapi_and_auth(self):
  self.assertEqual(self.client.get("/docs").status_code,200)
  self.assertEqual(self.client.get("/api/state").status_code,401)
  self.assertEqual(self.client.get("/api/state",headers=self.auth).status_code,200)
  self.assertEqual(self.client.get("/api/business/spatial/CAM-02",headers=self.auth).status_code,200)
 def test_role_denies_raw_video(self):
  headers={**self.auth,"X-APN-Role":"Business Operations"}
  self.assertEqual(self.client.get("/api/video/CAM-01",headers=headers).status_code,403)
 def test_auditor_can_verify_audit(self):
  headers={**self.auth,"X-APN-Role":"Auditor"};response=self.client.get("/api/audit/verify",headers=headers)
  self.assertEqual(response.status_code,200);self.assertTrue(response.json()["intact"])
 def test_ask_threshold_and_decision_routes(self):
  self.assertEqual(self.client.post("/api/ask",headers=self.auth,json={"question":"why did the case open?"}).status_code,200)
  aisle=self.client.post("/api/ask",headers=self.auth,json={"question":"How many customers were in aisle one?"}).json()
  self.assertEqual(aisle["facts"]["camera_id"],"CAM-02");self.assertIn("Tracking Agent",aisle["agents"])
  admin={**self.auth,"X-APN-Role":"Administrator"}
  self.assertTrue(self.client.patch("/api/thresholds",headers=admin,json={"values":{"queue":{"queue_len_alert":5}}}).json()["audited"])
  self.assertTrue(self.client.post("/api/handoffs/HO-001/decision",headers=self.auth,json={"decision":"reject"}).json()["recompute_required"])
 def test_calibration_and_real_identity_recompute(self):
  admin={**self.auth,"X-APN-Role":"Administrator"}
  payload={"image_points":[[0,0],[100,0],[100,100],[0,100]],"floor_points":[[0,0],[10,0],[10,10],[0,10]]}
  self.assertLess(self.client.post("/api/calibration/CAM-01",headers=admin,json=payload).json()["residual_error"],1e-5)
  (Path(__file__).resolve().parents[1]/"config/calibration/CAM-01.json").unlink(missing_ok=True)
  self.client.post("/api/handoffs/HO-001/decision",headers=self.auth,json={"decision":"reject"})
  before=len(self.client.get("/api/state",headers=self.auth).json()["entities"])
  response=self.client.post("/api/handoffs/HO-001/decision",headers=self.auth,json={"decision":"accept","note":"operator verified"}).json()
  self.assertTrue(response["recomputed"])
  self.assertLess(len(self.client.get("/api/state",headers=self.auth).json()["entities"]),before)
 def test_business_simulation_funnel_evaluation_and_report(self):
  self.assertEqual(len(self.client.get("/api/business/funnel",headers=self.auth).json()["stages"]),4)
  simulation=self.client.post("/api/business/simulate",headers=self.auth,json={"kind":"checkout","added_counters":1}).json()
  self.assertGreater(simulation["estimated_load_reduction_pct"],0)
  self.assertEqual(len(self.client.get("/api/evaluation/robustness",headers=self.auth).json()["scenarios"]),4)
  admin={**self.auth,"X-APN-Role":"Administrator"};report=self.client.post("/api/reports/generate",headers=admin).json()
  self.assertIn("executive_summary",report)
  showcase=self.client.get("/api/showcase",headers=self.auth).json();self.assertEqual(len(showcase["hypotheses"]),4)
  approval=self.client.post("/api/showcase/approve",headers=self.auth).json();self.assertFalse(approval["external_action_taken"])

if __name__=="__main__":unittest.main()
