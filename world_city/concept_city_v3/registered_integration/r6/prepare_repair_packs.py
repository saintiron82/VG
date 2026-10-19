"""Adapt sealed bridge/clergy producer handoffs without modifying their sources."""
import copy,json
from . import apply_packs as a
BRIDGE=a.CITY/'assemblies/waterworks/registered_bridge/south_approach_r02/normalized_resolved_placements.json'
BRIDGE_HASH='8e6f6892b8072a7c6a54088b1ee7915e516a8095d780486e4dcfaa83a10183ed'
CLERGY=a.CITY/'assemblies/landmarks/registered/precinct_r05_ground/local_frame_r01/corner_repair_r01/resolved_placements.json'
CLERGY_HASH='3ac9fab37acab132261b75c70f27c61452150164bab16e29e73023ab2283b5df'

def bridge():
 data=a.load(BRIDGE,BRIDGE_HASH);out=copy.deepcopy(data)
 out['source_normalized_pack']=dict(path=a.rel(BRIDGE),sha256=BRIDGE_HASH)
 out['replaced_placement_ids']=data['replacement_overlay']['removed_instance_ids']
 profile_ref=data['continuous_collision_profile'];profile=a.load(a.ROOT/profile_ref['path'],profile_ref['sha256'])
 out['collision_contracts']=[dict(id='SOUTHERN_FINITE_GRADED_LANE',source_profile=profile_ref,
   disable_native_mesh_collider_ids=['BRIDGE_MAIN_RIVER:SOUTH_VISIBLE_GRADED_COVER'],
   keep_native_mesh_collider_ids=['BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED'],
   add_triangles_world_xyz_m=[t['triangle_xyz_m'] for t in profile['triangles']],
   visual_owner='BRIDGE_MAIN_RIVER:SOUTH_VISIBLE_GRADED_COVER',
   continuous_profile_area_m2=profile['source_area_m2'],native_visual_pitch_m=profile['visible_pitch_m'],
   maximum_visual_collision_difference_m=0.026806761,
   tested_capsule_radius_m=0.3,tested_capsule_height_m=1.8,
   status='Bounded original-context fixture passed; composed R6 collision application and rerun required.',
   not_claimed=['Cart/full-width traffic','Central moving span or live city occupancy registry','Automatic global collision optimization'])]
 return out

def clergy():
 data=a.load(CLERGY,CLERGY_HASH);ref=data['principal_frame_overlay'];overlay=a.load(a.ROOT/ref['path'],ref['sha256'])
 ids={r['placement_id'] for r in overlay['replacements']};assert len(ids)==3
 placements=[copy.deepcopy(p) for p in data['placements'] if p['id'] in ids];assert len(placements)==3
 keys={p['asset_key'] for p in placements};assets={p['id']:a.asset_record(p) for p in data['assets'] if p['id'] in keys}
 assert len(assets)==3
 return dict(schema='riverstone.r6_three_clergy_cache_replacements.v1',status='native_repair_requires_matching_frozen_ground_patch',
   source=dict(path=a.rel(CLERGY),sha256=CLERGY_HASH),source_overlay=ref,
   assets=assets,placements=placements,replaced_placement_ids=sorted(ids),
   source_door_records=[p for p in data['actual_doors'] if p.get('compound_id') in ids],
   limits=['Only three actual clergy unions change; 74 other precinct placements remain identical.',
   'Sampling is in each principal frame, then rigidly placed. Common engine and building dimensions are unchanged.',
   'The 0.07845 m2 corner contact was repaired only at finite court/boundary geometry. Old and rejected geometry remain archived.'])

if __name__=='__main__':
 for name,fn in [('southern_repair_pack.json',bridge),('clergy_repair_pack.json',clergy)]:
  out=fn();p=a.HERE/name;assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(name,a.sha(p),len(out['placements']))
