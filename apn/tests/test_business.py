import json
import unittest
from pathlib import Path

from apn.business import BusinessAnalytics,OperationsSimulator,build_report,build_showcase,approve_showcase
from apn.evaluation import robustness_evaluation

ROOT=Path(__file__).resolve().parents[1]


class BusinessIntelligenceTests(unittest.TestCase):
 def test_vertical_profiles_change_questions_without_inventing_commerce(self):
  analytics=BusinessAnalytics(self.rows)
  supermarket=analytics.vertical_profile("supermarket");cafe=analytics.vertical_profile("cafe");retail=analytics.vertical_profile("retail")
  self.assertEqual(len(supermarket["comparison"]),4);self.assertNotEqual(supermarket["questions"],cafe["questions"])
  self.assertNotEqual(cafe["future"],retail["future"]);self.assertIn("POS",supermarket["truth_boundary"])

 @classmethod
 def setUpClass(cls):
  cls.rows=json.loads((ROOT/"output/phase2_yolo/observations.json").read_text());cls.analytics=BusinessAnalytics(cls.rows)
 def test_spatial_heatmap_paths_and_window_comparison(self):
  spatial=self.analytics.spatial("CAM-02");self.assertEqual((len(spatial["grid"]),len(spatial["grid"][0])),(4,8));self.assertGreater(len(spatial["paths"]),0)
  comparison=self.analytics.comparison("CAM-02");self.assertIn("peak_change",comparison);self.assertGreater(comparison["first"]["observations"]+comparison["second"]["observations"],0)
 def test_queue_and_uncertainty_aware_funnel(self):
  queue=self.analytics.queue();self.assertGreaterEqual(queue["peak_occupancy"],queue["threshold"]);self.assertIn("not validated",queue["boundary"])
  funnel=self.analytics.funnel();self.assertEqual(len(funnel["stages"]),4);self.assertGreaterEqual(funnel["global_identity_upper_bound"],funnel["global_identity_lower_bound"]);self.assertIn("not sales conversion",funnel["boundary"])
 def test_recommendations_simulation_and_report(self):
  recommendations=self.analytics.recommendations();self.assertTrue(recommendations[0]["requires_human"])
  simulation=OperationsSimulator(self.analytics.queue()).checkout(1,1,3);self.assertLess(simulation["projected"]["load_index"],simulation["baseline"]["load_index"])
  report=build_report(self.analytics);self.assertIn("executive_summary",report);self.assertEqual(len(report["camera_comparisons"]),4)
 def test_robustness_exposes_degradation_and_abstention(self):
  result=robustness_evaluation(self.rows,[{"state":"ambiguous"}]);lost=next(x for x in result["scenarios"]if x["scenario"]=="camera_loss")
  self.assertTrue(lost["agentic"]["local_agents_continue"]);self.assertTrue(lost["agentic"]["abstains"])
 def test_closed_loop_showcase_separates_observed_staged_and_inferred(self):
  showcase=build_showcase(self.rows,True);self.assertEqual(showcase["truth_boundary"]["observed"].split()[0],"Boxes,")
  self.assertEqual(next(x for x in showcase["hypotheses"]if x["id"]=="H-CAPACITY")["source"],"STAGED INPUT")
  measured_only=build_showcase(self.rows,False);self.assertEqual(measured_only["finding"]["confidence_state"],"insufficient-evidence")
  approval=approve_showcase(showcase);self.assertFalse(approval["external_action_taken"]);self.assertEqual(approval["verification"]["source"],"STAGED OUTCOME")

if __name__=="__main__":unittest.main()
