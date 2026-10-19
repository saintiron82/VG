"""Reconstructed deterministic operational candidate; no IO, timer or actuator authority."""
import copy,json,math,itertools
from pathlib import Path
HERE=Path(__file__).resolve().parent

def finite(v):
 try:return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
 except (ValueError,OverflowError):return False
def integer(v):return finite(v) and v>=0 and int(v)==v
def box_valid(b):return isinstance(b,dict) and all(isinstance(b.get(k),list) and len(b[k])==3 and all(finite(x) for x in b[k]) for k in ('min','max')) and all(b['min'][i]<=b['max'][i] for i in range(3))
def intersects(a,b):return all(a['min'][i]<=b['max'][i] and a['max'][i]>=b['min'][i] for i in range(3))
def transformed_box(b,t):
 pts=[[sum(t['basis'][i][j]*p[j] for j in range(3))+t['translation'][i] for i in range(3)] for p in itertools.product(*[(b['min'][i],b['max'][i]) for i in range(3)])]
 return {k:[fn(p[i] for p in pts) for i in range(3)] for k,fn in [('min',min),('max',max)]}
def rigid_valid(t):
 if not isinstance(t,dict) or not isinstance(t.get('basis'),list) or len(t['basis'])!=3 or not isinstance(t.get('translation'),list) or len(t['translation'])!=3:return False
 b=t['basis']
 if not all(isinstance(r,list) and len(r)==3 and all(finite(v) for v in r) for r in b) or not all(finite(v) for v in t['translation']):return False
 if any(abs(sum(b[i][k]*b[j][k] for k in range(3))-(1 if i==j else 0))>1e-6 for i in range(3) for j in range(3)):return False
 det=b[0][0]*(b[1][1]*b[2][2]-b[1][2]*b[2][1])-b[0][1]*(b[1][0]*b[2][2]-b[1][2]*b[2][0])+b[0][2]*(b[1][0]*b[2][1]-b[1][1]*b[2][0])
 return abs(det-1)<1e-6
