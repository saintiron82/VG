"""Reconstructed after executor loss; derive monitoring ownership from restored sealed geometry."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=HERE.parents[6]
def load(p):return json.loads(p.read_text())
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def merged(boxes,m=0):return {'min':[min(b['min'][i] for b in boxes)-m for i in range(3)],'max':[max(b['max'][i] for b in boxes)+m for i in range(3)]}
def build():
 env=load(BASE/'motion_envelopes.json');candidate=load(BASE/'candidate.json');audit=load(BASE/'geometry_audit.json');groups={}
 for q in env['leaf_swept_volumes']+env['other_swept_volumes']:groups.setdefault(q['id'].split(':')[0],[]).append(q['bounds_bridge_local_m'])
 mechanism=[{'id':k,'bounds':merged(v,.1)} for k,v in groups.items()];nav=merged([q['full_source_cache_swept_envelope_bridge_m'] for q in audit['navigation']],.5)
 volumes={'road_span':[{'id':'ROAD_BETWEEN_BARRIERS','bounds':{'min':[-13.5,3,-7.5],'max':[13.5,9,7.5]}}],'barrier_sweep':[q for q in mechanism if q['id'].startswith('BARRIER_')],'mechanism_sweep':mechanism,'navigation_actuation':[{'id':'VESSEL_NEAR_MOVING_SPAN','bounds':{'min':[-9,nav['min'][1],-10],'max':[9,nav['max'][1],10]}}],'navigation_passage':[{'id':'FULL_VESSEL_EXIT_GUARD','bounds':{'min':[-6.75,nav['min'][1],-25.5],'max':[6.75,nav['max'][1],25.5]}}]}
 rows=[
 ('ROAD_OPEN','leaves_seated covers_seated barriers_open',{},'ROAD_DRAIN','want_navigation'),
 ('ROAD_DRAIN','leaves_seated covers_seated barriers_open',{},'BARRIERS_CLOSING','road_admission_closed_ack road_clear_stable barrier_clear mechanism_clear navigation_actuation_clear navigation_admission_closed_ack navigation_passage_clear active_vessels_empty pending_vessels_empty'),
 ('BARRIERS_CLOSING','leaves_seated covers_seated road_clear barrier_clear mechanism_clear',{'barriers':'closed_locked'},'COVERS_STOWING','barriers_closed'),
 ('COVERS_STOWING','barriers_closed leaves_seated road_clear mechanism_clear',{'covers':'stowed_locked'},'LEAVES_RAISING','covers_stowed'),
 ('LEAVES_RAISING','barriers_closed covers_stowed road_clear mechanism_clear',{'leaves':'open_locked'},'NAVIGATION_OPEN','leaves_open'),
 ('NAVIGATION_OPEN','barriers_closed covers_stowed leaves_open road_clear',{},'NAVIGATION_DRAIN','want_road'),
 ('NAVIGATION_DRAIN','barriers_closed covers_stowed leaves_open road_clear',{},'LEAVES_LOWERING','navigation_admission_closed_ack navigation_clear_stable active_vessels_empty pending_vessels_empty navigation_passage_clear mechanism_clear'),
 ('LEAVES_LOWERING','barriers_closed covers_stowed road_clear mechanism_clear',{'leaves':'seated_locked'},'COVERS_SEATING','leaves_seated'),
 ('COVERS_SEATING','barriers_closed leaves_seated road_clear mechanism_clear',{'covers':'seated_locked'},'BARRIERS_OPENING','covers_seated'),
 ('BARRIERS_OPENING','leaves_seated covers_seated road_clear barrier_clear',{'barriers':'open_locked'},'ROAD_OPEN','barriers_open')]
 states={n:{'invariants':i.split(),'targets':t,'next':nxt,'guards':g.split()} for n,i,t,nxt,g in rows}
 for r in states.values():
  if r['targets']:r['invariants']+='road_admission_closed_ack navigation_admission_closed_ack navigation_passage_clear active_vessels_empty pending_vessels_empty'.split()
 d={'schema':'riverstone.drawbridge_operation.r01.reconstructed','geometry_pack':ref(BASE/'resolved_placements.json'),'geometry_envelopes':ref(BASE/'motion_envelopes.json'),'bridge_to_world':candidate['bridge_to_world'],'sensor_max_age_ms':500,'maximum_step_gap_ms':1000,'sensor_future_tolerance_ms':0,'required_coverage_ids':list(volumes),'volumes':volumes,'vessel_catalog':{q['asset_key']:q['union_source_cache_bounds_local_m'] for q in candidate['navigation_vessels']},'states':states,'initial_state':'ROAD_OPEN','commands':['request_road','request_navigation','stop','reset'],'known_actuator_status':{'leaves':['seated_locked','open_locked','moving','stopped'],'covers':['seated_locked','stowed_locked','moving','stopped'],'barriers':['open_locked','closed_locked','moving','stopped']},'clear_observation_frames_required':2,'sensor_contract':{'required_fields':['sequence','timestamp_ms','complete','coverage_ids','geometry_sha256','observations','pending_navigation_admissions','actuators','admission_ack','emergency_stop'],'empty_semantics':'Only explicit observations:[] with complete fresh coverage, known lock/admission feedback, matching geometry and monotonic sequence means empty.','observation':'id,kind; pedestrian/cart/other use bounds_bridge_local_m. Vessels require asset_key and rigid transform_bridge_local; controller computes whole rig from catalog.','admission_ack':'road/navigation each {closed:bool,generation:int}; current generation required.','coverage':'All finite volumes plus every tracked/pending vessel until observed full-envelope exit.'},'reconstruction':{'reason':'Executor filesystem lost after Library version5 checkpoint. Source reconstructed and retested; prior unarchived seal is historical evidence only.','prior_unarchived_seal':'11c55cfcc0dae189c31fbcacf58a3486c03963be12814daaa2db7223c4fa41bd'},'limits':['Timers never certify empty occupancy or locked completion.','Hinge-cover hoist/carriage supports remain absent in visible art.','Closed-world simulated sensing is not real city population integration.']}
 (HERE/'contract.json').write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(ref(HERE/'contract.json'))
if __name__=='__main__':build()
