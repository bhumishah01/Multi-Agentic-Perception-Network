from __future__ import annotations
import json,os,secrets,threading,time
from pathlib import Path
from typing import Any
from fastapi import Depends,FastAPI,Header,HTTPException,WebSocket,WebSocketDisconnect,Query
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from apn.config import load_config
from apn.core import ReplayClock,HashChainedLedger
from apn.security import RBAC
from apn.security.redact import mask_person
from apn.store import RuntimeStore
from apn.store.runtime import recompute_entities
from apn.perception.floor import FloorProjection
from apn.security.retention import purge_expired_crops
from apn.business import BusinessAnalytics,OperationsSimulator,build_report,build_showcase,approve_showcase
from apn.evaluation import robustness_evaluation
from apn.lab import SystemLab
from tools.sync_supermarket_media import signature as media_signature,sync as sync_supermarket_media
import cv2

ROOT=Path(__file__).resolve().parents[2]
CONFIG=load_config(ROOT/"config"/"cameras.yaml")
RBAC_ENGINE=RBAC.load(ROOT/"config"/"roles.yaml")
TOKEN=os.environ.get("APN_TOKEN","apn-local-demo")
OUTPUT=ROOT/"output"/"phase2_yolo"
SCENARIO=ROOT/"output"/"scenario"/"state.json"
MEDIA_CATALOG=ROOT/"data"/"supermarket_final"/"catalog.json"
MEDIA_SOURCE=Path(os.environ.get("APN_MEDIA_SOURCE","/Volumes/One Touch/SURVELLIANCE /SUPERMARKET FINAL"))
_initial_catalog=json.loads(MEDIA_CATALOG.read_text()) if MEDIA_CATALOG.exists() else {"reels":[]}
CLOCK=ReplayClock(max((item.get("duration_s",0) for item in _initial_catalog.get("reels",[])),default=27.0))
AGENT_STATES={f"camera-agent:{camera.id}":"running" for camera in CONFIG.cameras}
STORE=RuntimeStore(Path(os.environ.get("APN_RUNTIME_DB",ROOT/"runtime.sqlite3")))
MEDIA_LOCK=threading.Lock()
MEDIA_LAST_SCAN=0.0
MEDIA_SNAPSHOT:tuple=()


def load_json(path:Path,default:Any):
 try:return json.loads(path.read_text())
 except FileNotFoundError:return default

THRESHOLDS=load_json(ROOT/"config"/"thresholds.yaml",{})


def role_guard(permission:str):
 def guard(authorization:str=Header(default=""),x_apn_role:str=Header(default="Security Operator")):
  if authorization!=f"Bearer {TOKEN}":raise HTTPException(401,"valid local token required")
  if not RBAC_ENGINE.allows(x_apn_role,permission):raise HTTPException(403,f"{x_apn_role} lacks {permission}")
  return x_apn_role
 return guard


def observations():return load_json(OUTPUT/"observations.json",[])
def scenario():
 data=load_json(SCENARIO,{"entities":[],"handoffs":[],"cases":[],"messages":[]})
 return recompute_entities(data,STORE.overrides())
def analytics():return BusinessAnalytics(observations())
def system_lab():return SystemLab(observations(),scenario(),load_json(OUTPUT/"summary.json",{}))
def _media_snapshot():
 if not MEDIA_SOURCE.is_dir():return ()
 suffixes={".mp4",".mov",".m4v",".avi",".mkv"}
 return tuple(sorted((p.name,p.stat().st_size,p.stat().st_mtime_ns)for p in MEDIA_SOURCE.iterdir()if p.is_file()and not p.name.startswith((".","._"))and p.suffix.lower()in suffixes))

