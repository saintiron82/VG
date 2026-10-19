"""Reconstructed executable scenario vectors; timestamps and physical locks are simulated."""
import copy,json
from controller import Controller,HERE
class Rig:
 def __init__(self):self.c=Controller();self.now=0;self.seq=0;self.a={'leaves':'seated_locked','covers':'seated_locked','barriers':'open_locked'};self.obs=[];self.frames=[]
 def step(self,commands=[],edit=None,dt=100):
  self.now+=dt;self.seq+=1;s={'sequence':self.seq,'timestamp_ms':self.now,'complete':True,'coverage_ids':self.c.contract['required_coverage_ids'],'geometry_sha256':self.c.contract['geometry_pack']['sha256'],'observations':copy.deepcopy(self.obs),'pending_navigation_admissions':[],'actuators':self.a.copy(),'admission_ack':{k:{'closed':not v['enabled'],'generation':v['generation']} for k,v in self.c.admissions.items()},'emergency_stop':False}
  if edit:edit(s)
  o=self.c.step(self.now,s,commands);self.frames.append({'now_ms':self.now,'snapshot':s,'commands':commands,'expected':o});return o
 def until(self,state):
  for _ in range(40):
   o=self.step()
   if o['state']==state:return o
   self.a.update(o['actuator_targets'])
  raise AssertionError(o)
 def nav(self):self.step();self.step(['request_navigation']);return self.until('NAVIGATION_OPEN')
 def boat(self,z):return {'id':'RIG','kind':'vessel','asset_key':'registered_port_rigged_barge_24m','transform_bridge_local':{'basis':[[1,0,0],[0,1,0],[0,0,1]],'translation':[-2.5,-.9,z]}}
 def person(self):return {'id':'P','kind':'pedestrian','bounds_bridge_local_m':{'min':[-.4,4,-.4],'max':[.4,5.8,.4]}}
CASES=[]
def save(n,r):CASES.append({'id':n,'frames':r.frames})
def run():
 r=Rig();assert not r.step()['road_enabled'];assert r.step()['road_enabled'];r.nav();assert r.step()['navigation_enabled'];r.obs=[r.boat(0)];r.step();r.step(['request_road']);r.obs=[r.boat(36)]
 for _ in range(12):assert r.step()['state']=='NAVIGATION_DRAIN'
 r.obs=[r.boat(40)];r.step();r.obs=[];r.until('ROAD_OPEN');assert r.step()['road_enabled'];save('full_cycle_full_tail_exit',r)
 r=Rig();r.obs=[r.person()];r.step(['request_navigation'])
 for _ in range(10):assert r.step()['state']=='ROAD_DRAIN'
 r.obs=[];r.until('NAVIGATION_OPEN');save('pedestrian_drain',r)
 r=Rig();r.step(['request_navigation']);r.until('BARRIERS_CLOSING');r.a['barriers']='moving'
 for _ in range(20):assert r.step()['state']=='BARRIERS_CLOSING'
 save('no_timer_authority',r)
 r=Rig();r.step(['request_navigation']);r.until('LEAVES_RAISING');r.a['leaves']='moving';r.obs=[r.person()];assert r.step()['state']=='SAFE_HALT';assert r.step(['reset'])['state']=='SAFE_HALT';r.obs=[];r.a['leaves']='stopped';assert r.step(['reset'])['stop_all_actuators'];r.until('NAVIGATION_OPEN');save('intrusion_latched_reset',r)
 r=Rig();r.step(['request_navigation']);r.until('LEAVES_RAISING');r.a['leaves']='moving';assert r.step(['request_road'])['actuator_targets']=={'leaves':'open_locked'};r.until('ROAD_OPEN');save('no_midmotion_reversal',r)
 r=Rig();r.nav();r.obs=[r.boat(0)];r.step();r.obs=[];assert r.step()['halt_reason']=='tracked_vessel_missing';save('missing_tracked_rig',r)
 edits={'missing':lambda s:s.pop('observations'),'unknown':lambda s:s['actuators'].update(leaves='unknown'),'future':lambda s:s.update(timestamp_ms=s['timestamp_ms']+1),'stale':lambda s:s.update(timestamp_ms=0),'incomplete':lambda s:s.update(complete=False),'bad_coverage':lambda s:s.update(coverage_ids=[{}]),'bad_asset':lambda s:s.update(observations=[{'id':'V','kind':'vessel','asset_key':[]}]),'both_open':lambda s:[a.update(closed=False) for a in s['admission_ack'].values()],'contradictory':lambda s:s['actuators'].update(leaves='open_locked'),'pending_unknown':lambda s:s.update(pending_navigation_admissions=['V']),'emergency':lambda s:s.update(emergency_stop=True)}
 for n,edit in edits.items():
  r=Rig();r.now=1000;assert r.step(edit=edit)['state']=='SAFE_HALT';save(n,r)
 r=Rig();r.step();assert r.step(['reset'],dt=5000)['state']=='SAFE_HALT';save('large_clock_gap',r)
 r=Rig();r.step();assert r.step(['request_road','request_navigation','reset'])['state']=='SAFE_HALT';save('conflicting_commands',r)
 r=Rig();r.step();r.step();o=r.step(edit=lambda s:s['admission_ack']['navigation'].update(generation=100));assert o['state']=='SAFE_HALT' and not o['admission_commands']['road']['enabled'];save('opposite_gate_ack_loss',r)
 r=Rig();r.step();r.seq-=1;assert r.step()['halt_reason']=='rewritten_sequence';save('rewritten_sequence',r)
 r=Rig();r.step();r.step();r.seq-=2;assert r.step()['halt_reason']=='sequence_reversal';save('sequence_reversal',r)
 r=Rig();r.step(['request_navigation']);r.step();s=copy.deepcopy(r.frames[-1]['snapshot']);o=r.c.step(r.now+10,s,[]);r.frames.append({'now_ms':r.now+10,'snapshot':s,'commands':[],'expected':o});assert o['clear_frames']['road']==1;save('same_frame_not_clear_twice',r)
 assert not __import__('controller').finite(10**400)
 (HERE/'test_vectors.json').write_text(json.dumps({'cases':CASES},indent=2,sort_keys=True)+'\n');report={'valid':True,'cases':len(CASES),'frames':sum(len(c['frames']) for c in CASES),'reconstructed':True};(HERE/'python_test_report.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':run()
