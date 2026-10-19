import json,time,collections
from .height_field import HERE
from .revise_native_emission_r07 import ref
from ..r17_district_batches import author as a
from world_city.concept_city_v3.registered_integration.r8 import finite_boundary_index as side

def main():
 start=time.monotonic();p=HERE/'north_connected_earth_r03_candidate.json';d=json.loads(p.read_bytes());assert a.sha(p)=='d8e908db5989fa50b63ca0b2dec56e1a0dc709d6452190f3408645df2cc35e9a';logical=d['physical_earth_owners'];sp=a.CITY/'evidence/r8_district_r04/scene.json';scene=json.loads(sp.read_bytes());pubp=HERE/'finite_field_candidate_r07_native_bound.json';pub=json.loads(pubp.read_bytes());hp=HERE/'boundary_closure_handoff_r01.json';h=json.loads(hp.read_bytes());outside=pub['records']+h['accepted_adjacent_physical_owners'];index=a.TriangleIndex(scene,[r['polygon_xz_m']for r in logical]);result=side.interfaces(scene,index,logical,outside)
 summary={k:len(v)if isinstance(v,list)else v for k,v in result.items()if k not in ['indexed_execution']};print(summary,flush=True)
 out=dict(schema='riverstone.r18.north_local_boundary.v1',status='LOCAL_CANDIDATE_PENDING_NATIVE_UNKNOWN_CLASSIFICATION',sources=[ref(p),ref(sp),ref(pubp),ref(hp),ref(__import__('pathlib').Path(side.__file__)),ref(__import__('pathlib').Path(__file__))],**result,seconds=time.monotonic()-start);op=HERE/'north_connected_boundary_r03.json';op.write_text(json.dumps(out,separators=(',',':'))+'\n');print(ref(op),out['seconds'],flush=True)
 # Only exact unique unchanged source triangles may rebound into the base-R7 patch.
 base=a.load_scene();mapping=collections.defaultdict(list)
 for mat in {e['material']for e in result['side_surface_edits']}:
  flat=base['surfaces'][mat]
  for i in range(0,len(flat),3):mapping[mat,a.canonical_sha(flat[i:i+3])].append(i//3)
 edits=[];holds=[]
 for e in result['side_surface_edits']:
  ids=mapping[e['material'],e['source_triangle_sha256']]
  if len(ids)!=1:holds.append(dict(edit=e,base_matches=ids));continue
  edits.append(dict(e,triangle_index=ids[0]))
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R18_CONNECTED_NORTH_PREMASK_EARTH_R03',status='CANDIDATE_LOCAL_SIDES_PENDING_NATIVE_CLASSIFICATION',base_scene_sha256=a.SCENE_SHA256,source_surface_hashes={m:a.canonical_sha(base['surfaces'][m])for m in sorted({e['material']for e in edits})},surface_edits=edits,appended_surfaces={'ground_earth':[v for r in logical for t in r['triangles_xyz_m']for v in t],'bank':[v for t in result['appended_retaining_triangles_xyz_m']for v in t]},removed_foundation_proxy_ids=[],source_references=[ref(p),ref(op)],contextual_rebinding_holds=holds,replaces_entire_prior_north_restoration=ref(HERE/'north_mask_restoration_r01.json'));pp=HERE/'north_connected_surface_patch_r03.json';pp.write_text(json.dumps(patch,separators=(',',':'))+'\n');print(ref(pp),'rebind holds',len(holds),flush=True)
if __name__=='__main__':main()
