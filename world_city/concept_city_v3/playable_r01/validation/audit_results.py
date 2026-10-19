#!/usr/bin/env python3
"""Audit completed independent results; preserve every failed run."""
import argparse,hashlib,json,pathlib,math
P=argparse.ArgumentParser();P.add_argument('follow',type=pathlib.Path);P.add_argument('replay',type=pathlib.Path);P.add_argument('--output',type=pathlib.Path,required=True);a=P.parse_args()
if a.output.exists():raise SystemExit('Refusing existing output '+str(a.output))
def read(p):return json.loads(p.read_text())
def ref(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
f=read(a.follow/'report.json');r=read(a.replay/'report.json');inputs=read(a.follow/'recorded_inputs.json');assert f['mode']=='follow' and r['mode']=='replay'
checks=[]
def check(name,passed,detail=None):checks.append({'check':name,'pass':bool(passed),'detail':detail})
for key in ['physics_hz','controller_sha256','world_script_sha256','harness_sha256','tile_index_sha256','cases_sha256']:check('same_'+key,f[key]==r[key],{'follow':f[key],'replay':r[key]})
check('60hz',f['physics_hz']==r['physics_hz']==60)
check('follow_pass',f['status']=='PASS');check('replay_pass',r['status']=='PASS')
fc={c['id']:c for c in f['cases']};rc={c['id']:c for c in r['cases']}
check('identical_case_set',set(fc)==set(rc)==set(inputs['cases']))
summary=[]
for id,c in fc.items():
 d=rc[id];replay=inputs['cases'][id]
 check(id+'_input_fields_only',all(set(x)=={'tick','direction','speed_mps'} for x in replay['frames']))
 check(id+'_one_spawn_no_traversal_positions',all(x['spawn_position_assignments']==1 and x['traversal_position_assignments']==0 for x in [c,d]))
 check(id+'_real_capsule',all(abs(x['capsule_radius_m']-.23)<1e-6 and abs(x['capsule_height_m']-1.72)<1e-6 for x in [c,d]))
 check(id+'_pass',c['pass'] and d['pass'])
 ft={x['tick']:x for x in c['trace']};rt={x['tick']:x for x in d['trace']};common=set(ft)&set(rt)
 max_error=max((math.dist(ft[t]['feet_m'],rt[t]['feet_m']) for t in common),default=math.inf)
 check(id+'_recorded_input_reproduces_trajectory',max_error<=1e-5,{'matched_samples':len(common),'max_distance_m':max_error})
 summary.append({'id':id,'expect':c['expect'],'follow_pass':c['pass'],'replay_pass':d['pass'],'movement_ticks_follow':c['movement_ticks'],'final_endpoint_distance_m':c['final_distance_to_target_m'],'ground_loss_frames':c['ground_loss_frames'],'max_centerline_error_m':c['max_centerline_error_m'],'height_range_m':c['height_range_m'],'streaming_cells':c['streaming_cells'],'expected_native_obstacle_contact':c['expected_obstacle_contact'],'maximum_blocked_streak':c['max_blocked_streak'],'replay_max_trajectory_difference_m':max_error})
out={'schema':'riverstone.lily_city.control_audit.v1','status':'PASS' if all(x['pass'] for x in checks) else 'FAIL','sources':{'follow':ref(a.follow/'report.json'),'replay':ref(a.replay/'report.json'),'recorded_input':ref(a.follow/'recorded_inputs.json')},'checks':checks,'cases':summary,'manual_keyboard_test':False,'scope':'Actual unchanged Lily capsule in the production tiled r04 city. Automated input route-following plus separate saved direction/speed replay. GUI WASD/camera evidence remains separate.','limits':f['limits']}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'checks':len(checks),'failed':[x for x in checks if not x['pass']],'cases':summary},indent=2))
