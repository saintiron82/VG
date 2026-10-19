#!/usr/bin/env python3
"""Separate bounded-step candidate, with independent common-compiled safety fixtures."""
import argparse,copy,hashlib,json,sys
from pathlib import Path
import prepare as base
ROOT=base.ROOT;HERE=base.HERE
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.topography import author as a

def control_asset(name,boxes):
 master=a._new_master([-2,-2,2,2],'capsule_test_control','stone',{'isolated_physics_fixture':True,'not_city_geometry':True})
 master['components']=[{'id':'solid','parts':[{'id':'solid','pivot':[0,0,0]}],
  'operations':[{'id':'box_'+str(n),'part':'solid','action':'paint','material':'stone','shape':{'kind':'box','min':lo,'max':hi}} for n,(lo,hi) in enumerate(boxes)]}]
 master['instances']=[{'id':'control','component':'solid'}];master=a._finish(master)
 compiled,render=a.compile_sample(master,.05,max_candidate_cells=400000,max_output_cells=200000)
 mp=HERE/'controls'/f'{name}.master.json';rp=HERE/'controls'/f'{name}.render.json'
 base.write(mp,master);base.write(rp,render)
 return {'render_path':str(rp.relative_to(ROOT)),'render_sha256':base.digest(rp),'master_path':str(mp.relative_to(ROOT)),
         'master_sha256':base.digest(mp),'bounds':render['bounds'],'pitch_m':.05,'quad_count':render['quad_count']}

def prepare(scene,layers,out,fine_only):
 # Leave no-step prepared inputs/evidence untouched.
 p=base.prepare(scene,layers,out,fine_only)
 p['schema']='riverstone.city.r2_step_candidate_suite.v1'
 p['assumptions']['controller']='experimental generic step candidate; not production controller'
 p['assumptions']['step_policy']={'max_step_m':.15,'grounded_blocked_only':True,'up_forward_down_collision_sweeps':True,
      'motion':'move_and_collide only after test_move checks; no transform assignment within route',
      'transient_ground_policy':'retain is_on_floor misses; distinguish nearby support <=0.115m from unsupported flight'}
 controls=[('NEGATIVE_STEP_TOO_HIGH_0P25','riser025',.25,False),('NEGATIVE_STEP_LOW_HEADROOM','riser010_low_headroom',.1,True)]
 for rid,key,rise,ceiling in controls:
  asset=control_asset(key,[([-2,-.2,-2],[2,0,2]),([0,0,-2],[2,rise,2])]);p['assets'][key]=asset
  placement={'id':'CONTROL:'+key,'asset_key':key,'position_m':[0,0,0],'yaw_deg':0,'category':'isolated_control_ground','collision_layer':1}
  p['placements'][placement['id']]=placement;ids=[placement['id']]
  if ceiling:
   k=key+'_ceiling';p['assets'][k]=control_asset(k,[([-2,1.85,-2],[2,2.05,2])]);ident='CONTROL:'+k
   p['placements'][ident]={'id':ident,'asset_key':k,'position_m':[0,0,0],'yaw_deg':0,'category':'isolated_control_ceiling','collision_layer':2};ids.append(ident)
  route=base.route_record(rid,[[-1,0],[1,0]],'negative_control',[],expected_failure='blocked',
      test_scope='isolated common-compiled fixture; never city geometry',expected_contact_id=placement['id'])
  route.update(placement_ids=ids,building_ids=[]);p['routes'].append(route)
 for rel in ['StepCandidate.gd','StepCandidate.tscn','prepare_candidate.py','audit_report.py']:
  path=HERE/rel;p['implementation_hashes'][str(path.relative_to(ROOT))]=base.digest(path)
 p['coverage']['route_count']=len(p['routes']);p['coverage']['candidate_controls']=2
 p['coverage']['selected_collision_assets']=len(p['assets']);p['coverage']['selected_placements']=len(p['placements'])
 base.write(out,p);return p
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--scene',type=Path,default=ROOT/'world_city/runtime_city/generated/r2/scene.json')
 ap.add_argument('--layers',type=Path,default=ROOT/'world_city/runtime_city/generated/r2_topography/layer_manifest.json')
 ap.add_argument('--output',type=Path,default=HERE/'prepared.candidate.json');ap.add_argument('--fine-only',action='store_true')
 args=ap.parse_args();p=prepare(args.scene,args.layers,args.output,args.fine_only);print(json.dumps({'coverage':p['coverage'],'sources':p['sources']},indent=2))
