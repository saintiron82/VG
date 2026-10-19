"""Read-only source-hole classification against actual R04 tops/native geometry."""
import json,math,time,collections
from .height_field import HERE
from . import finite_geometry_r03 as g
from ..r17_district_batches import author as a
from world_city.concept_city_v3.traversal_r5 import prepare as b

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main():
 start=time.monotonic();review=HERE/'public_top_r01/top_review.json';scene_path=a.CITY/'evidence/r8_district_r04/scene.json';assert a.sha(scene_path)=='3c63a21f4490e1dada6be34428dc2d1ffacd326d8f34b2deee81e378ab6680d7';scene=json.loads(scene_path.read_bytes());proof=json.loads(review.read_bytes());holes=[r for r in proof['failures']if r['kind']=='source_hole'];owners=json.loads((HERE/'public_top_r01/physical_owners.json').read_bytes());print('owners schema',type(owners),str(owners)[:100],flush=True)
 if isinstance(owners,dict):owners=owners.get('owners',owners.get('records'))
 byowner={r['id']:r for r in owners};windows=[p for r in holes for p in r['polygons_xz_m']];top=a.TriangleIndex(scene,windows);wi=a.geo._SpatialIndex(8)
 for i,p in enumerate(windows):wi.add(i,p)
 wboxes=[a.bounds(p)for p in windows];surfaces=[];ni=a.geo._SpatialIndex(4);native_refs=[];natives=[];cache={}
 def add(rec):ni.add(len(surfaces),rec['polygon_xz_m']);surfaces.append(rec)
 for p in scene['common_instances']:
  asset=scene['common_assets'][p['asset_key']];bounds=asset.get('bounds')
  if bounds is None:
   rp=a.ROOT/asset['render_path'];assert a.sha(rp)==asset['render_sha256']
   if p['asset_key']not in cache:cache[p['asset_key']]=json.loads(rp.read_bytes());native_refs.append(ref(rp))
   bounds=cache[p['asset_key']]['bounds']
  bb=b.instance_bounds(p,bounds);poly=[[bb[0],bb[1]],[bb[2],bb[1]],[bb[2],bb[3]],[bb[0],bb[3]]]
  if not any(a.intersects(bb,wboxes[i])for i in wi.candidates(poly)):continue
  rp=a.ROOT/asset['render_path'];assert a.sha(rp)==asset['render_sha256']
  if p['asset_key']not in cache:cache[p['asset_key']]=json.loads(rp.read_bytes());native_refs.append(ref(rp))
  render=cache[p['asset_key']];natives.append(dict(id=p['id'],asset_key=p['asset_key'],collision_policy=p.get('collision_policy')))
  for gi,group in enumerate(render['groups']):
   for qi,q in enumerate(group['quads']):
    world=[b.transform(v,p)for v in q]
    if a.normal_y(world[:3])<=1e-12:continue
    poly=[[v[0],v[2]]for v in world];bb=a.bounds(poly)
    if not any(a.intersects(bb,wboxes[i])for i in wi.candidates(poly)):continue
    add(dict(id=p['id']+':UP:'+str(gi)+':'+str(qi),kind='actual_native_upface',native_instance_id=p['id'],asset_key=p['asset_key'],polygon_xz_m=poly,plane_y_xz_m=a.common.plane(world[:3]),vertices_xyz_m=world,render_sha256=asset['render_sha256'],collision_policy=p.get('collision_policy')))
 for contract in scene.get('collision_contracts',[]):
  for j,t in enumerate(contract.get('add_triangles_world_xyz_m',[])):
   if abs(a.normal_y(t))<=1e-12:continue
   poly=[[v[0],v[2]]for v in t];bb=a.bounds(poly)
   if any(a.intersects(bb,wboxes[i])for i in wi.candidates(poly)):add(dict(id=contract['id']+':TRI:'+str(j),kind='actual_declared_collision_profile',polygon_xz_m=poly,plane_y_xz_m=a.common.plane(t),vertices_xyz_m=t))
 caps_path=a.CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json';capdata=json.loads(caps_path.read_bytes());caprows=[dict(id=r['property_id']+':CUT:'+str(j),polygon_xz_m=c['polygon_xz_m'],native_top_y_m=max(v['world_y_interval_m'][1]for v in c['cells']))for r in capdata['records']for j,c in enumerate(r['candidate_columns'])];water=scene['terrain_contract']['water_domain_polygons'];rows=[]
 for n,h in enumerate(holes):
  owner=byowner[h['owner_id']];plane=owner['plane_y_xz_m'];tops=[];native=[];wet=[];cuts=[]
  for poly in h['polygons_xz_m']:
   for i in top.index.candidates(poly):
    r=top.rows[i];q=g.clip(poly,r['polygon_xz_m'])
    if q:tops.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m'],area_m2=g.area(q),delta_y_range_m=[min(a.common.height(r['plane_y_xz_m'],v)-a.common.height(plane,v)for v in q),max(a.common.height(r['plane_y_xz_m'],v)-a.common.height(plane,v)for v in q)]))
   for i in ni.candidates(poly):
    r=surfaces[i];q=g.clip(poly,r['polygon_xz_m'])
    if q:native.append(dict(id=r['id'],kind=r['kind'],native_instance_id=r.get('native_instance_id'),polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m'],area_m2=g.area(q),delta_y_range_m=[min(a.common.height(r['plane_y_xz_m'],v)-a.common.height(plane,v)for v in q),max(a.common.height(r['plane_y_xz_m'],v)-a.common.height(plane,v)for v in q)]))
   for r in water:
    q=g.clip(poly,r['polygon_xz_m'])
    if q:wet.append(dict(surface_id=r['surface_id'],polygon_xz_m=q,area_m2=g.area(q)))
   for r in caprows:
    q=g.clip(poly,r['polygon_xz_m'])
    if q:cuts.append(dict(id=r['id'],polygon_xz_m=q,area_m2=g.area(q),native_top_y_m=r['native_top_y_m']))
  current_cover=g.union([r['polygon_xz_m']for r in tops]);native_cover=g.union([r['polygon_xz_m']for r in native if max(abs(v)for v in r['delta_y_range_m'])<=.25]);remaining=g.subtract(h['polygons_xz_m'],current_cover+native_cover+[r['polygon_xz_m']for r in cuts]+[r['polygon_xz_m']for r in wet]);area_left=math.fsum(g.area(p)for p in remaining)
  rows.append(dict(owner_id=h['owner_id'],source_hole_area_m2=h['area_m2'],hole_polygons_xz_m=h['polygons_xz_m'],candidate_plane_y_xz_m=plane,current_rendered_top_pieces=tops,actual_native_and_contract_pieces=native,water_pieces=wet,authorized_access_skin_cut_pieces=cuts,unclassified_polygons_xz_m=remaining,unclassified_area_m2=area_left,status='SOURCE_HOLE_CLASSIFIED_PROVENANCE_ONLY'if area_left<=1e-7 else'FINITE_UNCOVERED_RESTORATION_OR_OWNERSHIP_DECISION_REQUIRED'))
  if n%25==0:print('classified',n,'seconds',time.monotonic()-start,flush=True)
 out=dict(schema='riverstone.r18.actual_source_hole_classification.v1',status='CLASSIFICATION_ONLY_NO_FILL_ACTIVATED',sources=[ref(review),ref(scene_path),ref(HERE/'public_top_r01/physical_owners.json'),ref(caps_path)]+native_refs,code_sha256=a.sha(__file__),actual_native_candidates=natives,actual_upfaces_indexed=len(surfaces),current_top_triangles_indexed=len(top.rows),rows=rows,summary=dict(holes=len(rows),source_hole_area_m2=math.fsum(r['source_hole_area_m2']for r in rows),unclassified_count=sum(r['unclassified_area_m2']>1e-7 for r in rows),unclassified_area_m2=math.fsum(r['unclassified_area_m2']for r in rows),seconds=time.monotonic()-start),scope='Every current top/native/profile overlap retains its actual plane and height difference. Near-height native union uses a labelled 0.25m diagnostic band only, never an acceptance tolerance or a support replacement. Restoration, removal, and co-ownership remain explicit decisions.',activation=False)
 target=HERE/'top_hole_classification_r02.json';target.write_text(json.dumps(out,separators=(',',':'))+'\n');print(out['summary'],ref(target),flush=True)
if __name__=='__main__':main()
