import asyncio
import unittest
from apn.agents.specialists import dwell_finding, queue_finding, restricted_entry, business_bottleneck,motion_findings,unattended_counter,abandoned_object
from apn.agents.evidence import EvidenceAgent
from apn.agents.orchestrator import OrchestratorAgent
from apn.cases import CaseBuilder
from apn.core import AsyncMessageBus, HashChainedLedger


class SpecialistsAndCasesTests(unittest.TestCase):
    def test_dwell_is_hypothesis_not_accusation(self):
        finding=dwell_finding("E-007","Shelves","CAM-02",30,20,["MSG-1"])
        self.assertIsNotNone(finding)
        self.assertNotIn("theft", finding.explanation.lower())
        self.assertEqual(finding.thresholds["dwell_s"],20)

    def test_queue_security_and_business_rules(self):
        self.assertIsNotNone(queue_finding("Checkout","CAM-04",5,100,4,90,["X"]))
        self.assertIsNotNone(restricted_entry("E-1","CAM-03","Restricted",["X"]))
        self.assertIsNotNone(business_bottleneck("Checkout","CAM-04",5,"growing",4,["X"]))

    def test_end_to_end_finding_opens_explainable_case(self):
        async def scenario():
            ledger=HashChainedLedger(); bus=AsyncMessageBus(ledger); builder=CaseBuilder(ledger); OrchestratorAgent(bus,builder)
            observation=await bus.publish("observation","camera-agent:CAM-02",ts_source=10,
                                          observed={"entity":"E-007"},evidence=("FRAME:CAM-02:20",),ts_ingest=10)
            finding=dwell_finding("E-007","Shelves","CAM-02",30,20,[observation.id])
            await bus.publish("finding","behaviour-agent",ts_source=40,
                              inferred={"finding":finding.model_dump(exclude={"evidence"})},
                              assumptions=("configured dwell threshold",),confidence=finding.confidence,
                              evidence=(observation.id,),caused_by=observation.id,ts_ingest=40)
            return builder,ledger
        builder,ledger=asyncio.run(scenario()); case=list(builder.cases.values())[0]
        self.assertEqual(case.state,"needs_human")
        self.assertGreaterEqual(len(case.hypotheses),2)
        self.assertIn("not a conclusion",case.narrative)
        self.assertEqual(builder.why(case.case_id)["trace"][0]["type"],"observation")
        self.assertEqual(ledger.messages()[-1].type,"case.opened")
    def test_additional_specialist_rules_and_evidence_bundle(self):
        self.assertTrue(any(x.kind=="against_flow" for x in motion_findings("E","Aisles","CAM-02",[(3,0,0),(2,0,1),(1,0,2)])))
        self.assertIsNotNone(unattended_counter("Service Counter","CAM-03",2,0,50,30,["X"]))
        self.assertIsNotNone(abandoned_object("Entrance","CAM-01",20,3,["X"]))
        rows=[{"camera_id":"CAM-01","local_track_id":"T-1","store_ts":1,"ts_source":1,"crop_ref":"c.jpg","foot_px":[1,2],"quality":{"blur":10,"occlusion_est":0}}]
        bundle=EvidenceAgent(rows).bundle(["CAM-01:T-1"],0,2)
        self.assertEqual(bundle["observation_count"],1)


if __name__ == "__main__": unittest.main()
