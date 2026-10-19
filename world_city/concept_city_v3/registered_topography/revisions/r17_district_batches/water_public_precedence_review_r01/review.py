import json,math
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
from ..final_profile_audit_r01.exact_clip import clip
HERE=Path(__file__).resolve().parent
R18=a.HERE.parent/'public_corridors_r18/finite_field_candidate_r07_native_bound.json';WATER=a.CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/fields.json';REQ=a.HERE/'contour_bulk_r01/exact_public_reservations.json';SCENE=a.CITY/'evidence/r8_district_61_assembly_preflight_r01/scene.json'
def run():
 req=[r for r in json.loads(REQ.read_bytes())['entries']if r['holding_id']=='BLOCK_005:R8_C006'][0];w=json.loads(WATER.read_bytes());water=[dict(t,id=p['id']+':'+str(i),profile_id=p['id'])for p in w['profiles']for i,t in enumerate(p['triangles'])];wi=index(water);public=json.loads(R18.read_bytes())['records'];pi=index(public);pieces=[]
 for q in req['public_union_parts_xz_m']:
  for j in wi.candidates(q):
   s=water[j];p=clip(q,s['polygon_xz_m'])
   if a.geo.polygon_area(p)<1e-10:continue
   for k in pi.candidates(p):
    r=public[k];z=clip(p,r['polygon_xz_m']);ar=a.geo.polygon_area(z)
    if ar<1e-10:continue
    err=max(abs(a.common.height(r['plane_y_xz_m'],x)-a.common.height(s['plane_y_xz_m'],x))for x in z)
    pieces.append(dict(id='WATER_R18:'+str(len(pieces)),polygon_xz_m=z,area_m2=ar,r18_id=r['id'],r18_plane_y_xz_m=r['plane_y_xz_m'],water_id=s['id'],water_plane_y_xz_m=s['plane_y_xz_m'],maximum_source_height_difference_m=err,source_r18_record=r))
 source_profile=a.HERE/'public_owner_completion_r06/BLOCK_005_R8_C003_profile.json';conflicts=json.loads(source_profile.read_bytes())['result']['conflicts'];windows=[[[x-.02,z-.02],[x+.02,z-.02],[x+.02,z+.02],[x-.02,z+.02]]for c in conflicts for x,z in[c['point_xz_m']]];scene=json.loads(SCENE.read_bytes());ix=a.TriangleIndex(scene,[r['polygon_xz_m']for r in pieces]+windows);actual=[];boundary=[]
 for c,w in zip(conflicts,windows):
  hits=[dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=r['intersection_polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],height_at_shared_point_m=a.common.height(r['plane_y_xz_m'],c['point_xz_m']))for r in ix.covering(w)];boundary.append(dict(fixed_contact=c,actual_current_top_hits=hits))
 for p in pieces:
  hits=[]
  for r in ix.covering(p['polygon_xz_m']):
   q=r['intersection_polygon_xz_m'];we=max(abs(a.common.height(r['plane_y_xz_m'],x)-a.common.height(p['water_plane_y_xz_m'],x))for x in q);re=max(abs(a.common.height(r['plane_y_xz_m'],x)-a.common.height(p['r18_plane_y_xz_m'],x))for x in q)
   hits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=q,area_m2=a.geo.polygon_area(q),plane_y_xz_m=r['plane_y_xz_m'],water_plane_error_m=we,r18_plane_error_m=re))
  actual.append(dict(overlap_id=p['id'],hits=hits))
 summary=dict(source_overlap_m2=sum(p['area_m2']for p in pieces),source_maximum_difference_m=max((p['maximum_source_height_difference_m']for p in pieces),default=0.),actual_water_matched_area_sum_m2=sum(h['area_m2']for r in actual for h in r['hits']if h['water_plane_error_m']<1e-6),actual_old_r18_matched_area_sum_m2=sum(h['area_m2']for r in actual for h in r['hits']if h['r18_plane_error_m']<1e-6 and h['water_plane_error_m']>=1e-6),actual_other_area_sum_m2=sum(h['area_m2']for r in actual for h in r['hits']if min(h['water_plane_error_m'],h['r18_plane_error_m'])>=1e-6))
 write(HERE/'overlap_review.json',dict(request_holding_id=req['holding_id'],named_public_road_id=req['named_public_road_id'],source_refs=[dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))for p in[R18,WATER,REQ,SCENE]],source_overlaps=pieces,actual_scene_comparison=actual,current_boundary_contacts=boundary,source_profile=dict(path=str(source_profile.relative_to(a.ROOT)),sha256=a.sha(source_profile)),summary=summary,activation=False));print(summary,flush=True)
if __name__=='__main__':run()
