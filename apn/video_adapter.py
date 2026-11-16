"""Optional single-camera baseline: OpenCV HOG + greedy centroid association.
Not a production tracker. Zone defaults cover image quadrants, not calibrated floor space.
"""
import argparse,hashlib,hmac,json,math,os,time,urllib.request
from collections import defaultdict

def main():
 import cv2
 p=argparse.ArgumentParser();p.add_argument('video');p.add_argument('--camera',default='CAM-1');p.add_argument('--url',default='http://127.0.0.1:8765');p.add_argument('--every',type=int,default=10);a=p.parse_args()
 if a.every<1:p.error('--every must be positive')
 token=os.environ['APN_TOKEN'];secret=os.environ['APN_INGEST_SECRET']
 cap=cv2.VideoCapture(a.video)
 if not cap.isOpened():raise SystemExit('Cannot open video')
 detector=cv2.HOGDescriptor();detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
 tracks={};next_id=0;frame_id=0
 while True:
  ok,frame=cap.read()
  if not ok:break
  frame_id+=1
  if frame_id%a.every:continue
  height,width=frame.shape[:2];frame=cv2.resize(frame,(640,max(128,int(height*640/width))))
  boxes,_=detector.detectMultiScale(frame,winStride=(8,8),padding=(8,8),scale=1.05)
  available={k:v for k,v in tracks.items() if frame_id-v[2]<=a.every*4};used=set();new={}
  for x,y,w,h in boxes:
   cx,cy=x+w/2,y+h
   candidates=[(math.hypot(cx-v[0],cy-v[1]),k) for k,v in available.items() if k not in used]
   distance,key=min(candidates,default=(float('inf'),None))
   if distance>80:key=next_id;next_id+=1
   used.add(key);new[key]=(cx,cy,frame_id)
   zone=['Entrance','Aisles','Service','Checkout'][(2 if cy>frame.shape[0]/2 else 0)+(1 if cx>320 else 0)]
   event=dict(ts=time.time(),camera=a.camera,track=f'{a.camera}-local-{key}',zone=zone,kind='observation',confidence=.5,source='video_hog_baseline')
   raw=json.dumps(event).encode();signature=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
   request=urllib.request.Request(a.url+'/api/ingest',data=raw,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','X-APN-Signature':signature})
   with urllib.request.urlopen(request,timeout=10) as response:response.read()
  tracks={**available,**new}
 cap.release();print('Processed',frame_id,'frames. Timestamps reflect processing time, not source capture time.')
if __name__=='__main__':main()
