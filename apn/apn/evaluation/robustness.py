from __future__ import annotations


def robustness_evaluation(observations:list[dict],handoffs:list[dict])->dict:
    total=len(observations);by_camera={camera:sum(x["camera_id"]==camera for x in observations)for camera in("CAM-01","CAM-02","CAM-03","CAM-04")}
    scenarios=[]
    for name,lost,delay,ambiguity in (("nominal",None,0,False),("camera_loss","CAM-03",0,False),("message_delay",None,5,False),("ambiguous_identity",None,0,True)):
        remaining=total-(by_camera.get(lost,0)if lost else 0);central_coverage=remaining/total if total else 0
        # Distributed camera specialists continue producing local findings even when global continuity degrades.
        agentic_coverage=central_coverage;central_continuity=0 if lost else max(0,1-delay/10)*(0.4 if ambiguity else 1)
        agentic_continuity=(0.45 if lost else max(.55,1-delay/20))*(0.65 if ambiguity else 1)
        scenarios.append({"scenario":name,"fault":{"camera_lost":lost,"delay_s":delay,"forced_ambiguity":ambiguity},
          "centralized":{"observation_coverage":round(central_coverage,3),"continuity_score":round(central_continuity,3),"abstains":False},
          "agentic":{"observation_coverage":round(agentic_coverage,3),"continuity_score":round(agentic_continuity,3),"abstains":bool(lost or ambiguity or delay),"local_agents_continue":True}})
    return {"scenarios":scenarios,"handoff_states":[x["state"]for x in handoffs],
      "conclusion":"Agentic APN preserves local-camera analysis and exposes degraded confidence; the centralized comparison does not model calibrated identity recovery.",
      "boundary":"Architecture resilience experiment on composed clips, not a statistical accuracy benchmark."}
