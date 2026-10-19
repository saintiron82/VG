"""Classify all four old 1.5 m2 R18 estate terminal holes against this batch."""
from build_ground_patch import *
OUT=Path(__file__).resolve().parent

def subtract(ps,masks):
 return terrain.common.subtract([q for p in ps if(q:=terrain.common.clean(p))],[q for p in masks if(q:=terrain.common.clean(p))])

def main():
 source=CITY/'registered_topography/revisions/public_corridors_r18/noble_terminal_source_holes_r01.json';data=load(source);pack=load(OUT/'resolved_native_candidate.json');ground=load(OUT/'native_ground_candidate_audit.json');routes=load(OUT/'runtime_routes.json');groups=[]
 for eid in('E4','E5','E6','E7'):
  old=eid+':registered_r1:infrastructure';rows=[dict(r['source_hole'],candidate_plane_y_xz_m=r['expected_public_owner']['plane_y_xz_m'])for g in data['groups']if g['property_id']==eid for r in g['records']];route=next(r for r in routes['routes']if r['owner_id']==eid);tops=load(ROOT/route['physical_top']['path'])['top_pieces'];native=[r for r in ground['new_native_upward_faces']if r['native_id']==route['native_fine_id']];pieces=[];restore=[];profile_deltas=[];uncontracted=[];stale_restorations=[]
  for row in rows:
   for q in row['hole_polygons_xz_m']:
    actual=[]
    for r in native:
     pp=geo.convex_intersection(q,r['polygon_xz_m'])
     if geo.polygon_area(pp)>1e-8:actual.append(pp)
    owned=[]
    for r in tops:
     pp=geo.convex_intersection(q,r['polygon_xz_m'])
     if geo.polygon_area(pp)<1e-8:continue
     owned.append(pp);deltas=[terrain.common.height(r['plane_y_xz_m'],v)-terrain.common.height(row['candidate_plane_y_xz_m'],v)for v in pp];profile_deltas+=deltas;pieces.append(dict(r,polygon_xz_m=pp,public_source_owner_id=row['owner_id'],candidate_R18_plane_y_xz_m=row['candidate_plane_y_xz_m'],physical_minus_current_R18_y_range_m=[min(deltas),max(deltas)]))
    for pp in subtract(actual,owned):
     if geo.polygon_area(pp)>1e-8:uncontracted.append(pp)
    for pp in subtract([q],actual):
     if geo.polygon_area(pp)>1e-8:restore.append(dict(polygon_xz_m=pp,plane_y_xz_m=row['candidate_plane_y_xz_m'],public_source_owner_id=row['owner_id'],new_ground_owner='R18_PUBLIC_FIELD'))
    for r in ground['restored_old_native_ground']:
     ar=geo.intersection_area(q,r['polygon_xz_m'])
     if ar>1e-8:stale_restorations.append(dict(restored_id=r['id'],area_m2=ar))
  groups.append(dict(owner_id=eid,old_native_instance_id=old,old_native_retired=old in pack['replacement_ledger']['existing_native_placements_removed'],source_hole_row_count=len(rows),source_hole_area_m2=sum(geo.polygon_area(q)for r in rows for q in r['hole_polygons_xz_m']),new_physical_top_pieces=pieces,public_ground_restoration_pieces=restore,new_native_without_continuous_contract=uncontracted,obsolete_height_restoration_contacts=stale_restorations,physical_minus_current_R18_range_m=[min(profile_deltas,default=0),max(profile_deltas,default=0)],public_restoration_area_m2=sum(geo.polygon_area(r['polygon_xz_m'])for r in restore),physical_native_area_m2=sum(geo.polygon_area(r['polygon_xz_m'])for r in pieces),pass_=not uncontracted and not stale_restorations and old in pack['replacement_ledger']['existing_native_placements_removed']))
 out=dict(status='PASS_FOUR_TERMINAL_OWNERSHIP_R18_RESTORATION_PENDING'if all(r['pass_']for r in groups)else'HELD_TERMINAL_NOTCH_FAILURE',source=ref(source),native_pack=ref(OUT/'resolved_native_candidate.json'),collision_contracts=ref(OUT/'collision_contracts.json'),ground_patch=ref(OUT/'native_ground_candidate_patch.json'),groups=groups,policy='The old R04 native cap failures remain unchanged evidence. All four old instances retire atomically. New actual fine-native tops are fully covered by continuous contracts; residual finite source-hole pieces belong to R18 and are never restored at an obsolete native cap height.',runtime_ready=False);write('r18_four_terminal_notches.json',out);print(out['status'],[(r['owner_id'],r['source_hole_area_m2'],r['public_restoration_area_m2'],r['physical_minus_current_R18_range_m'],len(r['new_native_without_continuous_contract']),len(r['obsolete_height_restoration_contacts']))for r in groups],flush=True)
if __name__=='__main__':main()
