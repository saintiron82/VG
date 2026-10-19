"""Remove retained vertical bank faces only inside the exact native stair base.

The native stair/retaining sides replace the former ground column. No water,
road, native geometry or controller is changed. Preserve the failing scene.
"""
import json,math,time
from .build_scene import a,HERE,BASE_SHA
from ...registered_topography.revisions.r15_merchant_local_patch import frozen
from ...registered_topography.revisions.r16_working_ranges.frozen_r6 import normal_y

def area3(t):
 u=[t[1][i]-t[0][i]for i in range(3)];v=[t[2][i]-t[0][i]for i in range(3)]
 return math.sqrt(sum(q*q for q in [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]))/2

def run():
 start=time.monotonic();base=a.CITY/'evidence/visual_registered_common_r7_palette_r01/scene.json';scene=a.load(base,BASE_SHA)
 pack_path=a.CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json';pack=a.load(pack_path,'499bec66a33e14e1f78fe35a7bfdc03fa1e0c9aaaf56ba9a225448e48bc94aed')
 masks=[r['polygon_xz_m'] for r in pack['actual_bearing_footprints'] if r['placement_id']=='PHASE02:real_neighborhood_stair:0'];assert len(masks)==1
 bb=frozen.bounds(masks[0]);vs=scene['surfaces']['bank'];edits=[];proof=[]
 for i in range(len(vs)//3):
  tri=vs[i*3:i*3+3];poly=[[v[0],v[2]]for v in tri]
  if not frozen.overlap(bb,frozen.bounds(poly)):continue
  if abs(normal_y(tri))>1e-8:raise ValueError('Unexpected nonvertical nearby bank triangle; cannot use vertical clipping')
  clipped=frozen.clip_vertical_triangle(tri,masks)
  if clipped['unchanged']:continue
  new=clipped['triangles_xyz_m'];removed=area3(tri)-sum(area3(t)for t in new)
  if removed<=1e-9:continue
  if removed<0:raise ValueError('Bank clipping increased area')
  edits.append(dict(material='bank',triangle_index=i,source_triangle_sha256=frozen.canonical_sha(tri),replacement_triangles_xyz_m=new))
  proof.append(dict(triangle_index=i,original_xyz_m=tri,kept_triangles_xyz_m=new,removed_area_3d_m2=removed,removed_parameter_intervals=clipped['removed_parameter_intervals']))
 assert {10037,10038,10047,10048}<={r['triangle_index'] for r in edits}
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R8_EXACT_STAIR_BANK_INTERFACE_R01',status='SOURCE_GEOMETRY_REPAIR_PENDING_CONTROLLER_REPLAY',base_scene_sha256=BASE_SHA,source_surface_hashes={'bank':frozen.canonical_sha(vs)},surface_edits=edits,appended_surfaces={},removed_foundation_proxy_ids=[])
 out=HERE/'stair_bank_patch_r01.json';assert not out.exists();out.write_text(json.dumps(patch,separators=(',',':'))+'\n')
 report=dict(schema='riverstone.exact_stair_bank_repair.v1',base_scene_sha256=BASE_SHA,source_pack_sha256=a.sha(pack_path),owned_stair_footprint_xz_m=masks[0],owned_stair_area_m2=34.2,changed_triangles=len(edits),removed_vertical_area_m2=sum(r['removed_area_3d_m2']for r in proof),native_geometry_unchanged=True,water_and_road_unchanged=True,original_failing_scene_preserved=True,proof=proof,seconds=time.monotonic()-start)
 rp=HERE/'stair_bank_review_r01.json';rp.write_text(json.dumps(report,indent=2)+'\n');binding=a.load(HERE/'precinct_preflight_binding.json');binding['patches'].append(dict(path=a.rel(out),sha256=a.sha(out)));binding['evidence'].append(dict(path=a.rel(rp),sha256=a.sha(rp)));binding['limits'][1]='Native stair and exact finite bank interface repaired; original no-step controller replay pending.'
 (HERE/'precinct_bank_binding_r01.json').write_text(json.dumps(binding,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['proof','owned_stair_footprint_xz_m']},indent=2))
if __name__=='__main__':run()