def media_catalog():
 global MEDIA_LAST_SCAN,MEDIA_SNAPSHOT
 now=time.monotonic()
 if now-MEDIA_LAST_SCAN>3 and MEDIA_LOCK.acquire(blocking=False):
  try:
   MEDIA_LAST_SCAN=now;snapshot=_media_snapshot()
   if snapshot and snapshot!=MEDIA_SNAPSHOT:
    MEDIA_SNAPSHOT=snapshot
    current=load_json(MEDIA_CATALOG,{})
    known={(x.get("filename"),x.get("clip_id"))for x in current.get("clips",[])}
    present={(name,media_signature(MEDIA_SOURCE/name))for name,_,_ in snapshot}
    if known!=present:sync_supermarket_media(MEDIA_SOURCE,ROOT)
  finally:MEDIA_LOCK.release()
 catalog=load_json(MEDIA_CATALOG,{"clips":[],"reels":[],"discovered_files":0,"assigned_files":0,"unassigned_files":0})
 connected=MEDIA_SOURCE.is_dir()
 return {**catalog,"source_connected":connected,"clips":[{**clip,"available":connected and Path(clip.get("source_path","")).is_file()}for clip in catalog.get("clips",[])]}


app=FastAPI(title="Agentic Perception Network",version="0.9.0",description="Local-only APN control and evidence API")

@app.middleware("http")
async def development_no_cache(request,call_next):
 response=await call_next(request)
 if not request.url.path.startswith("/api/"):
  response.headers["Cache-Control"]="no-store, max-age=0"
 return response


@app.get("/api/health")
def health():return {"status":"ok","mode":CONFIG.mode,"local_only":True}

@app.get("/api/media/catalog")
def get_media_catalog(role=Depends(role_guard("view_cases"))):return media_catalog()

@app.get("/api/state")
def state(role=Depends(role_guard("view_cases"))):
 data=scenario();summary=load_json(OUTPUT/"summary.json",{})
 return {"mode":CONFIG.mode,"timeline_label":"COMPOSED VALIDATION — source clips preserved","role":role,"media":media_catalog(),
         "clock":CLOCK.__dict__,"cameras":[{**camera.model_dump(mode="json"),"agent_state":AGENT_STATES[f'camera-agent:{camera.id}']} for camera in CONFIG.cameras],
         "summary":summary,"entities":data["entities"],"handoffs":data["handoffs"],"cases":data["cases"],"messages":data["messages"][-200:],
         "human_decisions":STORE.all(),"downstream_confidence":"degraded" if any(x!="running" for x in AGENT_STATES.values()) else "normal"}

@app.get("/api/cameras")
def cameras(role=Depends(role_guard("view_cases"))):return [{**x.model_dump(mode="json"),"agent_state":AGENT_STATES[f"camera-agent:{x.id}"]} for x in CONFIG.cameras]

@app.get("/api/entities")
def entities(role=Depends(role_guard("view_cases"))):return scenario()["entities"]

@app.get("/api/entities/{entity_id}/journey")
def entity_journey(entity_id:str,role=Depends(role_guard("view_cases"))):
 entity=next((x for x in scenario()["entities"] if x["entity_id"]==entity_id),None)
 if not entity:raise HTTPException(404,"entity not found")
 return entity["journey"]

@app.get("/api/tracks/{track_id}")
def track(track_id:str,role=Depends(role_guard("view_cases"))):
 rows=[x for x in observations() if f"{x['camera_id']}:{x['local_track_id']}"==track_id]
 if not rows:raise HTTPException(404,"track not found")
 return rows

@app.get("/api/cases")
def cases(role=Depends(role_guard("view_cases"))):return scenario()["cases"]

@app.get("/api/cases/{case_id}")
def case(case_id:str,role=Depends(role_guard("view_cases"))):
 item=next((x for x in scenario()["cases"] if x["case_id"]==case_id),None)
 if not item:raise HTTPException(404,"case not found")
 return item

@app.get("/api/cases/{case_id}/why")
def why(case_id:str,role=Depends(role_guard("view_cases"))):
 item=case(case_id,role);ids=set(item.get("trace",[]));return {"case":item,"messages":[x for x in scenario()["messages"] if x["id"] in ids],
  "thresholds":[x.get("thresholds",{}) for x in item.get("findings",[])],"alternative_hypotheses":item.get("hypotheses",[])}

