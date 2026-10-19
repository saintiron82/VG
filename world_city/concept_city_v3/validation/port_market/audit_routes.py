"""Independent native solid-section test of port loading routes and market reservations."""
import json,math,hashlib
from pathlib import Path
from world_city.runtime_city.checks import placement as geo
from .audit_native_floor_sections import slices,world,clean
ROOT=Path(__file__).resolve().parents[4];CITY=ROOT/'world_city/concept_city_v3';HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
P=CITY/'assemblies/landmarks/registered/port_r01/access_proposals.json';routes=load(P);I=CITY/'registered_integration/r2/candidate.json';pack=load(I);assets=pack['common_assets'];native={};instances=pack['common_instances'];index=geo._SpatialIndex(32);bounds={}
for j,p in enumerate(instances):
 key=p['asset_key']
 if key not in native:native[key]=load(ROOT/assets[key]['render_path'])
 b=native[key]['bounds'];ring=clean([world([x,z],p) for x,z in [(b['min'][0],b['min'][2]),(b['max'][0],b['min'][2]),(b['max'][0],b['max'][2]),(b['min'][0],b['max'][2])]])
 index.add(j,ring);bounds[j]=(ring,p['position_m'][1]+b['min'][1],p['position_m'][1]+b['max'][1])
rows=[]
for r in routes['routes']:
 ribbon=r['reserved_ribbon_xz_m'];y=r['threshold_y_m'];hits=[];checked=0
 for j in sorted(index.candidates(ribbon)):
  ring,lo,hi=bounds[j]
  if hi<=y+.05 or lo>=y+2.0 or not geo.positive_area_overlap(ribbon,ring,0):continue
  p=instances[j];rd=native[p['asset_key']];checked+=1
  for h in [.05,.25,.5,.75,1,1.25,1.5,1.75,1.99]:
   for local in slices(rd,y+h-p['position_m'][1]):
    q=clean([world(v,p) for v in local])
    if geo.positive_area_overlap(ribbon,q,1e-7):hits.append({'instance_id':p['id'],'height_above_floor_m':h,'intersection_xz_m':geo.convex_intersection(ribbon,q)})
 rows.append(dict(id=r['id'],ribbon_width_m=r['width_m'],nearby_native_instances_checked=checked,solid_conflicts=hits,pass_horizontal_native_clearance=not hits))
report=dict(schema='riverstone.native_port_route_audit.v1',input_hashes={str(P.relative_to(ROOT)):sha(P),str(I.relative_to(ROOT)):sha(I)},route_count=len(rows),passing=sum(r['pass_horizontal_native_clearance'] for r in rows),rows=rows,scope='Finite 3m route ribbons against exact native grid solid sections at nine walking heights, with full runtime instance broad-phase. Source flat height2.2m. No dynamic capsule, NPC, cart or visual claim.')
(HERE/'native_route_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2));print([(r['id'],len(r['solid_conflicts'])) for r in rows if r['solid_conflicts']])
