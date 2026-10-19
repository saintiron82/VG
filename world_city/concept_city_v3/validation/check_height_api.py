#!/usr/bin/env python3
"""Source-bound numerical grade, threshold and discrete-stair contract audit.

This does not run physics and does not compile or approve voxel terrain.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
import geometry as g

HERE=Path(__file__).resolve().parent
CITY=HERE.parent
ROOT=CITY.parents[1]
sys.path.insert(0,str(ROOT))

def check(plan_path,contract_path,author_path,legacy_flat_landings=False):
 paths={'plan':plan_path,'contract':contract_path,'author':author_path}
 raw={k:Path(p).read_bytes() for k,p in paths.items()}
 sha={k:hashlib.sha256(data).hexdigest() for k,data in raw.items()}
 plan=json.loads(raw['plan']);contract=json.loads(raw['contract']);issues=[];warnings=[]
 spec=importlib.util.spec_from_file_location('independent_height_api_target',author_path)
 author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
 if contract.get('source_plan_sha256')!=sha['plan'] or getattr(author,'SOURCE_PLAN_SHA256',None)!=sha['plan']:
  issues.append({'code':'mixed_source_revision','plan_sha256':sha['plan'],'contract_plan_sha256':contract.get('source_plan_sha256'),'api_plan_sha256':getattr(author,'SOURCE_PLAN_SHA256',None)})
 road_records=[];grade_limit=float(contract['grade_proof']['cart_limit'])
 for road in plan['roads']:
  worst={'grade':0};count=0
  for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):
   length=math.dist(a,b)
   if length<1e-8:continue
   normal=[-(b[1]-a[1])/length,(b[0]-a[0])/length]
   n=max(1,math.ceil(length/2))
   for j in range(n+1):
    for offset in (-road['width_m']/2-2,-road['width_m']/2,0,road['width_m']/2,road['width_m']/2+2):
     p=[a[k]+(b[k]-a[k])*j/n+normal[k]*offset for k in (0,1)]
     h=author.road_height_at(road['id'],*p);count+=1
     if not math.isfinite(h):issues.append({'code':'nonfinite_road_height','road_id':road['id'],'point_xz_m':p});continue
     # Independent central differences in X and Z estimate full gradient,
     # rather than accepting only centerline longitudinal sample slopes.
     eps=.01
     dx=(author.road_height_at(road['id'],p[0]+eps,p[1])-author.road_height_at(road['id'],p[0]-eps,p[1]))/(2*eps)
     dz=(author.road_height_at(road['id'],p[0],p[1]+eps)-author.road_height_at(road['id'],p[0],p[1]-eps))/(2*eps)
     grade=math.hypot(dx,dz)
     if grade>worst['grade']:worst={'grade':grade,'point_xz_m':p,'gradient':[dx,dz]}
  record={'road_id':road['id'],'samples':count,'maximum_sampled_full_width_and_shoulder_gradient':worst};road_records.append(record)
  if worst['grade']>grade_limit+1e-5:issues.append({'code':'road_gradient_exceeds_contract',**record})
 pads={p['building_id']:p for p in contract['building_pads']};path_index={p['id']:p for p in plan['paths']};pad_records=[]
 excluded=set(contract.get('superseded_landmark_pad_ids',[]))
 for building in plan['buildings'] if legacy_flat_landings else []:
  pad=pads.get(building['id'])
  if pad is None:
   # Source supersession must be explicit in the contract, not inferred from a
   # missing pad or an assembly being developed elsewhere.
   if building['id'] not in excluded:issues.append({'code':'building_missing_pad_contract','building_id':building['id']})
   continue
  door=building['entrance_xz_m'];floor=pad['floor_y_m'];path_id=pad.get('door_path_id');outer=pad['landing_outer_xz_m']
  if math.dist(door,pad['primary_entrance_xz_m'])>1e-6:issues.append({'code':'pad_primary_door_source_mismatch','building_id':building['id']})
  if not any(g.intersection_area(building['footprint_xz_m'],poly)>=g.area(building['footprint_xz_m'])-1e-5 for poly in pad['owned_polygons_xz_m']):
   issues.append({'code':'body_not_contained_by_pad_domain','building_id':building['id']})
  length=math.dist(door,outer);direction=[(outer[k]-door[k])/length for k in (0,1)] if length>1e-8 else [0,0]
  beyond=[outer[k]+direction[k]*.01 for k in (0,1)]
  path_y=author.path_height_at(path_id,*door);outer_y=author.path_height_at(path_id,*beyond)
  record={'building_id':building['id'],'primary_center_threshold_delta_m':path_y-floor,'landing_outer_center_delta_m':outer_y-floor,'landing_edge_height_deltas_m':[]}
  if abs(path_y-floor)>1e-5 or abs(outer_y-floor)>.00121:issues.append({'code':'primary_landing_center_height_discontinuity',**record})
  if length>2.00001:issues.append({'code':'declared_two_metre_landing_exceeds_extent','building_id':building['id'],'length_m':length,'path_id':path_id})
  path=path_index.get(path_id)
  if not path:issues.append({'code':'pad_door_path_missing_from_source','building_id':building['id'],'path_id':path_id})
  elif math.dist(door,outer)>1e-8:
   normal=[-(outer[1]-door[1])/math.dist(door,outer),(outer[0]-door[0])/math.dist(door,outer)]
   for side in (-1,1):
    point=[beyond[k]+normal[k]*max(2.4,path['width_m'])/2*side for k in (0,1)]
    record['landing_edge_height_deltas_m'].append(author.path_height_at(path_id,*point)-floor)
   if max(abs(v) for v in record['landing_edge_height_deltas_m'])>.02:
    warnings.append({'code':'flat_landing_outer_edge_crossfall_seam','building_id':building['id'],'deltas_m':record['landing_edge_height_deltas_m'],'note':'Center threshold continuity does not prove full-width seam or capsule clearance.'})
  pad_records.append(record)
 stair_records=[]
 for stair in contract.get('neighborhood_stair_geometry',[]):
  if 'treads' not in stair:
   warnings.append({'code':'stair_geometry_unavailable','stair_id':stair['id'],'status':stair.get('status')});continue
  heights=[stair['top_y_m']]+[t['top_y_m'] for t in stair['treads']]
  risers=[a-b for a,b in zip(heights,heights[1:])]
  record={'stair_id':stair['id'],'step_count':len(risers),'maximum_actual_riser_m':max(risers),'minimum_actual_riser_m':min(risers),'bottom_closure_error_m':abs(heights[-1]-stair['bottom_y_m']),'status':'source_geometry_only_not_capsule_tested'};stair_records.append(record)
  if min(risers)<=0 or max(risers)>.150001 or record['bottom_closure_error_m']>1e-6:issues.append({'code':'stair_riser_contract_mismatch',**record})
 changed=[key for key,path in paths.items() if Path(path).read_bytes()!=raw[key]]
 if changed:issues.append({'code':'input_changed_during_audit','inputs':changed})
 sources={}
 for key,data in raw.items():
  snapshot=HERE/'evidence'/'sources'/(key+'_'+sha[key]+Path(paths[key]).suffix);snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(data)
  sources[key]={'path':str(Path(paths[key]).resolve()),'sha256':sha[key],'snapshot':str(snapshot)}
 return {'schema':'riverstone.concept_city.independent_height_api.v1','status':'fail' if issues else 'pass_with_geometry_warnings' if warnings else 'pass','sources':sources,'scope':'roads_shoulders_and_discrete_source_stairs' if not legacy_flat_landings else 'legacy_flat_landing_contract_plus_roads',
  'implementation_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),HERE/'geometry.py']},
  'counts':{'roads':len(road_records),'grade_samples':sum(r['samples'] for r in road_records),'primary_pads':len(pad_records),'discrete_stairs':len(stair_records),'issues':len(issues),'warnings':len(warnings)},
  'checks':{'roads':road_records,'primary_pads':pad_records,'discrete_stairs':stair_records},'issues':issues,'warnings':warnings,
  'limitations':['Numerical source API audit only; finite sampling is not a proof of all gradients.','No actual capsule, production controller, NPC, common voxel geometry, or retaining support claim.','Primary doors only; secondary doors need explicit future assembly metadata.','Landing crossfall seams and actual stairs must be preserved in subsequent physics tests.']}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,default=CITY/'source/plan.json');ap.add_argument('--contract',type=Path,default=CITY/'topography/contract.json');ap.add_argument('--author',type=Path,default=CITY/'topography/author.py');ap.add_argument('--legacy-flat-landings',action='store_true',help='Only for archived pre-taper contracts; current entrances use check_entrance_seams.py');args=ap.parse_args()
 report=check(args.plan,args.contract,args.author,args.legacy_flat_landings);fingerprint=hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()[:12]
 output=HERE/'evidence'/('height_api_'+report['sources']['plan']['sha256'][:12]+'_'+fingerprint+'.json');output.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'counts':report['counts'],'issues':report['issues'],'output':str(output)},indent=2));raise SystemExit(2 if report['issues'] else 0)