class Decision(BaseModel):decision:str;note:str=""
@app.post("/api/cases/{case_id}/decision")
def decide_case(case_id:str,body:Decision,role=Depends(role_guard("decide"))):
 if not any(item["case_id"]==case_id for item in scenario()["cases"]):raise HTTPException(404,"case not found")
 item=STORE.add("case",case_id,body.decision,body.note,role);return {**item,"accepted":True}
@app.post("/api/handoffs/{handoff_id}/decision")
def decide_handoff(handoff_id:str,body:Decision,role=Depends(role_guard("decide"))):
 if body.decision not in {"accept","accepted","approve","reject","rejected"}:raise HTTPException(400,"decision must accept or reject")
 if not any(item["handoff_id"]==handoff_id for item in scenario()["handoffs"]):raise HTTPException(404,"handoff not found")
 before=len(scenario()["entities"]);item=STORE.add("handoff",handoff_id,body.decision,body.note,role);after=len(scenario()["entities"])
 return {**item,"accepted":True,"recomputed":True,"recompute_required":True,"entities_before":before,"entities_after":after}

@app.post("/api/agents/{agent_id}/{action}")
def agent_action(agent_id:str,action:str,role=Depends(role_guard("manage_agents"))):
 if agent_id not in AGENT_STATES or action not in {"pause","isolate","resume"}:raise HTTPException(400,"invalid agent or action")
 AGENT_STATES[agent_id]={"pause":"paused","isolate":"isolated","resume":"running"}[action];return {"agent_id":agent_id,"state":AGENT_STATES[agent_id]}

@app.get("/api/audit/verify")
def verify_audit(role=Depends(role_guard("view_audit"))):
 path=OUTPUT/"ledger.sqlite3"
 if not path.exists():return {"intact":False,"reason":"ledger missing"}
 ledger=HashChainedLedger(path);intact,broken=ledger.verify_chain();ledger.close();return {"intact":intact,"broken_at":broken}

@app.get("/api/audit")
def audit(role=Depends(role_guard("view_audit"))):
 path=OUTPUT/"ledger.sqlite3"
 if not path.exists():return []
 ledger=HashChainedLedger(path);items=[{"id":x.id,"type":x.type,"sender":x.sender,"ts":x.ts_source,"hash":x.hash} for x in ledger.messages()[-200:]];ledger.close();return items

class ThresholdPatch(BaseModel):values:dict[str,Any]
@app.patch("/api/thresholds")
def patch_thresholds(body:ThresholdPatch,role=Depends(role_guard("adjust_thresholds"))):
 THRESHOLDS.update(body.values);STORE.add("thresholds",None,json.dumps(body.values),"",role);return {"updated":body.values,"audited":True}

class CalibrationRequest(BaseModel):
 image_points:list[list[float]]
 floor_points:list[list[float]]

@app.get("/api/calibration/{camera_id}")
def calibration(camera_id:str,role=Depends(role_guard("adjust_thresholds"))):
 camera=next((item for item in CONFIG.cameras if item.id==camera_id),None)
 if not camera:raise HTTPException(404,"camera not found")
 saved=load_json(ROOT/"config"/"calibration"/f"{camera_id}.json",None)
 return {"camera_id":camera_id,"preview":f"/api/preview/{camera_id}?token={TOKEN}","calibration":saved,
         "instructions":"Select at least four matching image and floor-plan points."}

