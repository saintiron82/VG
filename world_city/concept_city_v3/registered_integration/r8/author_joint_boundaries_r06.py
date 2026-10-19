"""Atomic 61-holding/public boundary assembly with finite native interfaces."""
import json,time
from pathlib import Path
from .author_joint_boundaries import boundary_strip
from .build_scene import a,HERE,BASE_SHA,verify
from . import finite_boundary_index
from ...registered_topography.revisions.r17_district_batches import author as g
from ...registered_topography.revisions.public_corridors_r18.height_field import fixed_sources

R18=a.CITY/'registered_topography/revisions/public_corridors_r18'
R17=a.CITY/'registered_topography/revisions/r17_district_batches'
CONTEXT=a.CITY/'evidence/r8_district_r04/scene.json'
OUT=HERE/'joint_boundary_r06'
def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main():
 start=time.monotonic();OUT.mkdir(exist_ok=True);assert not(OUT/'surface_patch.json').exists()
 paths=[R18/'finite_field_candidate_r07_native_bound.json',R18/'public_top_r03_native_bound/physical_owners.json',R17/'contour_bulk_r01/physical_owner_handoff_r02.json',R17/'coherent_batch18_r01/physical_owner_handoff_r02.json',R18/'boundary_closure_handoff_r01.json',R18/'north_mask_restoration_r01.json']
 pub,public,private23,private18,native,north=[a.load(p)for p in paths]
 assert a.sha(paths[0])=='d807f13a82e2639e1e9c7ff37ce8750b60d783b80cee9205fe1ffe8344239683'
 assert a.sha(paths[2])=='9d3f4c559baea48c62e7d3405db44e73c4d69cf9207f3baea1d0f4bfed8a6ad1'
 assert a.sha(paths[3])=='8a9206e0514c6a7a9004193a48f695b7c205e8326f70c78913a560975b7a1da4'
 private20path=R17/'coherent_batch20_r01/physical_owner_handoff_r02.json';private20=a.load(private20path,'6a71cc25213103b050c5a4998a10e9aadbaebf46a93231e3239591ad2dfd4552');paths.append(private20path)
 scene=g.load_scene();context=a.load(CONTEXT,'3c63a21f4490e1dada6be34428dc2d1ffacd326d8f34b2deee81e378ab6680d7')
 logical=public['owners']+private23['physical_earth_owners']+private18['physical_earth_owners']+private20['physical_earth_owners']+north['physical_earth_owners']
 fixed,segments,refs=fixed_sources()
 outside=native['all_noble_physical_owners']+native['accepted_adjacent_physical_owners']+pub['report']['native_ownership_revision']['native_exclusions']
 outside+=fixed+private23['public_fixed_regions']+private18['public_fixed_regions']+private20['public_fixed_regions']
 outside += [s for row in segments if(s:=boundary_strip(row))]
 # The common transition exclusion is its actual +8m native terminal.
 outside += [dict(id=r['id'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=[0,0,8.])for r in pub['report']['common_cap_transition']['supplemental_native_exclusions']]
 windows=[r['polygon_xz_m']for r in logical];index=g.TriangleIndex(context,windows)
 print('Joint physical owners',len(logical),'current exterior source tops',len(index.rows),'seconds',time.monotonic()-start,flush=True)
 result=finite_boundary_index.interfaces(scene,index,logical,outside)
 # The north obsolete-hole remainder is finite earth, not extra traffic.
 append={'bank':[v for t in result['appended_retaining_triangles_xyz_m']for v in t], 'ground_earth':[v for r in north['physical_earth_owners']for t in r['triangles_xyz_m']for v in t]}
 code=OUT/'finite_boundary_index.py.txt';code.write_bytes((HERE/'finite_boundary_index.py').read_bytes())
 refs=[ref(p)for p in paths]+[ref(CONTEXT),ref(Path(__file__)),ref(code)]+refs
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R8_JOINT_61_HOLDING_PUBLIC_BOUNDARY_CLOSURE',status='SIDE_CANDIDATE_PENDING_NATIVE_CLOSURE_CLASSIFICATION_AND_RUNTIME',base_scene_sha256=BASE_SHA,source_surface_hashes={m:g.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in result['side_surface_edits']})},surface_edits=result['side_surface_edits'],appended_surfaces=append,removed_foundation_proxy_ids=[],source_references=refs)
 review=dict(status='FINITE_BOUNDARY_GEOMETRY_CANDIDATE',physical_owner_count=len(logical),public_owner_count=len(public['owners']),private_holding_count=61,source_side_edits=len(result['side_surface_edits']),new_retaining_triangles=len(result['appended_retaining_triangles_xyz_m']),north_restoration_area_m2=north['rendered_area_m2'],unknown_exterior_segments=result['unknown_exterior_segments'],boundary_seams=result['boundary_seams'],retired_sides=result['retired_sides'],source_refs=refs,indexed_execution=result['indexed_execution'],elapsed_s=time.monotonic()-start,activation=False,scope='Exact finite physical earth plus measured adjacent native planes. Native-side closure classification and actual runtime acceptance remain required; boundary-only contracts emit no extra walking ground.')
 for name,value in [('surface_patch.json',patch),('boundary_review.json',review)]:(OUT/name).write_text(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n')
 print({k:v for k,v in review.items()if k not in('source_refs','boundary_seams','unknown_exterior_segments','retired_sides','scope','indexed_execution')},'unknown',len(result['unknown_exterior_segments']),flush=True)
if __name__=='__main__':main()
