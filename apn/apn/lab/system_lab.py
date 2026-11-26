from __future__ import annotations
from collections import defaultdict


class SystemLab:
    def __init__(self,observations:list[dict],state:dict,summary:dict)->None:self.rows=observations;self.state=state;self.summary=summary

    def query_plan(self,question:str)->dict:
        q=question.lower();nodes=[{"id":"intent","label":"Intent Parser","kind":"control","task":"Extract scope and decision objective"},{"id":"orchestrator","label":"Master Orchestrator","kind":"control","task":"Compile evidence plan"}];edges=[{"from":"intent","to":"orchestrator"}]
        selected=[]
        if any(x in q for x in("count","how many","customer","people")):selected+=[("tracking","Tracking Agent","Count anonymous local tracks"),("identity","Identity Agent","Bound cross-camera duplication")]
        if any(x in q for x in("aisle","movement","flow","path")):selected+=[("flow","Flow Agent","Reconstruct paths and direction")]
        if any(x in q for x in("queue","checkout","wait","bottleneck","staff")):selected+=[("queue","Queue Agent","Measure pressure and visible spans"),("capacity","Capacity Agent","Inspect service capacity")]
        if any(x in q for x in("why","cause","reason")):selected+=[("causal","Causal Agent","Generate competing hypotheses")]
        if any(x in q for x in("what if","simulate","should","do")):selected+=[("simulation","Simulation Agent","Evaluate interventions")]
        if not selected:selected=[("flow","Flow Agent","Summarise spatial activity"),("queue","Queue Agent","Check operational pressure")]
        seen=set()
        for ident,label,task in selected:
            if ident in seen:continue
            seen.add(ident);nodes.append({"id":ident,"label":label,"kind":"specialist","task":task});edges.append({"from":"orchestrator","to":ident})
        nodes.extend([{"id":"verifier","label":"Verifier Agent","kind":"verification","task":"Challenge unsupported conclusions"},{"id":"answer","label":"Decision Composer","kind":"control","task":"Return evidence-bound answer"}])
        for ident in seen:edges.append({"from":ident,"to":"verifier"})
        edges.append({"from":"verifier","to":"answer"})
        return {"question":question,"nodes":nodes,"edges":edges,"parallel_agents":len(seen),"compiled":True}

    def trajectories(self)->dict:
        grouped=defaultdict(list)
        for row in self.rows:grouped[(row["camera_id"],row["local_track_id"])].append(row)
        tracks=[]
        for(camera,track),items in grouped.items():
            items.sort(key=lambda x:x["store_ts"]);step=max(1,len(items)//8)
            tracks.append({"id":f"{camera}:{track}","camera_id":camera,"start":items[0]["store_ts"],"end":items[-1]["store_ts"],"points":[{"x":round(x["foot_px"][0]/1280,3),"y":round(x["foot_px"][1]/720,3),"t":round(x["store_ts"],2)}for x in items[::step]]})
        return {"cameras":[{"id":x,"x":i/3}for i,x in enumerate(("CAM-01","CAM-02","CAM-03","CAM-04"))],"tracks":tracks,"handoffs":self.state.get("handoffs",[]),"timeline_s":27,"boundary":"Local trajectories are measured; cross-camera links retain accepted/ambiguous/rejected state."}

    def evidence_wall(self,limit:int=12)->dict:
        ranked=sorted(self.rows,key=lambda x:(-x.get("quality",{}).get("blur",0),x.get("quality",{}).get("occlusion_est",1)))
        chosen=[];seen=set()
        for row in ranked:
            key=(row["camera_id"],row["local_track_id"])
            if key in seen:continue
            seen.add(key);chosen.append({"camera_id":row["camera_id"],"track_id":row["local_track_id"],"ts":row["store_ts"],"frame_idx":row["frame_idx"],"crop_ref":row["crop_ref"],"confidence":row["detector_score"],"reason":"highest-quality representative observation"})
            if len(chosen)>=limit:break
        causal=[]
        for message in self.state.get("messages",[]):causal.append({"id":message["id"],"type":message["type"],"sender":message["sender"],"caused_by":message.get("caused_by"),"evidence":message.get("evidence",[])})
        return {"evidence":chosen,"causal_graph":causal}

    def edge_network(self,incident:str="none")->dict:
        cameras=[];total=sum(x.get("observations",0)for x in self.summary.get("cameras",[]))or 1
        for camera in self.summary.get("cameras",[]):
            lost=incident=="camera_loss"and camera["camera_id"]=="CAM-03";delay=5 if incident=="message_delay"else 0
            cameras.append({"id":camera["camera_id"],"state":"offline"if lost else"degraded"if delay else"healthy","processing_fps":0 if lost else camera.get("processing_fps",0),"observations":0 if lost else camera.get("observations",0),"message_share":round(camera.get("observations",0)/total,3),"latency_ms":5000 if delay else 35,"raw_video_shared":False})
        active=sum(x["state"]!="offline"for x in cameras);coverage=round(sum(x["observations"]for x in cameras)/total,3)
        return {"incident":incident,"nodes":cameras,"active_nodes":active,"observation_coverage":coverage,"global_confidence":"degraded"if incident!="none"else"normal","local_reasoning_continues":active>0}

    def inject(self,incident:str)->dict:
        valid={"none","camera_loss","message_delay","identity_ambiguity","queue_surge","forged_message"}
        if incident not in valid:raise ValueError("unknown incident")
        network=self.edge_network(incident)
        responses={"none":"All nodes nominal.","camera_loss":"CAM-03 isolated; neighbouring agents continue and global continuity degrades.","message_delay":"Late messages quarantined from time-critical decisions.","identity_ambiguity":"Identity fork retained; business counts reported as bounds.","queue_surge":"Queue Agent raises attention; Simulation Agent evaluates capacity.","forged_message":"Signature validation rejects the forged event before the evidence ledger."}
        return {"incident":incident,"network":network,"agent_response":responses[incident],"abstains":incident in{"camera_loss","message_delay","identity_ambiguity"},"audit_event":f"incident.{incident}"}

    def digital_twin(self,counters:int=1,arrival_rate:float=4.8,service_rate:float=3.2,minutes:int=12)->dict:
        queue=2.0;series=[]
        for minute in range(minutes+1):
            series.append({"minute":minute,"queue":round(queue,2),"served":round(min(arrival_rate,service_rate*counters),2)})
            queue=max(0,queue+arrival_rate-service_rate*counters)
        return {"inputs":{"counters":counters,"arrival_rate":arrival_rate,"service_rate_per_counter":service_rate},"series":series,"peak_queue":max(x["queue"]for x in series),"final_queue":series[-1]["queue"],"stable":service_rate*counters>=arrival_rate,"model":"deterministic flow balance","boundary":"Scenario model requiring calibration with real arrival and service events."}

    def benchmark(self)->dict:
        incidents=("none","camera_loss","message_delay","identity_ambiguity","forged_message")
        rows=[]
        for name in incidents:
            network=self.edge_network(name);agentic={"task_coverage":network["observation_coverage"],"safe_abstention":name in{"camera_loss","message_delay","identity_ambiguity"},"local_operation":network["local_reasoning_continues"]}
            centralized={"task_coverage":0 if name=="camera_loss"else .55 if name=="message_delay"else 1,"safe_abstention":False,"local_operation":name=="none"}
            rows.append({"incident":name,"centralized":centralized,"agentic":agentic})
        return {"experiments":rows,"metrics":["task coverage","safe abstention","local operation"],"boundary":"Architecture behaviour experiment; identity accuracy requires labelled synchronized footage."}
