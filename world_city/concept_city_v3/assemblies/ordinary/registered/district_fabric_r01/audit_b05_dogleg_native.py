from . import geometry as g
from .activate_backlands_subset import ActualNative,MaskIndex
from .refit_held_private_entries import rows
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import public_domain
from .refit_b05_native_junction_entry import FIELDS,LAYOUT
import copy,time

def run():
 p=g.HERE/'b05_native_junction_entry_r04/source_candidates.json';d=g.load(p);c=d['candidates'][0];scene_path=g.CITY/'evidence/r8_district_61_assembly_preflight_r01/scene.json';sc=g.load(scene_path);ret=set(d['retired_source_ids']);sc['common_instances']=[p for p in sc['common_instances']if p['id']not in ret];sc['boxes']=[p for p in sc['boxes']if p['id']not in{i+':owned_foundation'for i in ret}];f=next(r for r in g.load(FIELDS)['profiles']if r['id']=='NORTH_SHARED_JUNCTION');pub=[r['polygon_xz_m']for r in public_domain.records()]+f['polygons_xz_m'];private=a.common.subtract(c['polygons_xz_m'],pub);ni=ActualNative(sc);hits=ni.hit(private,c['floor_y_m']+.05,15.85+2.0);special=g.load(g.HERE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];sp=MaskIndex(rows(special,'APPROVED_SPECIAL_RESERVATION')).hit(private);report=dict(source=g.ref(p),candidate_index=0,actual_scene=g.ref(scene_path),private_route_polygons_xz_m=private,hypothetically_retired_ids=sorted(ret),retained_actual_native_clear_volume_contacts=hits,special_reservation_contacts=sp,source_boundary_openings=c['native_projection_contacts'],passed=not hits and not sp,scope='Private ribbon only; named public support columns are excluded because their exact walking planes are owned by R18. Final finite heights, public seams and retained terrain sides remain R17 gates.');g.write(p.parent/'candidate0_native_and_reservation_audit.json',report);print('contacts',hits,'special',sp,flush=True);print(g.ref(p.parent/'candidate0_native_and_reservation_audit.json'))
if __name__=='__main__':run()
