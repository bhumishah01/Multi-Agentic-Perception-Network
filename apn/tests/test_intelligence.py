import unittest

from intelligence import IntelligenceEngine


class IntelligenceEngineTests(unittest.TestCase):
    def test_observation_flows_through_agents_into_explainable_case(self):
        engine = IntelligenceEngine(dwell_threshold=10)
        engine.observe(ts=100, camera_id="CAM-1", local_track_id="T-1", zone="Aisles",
                       confidence=.9, evidence_id="FRAME-100")
        messages = engine.observe(ts=112, camera_id="CAM-1", local_track_id="T-1", zone="Aisles",
                                  confidence=.88, evidence_id="FRAME-112")
        case = engine.cases()[0]
        self.assertEqual(case["kind"], "extended_dwell")
        self.assertEqual(case["evidence"], ["MSG-000003", "FRAME-112"])
        self.assertIn("12.0s", case["explanation"])
        self.assertEqual(messages[-1].topic, "case.updated")
        self.assertEqual(
            [m["topic"] for m in engine.trace()],
            ["observation.created", "track.updated", "observation.created", "track.updated", "finding.created", "case.updated"],
        )

    def test_restricted_zone_opens_security_case_once(self):
        engine = IntelligenceEngine(restricted_zones={"Staff Only"})
        engine.observe(ts=10, camera_id="CAM-3", local_track_id="T-9", zone="Staff Only",
                       confidence=.92, evidence_id="FRAME-A")
        engine.observe(ts=11, camera_id="CAM-3", local_track_id="T-9", zone="Staff Only",
                       confidence=.91, evidence_id="FRAME-B")
        self.assertEqual(len(engine.cases()), 1)
        self.assertEqual(engine.cases()[0]["kind"], "restricted_zone_entry")

    def test_orchestrator_abstains_on_weak_finding(self):
        engine = IntelligenceEngine(dwell_threshold=1, minimum_confidence=.8)
        engine.observe(ts=1, camera_id="CAM-1", local_track_id="T-1", zone="Aisles",
                       confidence=.5, evidence_id="FRAME-1")
        engine.observe(ts=3, camera_id="CAM-1", local_track_id="T-1", zone="Aisles",
                       confidence=.5, evidence_id="FRAME-2")
        self.assertEqual(engine.cases(), [])
        self.assertIn("finding.abstained", [m["topic"] for m in engine.trace()])

    def test_invalid_confidence_is_rejected(self):
        with self.assertRaises(ValueError):
            IntelligenceEngine().observe(ts=1, camera_id="CAM-1", local_track_id="T-1",
                                         zone="Aisles", confidence=2, evidence_id="FRAME")


if __name__ == "__main__":
    unittest.main()
