import json,time,math
from .solve import HERE,SOURCE,write,ref
from .. import author as a
from ..bounded_profile_r01 import finite
from ..final_profile_audit_r01 import exact_clip
from ...r01_ownership import author as ownership

def run():
 src=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/final_b04_entry_clearance_r01/source_candidates.json';data=json.loads(src.read_bytes());c=data['records'][0];hid=c['holding_id'];old=json.loads((SOURCE/'profiles'/f"{hid.replace(':','_')}.json").read_bytes());review=json.loads((SOURCE/'actual_public_fringe_review_r01.json').read_bytes());faces={};roads=[];ri=a.geo._SpatialIndex(8)
 for r in json.loads(a.PLAN_PATH.read_bytes())['roads']:
  for p in ownership.corridor(r['polyline_xz_m'],r['width_m']):ri.add(len(roads),p);roads.append(p)
 for row in review['rows']:
  if row['holding_id']!=hid:continue
  for part in row['pieces']:
   for r in part['current_top_pieces']:
    if r['material']=='road' and a.geo.polygon_area(exact_clip.clip(part['polygon_xz_m'],r['polygon_xz_m']))>1e-10:faces[r['material'],r['triangle_index']]=r
 public=c['fixed_public_regions'][:];extra=[]
 for (mat,idx),r in faces.items():
  parts=[q for j in ri.candidates(r['polygon_xz_m'])if a.geo.polygon_area(q:=exact_clip.clip(r['polygon_xz_m'],roads[j]))>1e-10]
  for j,q in enumerate(a.common.disjoint_union(parts)):
   extra.append(dict(id=f'{hid}:ACTUAL_INCIDENTAL_PUBLIC:{mat}:{idx}:{j}',polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m'],source_kind='actual_retained_current_top',source_scene=review['current_scene'],source_material=mat,source_triangle_index=idx,source_triangle_sha256=r['source_triangle_sha256']))
 public+=extra;flat=[dict(id=hid+':FLAT_CORE:'+str(i),polygon_xz_m=p,plane_y_xz_m=[0,0,c['floor_y_m']])for i,p in enumerate(c['flat_owner_polygons_xz_m'])];domains=a.common.subtract(c['profile_domain_polygons_xz_m'],[r['polygon_xz_m']for r in public]);start=time.monotonic();result=finite.solve(domains,flat+public,lambda p:c['floor_y_m'],pitch=1.,limit=.15,seam_points=[p for r in flat+public for p in r['polygon_xz_m']]);out=dict(holding_id=hid,source=ref(src),candidate=c,candidate_index=0,private_domain_polygons_xz_m=domains,public_fixed_regions=public,court_fixed_regions=flat,result=result,grade_limit=.15,incidental_current_public_regions=extra,elapsed_s=time.monotonic()-start,activation=False);write('BLOCK_004_R8_C004_rebound_15.json',out);print(result['status'],result.get('maximum_gradient'),result.get('conflicts'),flush=True)
if __name__=='__main__':run()
