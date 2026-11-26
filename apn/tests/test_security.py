import unittest
from pathlib import Path
import numpy as np
from apn.security import RBAC,AgentSigner,mask_person,HealthMonitor
from apn.security.rbac import PermissionDenied


class SecurityTests(unittest.TestCase):
 def test_rbac_denial(self):
  rbac=RBAC.load(Path(__file__).parents[1]/"config"/"roles.yaml")
  self.assertTrue(rbac.allows("Administrator","manage_agents"))
  with self.assertRaises(PermissionDenied):rbac.require("Business Operations","view_raw_video")
 def test_signature_rejects_forgery(self):
  signer=AgentSigner({"agent":b"secret"});payload={"x":1};self.assertTrue(signer.verify("agent",payload,signer.sign("agent",payload)))
  self.assertFalse(signer.verify("agent",{"x":2},signer.sign("agent",payload)))
 def test_masking_changes_head_region_without_mutating_source(self):
  rng=np.random.default_rng(2);image=rng.integers(0,255,(100,100,3),dtype=np.uint8);masked=mask_person(image,(20,10,80,90))
  self.assertFalse(np.array_equal(masked[10:28,20:80],image[10:28,20:80]));self.assertTrue(np.array_equal(image,image.copy()))
 def test_health_frozen_replay_obstruction_and_teleport(self):
  monitor=HealthMonitor(frozen_frames=3);normal=np.full((30,30,3),200,dtype=np.uint8)
  alerts=[]
  for _ in range(3):alerts+=monitor.inspect_frame("C",normal)
  self.assertTrue(any(x["kind"]=="frozen_feed" for x in alerts))
  self.assertTrue(any(x["kind"]=="possible_obstruction" for x in monitor.inspect_frame("C",np.zeros_like(normal))))
  self.assertIsNotNone(monitor.inspect_motion("E",(0,0,0),(100,0,1)))
  monitor.heartbeat("agent",0);self.assertEqual(monitor.silent_agents(10,5)[0]["kind"],"agent_silence")
  spike=None
  for i in range(22):spike=monitor.inspect_message_rate("agent",i/100)
  self.assertEqual(spike["kind"],"message_rate_spike")

if __name__=="__main__":unittest.main()
