"""Actual final-scene finite seam support; no floor synthesis."""
from pathlib import Path
import sys
O=Path(__file__).resolve().parent
ROOT=next(p for p in O.parents if (p/'voxel_character').is_dir())
SRC=ROOT/'world_city/concept_city_v3/assemblies/landmarks/registered/precinct_r06_whole/primary_goals_completion_r01'
sys.path.insert(0,str(SRC))
from find_branches import *
O=Path(__file__).resolve().parent
def write(n,d):(O/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
class Support:
 def __init__(self,scene,windows,native):self.terrain=terrain.TriangleIndex(scene,windows);self.native=terrain.TriangleIndex({'surfaces':native},windows)
 def covering(self,p):
  claimed=[]
  for ix in [self.native,self.terrain]:
   for r in ix.covering(p):
    for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
     if geo.polygon_area(q)>1e-10:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)
def shorten(a,c,d=2):
 n=math.hypot(a[0]-c[0],a[2]-c[2]);t=min(1,d/n)if n else 0;return[c[i]+t*(a[i]-c[i])for i in range(3)]
def main():
 scene=load(SC);doc=load(O/'public_chain_candidates.json');cases=[]
 for route in doc['routes']:
  ss=route['public_segment_slices']
  for i,(a,c)in enumerate(zip(ss,ss[1:])):
   if a['source_route_id']==c['source_route_id']:continue
   center=a['points_xyz_m'][1];pts=[shorten(a['points_xyz_m'][0],center),center,shorten(c['points_xyz_m'][1],center)];cases.append(dict(id=route['id']+':JUNCTION:'+str(i),route_id=route['id'],points_xyz_m=pts,source_segments=[a,c]))
  for i,s in enumerate(route['splices']):
   if s['kind']=='finite_public_lateral_splice':cases.append(dict(id=route['id']+':LATERAL:'+str(i),route_id=route['id'],points_xyz_m=[s['from_xyz_m'],s['to_xyz_m']],source_splice=s))

 for c in cases:c['polys']=b.ribbon([[p[0],p[2]]for p in c['points_xyz_m']],.6)
 wins=[p for c in cases for p in c['polys']];native={};cache={};bindings=[]
 for p in scene['common_instances']:
  a=scene['common_assets'][p['asset_key']];bb=a.get('bounds');py=p['position_m'][1]
  if bb is None:bb=cache.setdefault(a['render_path'],load(ROOT/a['render_path']))['bounds']
  wp=b.xform(b.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),p)
  nearby=[c for c in cases if any(geo.intersection_area(wp,w)>1e-8 for w in c['polys'])]
  if not nearby:continue
  mesh=cache.setdefault(a['render_path'],load(ROOT/a['render_path']));bindings.append(dict(id=p['id'],asset_key=p['asset_key'],cache=dict(path=a['render_path'],sha256=a['render_sha256']),position_m=p['position_m'],yaw_rad=p['yaw_rad']))
  for c in nearby:
   fmin=min(q[1]for q in c['points_xyz_m']);fmax=max(q[1]for q in c['points_xyz_m']);bodies=[b.xform(q,p)for q in slab_rectangles(mesh,fmin-py+.05,fmax-py+1.8)] if bb['max'][1]+py>fmin+.05 and bb['min'][1]+py<fmax+1.8 else[]
   for w in c['polys']:
    for j,q in enumerate(bodies):
     ar=geo.intersection_area(w,q)
     if ar>1e-7:c.setdefault('native_contacts',[]).append(dict(native_id=p['id'],body_piece=j,area_m2=ar))
  vs=[]
  for gr in mesh['groups']:
   for q in gr['quads']:
    if max(v[1]for v in q)-min(v[1]for v in q)>1e-8:continue
    fy=q[0][1]+py
    if not any(min(v[1]for v in c['points_xyz_m'])-.5<=fy<=max(v[1]for v in c['points_xyz_m'])+.5 for c in nearby):continue
    ny=(q[1][2]-q[0][2])*(q[2][0]-q[0][0])-(q[1][0]-q[0][0])*(q[2][2]-q[0][2])
    if ny<=0:continue
    poly=b.xform([[v[0],v[2]]for v in q],p)
    for tri in terrain.fan_upward([[x,fy,z]for x,z in poly]):vs.extend(tri)
  if vs:native['native:'+p['id']]=vs
 idx=Support(scene,wins,native);sides=SideIndex(scene,wins)
 for c in cases:
  checks=[terrain.audit_polygon(idx,w,None,grade_limit=1)for w in c['polys']];owners=[dict(id=c['id']+':'+str(i)+':'+str(j),polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'])for i,x in enumerate(checks)for j,r in enumerate(x['source_pieces'])];bank=sides.audit(owners);c['support_checks']=checks;c['bank_contacts']=bank['contacts'];c['missing_area_m2']=sum(x['missing_area_m2']for x in checks);c['passed']=all(x['passes_existing_surface']for x in checks)and not c.get('native_contacts')and not bank['contacts'];print(c['id'],c['passed'],'missing',c['missing_area_m2'],'native',len(c.get('native_contacts',[])),'bank',len(bank['contacts']),flush=True)
 write('public_junction_review.json',dict(scene=ref(SC),candidate_routes=ref(O/'public_chain_candidates.json'),actual_native_bindings=bindings,splices=cases,status='PASS'if all(c['passed']for c in cases)else'FAIL',limits=['Finite source support and clearance only; unchanged-controller full-chain replay remains required.']))
if __name__=='__main__':main()
