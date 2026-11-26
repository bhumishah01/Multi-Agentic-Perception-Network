#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def metrics(predictions,truth,positive_states):
 known={(x["source"],x["target"]) for x in truth if x["truth"]=="same"}
 positive={(x["source"],x["target"]) for x in predictions if x["state"] in positive_states}
 tp=len(known & positive);fp=len(positive-known);fn=len(known-positive)
 return {"known_links":len(known),"predicted_positive_links":len(positive),
         "precision":round(tp/(tp+fp),3) if tp+fp else None,
         "recall":round(tp/(tp+fn),3) if tp+fn else None,
         "false_merge_rate":round(fp/len(positive),3) if positive else 0.0}


def main():
 state=json.loads((ROOT/"output/scenario/state.json").read_text());gt=json.loads((ROOT/"eval/groundtruth/handoffs.json").read_text())
 truth=gt["links"];states=[x["state"] for x in state["handoffs"]]
 predictions=[{"source":f'{x["source_camera"]}:{x["source_track"]}',"target":f'{x["target_camera"]}:{x["target_track"]}',"state":x["state"]} for x in state["handoffs"]]
 hsv=[{**x,"state":"accepted" if handoff["components"]["appearance"]>=.62 else "rejected"} for x,handoff in zip(predictions,state["handoffs"])]
 results={
  "dataset":"COMPOSED; integration test, not benchmark",
  "A_hog_hsv_baseline":{"observation_count":200,"IDF1":None,"ID_switches":None,"handoff_metrics":None,
    "reason":"HOG tracks are not hand-labelled densely enough for valid IDF1 or handoff scoring."},
  "B_yolo_bytetrack_hsv":{"observation_count":664,"IDF1":None,"ID_switches":None,"handoff_metrics":metrics(hsv,truth,{"accepted"}),
    "reason":"Only two known cross-segment links; report is an integration sanity check."},
  "C_full_negotiation":{"handoff_metrics_strict_accept":metrics(predictions,truth,{"accepted"}),
    "handoff_metrics_human_review_inclusive":metrics(predictions,truth,{"accepted","ambiguous"}),
    "states":states},
  "limitations":["CAM-01→CAM-02 ground truth is unknown.","No dense frame-level identity labels exist.",
                 "Clips are composed and too small for statistical claims.","Scores are heuristic, not calibrated probabilities."]}
 out=ROOT/"eval/results.json";out.write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
if __name__=="__main__":main()
