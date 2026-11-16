"""APN uncertainty-aware structured-event research prototype (stdlib only)."""
import concurrent.futures, hashlib, hmac, json, math, os, secrets, sqlite3, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).parent; DB=Path(os.environ.get('APN_DB',str(ROOT/'apn.sqlite3')))
REPLAY=ROOT/'output'/'realistic_store_v1'/'replay_evidence.json'; MEDIA=ROOT/'output'/'realistic_store_v1'
TOKEN=os.environ.get('APN_TOKEN') or secrets.token_urlsafe(24)
INGEST_SECRET=os.environ.get('APN_INGEST_SECRET') or secrets.token_urlsafe(32)
POOL=concurrent.futures.ThreadPoolExecutor(max_workers=6); LOCK=threading.Lock()
CAMERAS={f'CAM-{i}':True for i in range(1,5)}; ZONES=['Entrance','Aisles','Service','Checkout']

def connect():
 c=sqlite3.connect(DB,timeout=15); c.row_factory=sqlite3.Row; return c

def init():
 with connect() as c:c.executescript('''PRAGMA journal_mode=WAL;
 CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,camera TEXT,track TEXT,zone TEXT,kind TEXT,confidence REAL,source TEXT);
 CREATE TABLE IF NOT EXISTS handoffs(id INTEGER PRIMARY KEY,ts REAL,source_camera TEXT,source_track TEXT,target_camera TEXT,target_track TEXT,state TEXT,score REAL,margin REAL,provenance TEXT,run TEXT);
 CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,ts REAL,run TEXT,sender TEXT,recipient TEXT,kind TEXT,detail TEXT);
 CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,run TEXT,agent TEXT,state TEXT,detail TEXT,ts REAL);
 CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,ts REAL,action TEXT,detail TEXT);
 CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,question TEXT,state TEXT,result TEXT,ts REAL);''')

def write(table,columns,values):
 with connect() as c:c.execute(f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in values)})",values)
def audit(action,detail):write('audit',['ts','action','detail'],[time.time(),action,detail])
def task(run,agent,state,detail):write('tasks',['run','agent','state','detail','ts'],[run,agent,state,detail,time.time()])
def message(run,sender,recipient,kind,detail):write('messages',['ts','run','sender','recipient','kind','detail'],[time.time(),run,sender,recipient,kind,detail])

def ingest(e):
 if not {'ts','camera','track','zone','kind','confidence'}.issubset(e):raise ValueError('Missing event fields')
 if e['camera'] not in CAMERAS or e['zone'] not in ZONES:raise ValueError('Unknown camera or zone')
 if e['kind'] not in ['observation','enter','exit']:raise ValueError('Unsupported event kind')
 if not isinstance(e['track'],str) or not 1<=len(e['track'])<=80:raise ValueError('Invalid track')
 ts,confidence=float(e['ts']),float(e['confidence'])
 if not 0<=confidence<=1 or not 0<ts<=time.time()+60:raise ValueError('Invalid time or confidence')
 with connect() as c:
  cur=c.execute('INSERT INTO events(ts,camera,track,zone,kind,confidence,source) VALUES(?,?,?,?,?,?,?)',(ts,e['camera'],e['track'],e['zone'],e['kind'],confidence,e.get('source','external'))); return cur.lastrowid

def decide_handoff(candidate):
 components=candidate.get('components',{}); expected={'temporal','spatial','motion','appearance'}
 if set(components)!=expected or any(not 0<=float(v)<=1 for v in components.values()):raise ValueError('Handoff requires four component scores in [0,1]')
 score=round(.3*components['temporal']+.3*components['spatial']+.2*components['motion']+.2*components['appearance'],3)
 runner=float(candidate.get('runner_up_score',0))
 if not 0<=runner<=1:raise ValueError('Invalid runner-up score')
 margin=round(score-runner,3); state='accepted' if score>=.75 and margin>=.15 else 'ambiguous' if score>=.55 else 'rejected'
 return {'state':state,'score':score,'margin':margin,'components':components,'policy':'accepted>=.75 and margin>=.15; ambiguous>=.55; else rejected'}

def record_handoff(candidate,run='scenario'):
 decision=decide_handoff(candidate); cameras=[candidate.get('source_camera'),candidate.get('target_camera')]; tracks=[candidate.get('source_track'),candidate.get('target_track')]
 if any(c not in CAMERAS for c in cameras):raise ValueError('Unknown handoff camera')
 if any(not isinstance(t,str) or not t for t in tracks):raise ValueError('Invalid handoff track')
 with connect() as c:
  cur=c.execute('INSERT INTO handoffs(ts,source_camera,source_track,target_camera,target_track,state,score,margin,provenance,run) VALUES(?,?,?,?,?,?,?,?,?,?)',(float(candidate.get('ts',time.time())),cameras[0],tracks[0],cameras[1],tracks[1],decision['state'],decision['score'],decision['margin'],json.dumps(decision),run)); hid=cur.lastrowid
 return {'id':hid,**decision}

