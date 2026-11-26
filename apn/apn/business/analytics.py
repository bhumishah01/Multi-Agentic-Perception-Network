from __future__ import annotations
from collections import defaultdict
from statistics import mean,median


class BusinessAnalytics:
    """Deterministic operational measures derived only from anonymous observations."""
    def __init__(self,observations:list[dict],width:int=1280,height:int=720)->None:
        self.rows=observations;self.width=width;self.height=height

    def _rows(self,camera_id:str)->list[dict]:return [x for x in self.rows if x["camera_id"]==camera_id]

    @staticmethod
    def _group(rows:list[dict],field:str)->dict:
        groups=defaultdict(list)
        for row in rows:groups[row[field]].append(row)
        return groups

    def spatial(self,camera_id:str,cols:int=8,rows_n:int=4)->dict:
        selected=self._rows(camera_id);grid=[[0 for _ in range(cols)]for _ in range(rows_n)]
        for item in selected:
            x,y=item["foot_px"];col=min(cols-1,max(0,int(x/self.width*cols)));row=min(rows_n-1,max(0,int(y/self.height*rows_n)));grid[row][col]+=1
        maximum=max((value for row in grid for value in row),default=1)
        paths=[]
        for track,items in self._group(selected,"local_track_id").items():
            items.sort(key=lambda x:x["ts_source"]);step=max(1,len(items)//12)
            paths.append({"track_id":track,"points":[{"x":round(x["foot_px"][0]/self.width,3),"y":round(x["foot_px"][1]/self.height,3),"t":round(x["ts_source"],2)}for x in items[::step]],"observations":len(items)})
        return {"camera_id":camera_id,"grid":grid,"grid_cols":cols,"grid_rows":rows_n,"maximum":maximum,"paths":paths,
                "boundary":"Image-plane density, not calibrated square-metre density."}

    def window(self,camera_id:str,start:float,end:float)->dict:
        selected=[x for x in self._rows(camera_id)if start<=x["ts_source"]<end];frames=self._group(selected,"frame_idx");tracks=self._group(selected,"local_track_id")
        return {"start":start,"end":end,"local_tracks":len(tracks),"observations":len(selected),
                "peak_occupancy":max((len({x['local_track_id']for x in items})for items in frames.values()),default=0)}

    def comparison(self,camera_id:str)->dict:
        rows=self._rows(camera_id);duration=max((x["ts_source"]for x in rows),default=0);mid=duration/2
        first=self.window(camera_id,0,mid);second=self.window(camera_id,mid,duration+.001)
        return {"camera_id":camera_id,"first":first,"second":second,"track_change":second["local_tracks"]-first["local_tracks"],
                "peak_change":second["peak_occupancy"]-first["peak_occupancy"],"boundary":"Within-clip comparison; not a day-part trend."}

    def queue(self,camera_id:str="CAM-04")->dict:
        rows=self._rows(camera_id);tracks=self._group(rows,"local_track_id");frames=self._group(rows,"frame_idx")
        occupancy=[len({x["local_track_id"]for x in items})for items in frames.values()];spans=[max(x["ts_source"]for x in items)-min(x["ts_source"]for x in items)for items in tracks.values()]
        peak=max(occupancy,default=0);threshold=4;sustained=sum(value>=threshold for value in occupancy)
        endings=sum(1 for items in tracks.values()if max(x["ts_source"]for x in items)<max((x["ts_source"]for x in rows),default=0)-.25)
        return {"camera_id":camera_id,"local_tracks":len(tracks),"peak_occupancy":peak,"mean_occupancy":round(mean(occupancy),2)if occupancy else 0,
                "median_observed_span_s":round(median(spans),2)if spans else 0,"longest_observed_span_s":round(max(spans),2)if spans else 0,
                "frames_at_or_above_threshold":sustained,"threshold":threshold,"observed_track_endings":endings,
                "signal":"attention"if peak>=threshold else"normal","boundary":"Track spans are visible durations, not validated customer wait or service times."}

    def funnel(self)->dict:
        stages=[]
        for camera,name in (("CAM-01","Entrance"),("CAM-02","Main aisle"),("CAM-03","Service counter"),("CAM-04","Checkout")):
            count=len({x["local_track_id"]for x in self._rows(camera)});stages.append({"camera_id":camera,"name":name,"local_tracks":count})
        for index,stage in enumerate(stages):stage["passage_index"]=None if index==0 or not stages[index-1]["local_tracks"]else round(stage["local_tracks"]/stages[index-1]["local_tracks"],2)
        counts=[x["local_tracks"]for x in stages]
        return {"stages":stages,"global_identity_lower_bound":max(counts,default=0),"global_identity_upper_bound":sum(counts),
                "boundary":"Passage indices compare local-track volumes. They are not sales conversion rates because cross-camera identity remains ambiguous."}

    def recommendations(self)->list[dict]:
        queue=self.queue();aisle=self.comparison("CAM-02");items=[]
        if queue["signal"]=="attention":items.append({"id":"REC-QUEUE-01","priority":"review","title":"Validate checkout capacity","reason":f"Peak occupancy reached {queue['peak_occupancy']} tracks against a review threshold of {queue['threshold']}.","action":"Collect a longer sample and test an additional staffed checkout.","requires_human":True})
        if aisle["peak_change"]>0:items.append({"id":"REC-AISLE-01","priority":"observe","title":"Review late-clip aisle pressure","reason":f"Peak occupancy increased by {aisle['peak_change']} between clip halves.","action":"Compare the same zone across longer day-parts before changing layout.","requires_human":True})
        if not items:items.append({"id":"REC-COLLECT-01","priority":"observe","title":"Collect representative footage","reason":"The short composed clips do not establish a recurring operational pattern.","action":"Capture synchronized, consented samples across operating periods.","requires_human":True})
        return items

    def operational_readiness(self)->dict:
        comparisons={camera:self.comparison(camera) for camera in ("CAM-01","CAM-02","CAM-03","CAM-04")}
        anomalies=[]
        for camera,item in comparisons.items():
            if item["peak_change"]>=2:anomalies.append({"type":"OCCUPANCY_SHIFT","camera_id":camera,"change":item["peak_change"],"status":"review"})
        return {"event_stream":{"status":"active","events":len(self.rows),"mode":"batch-replay"},
                "baseline_anomalies":{"status":"active","count":len(anomalies),"items":anomalies,"method":"first half vs second half of each camera reel"},
                "reentry_accounting":{"status":"guarded","count":None,"reason":"Requires accepted cross-camera entity links; local track fragments are not counted as re-entry."},
                "pos_linkage":{"status":"not-connected","matched_purchases":None,"reason":"No supermarket POS file is connected. Purchases and revenue remain unclaimed."}}

    def vertical_profile(self,profile:str="supermarket")->dict:
        """Translate the same anonymous movement evidence into vertical-specific decisions.

        Product picks, purchases and orders require dedicated interaction models or
        business-system data.  They are deliberately presented as future signals,
        never fabricated from person tracks.
        """
        profiles={
            "supermarket":{
                "label":"Supermarket","unit":"aisle","primary":"Aisle attention & checkout flow",
                "questions":["Which aisle needs assistance?","Where does traffic disengage?","When should checkout capacity be reviewed?"],
                "future":["Shelf hand-product interaction","Pick-up → return sequence","Basket/POS-linked conversion","Day-part aisle comparison"],
                "action":"Reposition assistance or test capacity only after a repeated pattern is verified."},
            "cafe":{
                "label":"Café","unit":"service zone","primary":"Table utilisation & service rhythm",
                "questions":["How long is each table visibly occupied?","How quickly is a vacated table reset?","Where is staff coverage uneven?"],
                "future":["Table arrival → order → departure cycle","Vacated → cleaned → ready timing","Order/POS-linked seat yield","Staff service-response intervals"],
                "action":"Balance table turnover and guest experience using repeated service-period samples."},
            "retail":{
                "label":"Retail store","unit":"section","primary":"Section engagement & consideration",
                "questions":["Which sections attract repeat visits?","Where do visitors disengage?","When is associate assistance most useful?"],
                "future":["Product touch and return-to-rack events","Repeat section visits","Fitting-room journey","POS-linked browse-to-buy conversion"],
                "action":"Test placement or associate coverage where engagement is repeated but progression is weak."}}
        if profile not in profiles:raise ValueError("profile must be supermarket, cafe, or retail")
        camera_rows=[]
        for camera_id in ("CAM-01","CAM-02","CAM-03","CAM-04"):
            rows=self._rows(camera_id);tracks=self._group(rows,"local_track_id");frames=self._group(rows,"frame_idx")
            spans=[max(x["ts_source"]for x in items)-min(x["ts_source"]for x in items)for items in tracks.values()]
            camera_rows.append({"camera_id":camera_id,"label":{"CAM-01":"Entrance","CAM-02":"Main aisle","CAM-03":"Service area","CAM-04":"Checkout"}[camera_id],
                "local_tracks":len(tracks),"peak_occupancy":max((len({x['local_track_id']for x in items})for items in frames.values()),default=0),
                "median_visible_s":round(median(spans),1)if spans else 0})
        selected=profiles[profile]
        return {"profile":profile,**selected,"comparison":camera_rows,
            "available_now":["Anonymous traffic volume","Peak visible occupancy","Visible dwell proxy","Movement paths and density","Queue-pressure review cue"],
            "truth_boundary":"Current clips measure anonymous movement only. Product interest, purchases, orders, satisfaction and revenue require interaction detection and/or POS integration."}
