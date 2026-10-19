"""Bound finite incidental current-public contacts missed by terminal-only inputs."""
import json,math,time
from pathlib import Path
from .. import author as a
from ..coherent_final24_r01.prepare import ref,load
from ..bounded_profile_r01 import finite
from ..final_profile_audit_r01 import exact_clip
from ...r01_ownership import author as ownership
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'coherent_final24_r01'
def write(name,data):
 p=HERE/name;assert not p.exists(),str(p);p.write_text(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n')
def run():
 review=json.loads((SOURCE/'actual_public_fringe_review_r01.json').read_bytes());roadidx=a.geo._SpatialIndex(8);roads=[]
 for r in json.loads(a.PLAN_PATH.read_bytes())['roads']:
  for p in ownership.corridor(r['polyline_xz_m'],r['width_m']):roadidx.add(len(roads),p);roads.append(dict(road_id=r['id'],polygon_xz_m=p))
 for hid in ['BLOCK_003:R8_C001','BLOCK_006:R8_C001','BLOCK_008:R8_C001']:
  start=time.monotonic();old=json.loads((SOURCE/'profiles'/f"{hid.replace(':','_')}.json").read_bytes());faces={}
  for row in review['rows']:
   if row['holding_id']!=hid:continue
   for part in row['pieces']:
    for r in part['current_top_pieces']:
     if r['material']=='road' and a.geo.polygon_area(exact_clip.clip(part['polygon_xz_m'],r['polygon_xz_m']))>1e-10:faces[r['material'],r['triangle_index']]=r
  additions=[]
  for (mat,idx),r in faces.items():
   parts=[]
   for j in roadidx.candidates(r['polygon_xz_m']):
    q=exact_clip.clip(r['polygon_xz_m'],roads[j]['polygon_xz_m'])
    if a.geo.polygon_area(q)>1e-10:parts.append(q)
   for j,q in enumerate(a.common.disjoint_union(parts)):
    additions.append(dict(id=f'{hid}:ACTUAL_INCIDENTAL_PUBLIC:{mat}:{idx}:{j}',polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m'],source_kind='actual_retained_current_top',source_scene=review['current_scene'],source_material=mat,source_triangle_index=idx,source_triangle_sha256=r['source_triangle_sha256']))
  public=old['public_fixed_regions']+additions;flat=old['court_fixed_regions'];domains=a.common.subtract(old['private_domain_polygons_xz_m'],[r['polygon_xz_m']for r in additions]);fixed=flat+public
  output=dict(old,prior_profile=ref(SOURCE/'profiles'/f"{hid.replace(':','_')}.json"),public_fixed_regions=public,private_domain_polygons_xz_m=domains,incidental_current_public_regions=additions,activation=False)
  print('Solving',hid,'new public pieces',len(additions),'domains',len(domains),flush=True)
  for limit in [.12,.15,.25]:
   result=finite.solve(domains,fixed,lambda p:old['candidate']['floor_y_m'],pitch=1.,limit=limit,seam_points=[p for r in fixed for p in r['polygon_xz_m']]);value=dict(output,result=result,grade_limit=limit,elapsed_s=time.monotonic()-start);name=hid.replace(':','_')+'_'+str(int(limit*100))+'.json';write(name,value);print(hid,limit,result['status'],result.get('maximum_gradient'),len(result.get('conflicts',[])),flush=True)
   if result['status']=='PASSED_FINITE_TRIANGLE_GRADE' or result['status']=='INCOMPATIBLE_FIXED_REGIONS':break
if __name__=='__main__':run()