def seed():
 now=time.time()
 with connect() as c:c.execute("DELETE FROM events WHERE source='synthetic'");c.execute("DELETE FROM handoffs WHERE run='scenario'")
 for tick in range(36):
  for camera,zone,count in [('CAM-1','Entrance',8),('CAM-2','Aisles',10),('CAM-3','Service',9),('CAM-4','Checkout',12)]:
   for person in range(count):ingest({'ts':now-350+tick*10,'camera':camera,'track':f'{camera}-T{person:02}','zone':zone,'kind':'observation','confidence':.92 if person%4 else .64,'source':'synthetic'})
 templates=[('CAM-1','CAM-2',i,{'temporal':.94,'spatial':.91,'motion':.86,'appearance':.82},.55) for i in range(6)]
 templates += [('CAM-2','CAM-3',i,{'temporal':.86,'spatial':.79,'motion':.72,'appearance':.68},.69) for i in range(5)]
 templates += [('CAM-3','CAM-4',i,{'temporal':.42,'spatial':.49,'motion':.51,'appearance':.44},.31) for i in range(4)]
 for source,target,p,components,runner in templates:record_handoff({'ts':now-300+p*12,'source_camera':source,'source_track':f'{source}-T{p:02}','target_camera':target,'target_track':f'{target}-T{p:02}','components':components,'runner_up_score':runner})
 audit('scenario_loaded','Synthetic queue scenario: 4 views, 15 handoff hypotheses, deliberate ambiguity')

def load_replay():
 if not REPLAY.exists():raise ValueError('Run replay_pipeline.py before loading real evidence')
 evidence=json.loads(REPLAY.read_text());now=time.time();camera_map={'CAM-01':'CAM-1','CAM-02':'CAM-2','CAM-03':'CAM-3','CAM-04':'CAM-4'};zone_map={'Main Aisle':'Aisles','Service Counter':'Service'}
 with connect() as c:c.execute("DELETE FROM events WHERE source='real_replay'");c.execute("DELETE FROM handoffs WHERE run='real-replay'")
 imported=0
 for feed in evidence['cameras']:
  duration=feed['duration_ms']/1000;camera=camera_map[feed['camera']];zone=zone_map.get(feed['zone'],feed['zone'])
  for event in feed['events']:
   score=float(event['detector_score']);confidence=max(0,min(1,.5+.5*math.tanh(score)))
   ingest({'ts':now-duration+event['source_time_ms']/1000,'camera':camera,'track':event['track'].replace('CAM-0','CAM-'),'zone':zone,'kind':'observation','confidence':confidence,'source':'real_replay'});imported+=1
 with connect() as c:
  for handoff in evidence.get('handoffs',[]):
   c.execute('INSERT INTO handoffs(ts,source_camera,source_track,target_camera,target_track,state,score,margin,provenance,run) VALUES(?,?,?,?,?,?,?,?,?,?)',(now,camera_map[handoff['source_camera']],handoff['source_track'].replace('CAM-0','CAM-'),camera_map[handoff['target_camera']],handoff['target_track'].replace('CAM-0','CAM-'),handoff['state'],handoff['score'],handoff['margin'],json.dumps(handoff),'real-replay'))
 audit('real_replay_loaded',json.dumps({'observations':imported,'handoffs':len(evidence.get('handoffs',[])),'schema':evidence.get('schema')}));return {'source':'real_replay','observations':imported,'handoffs':len(evidence.get('handoffs',[]))}

class UnionFind:
 def __init__(self,items):self.parent={x:x for x in items}
 def find(self,x):
  while self.parent[x]!=x:self.parent[x]=self.parent[self.parent[x]];x=self.parent[x]
  return x
 def union(self,a,b):
  a,b=self.find(a),self.find(b)
  if a!=b:self.parent[b]=a

def identity_bounds(rows,handoffs):
 tracks={(r['camera'],r['track']) for r in rows}; conservative=UnionFind(tracks); optimistic=UnionFind(tracks)
 for h in handoffs:
  a=(h['source_camera'],h['source_track']);b=(h['target_camera'],h['target_track'])
  if a not in tracks or b not in tracks:continue
  if h['state']=='accepted':conservative.union(a,b);optimistic.union(a,b)
  elif h['state']=='ambiguous':optimistic.union(a,b)
 return {'minimum_if_ambiguous_matches_hold':len({optimistic.find(x) for x in tracks}),'maximum_without_ambiguous_merges':len({conservative.find(x) for x in tracks}),'local_track_count':len(tracks)}

