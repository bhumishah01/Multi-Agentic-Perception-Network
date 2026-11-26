#!/usr/bin/env python3
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
 expected=json.loads((ROOT/"scenarios/scenario_01.yaml").read_text())["expected"]
 state=json.loads((ROOT/"output/scenario/state.json").read_text())
 assert [x["source_camera"] for x in state["handoffs"]]+[state["handoffs"][-1]["target_camera"]]==expected["camera_order"]
 assert [x["state"] for x in state["handoffs"]]==expected["handoff_states"]
 assert state["cases"][0]["kind"]==expected["case_kind"]
 assert len(state["messages"])>=expected["minimum_messages"]
 assert len(state["cases"][0]["camera_ids"])>=expected["minimum_case_cameras"]
 summary=json.loads((ROOT/"output/phase2_yolo/summary.json").read_text());assert summary["ledger_intact"] and summary["observations"]>0
 required=["apn/core/protocol.py","apn/agents/handoff.py","apn/security/health.py","apn/api/main.py","web2/dist/index.html",
           "docs/ARCHITECTURE.md","docs/PROTOCOL.md","docs/THREAT_MODEL.md","docs/EVALUATION.md"]
 missing=[item for item in required if not (ROOT/item).exists()];assert not missing,f"missing: {missing}"
 print(json.dumps({"verified":True,"observations":summary["observations"],"messages":len(state["messages"]),
                   "handoffs":[x["state"] for x in state["handoffs"]],"case":state["cases"][0]["case_id"],"required_files":len(required)},indent=2))
if __name__=="__main__":main()
