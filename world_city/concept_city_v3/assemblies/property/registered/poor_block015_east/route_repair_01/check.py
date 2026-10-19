"""Finite all-route water, actual native walking slabs, joins, courts and door checks."""
import json,math,sys
from pathlib import Path
from .author import HERE,BASE,ROOT,PLAN,ref,write,disc,digest,apply
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.registered_source.geometry import triangulate
from world_city.concept_city_v3.registered_source.author import Domain
sys.path.insert(0,str(ROOT/'world_city/concept_city_v3/validation'))
from check_landmark_access_candidate import slab_rectangles,transform

def run():
 p=json.loads((HERE/'effective_placements.json').read_text());base=json.loads(BASE.read_text());overlay=json.loads((HERE/'route_addendum.json').read_text());plan=json.loads(PLAN.read_text());assert apply(base,overlay)==p;issues=[];water=[];native=[];renders={};index=g._SpatialIndex(20)
 for wi,w in enumerate(plan['water_reservations']['finite_water_polygons']):
  for ti,poly in enumerate(triangulate(w['polygon_xz_m'])):water.append(dict(id=f'{w["surface_id"]}:{w.get("segment_index","polygon")}:{wi}:{ti}',polygon=poly))
 water_index=g._SpatialIndex(20)
 for i,w in enumerate(water):water_index.add(i,w['polygon'])
 def water_hits(poly):
  found=[]
  for i in water_index.candidates(poly):
   w=water[i];q=g.convex_intersection(poly,w['polygon']);area=g.polygon_area(q)
   if area>1e-7:found.append(dict(water_id=w['id'],area_m2=area,polygon_xz_m=q))
  return found
 for k,a in p['assets'].items():
  for kind in ('master','render'):assert ref(ROOT/a[kind+'_path'])['sha256']==a[kind+'_sha256']
  renders[k]=json.loads((ROOT/a['render_path']).read_text())
 for m in p['placements']:
  floor=2.5-m['position_m'][1]
  for j,poly in enumerate(slab_rectangles(renders[m['asset_key']],floor+.05,floor+1.85)):native.append(dict(id=m['id']+':slab:'+str(j),polygon=transform(poly,m)))
 for i,o in enumerate(native):index.add(i,o['polygon'])
 paths=[dict(id=r['id'],polys=r['reserved_connection_polygons_xz_m'],line=r['complete_proposed_connection_xz_m'],width=r['width_m']) for r in p['access_proposals']]+[dict(id=r['id'],polys=r['reserved_polygons_xz_m'],line=r['polyline_xz_m'],width=r['width_m']) for r in p['court_paths']+p['ground_service_paths']]
 counts=dict(routes=len(paths),rounded_joins=0,native_walking_slabs=len(native),water_triangles=len(water),actual_doors=len(p['access_proposals']),runtime_groups=len(p['placements']),foundation_regions=sum(len(m['terrain_exclusion_regions_xz_m']) for m in p['ownership_masks']))
 def check(poly,ident,kind):
  for hit in water_hits(poly):issues.append(dict(kind=kind+'_water_overlap',id=ident,**hit))
  for i in index.candidates(poly):
   o=native[i];area=g.polygon_area(g.convex_intersection(poly,o['polygon']))
   if area>1e-6:issues.append(dict(kind=kind+'_native_slab_overlap',id=ident,obstacle=o['id'],area_m2=area))
 for r in paths:
  for poly in r['polys']:check(poly,r['id'],'ribbon')
  for point in r['line'][1:-1]:check(disc(point,r['width']),r['id'],'round_join');counts['rounded_joins']+=1
 for c in p['courts']:check(c['polygon_xz_m'],c['id'],'court')
 for m in p['ownership_masks']:
  for poly in m['terrain_exclusion_regions_xz_m']:
   for hit in water_hits(poly):issues.append(dict(kind='native_foundation_water_overlap',id=m['owner_id'],**hit))
 fixed=json.loads((ROOT/p['baseline_native_pack']['path']).read_text());fixed=[m for m in fixed['placements'] if m['id'] not in p['replaced_placement_ids']]
 for r in paths:
  for poly in r['polys']+[disc(q,r['width']) for q in r['line'][1:-1]]:
   for m in fixed:
    if g.positive_area_overlap(poly,m['actual_outer_footprint_xz_m'],1e-7):issues.append(dict(kind='retained_native_envelope_overlap',route_id=r['id'],id=m['id']))
 for door in p['access_proposals']:
  a,b=door['cached_threshold_stub_xz_m']
  for hit in water_hits(g.road_ribbon(a,b,door['width_m'])):issues.append(dict(kind='native_threshold_stub_water_overlap',id=door['id'],**hit))
 new=overlay['route_replacements'][0]['replacement'];polys=new['reserved_connection_polygons_xz_m']+new['reserved_round_join_polygons_xz_m']
 for poly in polys:
  for m in p['component_placements']+fixed:
   if g.positive_area_overlap(poly,m['actual_outer_footprint_xz_m'],1e-7):issues.append(dict(kind='changed_route_outer_envelope_overlap',id=m['id']))
 for door in p['access_proposals']:
  assert door['actual_cached_threshold_evidence'] and abs(door['actual_door_xyz_m'][1]-2.5)<1e-9
  original=next(r for r in base['access_proposals'] if r['id']==door['id'])
  for k in ('actual_door_xyz_m','threshold_lip_xyz_m','cached_threshold_stub_xz_m','actual_runtime_door_local_xyz_m','render_sha256'):assert door[k]==original[k]
 oldhits=[h for poly in overlay['route_replacements'][0]['original']['reserved_connection_polygons_xz_m'] for h in water_hits(poly)];assert sum(h['area_m2'] for h in oldhits)>1
 road=next(r for r in plan['roads'] if r['id']=='EAST_RADIAL');a,b=road['polyline_xz_m'][45:47];end=new['complete_proposed_connection_xz_m'][-1];landing=disc(end,1.8);assert Domain([g.road_ribbon(a,b,road['width_m'])]).contains(landing);assert not water_hits(landing)
 ground=json.loads((ROOT/p['ground_source']['path']).read_text())
 for gr in p['ground_ownership_records']:
  for poly in gr['polygons_xz_m']:
   for hit in water_hits(poly):issues.append(dict(kind='private_ground_water_overlap',id=gr['id'],**hit))
 report=dict(schema='riverstone.b015_recovery_finite_access_check.v1',status='pass_finite_water_and_native_static_clearance' if not issues else 'failed',base_pack=ref(BASE),effective_pack=ref(HERE/'effective_placements.json'),addendum=ref(HERE/'route_addendum.json'),checker=ref(Path(__file__)),counts=counts,issues=issues,old_route_water_conflicts=oldhits,old_water_area_m2=sum(h['area_m2'] for h in oldhits),new_route_length_m=overlay['length_m'],public_landing_polygon_xz_m=landing,public_lane_same_floor_m=2.5,geometry_proof=ref(HERE.parent/'actual_geometry_proof.json'),retained_water_ground_area_m2=next(r['area_m2'] for r in ground['ownership_ledger'] if r['category']=='retained_finite_water'),limits=['Exact finite horizontal water and native slab checks only.','Current terrain ownership must bind new ribbons and rounded join; no capsule or controller validation.','Rear-ground facility recipes remain source-only.'])
 write(HERE/'checks.json',report);print(json.dumps(dict(status=report['status'],counts=counts,issues=issues,old_water_area_m2=report['old_water_area_m2']),indent=2));return report
if __name__=='__main__':raise SystemExit(2 if run()['issues'] else 0)