def plan_agents(question):
 text=question.lower(); selected=[]
 if any(x in text for x in ['flow','traffic','congestion','queue','zone','bottleneck']):selected.append('Flow')
 if any(x in text for x in ['dwell','wait','slow','queue','bottleneck','friction']):selected.append('Dwell')
 if any(x in text for x in ['movement','path','reverse','stop','handoff','continuity','match','identity','uncertain']):selected.append('Movement')
 return (selected or ['Flow','Dwell'])+['Verifier']

def specialist(run,name,rows,handoffs,enabled):
 task(run,name,'working',f'Inspecting {len(rows)} observations and {len(handoffs)} handoffs');message(run,'Orchestrator',name,'task_request',f'Run typed {name.lower()} measurements')
 if name=='Flow':
  result={'unique_local_tracks_by_zone':{z:len({(r['camera'],r['track']) for r in rows if r['zone']==z}) for z in ZONES},'identity_count_bounds':identity_bounds(rows,handoffs),'note':'Minimum assumes ambiguous links match; maximum merges accepted links only.'}
 elif name=='Dwell':
  spans={}
  for r in rows:spans.setdefault((r['camera'],r['track'],r['zone']),[]).append(r['ts'])
  zones={}
  for (_,_,z),times in spans.items():
   if len(times)>1:zones.setdefault(z,[]).append(max(times)-min(times))
  result={'observed_span_seconds':{z:round(sum(v)/len(v),1) for z,v in zones.items()},'note':'Window-censored spans, not complete visits or service time.'}
 elif name=='Movement':
  result={'handoff_decisions':{s:sum(h['state']==s for h in handoffs) for s in ['accepted','ambiguous','rejected']},'review_required':[h['id'] for h in handoffs if h['state']=='ambiguous'],'note':'Heuristic evidence scores are not calibrated probabilities.'}
 else:
  ambiguity=sum(h['state']=='ambiguous' for h in handoffs); result={'low_confidence_events':sum(r['confidence']<.7 for r in rows),'offline_cameras':[k for k,v in enabled.items() if not v],'ambiguous_handoffs':ambiguity,'evidence_grade':'insufficient' if not rows else 'degraded' if ambiguity or not all(enabled.values()) else 'good'}
 task(run,name,'complete',json.dumps(result));message(run,name,'Orchestrator','result',json.dumps(result));return result

def investigate(run,question):
 try:
  agents=plan_agents(question);task(run,'Orchestrator','working','Plan: '+', '.join(agents)+'; preserve handoff uncertainty');cutoff=time.time()-600
  with LOCK:enabled=dict(CAMERAS)
  with connect() as c:
   rows=[dict(r) for r in c.execute('SELECT * FROM events WHERE ts>=? ORDER BY ts',(cutoff,)) if enabled.get(r['camera'])]
   handoffs=[dict(h) for h in c.execute('SELECT * FROM handoffs WHERE ts>=? ORDER BY ts',(cutoff,)) if enabled.get(h['source_camera']) and enabled.get(h['target_camera'])]
  futures={name:POOL.submit(specialist,run,name,rows,handoffs,enabled) for name in agents};results={n:f.result() for n,f in futures.items()}; verifier=results['Verifier']
  if not rows:summary='Insufficient evidence in the last ten minutes.'
  else:
   flow=results.get('Flow',{});counts=flow.get('unique_local_tracks_by_zone',{});top=max(counts,key=counts.get) if counts else None;bounds=flow.get('identity_count_bounds')
   summary=(f'{top} has the most local tracks ({counts[top]}).' if top else 'The requested measurements are available.')+(f" Cross-camera identity is bounded between {bounds['minimum_if_ambiguous_matches_hold']} and {bounds['maximum_without_ambiguous_merges']} people." if bounds else '')
  limitations=['No causal diagnosis, queue membership, staffing recommendation, or customer intent is inferred.']
  if verifier['evidence_grade']!='good':limitations.append('Evidence is degraded; ambiguous handoffs or missing views require operator review.')
  result={'summary':summary,'question':question,'plan':agents,'scope':'Last 10 minutes; enabled cameras; question selects typed specialists.','evidence_event_ids':[r['id'] for r in rows],'handoff_evidence_ids':[h['id'] for h in handoffs],'specialists':results,'sources':sorted({r['source'] for r in rows}),'limitations':limitations,'evidence_grade':verifier['evidence_grade'],'proposed_action':{'type':'operator_review','status':'required' if verifier['evidence_grade']=='degraded' else 'awaiting_review','detail':'Inspect ambiguous handoffs and source observations. No external action executed.'}}
  with connect() as c:c.execute('UPDATE runs SET state=?,result=? WHERE id=?',('complete',json.dumps(result),run))
  task(run,'Orchestrator','complete',summary);audit('investigation_complete',json.dumps({'run':run,'grade':verifier['evidence_grade'],'plan':agents}))
 except Exception as exc:
  with connect() as c:c.execute('UPDATE runs SET state=?,result=? WHERE id=?',('failed',json.dumps({'error':str(exc)}),run))
  audit('investigation_failed',json.dumps({'run':run,'error':str(exc)}))