@app.post("/api/calibration/{camera_id}")
def save_calibration(camera_id:str,body:CalibrationRequest,role=Depends(role_guard("adjust_thresholds"))):
 if not any(item.id==camera_id for item in CONFIG.cameras):raise HTTPException(404,"camera not found")
 try:projection,residual=FloorProjection.fit(body.image_points,body.floor_points)
 except ValueError as error:raise HTTPException(400,str(error)) from error
 target=ROOT/"config"/"calibration"/f"{camera_id}.json";target.parent.mkdir(parents=True,exist_ok=True)
 payload={"camera_id":camera_id,"homography":projection.matrix.tolist(),"residual_error":residual,"approximate":False}
 target.write_text(json.dumps(payload,indent=2));STORE.add("calibration",camera_id,"updated",f"residual={residual:.6f}",role)
 return payload

@app.post("/api/privacy/purge")
def privacy_purge(retention_hours:float=24,role=Depends(role_guard("manage_agents"))):
 audit=[];removed=purge_expired_crops(OUTPUT/"crops",retention_hours,audit)
 STORE.add("privacy",None,"retention_purge",json.dumps(audit[0]),role)
 return {"removed":removed,"retention_hours":retention_hours,"audited":True}

class AskRequest(BaseModel):
 question:str
 camera_id:str|None=None
 at_s:float|None=None
 window_s:float=10.0
