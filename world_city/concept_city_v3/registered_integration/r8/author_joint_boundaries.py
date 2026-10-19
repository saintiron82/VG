"""One public/private physical-earth closure over the existing finite helpers."""
import json,math,time
from .build_scene import a,HERE,BASE_SHA
from . import finite_boundary_index
from ...registered_topography.revisions.r17_district_batches import author as g
from ...registered_topography.revisions.r17_district_batches.contour_bulk_r01 import compose_districts as c
from ...registered_topography.revisions.public_corridors_r18.height_field import fixed_sources

PUBLIC=a.CITY/'registered_topography/revisions/public_corridors_r18/finite_field_candidate_r04_common.json'
PRIVATE=a.CITY/'registered_topography/revisions/r17_district_batches/contour_bulk_r01/physical_owner_handoff_r02.json'
CONTEXT=a.CITY/'evidence/r8_district_r04/scene.json'
OUT=HERE/'joint_boundary_r04'
def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def boundary_strip(row):
 u,v=row['xyz_m'];dx,dz=v[0]-u[0],v[2]-u[2];L=math.hypot(dx,dz)
 if L<1e-9:return None
 nx,nz=-dz/L*1e-4,dx/L*1e-4;dy=v[1]-u[1];ax,az=dy*dx/(L*L),dy*dz/(L*L)
 return dict(id='BOUNDARY_ONLY:'+row['id'],polygon_xz_m=[[u[0]+nx,u[2]+nz],[v[0]+nx,v[2]+nz],[v[0]-nx,v[2]-nz],[u[0]-nx,u[2]-nz]],plane_y_xz_m=[ax,az,u[1]-ax*u[0]-az*u[2]],boundary_only_not_rendered_or_walkable=True)
def main():
 start=time.monotonic();OUT.mkdir(exist_ok=True);assert not(OUT/'surface_patch.json').exists()
 pub=a.load(PUBLIC,'9b8852dce39ea122cf6fb2f057d6acd0fd8e826c73bf48916290165be1d94e14');private=a.load(PRIVATE,'9d3f4c559baea48c62e7d3405db44e73c4d69cf9207f3baea1d0f4bfed8a6ad1');scene=g.load_scene();context=a.load(CONTEXT,'3c63a21f4490e1dada6be34428dc2d1ffacd326d8f34b2deee81e378ab6680d7')
 public=[dict(id=r['id'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],kind='canonical_public_surface',material='road',action='field')for r in pub['records']]
 logical=public+private['physical_earth_owners'];outside,segments,refs=fixed_sources();outside+=private['public_fixed_regions']
 outside += [dict(id=r['id'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=[0,0,8.])for r in pub['report']['common_cap_transition']['supplemental_native_exclusions']]
 outside += [s for row in segments if(s:=boundary_strip(row))]
 windows=[r['polygon_xz_m']for r in logical];index=g.TriangleIndex(context,windows)
 print('Joint physical owners',len(logical),'current exterior source tops',len(index.rows),'seconds',time.monotonic()-start,flush=True)
 result=finite_boundary_index.interfaces(scene,index,logical,outside)
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R8_JOINT_PUBLIC_PRIVATE_BOUNDARY_CLOSURE',status='SIDE_CANDIDATE_PENDING_EXACT_COMPOSITION_AND_RUNTIME',base_scene_sha256=BASE_SHA,source_surface_hashes={m:g.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in result['side_surface_edits']})},surface_edits=result['side_surface_edits'],appended_surfaces={'bank':[v for t in result['appended_retaining_triangles_xyz_m']for v in t]},removed_foundation_proxy_ids=[],source_references=[ref(PUBLIC),ref(PRIVATE),ref(CONTEXT),ref(HERE/'author_joint_boundaries.py')]+refs)
 patch['source_references'].append(ref(HERE/'finite_boundary_index.py'))
 review=dict(status='FINITE_BOUNDARY_GEOMETRY_CANDIDATE',public_owner_count=len(public),private_owner_count=len(private['physical_earth_owners']),source_side_edits=len(result['side_surface_edits']),new_retaining_triangles=len(result['appended_retaining_triangles_xyz_m']),unknown_exterior_segments=result['unknown_exterior_segments'],boundary_seams=result['boundary_seams'],retired_sides=result['retired_sides'],source_refs=patch['source_references'],indexed_execution=result['indexed_execution'],elapsed_s=time.monotonic()-start,activation=False,scope='Current accepted exterior planes and boundary-only fixed contracts provide adjacent height. Boundary strips are not emitted as geometry or asserted as extra ground. Exact composition with prior finite edits and final clear-volume replay remain mandatory.')
 for name,value in [('surface_patch.json',patch),('boundary_review.json',review)]:(OUT/name).write_text(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n')
 print({k:v for k,v in review.items()if k not in('source_refs','boundary_seams','unknown_exterior_segments','retired_sides','scope','indexed_execution')},'unknown',len(result['unknown_exterior_segments']),flush=True)
if __name__=='__main__':main()
