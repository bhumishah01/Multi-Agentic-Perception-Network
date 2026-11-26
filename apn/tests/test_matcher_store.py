import tempfile
import unittest
from pathlib import Path

import numpy as np

from apn.agents.handoff import HandoffPolicy
from apn.agents.matcher import TrackMatcher
from apn.store.runtime import RuntimeStore, recompute_entities


class MatcherAndStoreTests(unittest.TestCase):
 def test_matcher_ranks_all_candidates_and_uses_margin(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   for name,vector in {"s.npy":[1,0],"good.npy":[.99,.01],"bad.npy":[0,1]}.items():np.save(root/name,np.asarray(vector,dtype=float))
   def row(camera,track,ts,ref,x):return {"camera_id":camera,"local_track_id":track,"store_ts":ts,"embedding_ref":ref,"foot_px":[x,100]}
   rows=[row("A","T1",1,"s.npy",100),row("B","GOOD",2,"good.npy",110),row("B","BAD",2,"bad.npy",900)]
   policy=HandoffPolicy({"appearance":.45,"temporal":.2,"spatial":.15,"topology":.1,"exclusivity":.1})
   ranked=TrackMatcher(rows,root,policy).rank(("A","T1"),"B")
   self.assertEqual([x["track"][1] for x in ranked],["GOOD","BAD"])
   self.assertGreater(ranked[0]["decision"]["margin"],.1)

 def test_decisions_persist_and_recompute_components(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/"runtime.db";store=RuntimeStore(path)
   store.add("handoff","H1","accept","reviewed","Operator")
   self.assertEqual(RuntimeStore(path).overrides(),{"H1":"accept"})
   data={"handoffs":[{"handoff_id":"H1","source_camera":"A","source_track":"T1","target_camera":"B","target_track":"T2","state":"ambiguous"}],
         "entities":[{"journey":[{"camera_id":"A","local_track_id":"T1","start":0},{"camera_id":"B","local_track_id":"T2","start":1}]}]}
   computed=recompute_entities(data,store.overrides())
   self.assertEqual(len(computed["entities"]),1)
   self.assertEqual(computed["handoffs"][0]["state"],"accepted")

if __name__=="__main__":unittest.main()
