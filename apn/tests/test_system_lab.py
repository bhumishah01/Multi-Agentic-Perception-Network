import json,unittest
from pathlib import Path
from apn.lab import SystemLab
ROOT=Path(__file__).resolve().parents[1]
class SystemLabTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  rows=json.loads((ROOT/"output/phase2_yolo/observations.json").read_text());state=json.loads((ROOT/"output/scenario/state.json").read_text());summary=json.loads((ROOT/"output/phase2_yolo/summary.json").read_text());cls.lab=SystemLab(rows,state,summary)
 def test_query_compiler_changes_execution_graph(self):
  queue=self.lab.query_plan("why is checkout queue high and what should we do?");flow=self.lab.query_plan("show aisle movement paths")
  self.assertNotEqual({x["id"]for x in queue["nodes"]},{x["id"]for x in flow["nodes"]});self.assertIn("simulation",{x["id"]for x in queue["nodes"]})
 def test_trajectories_evidence_and_causal_graph_are_real(self):
  self.assertGreater(len(self.lab.trajectories()["tracks"]),10);wall=self.lab.evidence_wall();self.assertTrue(wall["evidence"]);self.assertTrue(wall["causal_graph"])
 def test_incidents_change_network_and_preserve_local_operation(self):
  lost=self.lab.inject("camera_loss");self.assertEqual(lost["network"]["active_nodes"],3);self.assertTrue(lost["network"]["local_reasoning_continues"]);self.assertTrue(lost["abstains"])
 def test_digital_twin_and_benchmark(self):
  one=self.lab.digital_twin(1);two=self.lab.digital_twin(2);self.assertGreater(one["final_queue"],two["final_queue"]);self.assertEqual(len(self.lab.benchmark()["experiments"]),5)
if __name__=="__main__":unittest.main()
