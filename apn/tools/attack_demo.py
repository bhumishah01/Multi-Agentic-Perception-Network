#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
import cv2,numpy as np
PROJECT_ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT_ROOT))
from apn.security import AgentSigner,HealthMonitor


def main():
 signer=AgentSigner({"camera-agent:CAM-01":b"local-demo-secret"});payload={"camera":"CAM-01","track":"forged"}
 forged_ok=signer.verify("camera-agent:CAM-01",payload,"0"*64)
 monitor=HealthMonitor(frozen_frames=3);frame=np.full((80,120,3),180,dtype=np.uint8);frozen=[]
 for _ in range(3):frozen.extend(monitor.inspect_frame("CAM-01",frame))
 replay_monitor=HealthMonitor(frozen_frames=10);replay=[]
 frames=[np.full((80,120,3),v,dtype=np.uint8) for v in (50,100,150)]*2
 for item in frames:replay.extend(replay_monitor.inspect_frame("CAM-02",item))
 result={"forged_observation_rejected":not forged_ok,"frozen_feed_detected":any(x["kind"]=="frozen_feed" for x in frozen),
         "replayed_clip_detected":any(x["kind"]=="replayed_sequence" for x in replay)}
 print(json.dumps(result,indent=2));raise SystemExit(0 if all(result.values()) else 1)
if __name__=="__main__":main()
