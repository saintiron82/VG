"""Immutable R6 top-winding correction. No coordinate, plane, or owner change."""
import copy,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path
from .. import author as a, frozen as old
HERE=Path(__file__).resolve().parent
SCENE_PATH=a.CITY/'evidence/visual_registered_common_r6/scene.json'
SCENE_SHA256='7dd4093c6cd27898fd64fce75a4010cb70c751d12dc0a75b1a44a20c6c3da3e8'
PATCH_PATH=a.HERE/'subset_07/scene_patch.json'
PATCH_SHA256='58503c5ed70707306e781aa5a30e678660b42f7cb7f57d2371f7164bfcb79999'

def normal_y(t):
 u,v,w=t;return (v[2]-u[2])*(w[0]-u[0])-(v[0]-u[0])*(w[2]-u[2])
def upward_xyz(t):
 """Keep the exact existing XYZ values; reverse only a downward top."""
 return [t[0],t[2],t[1]] if normal_y(t)<-1e-10 else t

def fan_upward(vertices):
 """Correct future finite top emitter, independent of XZ polygon winding."""
 for i in range(1,len(vertices)-1):
  tri=[vertices[0],vertices[i],vertices[i+1]]
  if abs(normal_y(tri))>1e-10:yield upward_xyz(tri)

def normalize_source_records(records):
 out=[]
 for r in records:
  t=upward_xyz(r['vertices_xyz_m']);q=dict(r,vertices_xyz_m=t)
  if 'polygon_xz_m' in q:q['polygon_xz_m']=[[v[0],v[2]] for v in t]
  # Stored affine coefficients remain exactly the same, not recomputed.
  out.append(q)
 return out

def build_ground_upward(*args,**kwargs):
 from .. import restore_ground
 d=restore_ground.build(*args,**kwargs);d['triangles']=normalize_source_records(d['triangles']);return d

def load_scene():
 raw=SCENE_PATH.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=SCENE_SHA256:raise ValueError('Changed actual R6 scene')
 return json.loads(raw)

def make_patch(scene):
 if a.sha(PATCH_PATH)!=PATCH_SHA256:raise ValueError('Changed sealed R15 subset')
 source=json.loads(PATCH_PATH.read_bytes());expected=Counter()
 for material,vs in source['appended_surfaces'].items():
  for i in range(0,len(vs),3):
   tri=vs[i:i+3]
   if normal_y(tri)<-1e-10:expected[(material,old.canonical_sha(tri))]+=1
 edits=[];found=Counter();hashes={};counts=Counter();areas=defaultdict(float)
 for material,vs in scene['surfaces'].items():
  for i in range(0,len(vs),3):
   tri=vs[i:i+3];ny=normal_y(tri)
   if ny>=-1e-10:continue
   key=(material,old.canonical_sha(tri));found[key]+=1
   edits.append(dict(material=material,triangle_index=i//3,source_triangle_sha256=key[1],replacement_triangles_xyz_m=[upward_xyz(tri)]));counts[material]+=1;areas[material]+=-ny/2
  if counts[material]:hashes[material]=old.canonical_sha(vs)
 if found!=expected:raise ValueError('Downward R6 tops do not exactly match sealed R15 additions')
 if len(edits)!=3406:raise ValueError('Unexpected repair scope')
 return dict(schema='riverstone.frozen_scene_patch.v1',id='R15_WINDING_REPAIR_R01',status='EXACT_ORIENTATION_REPAIR_PENDING_VIEW_AND_CAPSULE_REPLAY',base_scene_sha256=SCENE_SHA256,source_surface_hashes=hashes,surface_edits=edits,appended_surfaces={},removed_foundation_proxy_ids=[],source_r15_patch_sha256=PATCH_SHA256,counts=dict(counts),projected_area_m2=dict(areas),policy='Only swap triangle vertices b/c when authored normal Y is negative. XYZ values, material, plane, projected area, bounds, owner domains, native geometry, collision source and controller settings otherwise remain unchanged.')

def apply_to_scene(scene,patch):
 if patch['base_scene_sha256']!=SCENE_SHA256:raise ValueError('Wrong base scene')
 out=dict(scene);surfaces=dict(scene['surfaces']);seen=set()
 for material,value in patch['source_surface_hashes'].items():
  if old.canonical_sha(scene['surfaces'][material])!=value:raise ValueError('Changed source material array')
  surfaces[material]=list(scene['surfaces'][material])
 for r in patch['surface_edits']:
  key=r['material'],r['triangle_index']
  if key in seen:raise ValueError('Duplicate source index')
  seen.add(key);start=r['triangle_index']*3;oldtri=scene['surfaces'][r['material']][start:start+3]
  if old.canonical_sha(oldtri)!=r['source_triangle_sha256']:raise ValueError('Changed source triangle')
  new=r['replacement_triangles_xyz_m']
  if len(new)!=1 or new[0]!=[oldtri[0],oldtri[2],oldtri[1]] or normal_y(oldtri)>=0:raise ValueError('Non-orientation edit rejected')
  surfaces[r['material']][start:start+3]=new[0]
 out['surfaces']=surfaces
 return out

def apply_orientation(scene):
 """Pure one-argument replay of the hash-bound R6 orientation ledger.

 Caller verifies the original R6 file bytes via SCENE_SHA256. This function
 independently verifies the complete affected material arrays and all edited
 triangles, leaving every other field untouched.
 """
 path=HERE/'scene_patch.json'
 if a.sha(path)!='6f327c3caa7cb60eaa283a320a67a7583f43d8702698152771956f7a1f34ee85':
  raise ValueError('Changed orientation ledger')
 return apply_to_scene(scene,json.loads(path.read_bytes()))

def main():
 scene=load_scene();patch=make_patch(scene);fixed=apply_to_scene(scene,patch);changed={(r['material'],r['triangle_index']) for r in patch['surface_edits']};unchanged=0
 for material,vs in scene['surfaces'].items():
  corrected=fixed['surfaces'][material]
  if len(vs)!=len(corrected):raise AssertionError('Changed vertex count')
  for i in range(0,len(vs),3):
   a0=vs[i:i+3];b0=corrected[i:i+3]
   if (material,i//3) not in changed:
    assert a0==b0;unchanged+=1
   else:assert sorted(a0)==sorted(b0) and normal_y(b0)>0
 report=dict(status='PASS_EXACT_ORIENTATION_TRANSFORM',base_scene_sha256=SCENE_SHA256,reversed_triangle_count=len(changed),unchanged_triangle_count=unchanged,remaining_downward_top_count=sum(normal_y(vs[i:i+3])<-1e-10 for vs in fixed['surfaces'].values() for i in range(0,len(vs),3)),counts=patch['counts'],projected_area_m2=patch['projected_area_m2'],same_vertex_sets=True,same_triangle_planes=True,same_vertex_array_lengths=True,native_geometry_unchanged=True,renderer_unchanged=True,coverage_and_capsule_status='Separate regression/replay required')
 for name,data in [('scene_patch.json',patch),('transform_report.json',report)]:
  p=HERE/name
  if p.exists():raise ValueError('Refusing to overwrite repair evidence')
  p.write_text(json.dumps(data,separators=(',',':'))+'\n');print(name,a.sha(p),flush=True)
if __name__=='__main__':main()