class Controller:
 def __init__(self,contract=None):
  self.contract=copy.deepcopy(contract or json.loads((HERE/'contract.json').read_text()));self.state=self.contract['initial_state'];self.resume_state=self.state;self.desired_mode='road';self.halt_reason='';self.last_now=None;self.last_sequence=None;self.last_timestamp=None;self.last_snapshot=None;self.active_vessels=set();self.exit_ledger=[];self.road_streak=0;self.nav_streak=0;self.admissions={k:{'enabled':False,'generation':0} for k in ('road','navigation')};self.facts={};self.valid=False;self.last_reset_rejection='';self.transition_serial=0
 def _halt(self,reason):
  if self.state!='SAFE_HALT':self.resume_state=self.state;self.halt_reason=reason;self.transition_serial+=1
  self.state='SAFE_HALT';self.road_streak=0;self.nav_streak=0
 def _admissions(self):
  for k in self.admissions:
   enabled=self.valid and not self.halt_reason and ((k=='road' and self.state=='ROAD_OPEN' and self.desired_mode=='road') or (k=='navigation' and self.state=='NAVIGATION_OPEN' and self.desired_mode=='navigation'))
   if self.admissions[k]['enabled']!=enabled:self.admissions[k]['enabled']=enabled;self.admissions[k]['generation']+=1
 def _validate(self,now,s):
  def fail(r):return r,False,{}
  if not isinstance(s,dict):return fail('snapshot_not_object')
  if any(k not in s for k in self.contract['sensor_contract']['required_fields']):return fail('missing_required_field')
  if s['complete'] is not True:return fail('incomplete_coverage')
  if not isinstance(s['coverage_ids'],list) or any(not isinstance(v,str) for v in s['coverage_ids']) or set(s['coverage_ids'])!=set(self.contract['required_coverage_ids']) or len(s['coverage_ids'])!=len(self.contract['required_coverage_ids']):return fail('incomplete_coverage')
  if s['geometry_sha256']!=self.contract['geometry_pack']['sha256']:return fail('geometry_mismatch')
  if not integer(s['sequence']) or not integer(s['timestamp_ms']):return fail('invalid_sensor_time')
  if s['timestamp_ms']>now:return fail('future_sensor_time')
  if now-s['timestamp_ms']>self.contract['sensor_max_age_ms']:return fail('stale_sensor')
  new=self.last_sequence is None or s['sequence']>self.last_sequence
  if self.last_sequence is not None:
   if s['sequence']<self.last_sequence:return fail('sequence_reversal')
   if s['sequence']==self.last_sequence and s!=self.last_snapshot:return fail('rewritten_sequence')
   if new and s['timestamp_ms']<=self.last_timestamp:return fail('timestamp_not_increasing')
  if not isinstance(s['emergency_stop'],bool):return fail('invalid_emergency_signal')
  if not isinstance(s['actuators'],dict) or set(s['actuators'])!=set(self.contract['known_actuator_status']):return fail('unknown_actuator_feedback')
  if any(s['actuators'][k] not in allowed for k,allowed in self.contract['known_actuator_status'].items()):return fail('unknown_actuator_feedback')
  a=s['actuators']
  if (a['barriers']=='open_locked' and (a['leaves']!='seated_locked' or a['covers']!='seated_locked')) or (a['leaves']=='open_locked' and a['covers']!='stowed_locked'):return fail('contradictory_pose')
  if not isinstance(s['admission_ack'],dict) or set(s['admission_ack'])!={'road','navigation'}:return fail('unknown_admission_feedback')
  for a in s['admission_ack'].values():
   if not isinstance(a,dict) or set(a)!={'closed','generation'} or not isinstance(a['closed'],bool) or not integer(a['generation']):return fail('unknown_admission_feedback')
  if not s['admission_ack']['road']['closed'] and not s['admission_ack']['navigation']['closed']:return fail('contradictory_admission_feedback')
  if not isinstance(s['observations'],list) or not isinstance(s['pending_navigation_admissions'],list):return fail('missing_occupancy')
  observed={}
  for o in s['observations']:
   if not isinstance(o,dict) or not isinstance(o.get('id'),str) or not o['id'] or o['id'] in observed:return fail('invalid_object_id')
   if o.get('kind') not in ('pedestrian','cart','vessel','other'):return fail('unknown_object_kind')
   if o['kind']=='vessel':
    if not isinstance(o.get('asset_key'),str) or o['asset_key'] not in self.contract['vessel_catalog'] or not rigid_valid(o.get('transform_bridge_local')):return fail('unknown_full_vessel_geometry')
    b=transformed_box(self.contract['vessel_catalog'][o['asset_key']],o['transform_bridge_local'])
   else:b=o.get('bounds_bridge_local_m')
   if not box_valid(b):return fail('invalid_object_bounds')
   observed[o['id']]={'kind':o['kind'],'bounds':b}
  p=s['pending_navigation_admissions']
  if any(not isinstance(i,str) or i not in observed or observed[i]['kind']!='vessel' for i in p) or len(set(p))!=len(p):return fail('unknown_pending_vessel')
  if any(i not in observed or observed[i]['kind']!='vessel' for i in self.active_vessels):return fail('tracked_vessel_missing')
  return '',new,observed
 def _hit(self,b,volume):return any(intersects(b,q['bounds']) for q in self.contract['volumes'][volume])
 def _facts(self,s,observed):
  a=s['actuators'];f={'leaves_seated':a['leaves']=='seated_locked','leaves_open':a['leaves']=='open_locked','covers_seated':a['covers']=='seated_locked','covers_stowed':a['covers']=='stowed_locked','barriers_open':a['barriers']=='open_locked','barriers_closed':a['barriers']=='closed_locked','want_road':self.desired_mode=='road','want_navigation':self.desired_mode=='navigation','active_vessels_empty':not self.active_vessels,'pending_vessels_empty':not s['pending_navigation_admissions']}
  for name in self.contract['required_coverage_ids']:f[{'road_span':'road_clear','barrier_sweep':'barrier_clear','mechanism_sweep':'mechanism_clear'}.get(name,name+'_clear')]=not any(self._hit(o['bounds'],name) for o in observed.values() if not(name=='road_span' and o['kind']=='vessel'))
  for k in self.admissions:
   a=s['admission_ack'][k];t=self.admissions[k];f[k+'_admission_closed_ack']=not t['enabled'] and a['closed'] and a['generation']==t['generation'];f[k+'_admission_open_ack']=t['enabled'] and not a['closed'] and a['generation']==t['generation']
  f['road_clear_stable']=self.road_streak>=self.contract['clear_observation_frames_required'];f['navigation_clear_stable']=self.nav_streak>=self.contract['clear_observation_frames_required'];return f
 def _invariant_failure(self,state,s,f):
  r=self.contract['states'][state]
  for k in r['invariants']:
   if not f.get(k,False):return 'invariant:'+k
  for k,v in s['actuators'].items():
   if v in ('moving','stopped') and k not in r['targets']:return 'unexpected_actuator_motion:'+k
  return ''
 def step(self,now_ms,snapshot,commands=None):
  self.last_reset_rejection='';fault=False;commands=[] if commands is None else commands
  if not integer(now_ms):self.valid=False;self._halt('invalid_controller_clock');self._admissions();return self.output()
  if self.last_now is not None and (now_ms<self.last_now or now_ms-self.last_now>self.contract['maximum_step_gap_ms']):self._halt('controller_clock_discontinuity');fault=True
  self.last_now=now_ms
  if not isinstance(commands,list) or any(c not in self.contract['commands'] for c in commands):self._halt('invalid_command');commands=[];fault=True
  if ('request_road' in commands and 'request_navigation' in commands) or ('reset' in commands and 'stop' in commands):self._halt('conflicting_commands');fault=True
  if 'request_road' in commands:self.desired_mode='road'
  if 'request_navigation' in commands:self.desired_mode='navigation'
  if 'stop' in commands:self._halt('manual_stop')
  reason,new,observed=self._validate(now_ms,snapshot);self.valid=not reason
  if reason:self._halt(reason);self._admissions();return self.output()
  s=snapshot
  if new:
   self.last_sequence=s['sequence'];self.last_timestamp=s['timestamp_ms'];self.last_snapshot=copy.deepcopy(s)
   for i,o in observed.items():
    if o['kind']=='vessel':
     if self._hit(o['bounds'],'navigation_passage'):self.active_vessels.add(i)
     elif i in self.active_vessels:self.active_vessels.remove(i);self.exit_ledger.append({'id':i,'sequence':s['sequence'],'full_bounds_bridge_local_m':o['bounds']})
  if s['emergency_stop']:self._halt('emergency_stop')
  opposite={'ROAD_OPEN':'navigation','NAVIGATION_OPEN':'road'}.get(self.state)
  if opposite:
   a=s['admission_ack'][opposite];t=self.admissions[opposite]
   if t['enabled'] or not a['closed'] or a['generation']!=t['generation']:self._halt('opposite_admission_not_secured')
  self._admissions();f=self._facts(s,observed)
  if new:
   self.road_streak=self.road_streak+1 if self.state=='ROAD_DRAIN' and f['road_clear'] and f['road_admission_closed_ack'] else 0
   self.nav_streak=self.nav_streak+1 if self.state=='NAVIGATION_DRAIN' and f['navigation_passage_clear'] and f['active_vessels_empty'] and f['pending_vessels_empty'] and f['navigation_admission_closed_ack'] else 0
  f=self._facts(s,observed)
  if self.state=='SAFE_HALT':
   if 'reset' in commands and 'stop' not in commands and not s['emergency_stop'] and not fault:
    why=self._invariant_failure(self.resume_state,s,f)
    if not why and f['road_admission_closed_ack'] and f['navigation_admission_closed_ack']:
     self.state=self.resume_state;self.halt_reason='';self.transition_serial+=1;self._admissions();self.facts=self._facts(s,observed);return self.output(True)
    self.last_reset_rejection=why or 'admission_closure_not_acknowledged'
   self.facts=f;return self.output()
  why=self._invariant_failure(self.state,s,f)
  if why:self._halt(why);self._admissions();self.facts=f;return self.output()
  r=self.contract['states'][self.state]
  if all(f.get(k,False) for k in r['guards']):
   nxt=r['next'];why=self._invariant_failure(nxt,s,f)
   if why:self._halt(why)
   else:
    self.state=nxt;self.transition_serial+=1
    if nxt=='ROAD_DRAIN':self.road_streak=0
    if nxt=='NAVIGATION_DRAIN':self.nav_streak=0
  self._admissions();self.facts=self._facts(s,observed);return self.output()
 def output(self,suppress_motion=False):
  safe=self.valid and self.state!='SAFE_HALT';road=safe and self.state=='ROAD_OPEN' and self.facts.get('road_admission_open_ack',False) and self.facts.get('navigation_admission_closed_ack',False);nav=safe and self.state=='NAVIGATION_OPEN' and self.facts.get('navigation_admission_open_ack',False) and self.facts.get('road_admission_closed_ack',False)
  return {'state':self.state,'desired_mode':self.desired_mode,'halt_reason':self.halt_reason,'reset_rejection':self.last_reset_rejection,'transition_serial':self.transition_serial,'road_enabled':bool(road),'navigation_enabled':bool(nav),'road_exit_only':bool(safe and self.state=='ROAD_DRAIN'),'navigation_exit_only':bool(safe and self.state=='NAVIGATION_DRAIN'),'admission_commands':copy.deepcopy(self.admissions),'actuator_targets':copy.deepcopy(self.contract['states'][self.state]['targets']) if safe and not suppress_motion else {},'stop_all_actuators':not safe or suppress_motion,'active_vessel_ids':sorted(self.active_vessels),'exit_ledger':copy.deepcopy(self.exit_ledger),'clear_frames':{'road':self.road_streak,'navigation':self.nav_streak},'sensor_valid':self.valid}
