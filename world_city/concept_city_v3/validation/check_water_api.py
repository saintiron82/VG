#!/usr/bin/env python3
"""Hash-bound independent finite-domain and full-width water-join API audit.

Imports the authored height API to sample its result, but derives join agreement,
clip containment and bed clearance independently. No hydraulic simulation.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from collections import defaultdict
import geometry as g

HERE=Path(__file__).resolve().parent
CITY=HERE.parent
ROOT=CITY.parents[1]
sys.path.insert(0,str(ROOT))

def check(author_path,contract_path,plan_path):
 paths={'author':author_path,'contract':contract_path,'plan':plan_path,'polygon_dependency':ROOT/'world_city/runtime_city/checks/placement.py'}
 raw={k:Path(p).read_bytes() for k,p in paths.items()}
 hashes={k:hashlib.sha256(v).hexdigest() for k,v in raw.items()}
 contract=json.loads(raw['contract']);issues=[];warnings=[]
 if contract.get('source_plan_sha256')!=hashes['plan']:
  issues.append({'code':'contract_plan_hash_mismatch','contract_sha256':contract.get('source_plan_sha256'),'current_plan_sha256':hashes['plan']})
 spec=importlib.util.spec_from_file_location('audited_water_author',author_path)
 author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
 if getattr(author,'SOURCE_PLAN_SHA256',None)!=hashes['plan']:
  issues.append({'code':'imported_author_plan_hash_mismatch'})
 surfaces={w['id']:w for w in contract['water_surfaces']}
 if author.WATER_SURFACES!=[{k:v for k,v in surface.items() if k!='finite_domains'} for surface in contract['water_surfaces']]:
  issues.append({'code':'contract_author_water_surfaces_mismatch'})
 domains=contract.get('water_domain_polygons',[])
 if domains and domains!=author.finite_water_polygons():
  issues.append({'code':'contract_author_finite_water_domains_mismatch'})
 domain_overlap_count=0;maximum_domain_overlap=0
 for i,domain in enumerate(domains):
  polygon=domain['polygon_xz_m'];box=g.bounds(polygon)
  for other in domains[:i]:
   if not g.bbox_overlap(box,g.bounds(other['polygon_xz_m'])):continue
   overlap=g.intersection_area(polygon,other['polygon_xz_m'])
   if overlap>1e-6:
    domain_overlap_count+=1;maximum_domain_overlap=max(maximum_domain_overlap,overlap)
    issues.append({'code':'positive_area_water_domain_overlap','surface_a':domain['surface_id'],'surface_b':other['surface_id'],'overlap_area_m2':overlap})
 samples=[]
 for water in contract['water_surfaces']:
  line=water.get('polyline_xz_m',[])
  for i,(a,b) in enumerate(zip(line,line[1:])):
   length=math.dist(a,b);count=max(1,math.ceil(length/2));half=water['width_m']/2
   normal=[-(b[1]-a[1])/length,(b[0]-a[0])/length]
   offsets=sorted(set([-half,-half/2,0,half/2,half]))
   for j in range(count+1):
    for offset in offsets:
     samples.append([a[k]+(b[k]-a[k])*j/count+normal[k]*offset for k in (0,1)])
   # Dense join neighborhoods catch capped same-surface segment overlaps.
   for point in (a,b):
    for ix in range(-6,7):
     for iz in range(-6,7):samples.append([point[0]+ix*half/6,point[1]+iz*half/6])
 join_records=defaultdict(list);checked=0;maximum_bed_error=0
 for point in samples:
  hits=author.water_samples_at(*point);checked+=1
  for hit in hits:
   water=surfaces[hit['id']];clip=water.get('clip_bounds_xz_m')
   if clip and not(clip[0]-1e-7<=point[0]<=clip[2]+1e-7 and clip[1]-1e-7<=point[1]<=clip[3]+1e-7):
    issues.append({'code':'water_domain_outside_clip','water_id':hit['id'],'point_xz_m':point})
   maximum_bed_error=max(maximum_bed_error,abs(hit['water_y_m']-hit['bed_y_m']-water['bed_depth_m']))
  for i,a in enumerate(hits):
   for b in hits[i+1:]:
    difference=abs(a['water_y_m']-b['water_y_m'])
    if difference>1e-5:
     key=tuple(sorted([a['id']+':'+str(a.get('segment','polygon')),b['id']+':'+str(b.get('segment','polygon'))]))
     join_records[key].append({'point_xz_m':point,'difference_m':difference,'heads_m':[a['water_y_m'],b['water_y_m']]})
 for pair,rows in join_records.items():
  warnings.append({'code':'overlapping_water_domains_have_different_heads','domains':pair,'sample_count':len(rows),'maximum_difference_m':max(v['difference_m'] for v in rows),'worst_sample':max(rows,key=lambda v:v['difference_m'])})
 if maximum_bed_error>1e-8:issues.append({'code':'water_bed_depth_inconsistent','maximum_error_m':maximum_bed_error})
 # The two source canal mouths must agree across the WHOLE shoreline opening.
 mouths=[]
 canal=surfaces['SERVICE_CANAL']
 for segment,point in [(0,canal['polyline_xz_m'][0]),(len(canal['polyline_xz_m'])-2,canal['polyline_xz_m'][-1])]:
  rows=[]
  for j in range(-100,101):
   p=[point[0]+j*.05,point[1]]
   hits=author.water_samples_at(*p)
   ca=[v for v in hits if v['id']=='SERVICE_CANAL' and v.get('segment')==segment]
   ri=[v for v in hits if v['id']=='MAIN_RIVER']
   if ca and ri:rows.append(abs(ca[0]['water_y_m']-ri[0]['water_y_m']))
  record={'segment':segment,'shoreline_z_m':point[1],'sample_count':len(rows),'maximum_head_difference_m':max(rows,default=None)};mouths.append(record)
  if not rows or max(rows)>1e-6:issues.append({'code':'river_mouth_full_width_head_discontinuity',**record})
 changed=[k for k,p in paths.items() if Path(p).read_bytes()!=raw[k]]
 if changed:issues.append({'code':'input_changed_during_audit','inputs':changed})
 sources={}
 for k,data in raw.items():
  snapshot=HERE/'evidence'/'sources'/(k+'_'+hashes[k]+Path(paths[k]).suffix)
  snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(data)
  sources[k]={'path':str(Path(paths[k]).resolve()),'sha256':hashes[k],'snapshot':str(snapshot)}
 return {'schema':'riverstone.concept_city.independent_water_api.v1','status':'fail' if issues else 'pass_with_geometry_warnings' if warnings else 'pass',
  'sources':sources,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  'counts':{'sample_points':checked,'issues':len(issues),'warnings':len(warnings)},'issues':issues,'warnings':warnings,
  'checks':{'river_mouth_full_width':mouths,'maximum_bed_depth_error_m':maximum_bed_error,'finite_domain_polygons':len(domains),'positive_area_domain_overlaps':domain_overlap_count,'maximum_domain_overlap_area_m2':maximum_domain_overlap},
  'limitations':['Finite source API only; no display/common voxel mesh or capsule certification.','Sampled agreement is not hydraulic, capacity, erosion, flood or water-quality approval.','Same-surface overlap warnings are retained; a source graph can pass while water drawing domains still disagree.']}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--author',type=Path,default=CITY/'topography/author.py');ap.add_argument('--contract',type=Path,default=CITY/'topography/contract.json');ap.add_argument('--plan',type=Path,default=CITY/'source/plan.json');args=ap.parse_args()
 report=check(args.author,args.contract,args.plan)
 output=HERE/'evidence'/('water_api_'+report['sources']['contract']['sha256'][:12]+'_'+hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()[:12]+'.json')
 output.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'counts':report['counts'],'issues':report['issues'],'warnings':report['warnings'],'checks':report['checks'],'output':str(output)},indent=2))
 raise SystemExit(2 if report['issues'] else 0)
