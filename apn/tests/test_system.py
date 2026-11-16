import os,tempfile,unittest,json
from pathlib import Path
import server
class SystemTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();server.DB=Path(self.temp.name)/'test.sqlite3';server.init()
  server.CAMERAS.update({k:True for k in server.CAMERAS})
 def tearDown(self):self.temp.cleanup()
 def run_case(self):
  with server.connect() as c:c.execute('INSERT INTO runs VALUES(?,?,?,?,?)',('test','Investigate','running',None,0))
  server.investigate('test','Investigate')
  return server.snapshot()['runs'][0]
 def test_no_evidence_abstains(self):
  self.assertIn('Insufficient',self.run_case()['result']['summary'])
 def test_synthetic_evidence_and_counts(self):
  server.seed();r=self.run_case()['result'];self.assertEqual(r['specialists']['Flow']['unique_local_tracks_by_zone']['Checkout'],12)
  self.assertEqual(r['sources'],['synthetic']);self.assertEqual(len(r['evidence_event_ids']),1404)
  self.assertEqual(r['specialists']['Flow']['identity_count_bounds'],{'minimum_if_ambiguous_matches_hold':28,'maximum_without_ambiguous_merges':33,'local_track_count':39})
  self.assertEqual(r['evidence_grade'],'degraded')
 def test_camera_loss_changes_coverage(self):
  server.seed();server.CAMERAS['CAM-4']=False;r=self.run_case()['result']
  self.assertEqual(r['specialists']['Flow']['unique_local_tracks_by_zone']['Checkout'],0)
  self.assertIn('CAM-4',r['specialists']['Verifier']['offline_cameras'])
 def test_invalid_event_rejected(self):
  with self.assertRaises(ValueError):server.ingest({'ts':1})
 def test_handoff_policy_preserves_ambiguity(self):
  accepted=server.decide_handoff({'components':{'temporal':.95,'spatial':.9,'motion':.85,'appearance':.8},'runner_up_score':.5})
  ambiguous=server.decide_handoff({'components':{'temporal':.86,'spatial':.79,'motion':.72,'appearance':.68},'runner_up_score':.69})
  rejected=server.decide_handoff({'components':{'temporal':.4,'spatial':.4,'motion':.4,'appearance':.4},'runner_up_score':.2})
  self.assertEqual([accepted['state'],ambiguous['state'],rejected['state']],['accepted','ambiguous','rejected'])
 def test_question_selects_typed_specialists(self):
  self.assertEqual(server.plan_agents('Where are handoffs failing?'),['Movement','Verifier'])
  self.assertEqual(server.plan_agents('Which queue has the longest wait?'),['Flow','Dwell','Verifier'])
  self.assertEqual(server.plan_agents('Which cross-camera matches are uncertain?'),['Movement','Verifier'])
 def test_real_replay_imports_observations_and_candidates(self):
  loaded=server.load_replay();state=server.snapshot()
  self.assertEqual(loaded,{'source':'real_replay','observations':213,'handoffs':11})
  self.assertEqual(len([e for e in state['events'] if e['source']=='real_replay']),80)
  self.assertEqual(len([h for h in state['handoffs'] if h['run']=='real-replay']),11)
if __name__=='__main__':unittest.main()
