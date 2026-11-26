from __future__ import annotations
from collections import defaultdict


class EvidenceAgent:
    def __init__(self,observations:list[dict]) -> None:self.observations=observations
    def bundle(self,entity_tracks:list[str],start:float,end:float,max_crops_per_camera:int=3)->dict:
        eligible=[]
        for item in self.observations:
            key=f"{item['camera_id']}:{item['local_track_id']}"
            if key in entity_tracks and start<=item['store_ts']<=end:eligible.append(item)
        by_camera=defaultdict(list)
        for item in eligible:by_camera[item['camera_id']].append(item)
        crops={camera:[x['crop_ref'] for x in sorted(rows,key=lambda r:(-r['quality']['blur'],r['quality']['occlusion_est']))[:max_crops_per_camera]] for camera,rows in by_camera.items()}
        clips={camera:{"start_source_s":min(x['ts_source'] for x in rows),"end_source_s":max(x['ts_source'] for x in rows)} for camera,rows in by_camera.items()}
        paths={camera:[x['foot_px'] for x in rows] for camera,rows in by_camera.items()}
        return {"entity_tracks":entity_tracks,"crops":crops,"clips":clips,"paths":paths,"privacy":"role_checked","observation_count":len(eligible)}
