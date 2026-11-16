"""Offline multi-camera replay: real frames -> detections -> local tracks -> events.

This first baseline uses OpenCV's built-in HOG person detector so it runs without
model downloads. It preserves source timestamps and writes annotated videos plus
JSON evidence. Replace the detector later with a benchmarked modern model.
"""
import argparse, json, math
from dataclasses import dataclass
from pathlib import Path
import cv2

CAMERAS={
 "cam_01_entrance.mp4":("CAM-01","Entrance"),
 "cam_02_main_aisle.mp4":("CAM-02","Main Aisle"),
 "cam_03_service_counter.mp4":("CAM-03","Service Counter"),
 "cam_04_checkout.mp4":("CAM-04","Checkout"),
}

@dataclass
class Track:
 id:int; x:float; y:float; last_frame:int; first_ms:float; last_ms:float; observations:int=1; hue_sum:float=0; sat_sum:float=0; val_sum:float=0; appearance_samples:int=0

def appearance(image,box):
 x,y,w,h,_=box; x1=max(0,x+w//4);x2=min(image.shape[1],x+3*w//4);y1=max(0,y+h//5);y2=min(image.shape[0],y+3*h//5)
 crop=image[y1:y2,x1:x2]
 if crop.size==0:return None
 hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV);mean=cv2.mean(hsv)
 return [round(mean[0]/179,4),round(mean[1]/255,4),round(mean[2]/255,4)]

def associate(tracks,centres,frame,max_distance=110,max_age=18):
 active={k:v for k,v in tracks.items() if frame-v.last_frame<=max_age}; assigned={}; used=set()
 for index,(x,y) in enumerate(centres):
  candidates=sorted((math.hypot(x-t.x,y-t.y),key) for key,t in active.items() if key not in used)
  if candidates and candidates[0][0]<=max_distance:
   _,key=candidates[0];used.add(key);assigned[index]=key
 return active,assigned

