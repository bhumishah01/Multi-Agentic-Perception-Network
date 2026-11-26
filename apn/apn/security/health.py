from __future__ import annotations
from collections import deque
import hashlib
import cv2
import numpy as np


class HealthMonitor:
    def __init__(self,frozen_frames:int=3,brightness_drop:float=.5,max_speed:float=12) -> None:
        self.frozen_frames=frozen_frames;self.brightness_drop=brightness_drop;self.max_speed=max_speed
        self.hashes:dict[str,deque[str]]={};self.reference_brightness:dict[str,float]={}
        self.heartbeats:dict[str,float]={};self.message_times:dict[str,deque[float]]={}
    def inspect_frame(self,camera_id:str,frame:np.ndarray)->list[dict]:
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY);digest=hashlib.sha256(cv2.resize(gray,(32,18)).tobytes()).hexdigest();alerts=[]
        history=self.hashes.setdefault(camera_id,deque(maxlen=max(10,self.frozen_frames)))
        history.append(digest);brightness=float(gray.mean());reference=self.reference_brightness.setdefault(camera_id,brightness)
        if len(history)>=self.frozen_frames and len(set(list(history)[-self.frozen_frames:]))==1:alerts.append({"kind":"frozen_feed","camera_id":camera_id})
        if brightness<reference*self.brightness_drop:alerts.append({"kind":"possible_obstruction","camera_id":camera_id})
        if len(history)>=6 and list(history)[-3:]==list(history)[-6:-3]:alerts.append({"kind":"replayed_sequence","camera_id":camera_id})
        return alerts
    def inspect_motion(self,entity_id:str,previous:tuple[float,float,float],current:tuple[float,float,float])->dict|None:
        x1,y1,t1=previous;x2,y2,t2=current;speed=((x2-x1)**2+(y2-y1)**2)**.5/max(t2-t1,1e-6)
        return {"kind":"impossible_motion","entity_id":entity_id,"speed":speed} if speed>self.max_speed else None
    def heartbeat(self,agent_id:str,ts:float)->None:self.heartbeats[agent_id]=ts
    def silent_agents(self,now:float,timeout_s:float)->list[dict]:
        return [{"kind":"agent_silence","agent_id":agent,"silent_s":now-ts} for agent,ts in self.heartbeats.items() if now-ts>timeout_s]
    def inspect_message_rate(self,agent_id:str,ts:float,max_per_second:int=20)->dict|None:
        times=self.message_times.setdefault(agent_id,deque());times.append(ts)
        while times and ts-times[0]>1:times.popleft()
        return {"kind":"message_rate_spike","agent_id":agent_id,"rate":len(times)} if len(times)>max_per_second else None
