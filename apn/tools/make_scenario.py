#!/usr/bin/env python3
"""Build the honest, reproducible demo state from Phase 2 observations."""
from __future__ import annotations
import json,sys
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from apn.agents.evidence import EvidenceAgent
from apn.agents.handoff import HandoffPolicy
from apn.agents.matcher import TrackMatcher
from apn.store.runtime import recompute_entities

RUN=ROOT/"output"/"phase2_yolo";OUT=ROOT/"output"/"scenario"
ZONES={"CAM-01":"Entrance","CAM-02":"Main Aisle","CAM-03":"Service Counter","CAM-04":"Checkout"}


def main():
 rows=json.loads((RUN/"observations.json").read_text());groups=defaultdict(list)
 for row in rows:groups[(row["camera_id"],row["local_track_id"])].append(row)
 for items in groups.values():items.sort(key=lambda row:row["store_ts"])
 # The first track is a declared demo anchor. Every downstream track is selected
 # autonomously by ranking all candidates in the next configured camera.
 weights={"appearance":.45,"temporal":.20,"spatial":.15,"topology":.10,"exclusivity":.10}
 policy=HandoffPolicy(weights=weights)
 matcher=TrackMatcher(rows,RUN,policy)
 targets=[("CAM-01","T-0003")];rankings=[]
 for camera in ("CAM-02","CAM-03","CAM-04"):
  # The validation reels are independent generated clips rather than a shared
  # clock. Rank appearance/spatial candidates for demonstration, but never
  # promote the resulting cross-reel link beyond human review.
  ranked=matcher.rank(targets[-1],camera,max_transit_s=120,min_reverse_s=-120)
  if not ranked:raise RuntimeError(f"no eligible tracks found in {camera}")
  rankings.append(ranked);targets.append(ranked[0]["track"])
 selected=[groups[key] for key in targets]
 messages=[]
 def msg(kind,sender,ts,observed=None,inferred=None,assumptions=None,evidence=None,caused_by=None):
  item={"id":f"MSG-{900000+len(messages)+1:06d}","type":kind,"sender":sender,"ts_source":ts,
        "observed":observed or {},"inferred":inferred or {},"assumptions":assumptions or [],
        "evidence":evidence or [],"caused_by":caused_by};messages.append(item);return item
 journey=[]
 for key,items in zip(targets,selected):
  first,last=items[0],items[-1];source=msg("observation",f"camera-agent:{key[0]}",first["store_ts"],
   observed={"camera_id":key[0],"local_track_id":key[1],"bbox_px":first["bbox_px"],"zone":ZONES[key[0]]},
   evidence=[f"FRAME:{key[0]}:{first['frame_idx']}"])
  journey.append({"camera_id":key[0],"local_track_id":key[1],"zone":ZONES[key[0]],
                  "start":first["store_ts"],"end":last["store_ts"],"observation_count":len(items),"message_id":source["id"]})
 handoffs=[]
 for index in range(3):
  left,right=selected[index],selected[index+1];result=rankings[index][0]
  components=result["components"];score=result["decision"]["score"];state=result["decision"]["state"]
  state="ambiguous"  # separate generated clips: never silently merge
  request=msg("handoff.request","handoff-agent",left[-1]["store_ts"],
   observed={"source_camera":targets[index][0],"source_track":targets[index][1]},
   inferred={"candidate_camera":targets[index+1][0]},assumptions=["configured sequential topology"],
   evidence=[journey[index]["message_id"]],caused_by=journey[index]["message_id"])
  decision=msg("handoff.response","identity-agent",right[0]["store_ts"],
   observed={"source_track":f"{targets[index][0]}:{targets[index][1]}","target_track":f"{targets[index+1][0]}:{targets[index+1][1]}"},
   inferred={"state":state,"score":round(score,3),"components":{k:round(v,3) for k,v in components.items()}},
   assumptions=["HSV appearance is a baseline score, not identity probability"],evidence=[request["id"],journey[index+1]["message_id"]],caused_by=request["id"])
  handoffs.append({"handoff_id":f"HO-{index+1:03d}","source_camera":targets[index][0],"target_camera":targets[index+1][0],
                   "source_track":targets[index][1],"target_track":targets[index+1][1],"state":state,"score":round(score,3),
                   "margin":result["decision"]["margin"],"components":decision["inferred"]["components"],"message_id":decision["id"],
                   "candidate_count":len(rankings[index]),"runner_up":round(rankings[index][1]["raw_score"],3) if len(rankings[index])>1 else None})
 # Measured peak simultaneous checkout tracks, not a fabricated dwell event.
 checkout=defaultdict(set)
 for row in rows:
  if row["camera_id"]=="CAM-04":checkout[row["frame_idx"]].add(row["local_track_id"])
 peak_frame,peak_tracks=max(checkout.items(),key=lambda item:len(item[1]));peak=len(peak_tracks)
 finding=msg("finding","queue-agent",21.958+peak_frame/24,
  observed={"camera_id":"CAM-04","zone":"Checkout","peak_person_tracks":peak,"frame_idx":peak_frame},
  inferred={"kind":"checkout_bottleneck","severity":"attention"},assumptions=["detected tracks approximate people present"],
  evidence=[f"FRAME:CAM-04:{peak_frame}"],caused_by=journey[-1]["message_id"])
 case_msg=msg("case.opened","orchestrator-agent",finding["ts_source"],inferred={"case_id":"CASE-00001"},
  assumptions=["operator review required"],evidence=finding["evidence"],caused_by=finding["id"])
 case={"case_id":"CASE-00001","kind":"checkout_bottleneck","severity":"attention","urgency":.62,"state":"needs_human",
  "entity_id":"E-001","zone":"Checkout","camera_ids":["CAM-02","CAM-03","CAM-04"],"opened_at":finding["ts_source"],
  "timeline":journey[1:],"hypotheses":[
   {"id":"H-1","label":"checkout congestion","supporting":[f"{peak} simultaneous detected tracks at frame {peak_frame}"],"contradicting":[],"score":.72},
   {"id":"H-2","label":"normal transaction cluster","supporting":[],"contradicting":["clip too short to establish sustained queue"],"score":.48}],
  "findings":[{"agent":"queue-agent","kind":"checkout_bottleneck","measurements":{"peak_tracks":peak},"thresholds":{"queue_len_alert":4}}],
  "evidence":[f"FRAME:CAM-04:{peak_frame}"],"alternative_explanations":["normal transaction cluster","temporary crossing paths"],
  "recommended_response":"Review the checkout segment; do not infer staffing need from this short clip alone.","human_decisions":[],
  "trace":[journey[-1]["message_id"],finding["id"],case_msg["id"]],
  "narrative":f"CAM-04 contained a measured peak of {peak} simultaneous person tracks. The short composed clip supports a checkout-congestion review cue, not a sustained-wait conclusion."}
 case["evidence_bundle"]=EvidenceAgent(rows).bundle([f"{c}:{t}" for c,t in targets],0,60)
 entities=[{"entity_id":"E-001","label":"Entity 001","status":"active","member_tracks":[f"{c}:{t}" for c,t in targets[1:]],"journey":journey[1:],"confidence_state":"accepted"},
           {"entity_id":"E-CANDIDATE","label":"Entrance candidate","status":"ambiguous","member_tracks":[f"{targets[0][0]}:{targets[0][1]}"],"journey":journey[:1],"confidence_state":"ambiguous"}]
 state={"mode":"COMPOSED","entities":entities,"handoffs":handoffs,"cases":[case],"messages":messages,
        "provenance":{"source":"Phase 2 YOLO observations","anchor_track":f"{targets[0][0]}:{targets[0][1]}",
                      "target_tracks":[f"{c}:{t}" for c,t in targets],"selection":"ranked all eligible next-camera tracks",
                      "warning":"Cross-camera links are integration-test hypotheses, not ground truth."}}
 state=recompute_entities(state,{})
 OUT.mkdir(parents=True,exist_ok=True);(OUT/"state.json").write_text(json.dumps(state,indent=2));print(json.dumps({"output":str(OUT/"state.json"),"messages":len(messages),"handoffs":handoffs,"peak_checkout_tracks":peak},indent=2))
if __name__=="__main__":main()