def process(video,out_dir,every=3):
 camera,zone=CAMERAS[video.name];cap=cv2.VideoCapture(str(video))
 if not cap.isOpened():raise RuntimeError(f'Cannot open {video}')
 fps=cap.get(cv2.CAP_PROP_FPS) or 24;width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 writer=cv2.VideoWriter(str(out_dir/f'{camera.lower()}_annotated.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps,(width,height))
 detector=cv2.HOGDescriptor();detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
 tracks={};next_id=1;events=[];frame=0;last_boxes=[];last_ids=[]
 while True:
  ok,image=cap.read()
  if not ok:break
  source_ms=cap.get(cv2.CAP_PROP_POS_MSEC)
  if frame%every==0:
   scale=min(1,960/width);small=cv2.resize(image,None,fx=scale,fy=scale) if scale<1 else image
   boxes,weights=detector.detectMultiScale(small,winStride=(8,8),padding=(8,8),scale=1.04)
   boxes=[(int(x/scale),int(y/scale),int(w/scale),int(h/scale),float(weights[i])) for i,(x,y,w,h) in enumerate(boxes)]
   centres=[(x+w/2,y+h) for x,y,w,h,_ in boxes];tracks,assigned=associate(tracks,centres,frame)
   ids=[]
   for i,(x,y) in enumerate(centres):
    tid=assigned.get(i)
    if tid is None:tid=next_id;next_id+=1;tracks[tid]=Track(tid,x,y,frame,source_ms,source_ms)
    else:
     t=tracks[tid];t.x=x;t.y=y;t.last_frame=frame;t.last_ms=source_ms;t.observations+=1
    ids.append(tid);box=boxes[i];look=appearance(image,box);t=tracks[tid]
    if look:t.hue_sum+=look[0];t.sat_sum+=look[1];t.val_sum+=look[2];t.appearance_samples+=1
    events.append({'camera':camera,'track':f'{camera}-T{tid:03}','zone':zone,'kind':'observation','source_time_ms':round(source_ms,1),'frame':frame,'bbox':[box[0],box[1],box[2],box[3]],'detector_score':round(box[4],3),'appearance_hsv':look,'source':'opencv_hog'})
   last_boxes,last_ids=boxes,ids
  for (x,y,w,h,score),tid in zip(last_boxes,last_ids):
   cv2.rectangle(image,(x,y),(x+w,y+h),(72,235,160),2);cv2.putText(image,f'{camera}-T{tid:03} {score:.2f}',(x,max(24,y-8)),cv2.FONT_HERSHEY_SIMPLEX,.55,(72,235,160),2)
  cv2.putText(image,f'{camera}  {zone}  {source_ms/1000:05.2f}s',(18,34),cv2.FONT_HERSHEY_SIMPLEX,.8,(255,255,255),2)
  writer.write(image);frame+=1
 cap.release();writer.release()
 summaries=[]
 for tid,t in sorted(tracks.items()):
  look=[round(t.hue_sum/t.appearance_samples,4),round(t.sat_sum/t.appearance_samples,4),round(t.val_sum/t.appearance_samples,4)] if t.appearance_samples else None
  summaries.append({'track':f'{camera}-T{tid:03}','first_ms':round(t.first_ms,1),'last_ms':round(t.last_ms,1),'observations':t.observations,'observed_span_ms':round(t.last_ms-t.first_ms,1),'appearance_hsv':look})
 return {'camera':camera,'zone':zone,'video':str(video),'fps':fps,'frames':frame,'duration_ms':round(frame/fps*1000,1),'tracks':summaries,'events':events}

def match_handoffs(results):
 handoffs=[]
 for source,target in zip(results,results[1:]):
  targets=[t for t in target['tracks'] if t['appearance_hsv']]
  for track in source['tracks']:
   if not track['appearance_hsv'] or not targets:continue
   ranked=[]
   for candidate in targets:
    a,b=track['appearance_hsv'],candidate['appearance_hsv'];distance=math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))/math.sqrt(3);similarity=max(0,1-distance)
    ranked.append((similarity,candidate))
   ranked.sort(key=lambda item:item[0],reverse=True);best=ranked[0];runner=ranked[1][0] if len(ranked)>1 else 0;margin=best[0]-runner
   state='accepted' if best[0]>=.86 and margin>=.08 else 'ambiguous' if best[0]>=.72 else 'rejected'
   handoffs.append({'source_camera':source['camera'],'source_track':track['track'],'target_camera':target['camera'],'target_track':best[1]['track'],'state':state,'score':round(best[0],3),'margin':round(margin,3),'evidence':{'method':'mean torso HSV similarity','source_appearance':track['appearance_hsv'],'target_appearance':best[1]['appearance_hsv']},'warning':'Appearance-only research candidate; not a confirmed identity.'})
 return handoffs

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path('data/realistic_store_v1/videos'));p.add_argument('--output',type=Path,default=Path('output/realistic_store_v1'));p.add_argument('--every',type=int,default=3);a=p.parse_args()
 if a.every<1:p.error('--every must be positive')
 a.output.mkdir(parents=True,exist_ok=True);results=[]
 for filename in CAMERAS:
  path=a.input/filename
  if not path.exists():raise SystemExit(f'Missing {path}')
  print('Processing',path,flush=True);results.append(process(path,a.output,a.every))
 evidence={'schema':'apn.replay.v2','detector':'OpenCV HOG baseline; scores are not calibrated probabilities','cameras':results,'handoffs':match_handoffs(results)}
 (a.output/'replay_evidence.json').write_text(json.dumps(evidence,indent=2))
 summary={'cameras':[{'camera':r['camera'],'zone':r['zone'],'frames':r['frames'],'duration_ms':r['duration_ms'],'track_count':len(r['tracks']),'event_count':len(r['events'])} for r in results],'handoffs':{state:sum(h['state']==state for h in evidence['handoffs']) for state in ['accepted','ambiguous','rejected']}}
 (a.output/'replay_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
