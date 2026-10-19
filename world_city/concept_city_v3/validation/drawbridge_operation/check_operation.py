#!/usr/bin/env python3
"""Independent reconstructed controller traces. Fake sensing is explicit.
This checker controls observations, not controller internals. Replays are portable
JSON for the separately implemented Godot interpreter. No city release implied.
"""
import copy,hashlib,importlib.util,json,math,pathlib,sys,traceback
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'world_city').is_dir())
OP=ROOT/'world_city/concept_city_v3/assemblies/waterworks/registered_bridge/drawbridge_candidate/operation_r01'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('operation_under_review',OP/'controller.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
C=json.loads((OP/'contract.json').read_text())
INPUT_HASHES={str(p.relative_to(ROOT)):sha(p) for p in [OP/'controller.py',OP/'contract.json']}
for k in ['geometry_pack','geometry_envelopes']:
 p=ROOT/C[k]['path'];assert sha(p)==C[k]['sha256'],'geometry binding mismatch: '+k;INPUT_HASHES[str(p.relative_to(ROOT))]=sha(p)
geometry=json.loads((ROOT/C['geometry_pack']['path']).read_text())
candidate_path=ROOT/geometry['candidate']['path'];assert sha(candidate_path)==geometry['candidate']['sha256'];INPUT_HASHES[str(candidate_path.relative_to(ROOT))]=sha(candidate_path)
candidate=json.loads(candidate_path.read_text())
assert C['vessel_catalog']=={v['asset_key']:v['union_source_cache_bounds_local_m'] for v in candidate['navigation_vessels']},'controller catalog shrinks/changes sealed full-rig geometry'
for v in candidate['navigation_vessels']:
 for k in ['source','cache']:
  p=ROOT/v[k]['path'];assert sha(p)==v[k]['sha256'];INPUT_HASHES[str(p.relative_to(ROOT))]=sha(p)

class Trace:
 def __init__(self,name):
  self.name=name;self.c=M.Controller(C);self.now=0;self.seq=0;self.out=None;self.frames=[]
  self.s={'sequence':0,'timestamp_ms':0,'complete':True,'coverage_ids':copy.deepcopy(C['required_coverage_ids']),'geometry_sha256':C['geometry_pack']['sha256'],'observations':[],'pending_navigation_admissions':[],'actuators':{'leaves':'seated_locked','covers':'seated_locked','barriers':'open_locked'},'admission_ack':{k:{'closed':True,'generation':0} for k in ['road','navigation']},'emergency_stop':False}
 def tick(self,commands=None,mut=None,dt=100,auto_lock=False,auto_ack=True):
  self.now+=dt;self.seq+=1;self.s['sequence']=self.seq;self.s['timestamp_ms']=self.now
  if self.out:
   if auto_ack:
    self.s['admission_ack']={k:{'closed':not v['enabled'],'generation':v['generation']} for k,v in self.out['admission_commands'].items()}
   if auto_lock:self.s['actuators'].update(self.out['actuator_targets'])
  s=copy.deepcopy(self.s)
  if mut:mut(s)
  f={'now_ms':self.now,'snapshot':copy.deepcopy(s),'commands':commands or []}
  out=self.c.step(f['now_ms'],s,f['commands']);f['expected']=copy.deepcopy(out);self.frames.append(f);self.out=out
  assert not(out['road_enabled'] and out['navigation_enabled']),'simultaneous route grants'
  if out['state']=='SAFE_HALT':
   assert out['stop_all_actuators'] and not out['actuator_targets'],'halt commands movement'
   assert not any(v['enabled'] for v in out['admission_commands'].values()),'halt leaves admission open'
   assert not out['road_enabled'] and not out['navigation_enabled'],'halt leaves route enabled'
  if out['actuator_targets']:
   assert not out['road_enabled'] and not out['navigation_enabled'],'movement with route grant'
   for k,v in out['admission_commands'].items():
    assert not v['enabled'],'motion admits new traffic'
    assert s['admission_ack'][k]=={'closed':True,'generation':v['generation']},'motion without current closed acknowledgement'
  return out
 def ready(self):
  self.tick();assert not self.out['road_enabled'];self.tick();assert self.out['road_enabled'];return self
 def reach(self,state,request=None):
  if request:self.tick([request])
  for _ in range(25):
   if self.out and self.out['state']==state:return self
   self.tick(auto_lock=True)
  raise AssertionError('could not reach '+state+': '+str(self.out))
 def navigation(self):
  self.ready();self.reach('NAVIGATION_OPEN','request_navigation');self.tick();assert self.out['navigation_enabled'];return self
 def halted(self):assert self.out['state']=='SAFE_HALT',self.out
 def obs(self,x=0,z=0,kind='pedestrian'):
  self.s['observations']=[{'id':'P','kind':kind,'bounds_bridge_local_m':{'min':[x-.4,4,z-.4],'max':[x+.4,5.8,z+.4]}}]
 def vessel(self,z=0,extra=None):
  o={'id':'SHIP','kind':'vessel','asset_key':'registered_port_rigged_barge_24m','transform_bridge_local':{'basis':[[1,0,0],[0,1,0],[0,0,1]],'translation':[-2.5,0,z]}}
  if extra:o.update(extra)
  self.s['observations']=[o]
RESULTS=[];FIXTURES=[]
def run(name,fn,json_compatible=True):
 t=Trace(name)
 try:fn(t);result={'id':name,'pass':True,'frames':len(t.frames)}
 except Exception as e:result={'id':name,'pass':False,'error':repr(e),'traceback':traceback.format_exc(),'frames':len(t.frames)}
 RESULTS.append(result)
 if json_compatible:FIXTURES.append({'id':name,'frames':t.frames})
def malformed(t,fn):t.tick(mut=fn);t.halted()
# Independent schema/freshness negatives, from the explicitly complete baseline.
mutators={
 'missing_observations':lambda s:s.pop('observations'),
 'missing_complete':lambda s:s.pop('complete'),
 'incomplete_coverage':lambda s:s.update(complete=False),
 'coverage_missing_volume':lambda s:s['coverage_ids'].pop(),
 'coverage_duplicate':lambda s:s['coverage_ids'].__setitem__(0,s['coverage_ids'][1]),
 'coverage_unhashable_member':lambda s:s['coverage_ids'].__setitem__(0,{}),
 'wrong_geometry':lambda s:s.update(geometry_sha256='0'*64),
 'future_sensor':lambda s:s.update(timestamp_ms=s['timestamp_ms']+1),
 'stale_sensor':lambda s:s.update(timestamp_ms=0),
 'negative_sequence':lambda s:s.update(sequence=-1),
 'boolean_sequence':lambda s:s.update(sequence=True),
 'unknown_actuator':lambda s:s['actuators'].update(leaves='unknown'),
 'malformed_actuator_member':lambda s:s['actuators'].update(leaves={}),
 'missing_admission':lambda s:s['admission_ack'].pop('navigation'),
 'untyped_ack':lambda s:s['admission_ack']['navigation'].update(closed=1),
 'both_admissions_open':lambda s:[v.update(closed=False) for v in s['admission_ack'].values()],
 'opposite_ack_wrong_generation':lambda s:s['admission_ack']['navigation'].update(generation=1),
 'unknown_pending_vessel':lambda s:s.update(pending_navigation_admissions=['ABSENT']),
 'unhashable_pending_vessel':lambda s:s.update(pending_navigation_admissions=[{}]),
 'unknown_object_kind':lambda s:s.update(observations=[{'id':'A','kind':'spectre'}]),
 'reversed_object_bounds':lambda s:s.update(observations=[{'id':'A','kind':'other','bounds_bridge_local_m':{'min':[1,1,1],'max':[0,0,0]}}]),
 'contradictory_locks':lambda s:s['actuators'].update(leaves='open_locked'),
 'emergency_stop':lambda s:s.update(emergency_stop=True),
}
for name,fn in mutators.items():
 if name=='stale_sensor':run(name,lambda t,f=fn:(setattr(t,'now',600),malformed(t,f)))
 else:run(name,lambda t,f=fn:malformed(t,f))
run('huge_sensor_integer',lambda t:malformed(t,lambda s:s.update(sequence=10**400)),False)
run('startup_requires_open_ack',lambda t:t.ready())
def complete_cycle(t):
 t.navigation();t.reach('ROAD_OPEN','request_road');t.tick();assert t.out['road_enabled']
run('normal_guarded_round_trip',complete_cycle)
def road_occupied(t):
 t.ready();t.obs();t.tick(['request_navigation'])
 for _ in range(20):t.tick(auto_lock=True);assert t.out['state']=='ROAD_DRAIN' and not t.out['actuator_targets']
 t.s['observations']=[];t.reach('NAVIGATION_OPEN');t.tick();assert t.out['navigation_enabled']
run('occupied_road_drains_before_movement',road_occupied)
def tail(t):
 t.navigation();t.vessel(0);t.tick();assert t.out['active_vessel_ids']==['SHIP'];t.tick(['request_road'])
 for z in [30,36,37,37.5]:
  t.vessel(z)
  for _ in range(3):t.tick(auto_lock=True);assert t.out['state']=='NAVIGATION_DRAIN' and t.out['active_vessel_ids']==['SHIP']
 t.vessel(37.5001);t.tick();assert t.out['state']=='NAVIGATION_DRAIN' and not t.out['active_vessel_ids'];t.tick();assert t.out['state']=='LEAVES_LOWERING'
run('full_rig_tail_and_tangent_hold',tail)
def fake_hull(t):
 t.navigation();t.vessel(36,{'bounds_bridge_local_m':{'min':[99,99,99],'max':[100,100,100]}});t.tick(['request_road'])
 for _ in range(5):t.tick();assert t.out['state']=='NAVIGATION_DRAIN' and t.out['active_vessel_ids']==['SHIP']
run('supplied_tiny_hull_cannot_replace_rig',fake_hull)
def vanished(t):
 t.navigation();t.vessel();t.tick();t.s['observations']=[];t.tick();t.halted()
run('tracked_vessel_cannot_disappear',vanished)
def pending(t):
 t.navigation();t.vessel(60);t.s['pending_navigation_admissions']=['SHIP'];t.tick(['request_road'])
 for _ in range(5):t.tick();assert t.out['state']=='NAVIGATION_DRAIN'
run('pending_admission_prevents_lowering',pending)
def malformed_vessel(t,kind):
 t.navigation();t.vessel()
 if kind=='asset':t.s['observations'][0]['asset_key']={}
 if kind=='scale':t.s['observations'][0]['transform_bridge_local']['basis'][0][0]=.1
 if kind=='mirror':t.s['observations'][0]['transform_bridge_local']['basis'][0][0]=-1
 if kind=='nan':t.s['observations'][0]['transform_bridge_local']['translation'][0]=float('nan')
 t.tick();t.halted()
for kind in ['asset','scale','mirror','nan']:run('vessel_'+kind,lambda t,k=kind:malformed_vessel(t,k),kind!='nan')
def admission_loss(t,nav,reopen):
 (t.navigation if nav else t.ready)();opposite='road' if nav else 'navigation'
 t.tick(mut=lambda s:s['admission_ack'][opposite].update(**({'closed':False} if reopen else {'generation':999})));t.halted()
for nav in [False,True]:
 for reopen in [False,True]:run(('navigation' if nav else 'road')+'_opposite_'+('reopened' if reopen else 'ack_lost'),lambda t,n=nav,r=reopen:admission_loss(t,n,r))
def no_timer(t):
 t.ready();t.reach('LEAVES_RAISING','request_navigation');t.s['actuators']['leaves']='moving'
 for _ in range(80):t.tick();assert t.out['state']=='LEAVES_RAISING'
run('elapsed_time_never_substitutes_locked_pose',no_timer)
def mid_motion(t,kind):
 t.ready();t.reach('LEAVES_RAISING','request_navigation');t.s['actuators']['leaves']='moving'
 if kind=='intrusion':t.obs()
 mut=(lambda s:s.update(timestamp_ms=0)) if kind=='stale' else (lambda s:s['admission_ack']['road'].update(closed=False)) if kind=='admission' else None
 t.tick(mut=mut);t.halted()
for kind in ['intrusion','stale','admission']:run('mid_raise_'+kind,lambda t,k=kind:mid_motion(t,k))
def reset(t):
 t.ready();t.tick(['stop']);t.halted();t.tick();t.halted();t.tick(['reset']);assert t.out['state']=='ROAD_OPEN' and t.out['stop_all_actuators'] and not t.out['actuator_targets'];t.tick();assert t.out['road_enabled']
run('latched_stop_explicit_safe_reset',reset)
def unsafe_reset(t):
 t.ready();t.reach('LEAVES_RAISING','request_navigation');t.obs();t.tick();t.halted();t.tick(['reset']);t.halted()
run('reset_rejected_while_intruder_present',unsafe_reset)
def reversal(t):
 t.ready();t.reach('LEAVES_RAISING','request_navigation');t.s['actuators']['leaves']='moving';t.tick(['request_road']);assert t.out['state']=='LEAVES_RAISING' and t.out['actuator_targets']=={'leaves':'open_locked'}
 t.reach('ROAD_OPEN');t.tick();assert t.out['road_enabled']
run('request_reversal_completes_safe_raise_first',reversal)
def duplicate(t):
 t.ready();t.tick(['request_navigation']);t.tick();assert t.out['clear_frames']['road']==1
 last=t.frames[-1];out=t.c.step(last['now_ms'],copy.deepcopy(last['snapshot']),[]);t.frames.append({'now_ms':last['now_ms'],'snapshot':copy.deepcopy(last['snapshot']),'commands':[],'expected':out});assert out['clear_frames']['road']==1 and out['state']=='ROAD_DRAIN'
run('identical_sequence_does_not_count_as_new_clearance',duplicate)
def rewritten(t):
 t.ready();seq=t.frames[-1]['snapshot']['sequence'];t.tick(mut=lambda s:s.update(sequence=seq));t.halted()
run('rewritten_sequence_halts',rewritten)
def timestamp(t):
 t.ready();ts=t.frames[-1]['snapshot']['timestamp_ms'];t.tick(mut=lambda s:s.update(timestamp_ms=ts));t.halted()
run('new_sequence_requires_new_timestamp',timestamp)
run('clock_gap_halts',lambda t:(t.ready(),t.tick(dt=1001),t.halted()))
run('conflicting_requests_halt',lambda t:(t.ready(),t.tick(['request_road','request_navigation']),t.halted()))
run('unknown_command_halts',lambda t:(t.ready(),t.tick(['teleport']),t.halted()))
# Source-bound complete sweep coverage, independently checked by AABB containment.
env=json.loads((ROOT/C['geometry_envelopes']['path']).read_text());boxes=env['leaf_swept_volumes']+env['other_swept_volumes'];uncovered=[]
for b in boxes:
 bb=b.get('bounds_bridge_local_m')
 if bb and not any(all(q['bounds']['min'][i]<=bb['min'][i]+1e-9 and q['bounds']['max'][i]>=bb['max'][i]-1e-9 for i in range(3)) for q in C['volumes']['mechanism_sweep']):uncovered.append(b['id'])
for p,h in INPUT_HASHES.items():assert sha(ROOT/p)==h,'source changed during run'
report={'schema':'riverstone.independent.operation_reconstructed.v1','status':'pass_bounded_simulated_controller' if all(x['pass'] for x in RESULTS) and not uncovered else 'FAIL','sources':INPUT_HASHES,'checker_sha256':sha(pathlib.Path(__file__)),'scope':'Independent adversarial API traces with explicit simulated sensing. No native actor sensor, physical admission blocker, or city runtime approval.','results':RESULTS,'case_count':len(RESULTS),'passing_count':sum(x['pass'] for x in RESULTS),'json_case_count':len(FIXTURES),'json_frame_count':sum(len(x['frames']) for x in FIXTURES),'motion_enclosure_count':len(boxes),'uncovered_motion_enclosures':uncovered,'prior_unarchived_results_reused':False}
prefix='operation_'+sha(OP/'controller.py')[:12]+'_'+report['checker_sha256'][:12]
(HERE/(prefix+'.json')).write_text(json.dumps(report,indent=2)+'\n');(HERE/(prefix+'.fixtures.json')).write_text(json.dumps({'cases':FIXTURES},indent=2,allow_nan=False)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['sources','results']},indent=2));print('REPORT',prefix+'.json');print('FAILURES',json.dumps([r for r in RESULTS if not r['pass']],indent=2));sys.exit(0 if report['status'].startswith('pass') else 1)