def snapshot():
 with connect() as c:
  events=[dict(r) for r in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 80')];handoffs=[dict(r) for r in c.execute('SELECT * FROM handoffs ORDER BY id DESC LIMIT 40')];messages=[dict(r) for r in c.execute('SELECT * FROM messages ORDER BY id DESC LIMIT 40')];tasks=[dict(r) for r in c.execute('SELECT * FROM tasks ORDER BY id DESC LIMIT 35')];runs=[dict(r) for r in c.execute('SELECT * FROM runs ORDER BY ts DESC LIMIT 10')];logs=[dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 20')]
 for h in handoffs:h['provenance']=json.loads(h['provenance'])
 for r in runs:r['result']=json.loads(r['result']) if r['result'] else None
 with LOCK:cameras=dict(CAMERAS)
 return {'events':events,'handoffs':handoffs,'messages':messages,'tasks':tasks,'runs':runs,'audit':logs,'cameras':cameras}

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*_):pass
 def respond(self,status,data):
  body=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
 def do_GET(self):
  if self.path.startswith('/media/'):
   name=self.path.removeprefix('/media/')
   if '/' in name or '..' in name:return self.respond(400,{'error':'Invalid media path'})
   file=MEDIA/name
   if not file.is_file() or file.suffix!='.mp4':return self.respond(404,{'error':'Media not found'})
   body=file.read_bytes();self.send_response(200);self.send_header('Content-Type','video/mp4');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body);return
  if self.path in ['/','/app.js','/style.css','/real.css']:
   file=ROOT/'web'/('index.html' if self.path=='/' else self.path[1:]);body=file.read_bytes();self.send_response(200);self.send_header('Content-Type',{'html':'text/html','js':'text/javascript','css':'text/css'}[file.suffix[1:]]);self.send_header('Content-Security-Policy',"default-src 'self'; media-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'");self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body);return
  if self.path=='/health':return self.respond(200,{'status':'ok'})
  if self.headers.get('Authorization')!='Bearer '+TOKEN:return self.respond(401,{'error':'Valid session token required'})
  if self.path=='/api/state':return self.respond(200,snapshot())
  return self.respond(404,{'error':'Not found'})
 def do_POST(self):
  if self.headers.get('Authorization')!='Bearer '+TOKEN:return self.respond(401,{'error':'Valid session token required'})
  try:
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=65536:return self.respond(413,{'error':'Invalid body size'})
   raw=self.rfile.read(size);data=json.loads(raw)
   if self.path=='/api/ingest':
    expected=hmac.new(INGEST_SECRET.encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,self.headers.get('X-APN-Signature','')):return self.respond(403,{'error':'Invalid signature'})
    if abs(time.time()-float(data['ts']))>60:raise ValueError('Event timestamp outside ingestion window')
    return self.respond(201,{'event_id':ingest(data)})
   if self.path=='/api/demo':seed();return self.respond(200,{'source':'synthetic'})
   if self.path=='/api/replay':return self.respond(200,load_replay())
   if self.path=='/api/camera':
    if data.get('camera') not in CAMERAS or type(data.get('enabled')) is not bool:raise ValueError('Invalid camera state')
    with LOCK:CAMERAS[data['camera']]=data['enabled']
    audit('camera_state',json.dumps(data));return self.respond(200,{'ok':True})
   if self.path=='/api/investigate':
    question=data.get('question','').strip()
    if not 1<=len(question)<=1000:raise ValueError('Question must contain 1-1000 characters')
    run=secrets.token_hex(6)
    with connect() as c:c.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(run,question,'running',None,time.time()))
    threading.Thread(target=investigate,args=(run,question),daemon=True).start();return self.respond(202,{'run':run})
   return self.respond(404,{'error':'Not found'})
  except (ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:return self.respond(400,{'error':str(exc)})

if __name__=='__main__':
 init();print('APN: http://127.0.0.1:8765\nSession token (paste into workspace): '+TOKEN,flush=True);print('Ingest secret available through APN_INGEST_SECRET when configured. Bind: localhost only.',flush=True);ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
