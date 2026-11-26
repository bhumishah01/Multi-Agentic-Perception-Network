from __future__ import annotations
import math
from apn.cases.models import Finding


def dwell_finding(entity_id: str, zone: str, camera_id: str, dwell_s: float,
                  threshold_s: float, evidence: list[str]) -> Finding | None:
    if dwell_s <= threshold_s:
        return None
    confidence = min(.95, .55 + .4 * min(1, (dwell_s - threshold_s) / max(threshold_s, 1)))
    return Finding(kind="extended_dwell", agent="behaviour-agent", entity_id=entity_id, zone=zone,
                   camera_ids=[camera_id], severity="attention", confidence=confidence,
                   measurements={"dwell_s": dwell_s}, thresholds={"dwell_s": threshold_s},
                   explanation=f"Observed dwell {dwell_s:.1f}s exceeded the configured {threshold_s:.1f}s threshold.",
                   evidence=evidence)


def loiter_finding(entity_id: str, zone: str, camera_id: str, window_s: float,
                   displacement: float, max_displacement: float, evidence: list[str]) -> Finding | None:
    if displacement > max_displacement:
        return None
    return Finding(kind="loitering", agent="behaviour-agent", entity_id=entity_id, zone=zone,
                   camera_ids=[camera_id], severity="attention", confidence=.65,
                   measurements={"window_s":window_s,"displacement":displacement},
                   thresholds={"max_displacement":max_displacement},
                   explanation=f"Displacement {displacement:.2f} remained below {max_displacement:.2f} over {window_s:.1f}s.",
                   evidence=evidence)


def queue_finding(zone: str, camera_id: str, count: int, wait_s: float,
                  count_threshold: int, wait_threshold: float, evidence: list[str]) -> Finding | None:
    if count < count_threshold and wait_s < wait_threshold:
        return None
    return Finding(kind="queue_breach", agent="queue-agent", zone=zone, camera_ids=[camera_id],
                   severity="attention", confidence=.72, measurements={"count":count,"wait_s":wait_s},
                   thresholds={"count":count_threshold,"wait_s":wait_threshold},
                   explanation=f"Queue measurement reached {count} people with observed wait {wait_s:.1f}s.",
                   evidence=evidence)


def restricted_entry(entity_id: str, camera_id: str, zone: str, evidence: list[str]) -> Finding | None:
    if zone != "Restricted":
        return None
    return Finding(kind="restricted_zone_entry", agent="security-agent", entity_id=entity_id, zone=zone,
                   camera_ids=[camera_id], severity="high", confidence=.9,
                   measurements={"zone":zone}, thresholds={"allowed": "false"},
                   explanation="An anonymous tracked entity entered the configured staff-only zone.", evidence=evidence)


def business_bottleneck(zone: str, camera_id: str, count: int, trend: str,
                        threshold: int, evidence: list[str]) -> Finding | None:
    if count < threshold or trend not in {"growing", "stable_high"}:
        return None
    return Finding(kind="checkout_bottleneck", agent="business-ops-agent", zone=zone,
                   camera_ids=[camera_id], severity="attention", confidence=.7,
                   measurements={"count":count,"trend":trend}, thresholds={"count":threshold},
                   explanation=f"Checkout occupancy is {count} and the measured trend is {trend}.", evidence=evidence)


def motion_findings(entity_id:str,zone:str,camera_id:str,points:list[tuple[float,float,float]],expected_flow:tuple[float,float]=(1,0))->list[Finding]:
    if len(points)<3:return []
    findings=[];x0,y0,t0=points[0];x1,y1,t1=points[-1];duration=max(t1-t0,1e-6);displacement=math.hypot(x1-x0,y1-y0);speed=displacement/duration
    vx,vy=x1-x0,y1-y0;dot=vx*expected_flow[0]+vy*expected_flow[1]
    revisits=sum(math.hypot(points[i][0]-points[i-2][0],points[i][1]-points[i-2][1])<.5 for i in range(2,len(points)))
    evidence=[f"TRAJECTORY:{camera_id}:{entity_id}"]
    if dot<0:findings.append(Finding(kind="against_flow",agent="behaviour-agent",entity_id=entity_id,zone=zone,camera_ids=[camera_id],severity="info",confidence=.65,measurements={"flow_dot":dot},thresholds={"flow_dot":0},explanation="Measured displacement opposes the configured zone flow vector.",evidence=evidence))
    if revisits>=2:findings.append(Finding(kind="pacing_backtracking",agent="behaviour-agent",entity_id=entity_id,zone=zone,camera_ids=[camera_id],severity="attention",confidence=.62,measurements={"revisits":revisits},thresholds={"revisits":2},explanation="The measured path revisited earlier positions.",evidence=evidence))
    if speed>3.0:findings.append(Finding(kind="running_cue",agent="behaviour-agent",entity_id=entity_id,zone=zone,camera_ids=[camera_id],severity="attention",confidence=.6,measurements={"speed":speed},thresholds={"speed":3.0},explanation="Estimated map speed exceeded the configured running-cue threshold.",evidence=evidence))
    return findings


def unattended_counter(zone:str,camera_id:str,customer_count:int,staff_count:int,idle_s:float,threshold_s:float,evidence:list[str])->Finding|None:
    if customer_count<1 or staff_count>0 or idle_s<threshold_s:return None
    return Finding(kind="unattended_service_counter",agent="business-ops-agent",zone=zone,camera_ids=[camera_id],severity="attention",confidence=.68,
                   measurements={"customers":customer_count,"staff":staff_count,"idle_s":idle_s},thresholds={"idle_s":threshold_s},
                   explanation="Customers were detected while the configured service position had no staff track.",evidence=evidence)


def abandoned_object(zone:str,camera_id:str,stationary_s:float,nearest_person_m:float,evidence:list[str])->Finding|None:
    if stationary_s<15 or nearest_person_m<2:return None
    return Finding(kind="abandoned_object_cue",agent="security-agent",zone=zone,camera_ids=[camera_id],severity="attention",confidence=.45,
                   measurements={"stationary_s":stationary_s,"nearest_person_m":nearest_person_m},thresholds={"stationary_s":15,"nearest_person_m":2},
                   explanation="Experimental generic-object cue: a stationary detection remained separated from tracked people.",evidence=evidence)
