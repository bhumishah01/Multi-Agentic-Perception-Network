import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from apn.core import AsyncMessageBus, HashChainedLedger, ReplayClock


class CoreRuntimeTests(unittest.TestCase):
    def test_chain_trace_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = HashChainedLedger(Path(directory) / "ledger.sqlite3")
            bus = AsyncMessageBus(ledger)

            async def scenario():
                observation = await bus.publish(
                    "observation", "camera-agent:CAM-01", ts_source=1,
                    observed={"camera_id": "CAM-01", "frame_idx": 24},
                    evidence=("FRAME:CAM-01:24",), ts_ingest=10,
                )
                return await bus.publish(
                    "track.updated", "tracking-agent", ts_source=1,
                    inferred={"entity": "local:CAM-01:T-1"}, assumptions=("centroid association",),
                    evidence=(observation.id,), caused_by=observation.id, score=.7, ts_ingest=11,
                )

            child = asyncio.run(scenario())
            self.assertEqual([item.type for item in ledger.trace(child.id)], ["observation", "track.updated"])
            self.assertEqual(ledger.verify_chain(), (True, None))
            row = ledger.connection.execute("SELECT envelope FROM message_ledger WHERE message_id='MSG-000001'").fetchone()
            damaged = json.loads(row["envelope"])
            damaged["observed"]["frame_idx"] = 999
            ledger.connection.execute(
                "UPDATE message_ledger SET envelope=? WHERE message_id='MSG-000001'", (json.dumps(damaged),)
            )
            self.assertEqual(ledger.verify_chain(), (False, "MSG-000001"))

    def test_replay_delivery_is_deterministic(self):
        async def run_once():
            ledger = HashChainedLedger()
            bus = AsyncMessageBus(ledger)
            seen = []

            async def receive(message):
                seen.append(message.id)

            bus.subscribe("observation", receive)
            later = await bus.publish("observation", "cam", ts_source=2, observed={"n": 2}, ts_ingest=2)
            earlier = await bus.publish("observation", "cam", ts_source=1, observed={"n": 1}, ts_ingest=1)
            seen.clear()
            await bus.replay([later, earlier])
            return seen

        self.assertEqual(asyncio.run(run_once()), ["MSG-000002", "MSG-000001"])
        self.assertEqual(asyncio.run(run_once()), ["MSG-000002", "MSG-000001"])

    def test_replay_clock(self):
        clock = ReplayClock(10)
        clock.set_speed(2)
        clock.play()
        self.assertEqual(clock.advance(2), 4)
        clock.seek(9)
        self.assertEqual(clock.advance(1), 10)
        self.assertFalse(clock.playing)


if __name__ == "__main__":
    unittest.main()
