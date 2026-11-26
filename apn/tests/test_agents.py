import asyncio
import unittest
from apn.agents.handoff import HandoffPolicy, HandoffAgent, assign_exclusive
from apn.agents.identity import IdentityAgent
from apn.core import AsyncMessageBus, HashChainedLedger


WEIGHTS = {"appearance":.45,"temporal":.20,"spatial":.15,"topology":.10,"exclusivity":.10}


class AgentTests(unittest.TestCase):
    def test_handoff_accept_ambiguous_reject(self):
        policy = HandoffPolicy(WEIGHTS)
        high = {key:.95 for key in WEIGHTS}
        mid = {key:.68 for key in WEIGHTS}
        low = {key:.2 for key in WEIGHTS}
        self.assertEqual(policy.decide(high,.5)["state"], "accepted")
        self.assertEqual(policy.decide(mid,.65)["state"], "ambiguous")
        self.assertEqual(policy.decide(low,.1)["state"], "rejected")

    def test_minimal_disclosure_request_has_no_crop(self):
        async def scenario():
            ledger = HashChainedLedger(); bus = AsyncMessageBus(ledger)
            HandoffAgent(bus, {"CAM-01":["CAM-02"]})
            await bus.publish("exit.predicted", "camera-agent:CAM-01", ts_source=1,
                              observed={"source_camera":"CAM-01","source_track":"T-1","exit_edge":"right","last_foot_floor":None},
                              inferred={"target_camera":"CAM-02"}, assumptions=("edge topology",),
                              evidence=("FRAME:1",), ts_ingest=1)
            return ledger.messages()[-1]
        request = asyncio.run(scenario())
        self.assertEqual(request.type, "handoff.request")
        self.assertTrue(request.payload["minimal_disclosure"])
        self.assertFalse(any(key in request.payload for key in ("crop","crop_ref","image","bytes")))

    def test_accepted_link_can_be_split_for_recompute(self):
        async def scenario():
            ledger=HashChainedLedger(); bus=AsyncMessageBus(ledger); agent=IdentityAgent(bus,HandoffPolicy(WEIGHTS))
            high={key:.95 for key in WEIGHTS}
            await agent.evaluate("CAM-01:T-1","CAM-02:T-4",high,.4,1,"MSG-000000")
            self.assertEqual(len(agent.entities),1)
            await agent.unlink("CAM-01:T-1","CAM-02:T-4",2,"MSG-000001")
            return agent,ledger
        agent, ledger = asyncio.run(scenario())
        self.assertEqual(len(agent.entities),2)
        self.assertEqual(ledger.messages()[-1].type,"identity.unlink")
        self.assertTrue(ledger.messages()[-1].inferred["recompute_required"])
    def test_conflicting_claims_receive_exclusive_assignment(self):
        assigned=assign_exclusive(["R1","R2"],["C1","C2"],{("R1","C1"):.9,("R1","C2"):.8,("R2","C1"):.85,("R2","C2"):.1})
        self.assertEqual({item[1] for item in assigned},{"C1","C2"})
        self.assertEqual(sum(item[2] for item in assigned),1.65)


if __name__ == "__main__": unittest.main()
