"""Separate retained native bottom holes from restorable ordinary-body vacancies."""
from . import geometry as g
from .design import HERE as SOURCE
from .allocate_backlands import OUT
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as tc
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles

def run():
 p=OUT/'missing_top_ownership.json';d=g.load(p);scene=g.load(g.R7);retired=set(g.load(SOURCE/'effective_city_manifest_r01.json')['replaced_placement_ids']);proj=g.load(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json')['instances'];inst={i['id']:i for i in scene['common_instances']};si=g.geo._SpatialIndex(16)
 for j,r in enumerate(proj):
  if r['id']not in retired:
   for q in r['native_owner_parts_xz_m']:si.add(j,q)
 cache={};occupied=[];left=[]
 for n,r in enumerate(d['unclassified']):
  poly=r['polygon_xz_m'];cuts=[]
  for j in si.candidates(poly):
   rec=proj[j];i=inst[rec['id']];key=i['asset_key'];a=scene['common_assets'][key]
   if key not in cache:
    lo=a['bounds']['min'][1];pitch=a.get('pitch_m',a.get('key',{}).get('pitch',.125)if isinstance(a.get('key'),dict)else .125);cache[key]=slab_rectangles(g.load(g.ROOT/a['render_path']),lo+.001,lo+min(.124,pitch-.001))
   local=cache[key];c=[i['position_m'][0],i['position_m'][2]];yaw=i['yaw_rad'];native=g.transform(local,c,yaw)
   for foot in native:
    q=tc.clean(g.geo.convex_intersection(poly,foot))
    if q:cuts.append(q);occupied.append(dict(ground_owner_id=r['ground_owner_id'],retained_native_id=i['id'],asset_key=key,render_sha256=a['render_sha256'],native_bottom_world_y_m=i['position_m'][1]+a['bounds']['min'][1],polygon_xz_m=q,area_m2=g.geo.polygon_area(q),restore_as_ground=False))
  for q in tc.subtract([poly],cuts):
   if g.geo.polygon_area(q)>1e-7:left.append(dict(ground_owner_id=r['ground_owner_id'],polygon_xz_m=q,area_m2=g.geo.polygon_area(q),status='HELD_UNCLASSIFIED_MISSING_R7_TOP'))
 out=dict(d,prior_missing_ownership=g.ref(p),retained_native_occupied_holes=occupied,unclassified=left);out['summary']=dict(d['summary'],retained_native_bottom_hole_area_m2=sum(r['area_m2']for r in occupied),unclassified_missing_area_m2=sum(r['area_m2']for r in left));g.write(OUT/'missing_top_ownership_final.json',out);print(out['summary'])
if __name__=='__main__':run()