@app.post("/api/ask")
def ask(body:AskRequest,role=Depends(role_guard("view_cases"))):
 data=scenario();question=body.question.lower();rows=observations();case_item=data["cases"][0] if data["cases"] else None
 camera=body.camera_id or ("CAM-02" if any(word in question for word in ("aisle","aisle one","main aisle")) else "CAM-04" if any(word in question for word in ("checkout","queue","bottleneck")) else None)
 selected=[row for row in rows if not camera or row["camera_id"]==camera]
 if body.at_s is not None:selected=[row for row in selected if max(0,body.at_s-body.window_s)<=row["ts_source"]<=body.at_s]
 tracks:dict[str,list[dict]]={}
 frames:dict[int,set[str]]={}
 for row in selected:
  tracks.setdefault(row["local_track_id"],[]).append(row)
  frames.setdefault(row["frame_idx"],set()).add(row["local_track_id"])
 unique=len(tracks);peak=max((len(items) for items in frames.values()),default=0)
 spans=sorted(max(items,key=lambda x:x["ts_source"])["ts_source"]-min(items,key=lambda x:x["ts_source"])["ts_source"] for items in tracks.values())
 median_span=round(spans[len(spans)//2],2) if spans else 0.0;longest_span=round(max(spans),2) if spans else 0.0
 right=left=stable=0
 for items in tracks.values():
  items.sort(key=lambda x:x["ts_source"]);delta=items[-1]["foot_px"][0]-items[0]["foot_px"][0]
  if delta>80:right+=1
  elif delta<-80:left+=1
  else:stable+=1
 agents=["Camera Agent"]
 if any(word in question for word in ("how many","count","customer","people")):agents+=["Tracking Agent","Identity Agent"]
 if any(word in question for word in ("aisle","movement","flow")):agents+=["Movement Agent"]
 if any(word in question for word in ("queue","checkout","bottleneck","wait")):agents+=["Queue Agent"]
 agents+=["Business Agent","Evidence Agent"]
 if camera:
  label=next(item.name for item in CONFIG.cameras if item.id==camera)
  answer=f"{label} produced {unique} anonymous local tracks, with a measured peak of {peak} simultaneous tracks. Median observed track duration was {median_span}s; the longest was {longest_span}s."
 elif "why" in question and case_item:answer=case_item["narrative"]
 else:answer=f"Across the four camera zones, the perception layer recorded {len(rows)} observations from {unique} local tracks. Ask about the grocery aisles, promotions, assistance, checkout, movement, or queues for a focused analysis."
 risk="attention" if peak>=5 else "normal"
 insights=[f"Peak occupancy was {peak} simultaneous local tracks.",f"Observed movement: {right} rightward, {left} leftward, {stable} short/stable tracks."]
 if camera=="CAM-02":insights.append("Use repeated peak and dwell patterns to test aisle placement; this clip alone cannot establish product engagement or conversion.")
 if camera=="CAM-04":insights.append("A checkout peak above four tracks is a staffing-review cue, but service time needs longer footage.")
 recommendation="Review a longer synchronized sample before changing staffing or layout." if risk=="attention" else "Continue collecting footage; no intervention is justified by this short sample."
 return {"answer":answer,"facts":{"camera_id":camera,"local_tracks":unique,"observations":len(selected),"peak_occupancy":peak,"median_track_s":median_span,
          "longest_track_s":longest_span,"rightward":right,"leftward":left,"stable":stable,"risk":risk,"case":case_item["case_id"] if case_item else None},
         "insights":insights,"recommendation":recommendation,
         "agents":agents,"trace":case_item["trace"] if case_item else [],"generated":False,"evidence_window":{"camera_id":camera,"end_s":body.at_s,"window_s":body.window_s},"boundary":"Local tracks may split or repeat across cameras; no biometric identification is used."}

@app.get("/api/live/window")
def live_window(camera_id:str="CAM-02",at_s:float=10.0,window_s:float=10.0,role=Depends(role_guard("view_cases"))):
 rows=[x for x in observations()if x["camera_id"]==camera_id and max(0,at_s-window_s)<=x["ts_source"]<=at_s]
 tracks={x["local_track_id"]for x in rows};frames:dict[int,set[str]]={}
 for row in rows:frames.setdefault(row["frame_idx"],set()).add(row["local_track_id"])
 zones={x.get("zone")for x in rows if x.get("zone")}
 return {"camera_id":camera_id,"at_s":round(at_s,1),"window_s":window_s,"observations":len(rows),"local_tracks":len(tracks),"peak_occupancy":max((len(x)for x in frames.values()),default=0),"zones":sorted(zones),"source":"processed observation ledger"}

@app.post("/api/replay/{action}")
def replay(action:str,value:float|None=None,role=Depends(role_guard("view_cases"))):
 if action=="play":CLOCK.play()
 elif action=="pause":CLOCK.pause()
 elif action=="seek":CLOCK.seek(value or 0)
 elif action=="speed":CLOCK.set_speed(value or 1)
 else:raise HTTPException(400,"invalid replay action")
 return CLOCK.__dict__

@app.get("/api/video/{camera_id}")
def video(camera_id:str,token:str=Query(default=""),authorization:str=Header(default=""),x_apn_role:str=Header(default="Security Operator")):
 if authorization!=f"Bearer {TOKEN}" and token!=TOKEN:raise HTTPException(401,"valid local token required")
 if not RBAC_ENGINE.allows(x_apn_role,"view_raw_video"):raise HTTPException(403,f"{x_apn_role} lacks view_raw_video")
 camera=next((x for x in CONFIG.cameras if x.id==camera_id),None)
 if not camera:raise HTTPException(404,"camera not found")
 return FileResponse(ROOT/camera.file,media_type="video/mp4")

@app.get("/api/source-video/{clip_id}")
def source_video(clip_id:str,token:str=Query(default=""),authorization:str=Header(default=""),x_apn_role:str=Header(default="Security Operator")):
 if authorization!=f"Bearer {TOKEN}" and token!=TOKEN:raise HTTPException(401,"valid local token required")
 if not RBAC_ENGINE.allows(x_apn_role,"view_raw_video"):raise HTTPException(403,f"{x_apn_role} lacks view_raw_video")
 clip=next((x for x in media_catalog().get("clips",[])if x.get("clip_id")==clip_id),None)
 if not clip:raise HTTPException(404,"source clip not found")
 target=Path(clip["source_path"]).resolve()
 if MEDIA_SOURCE.resolve() not in target.parents or not target.is_file():raise HTTPException(403,"invalid source path")
 return FileResponse(target,media_type="video/mp4")

@app.get("/api/observations")
def observation_feed(camera_id:str|None=None,role=Depends(role_guard("view_cases"))):
 rows=observations()
 if camera_id:rows=[row for row in rows if row["camera_id"]==camera_id]
 return rows

@app.get("/api/business/spatial/{camera_id}")
def business_spatial(camera_id:str,role=Depends(role_guard("view_cases"))):
 if not any(camera.id==camera_id for camera in CONFIG.cameras):raise HTTPException(404,"camera not found")
 return analytics().spatial(camera_id)

@app.get("/api/business/comparison/{camera_id}")
def business_comparison(camera_id:str,role=Depends(role_guard("view_cases"))):
 if not any(camera.id==camera_id for camera in CONFIG.cameras):raise HTTPException(404,"camera not found")
 return analytics().comparison(camera_id)

@app.get("/api/business/queue")
def business_queue(role=Depends(role_guard("view_cases"))):return analytics().queue()

@app.get("/api/business/funnel")
def business_funnel(role=Depends(role_guard("view_cases"))):return analytics().funnel()

@app.get("/api/business/recommendations")
def business_recommendations(role=Depends(role_guard("view_cases"))):return analytics().recommendations()

@app.get("/api/business/operational-readiness")
def business_operational_readiness(role=Depends(role_guard("view_cases"))):return analytics().operational_readiness()

@app.get("/api/business/profile/{profile}")
def business_profile(profile:str,role=Depends(role_guard("view_cases"))):
 try:return analytics().vertical_profile(profile)
 except ValueError as error:raise HTTPException(400,str(error))from error

@app.post("/api/business/recommendations/{recommendation_id}/decision")
def decide_recommendation(recommendation_id:str,body:Decision,role=Depends(role_guard("decide"))):
 item=next((x for x in analytics().recommendations()if x["id"]==recommendation_id),None)
 if not item:raise HTTPException(404,"recommendation not found")
 return {**STORE.add("recommendation",recommendation_id,body.decision,body.note,role),"accepted":True,"external_action_taken":False}

class SimulationRequest(BaseModel):
 kind:str="checkout"
 open_counters:int=1
 added_counters:int=1
 capacity_per_counter:int=3
 flow_capacity_change_pct:float=20

@app.post("/api/business/simulate")
def simulate(body:SimulationRequest,role=Depends(role_guard("view_cases"))):
 simulator=OperationsSimulator(analytics().queue())
 if body.kind=="checkout":return simulator.checkout(body.open_counters,body.added_counters,body.capacity_per_counter)
 if body.kind=="aisle":return simulator.aisle(body.flow_capacity_change_pct)
 raise HTTPException(400,"kind must be checkout or aisle")

@app.post("/api/reports/generate")
def generate_report(role=Depends(role_guard("export"))):
 report=build_report(analytics());folder=ROOT/"output"/"reports";folder.mkdir(parents=True,exist_ok=True)
 target=folder/f'{report["report_id"]}.json';target.write_text(json.dumps(report,indent=2));STORE.add("report",report["report_id"],"generated",str(target),role)
 return {**report,"saved_to":str(target.relative_to(ROOT))}

@app.get("/api/evaluation/robustness")
def evaluation_robustness(role=Depends(role_guard("view_cases"))):return robustness_evaluation(observations(),scenario()["handoffs"])

@app.get("/api/showcase")
def showcase(staged_scenario:bool=True,role=Depends(role_guard("view_cases"))):return build_showcase(observations(),staged_scenario)

@app.post("/api/showcase/approve")
def showcase_approve(role=Depends(role_guard("decide"))):
 result=approve_showcase(build_showcase(observations(),True));STORE.add("intervention",result["intervention_id"],result["status"],"staged showcase only",role)
 return result

class PlanRequest(BaseModel):question:str
@app.post("/api/lab/plan")
def lab_plan(body:PlanRequest,role=Depends(role_guard("view_cases"))):return system_lab().query_plan(body.question)

@app.get("/api/lab/trajectories")
def lab_trajectories(role=Depends(role_guard("view_cases"))):return system_lab().trajectories()

@app.get("/api/lab/evidence")
def lab_evidence(role=Depends(role_guard("view_cases"))):return system_lab().evidence_wall()

@app.get("/api/lab/network")
def lab_network(incident:str="none",role=Depends(role_guard("view_cases"))):return system_lab().edge_network(incident)

class IncidentRequest(BaseModel):incident:str
@app.post("/api/lab/incidents")
def lab_incident(body:IncidentRequest,role=Depends(role_guard("manage_agents"))):
 try:result=system_lab().inject(body.incident)
 except ValueError as error:raise HTTPException(400,str(error))from error
 STORE.add("incident",body.incident,"injected","system laboratory",role);return result

class TwinRequest(BaseModel):counters:int=1;arrival_rate:float=4.8;service_rate:float=3.2
@app.post("/api/lab/digital-twin")
def lab_twin(body:TwinRequest,role=Depends(role_guard("view_cases"))):return system_lab().digital_twin(body.counters,body.arrival_rate,body.service_rate)

@app.get("/api/lab/benchmark")
def lab_benchmark(role=Depends(role_guard("view_cases"))):return system_lab().benchmark()

@app.get("/api/preview/{camera_id}")
def preview(camera_id:str,token:str=""):
 if token!=TOKEN:raise HTTPException(401,"valid local token required")
 target=OUTPUT/"previews"/f"{camera_id.lower()}_preview.jpg"
 if not target.is_file():raise HTTPException(404,"preview not generated")
 return FileResponse(target,media_type="image/jpeg")

@app.get("/api/crop/{crop_path:path}")
def crop(crop_path:str,role=Depends(role_guard("view_raw_video"))):
 target=(OUTPUT/"crops"/crop_path).resolve()
 if OUTPUT.resolve() not in target.parents or not target.is_file():raise HTTPException(404,"crop not found")
 return FileResponse(target,media_type="image/jpeg")

@app.get("/api/crop-masked/{crop_path:path}")
def crop_masked(crop_path:str,role=Depends(role_guard("view_masked_video"))):
 target=(OUTPUT/"crops"/crop_path).resolve()
 if OUTPUT.resolve() not in target.parents or not target.is_file():raise HTTPException(404,"crop not found")
 image=cv2.imread(str(target));masked=mask_person(image,(0,0,image.shape[1],image.shape[0]),"masked");ok,encoded=cv2.imencode(".jpg",masked,[cv2.IMWRITE_JPEG_QUALITY,95])
 if not ok:raise HTTPException(500,"masking failed")
 return Response(content=encoded.tobytes(),media_type="image/jpeg")

@app.get("/api/evidence-thumb/{crop_path:path}")
def evidence_thumb(crop_path:str,token:str=""):
 if token!=TOKEN:raise HTTPException(401,"valid local token required")
 crop_path=crop_path.removeprefix("crops/")
 target=(OUTPUT/"crops"/crop_path).resolve()
 if OUTPUT.resolve()not in target.parents or not target.is_file():raise HTTPException(404,"crop not found")
 image=cv2.imread(str(target));masked=mask_person(image,(0,0,image.shape[1],image.shape[0]),"masked");ok,encoded=cv2.imencode(".jpg",masked,[cv2.IMWRITE_JPEG_QUALITY,95])
 if not ok:raise HTTPException(500,"masking failed")
 return Response(content=encoded.tobytes(),media_type="image/jpeg")

@app.websocket("/api/stream")
async def stream(socket:WebSocket,token:str=""):
 if token!=TOKEN:await socket.close(code=4401);return
 await socket.accept()
 try:
  for message in scenario()["messages"][-200:]:await socket.send_json(message)
  while True:await socket.receive_text()
 except WebSocketDisconnect:return

WEB=ROOT/"web2"/"dist"
if WEB.exists():app.mount("/",StaticFiles(directory=WEB,html=True),name="workspace")
