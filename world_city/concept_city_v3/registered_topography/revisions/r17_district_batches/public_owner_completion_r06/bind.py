"""Resolve the entire requested frontage by current physical owner priority."""
import json,math,time
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
from ..final_profile_audit_r01.exact_clip import clip,difference
from ..public_dependency_review_r01 import review
HERE=Path(__file__).resolve().parent
REQUEST=a.HERE/'contour_bulk_r01/exact_public_reservations.json';CURRENT=a.HERE.parent/'public_corridors_r18/finite_field_candidate_r07_native_bound.json';WATER=a.CITY/'assemblies/waterworks/registered_water_completion_r01';FIELDS=WATER/'approaches_r02/fields.json';DECKS=WATER/'crossing_interfaces.json';RECOVERED=a.CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json'
IDS=['BLOCK_005:R8_C003','BLOCK_005:R8_C006','BLOCK_005:R8_C008','BLOCK_008:R8_C003']
def run():
 requests=[e for e in json.loads(REQUEST.read_bytes())['entries']if e['holding_id']in IDS];water=[]
 for c in json.loads(DECKS.read_bytes())['crossings']:water.append(dict(id=c['id']+':ACTUAL_NATIVE_TRAFFIC_TOP',polygon_xz_m=c['traffic_polygon_xz_m'],plane_y_xz_m=[0,0,c['deck_top_y_m']],source_kind='actual_common_native_traffic_top',source_interface_id=c['id']))
 for p in json.loads(FIELDS.read_bytes())['profiles']:
  for i,t in enumerate(p['triangles']):water.append(dict(id=p['id']+':TRIANGLE:'+str(i),polygon_xz_m=t['polygon_xz_m'],plane_y_xz_m=t['plane_y_xz_m'],source_kind='sealed_water_approach_field',source_triangle_sha256=a.canonical_sha(t['vertices_xyz_m'])))
 current=[dict(r,source_kind='current_r07_public_field')for r in json.loads(CURRENT.read_bytes())['records']];inst=[];rec=json.loads(RECOVERED.read_bytes())
 for kind in ['approaches','landings']:
  for i,t in enumerate(rec[kind]['triangles']):inst.append(dict(id='ACTUAL_INSTITUTION:'+kind+':'+str(i),polygon_xz_m=t['polygon_xz_m'],plane_y_xz_m=a.common.plane(t['triangle_xyz_m']),source_kind='retained_actual_institutional_top',source_triangle_sha256=a.canonical_sha(t['triangle_xyz_m']),source_json_pointer='/'+kind+'/triangles/'+str(i)))
 scene=json.loads(review.R04.read_bytes());tops=a.TriangleIndex(scene,[p for e in requests for p in e['public_union_parts_xz_m']]);old=[dict(r,id='R04_RETAINED:'+r['material']+':'+str(r['triangle_index']),source_kind='actual_unchanged_retained_r04_top')for r in tops.rows];layers=[(water,index(water)),(current,index(current)),(inst,index(inst)),(old,index(old))];out=[]
 for e in requests:
  start=time.monotonic();regions=[];uncovered=[]
  for p in e['public_union_parts_xz_m']:
   rem=[p]
   for layer,ix in layers:
    for j in sorted(ix.candidates(p)):
     if not rem:break
     r=layer[j];nextrem=[]
     for q in rem:
      z=clip(q,r['polygon_xz_m']);ar=a.geo.polygon_area(z)
      if ar>1e-12:
       regions.append(dict(r,id=r['id']+':CLIP:'+str(len(regions)),polygon_xz_m=z,gradient=math.hypot(*r['plane_y_xz_m'][:2])));nextrem+=difference(q,r['polygon_xz_m'])
      else:nextrem.append(q)
     rem=nextrem
   uncovered+=rem
  area=sum(a.geo.polygon_area(p)for p in uncovered);row=dict(holding_id=e['holding_id'],public_road_id=e['named_public_road_id'],profile_regions=regions,remaining_polygons_xz_m=uncovered,uncovered_area_m2=area,status='SOURCE_COVERAGE_READY'if area<1e-7 else'HELD_FINITE_OWNER_GAP');out.append(row);print(e['holding_id'],len(regions),'gap',area,'seconds',time.monotonic()-start,flush=True)
 refs=[dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))for p in[REQUEST,CURRENT,FIELDS,DECKS,RECOVERED,review.R04]];write(HERE/'actual_public_inputs.json',dict(entries=out,source_refs=refs,priority=['actual native traffic deck and sealed water approach planes','current R07 public field','actual retained institutional landings/approaches','unchanged actual R04 tops outside all prior owners'],activation=False))
if __name__=='__main__':run()
