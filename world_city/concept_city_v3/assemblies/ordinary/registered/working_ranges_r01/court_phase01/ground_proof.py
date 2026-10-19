"""Bounded exact corrected-R6 triangle evidence; no terrain or scene export."""
from .author import *
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges.frozen_r6 import load_scene,SurfaceIndex,bounds

def run():
 p=load(HERE/'resolved_placements.json');h=load(HERE/'terrain_handoff.json');s=load(HERE/'source_plan.json');idx=SurfaceIndex(load_scene(),windows=[bounds(c['source']['polygon_xz_m'])for c in s['courts']],margin=1);proofs=[]
 queries=[dict(id=b['id'],polygon_xz_m=b['polygon_xz_m'],kind='native_bearing')for b in h['native_bearing_owners']]+[dict(id=c['id'],polygon_xz_m=c['source']['polygon_xz_m'],kind='court_ground')for c in s['courts']]
 for q in queries:
  pieces=idx.cover(q['polygon_xz_m']);area=geo.polygon_area(q['polygon_xz_m']);covered=sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in pieces);heights=[idx.height(r,*v)for r in pieces for v in r['intersection_polygon_xz_m']];assert abs(area-covered)<1e-7,(q['id'],area,covered);assert all(abs(y-2.5)<1e-8 for y in heights),(q['id'],heights)
  proofs.append(dict(**q,area_m2=area,covered_area_m2=covered,min_y_m=min(heights),max_y_m=max(heights),fully_covered=True,pieces=pieces))
 original=load(PARENT/'freeze_manifest.json');unchanged=[ref(ROOT/f['path'])==f for f in original['files']];assert all(unchanged)
 o=dict(schema='riverstone.court_phase01.ground_proof.v1',corrected_r6=ref(R6),placement_pack=ref(HERE/'resolved_placements.json'),terrain_handoff=ref(HERE/'terrain_handoff.json'),method='Exact clipped upward rendered triangles from corrected R6; bounded to the two court boxes',proofs=proofs,all_actual_ground_exactly_2_5=True,all_native_bearings_covered=True,unchanged_parent_sealed_files=len(unchanged),parent_manifest=ref(PARENT/'freeze_manifest.json'),original_parent_files_unchanged=True);write(HERE/'ground_proof.json',o);print(json.dumps({k:v for k,v in o.items()if k not in('proofs',)},indent=2));return o
if __name__=='__main__':run()
