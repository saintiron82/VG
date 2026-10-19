"""Preserve water and every positive-area submerged/bank interface."""
import json,math,time
from .. import author as a,side_clearance
from .source_preflight import HERE,write

def clip3(tri,p):
 out=tri;sgn=1 if a.geo.signed_polygon_area(p)>0 else-1
 for u,v in zip(p,p[1:]+p[:1]):out=side_clearance.halfspace(out,lambda q:sgn*a.geo._cross(u,v,[q[0],q[2]]))
 return out

def run():
 t=time.monotonic();scene=a.load_scene();water=[r['polygon_xz_m']for r in scene['terrain_contract']['water_domain_polygons']];wi=a.geo._SpatialIndex(16)
 for i,p in enumerate(water):wi.add(i,p)
 patch=json.loads((HERE/'candidate_scene_patch.json').read_bytes());owners=json.loads((HERE/'owners.json').read_bytes())['owners'];report=json.loads((HERE/'composition_report.json').read_bytes());hits=[];bankchanges=[]
 for o in owners:
  for i in wi.candidates(o['polygon_xz_m']):
   q=a.clip(o['polygon_xz_m'],water[i])
   if q and(a0:=a.geo.polygon_area(q))>1e-7:hits.append(dict(owner_id=o['id'],water_index=i,area_m2=a0,polygon_xz_m=q))
 for r in patch['surface_edits']:
  if r['material']!='bank':continue
  tr=scene['surfaces']['bank'][r['triangle_index']*3:r['triangle_index']*3+3];p=[[v[0],v[2]]for v in tr]
  for i in wi.candidates(p):
   before=side_clearance.area3d(clip3(tr,water[i]));after=sum(side_clearance.area3d(clip3(q,water[i]))for q in r['replacement_triangles_xyz_m'])
   if before-after>1e-7:bankchanges.append(dict(source_triangle_index=r['triangle_index'],water_index=i,removed_wet_bank_area_m2=before-after))
 result=dict(scene_patch_sha256=a.sha(HERE/'candidate_scene_patch.json'),water_array_edits=[r['triangle_index']for r in patch['surface_edits']if r['material']=='water'],dry_owner_wet_overlaps=hits,wet_bank_removed=bankchanges,elapsed_s=time.monotonic()-t,status='PASS'if not(hits or bankchanges)else'FAILED',activation=False);write('water_review.json',result);print(result,flush=True)
if __name__=='__main__':run()
