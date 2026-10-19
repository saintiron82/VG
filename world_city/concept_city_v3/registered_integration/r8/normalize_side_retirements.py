"""Give near-vertical source faces one exact-3D retirement owner.

Top producers reconstruct retained Y(X,Z), which is ill-conditioned on almost
vertical inherited faces. The joint side producer instead clips the original
XYZ polygon. No public/private appended top, native object or grade is changed.
"""
import copy,json,sys
from pathlib import Path
from .build_scene import a,verify
from .compose_finite_patches import cross,sub,dot
from ..r6 import merge_patches as m
from ...registered_topography.revisions.r17_district_batches import side_clearance

TOP_PHYSICAL_SOURCES={
 'R18_NATIVE_BOUND_PUBLIC_TOPS_R03':'registered_topography/revisions/public_corridors_r18/public_top_r03_native_bound/physical_owners.json',
 'R17_READY_23_TOPS':'registered_topography/revisions/r17_district_batches/contour_bulk_r01/physical_owner_handoff_r02.json',
 'R17_READY_18_INCREMENTAL_TOPS':'registered_topography/revisions/r17_district_batches/coherent_batch18_r01/physical_owner_handoff_r02.json',
 'R17_READY_20_INCREMENTAL_TOPS':'registered_topography/revisions/r17_district_batches/coherent_batch20_r01/physical_owner_handoff_r02.json',
}
def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def normalize(scene,patches):
 patches=copy.deepcopy(patches);joints=[p for p in patches if p['id'].startswith('R8_JOINT_')and p['id'].endswith('_PUBLIC_BOUNDARY_CLOSURE')]
 if len(joints)!=1:raise ValueError('Exactly one authoritative joint physical-side producer is required')
 joint=joints[0];keys={(r['material'],r['triangle_index']):r for r in joint['surface_edits']};flips=[];zeros=[]
 for key,row in keys.items():
  source=scene['surfaces'][key[0]][key[1]*3:key[1]*3+3];n=cross(sub(source[1],source[0]),sub(source[2],source[0]));clean=[]
  if not side_clearance.physical_side(source,key[0]):raise ValueError('Joint side producer edited a walking top')
  for i,t in enumerate(row['replacement_triangles_xyz_m']):
   nn=cross(sub(t[1],t[0]),sub(t[2],t[0]));sign=dot(nn,n)
   if sign<0:
    # Restore the original side's front orientation without moving vertices.
    flips.append(dict(material=key[0],triangle_index=key[1],replacement_index=i,area_m2=side_clearance.area3d(t)));t=[t[0],t[2],t[1]]
   elif sign==0:
    if side_clearance.area3d(t)!=0:raise ValueError('Nonzero side face perpendicular to original source')
    zeros.append(dict(material=key[0],triangle_index=key[1],replacement_index=i));continue
   clean.append(t)
  row['replacement_triangles_xyz_m']=clean
 joint['side_orientation_normalization']=dict(source_plane_orientation_restored=flips,exact_zero_area_faces_removed=zeros,all_vertex_positions_unchanged=True)
 joint_hash=m.canonical_sha(joint);refs={r['path']:r['sha256']for r in joint['source_references']};delegated=[];unmatched=[]
 for p in patches:
  source_name=TOP_PHYSICAL_SOURCES.get(p['id'])
  if not source_name:continue
  source=a.CITY/source_name;rp=ref(source)
  if refs.get(rp['path'])!=rp['sha256']:raise ValueError('Joint boundary lacks exact producer physical-domain binding: '+p['id'])
  keep=[];rows=[]
  for row in p['surface_edits']:
   key=row['material'],row['triangle_index'];original=scene['surfaces'][key[0]][key[1]*3:key[1]*3+3]
   if not side_clearance.physical_side(original,key[0]):keep.append(row);continue
   if key not in keys:keep.append(row);unmatched.append(dict(patch_id=p['id'],material=key[0],triangle_index=key[1]));continue
   if keys[key]['source_triangle_sha256']!=row['source_triangle_sha256']:raise ValueError('Side retirement source changed')
   rows.append(dict(material=key[0],triangle_index=key[1],source_triangle_sha256=row['source_triangle_sha256'],source_area_m2=side_clearance.area3d(original)))
  if rows:
   p['surface_edits']=keep;p.setdefault('requires_patch_ids',[]).append(joint['id']);p.setdefault('requires_patch_canonical_sha256',{})[joint['id']]=joint_hash
   p['physical_side_delegation']=dict(physical_domain=rp,joint_patch_id=joint['id'],source_rows=rows,appended_top_surfaces_unchanged=True,policy='Only original nonwalking physical-side faces are delegated to the existing exact XYZ clipping result. No new top ownership or floating height reconstruction is introduced.')
   delegated.extend(dict(patch_id=p['id'],**r)for r in rows)
 return patches,dict(delegated_source_rows=delegated,unmatched_physical_side_rows_retained=unmatched,side_orientation_flips=flips,exact_zero_area_faces_removed=zeros,geometry_positions_unchanged=True)
def main(binding_path,destination):
 out=Path(destination);out.mkdir(parents=True,exist_ok=True);b=a.load(binding_path);scene=verify(b['base_scene']);before=[verify(r)for r in b['patches']];after,report=normalize(scene,before)
 for i,(old,new)in enumerate(zip(before,after)):
  if old==new:continue
  p=out/f'producer_{i:02d}.json';assert not p.exists();p.write_text(json.dumps(new,separators=(',',':'))+'\n');b['patches'][i]=ref(p)
 report['source_binding']=ref(Path(binding_path));report['code']=ref(Path(__file__));p=out/'review.json';p.write_text(json.dumps(report,indent=2)+'\n');b['evidence'].append(ref(p));p=out/'binding.json';p.write_text(json.dumps(b,indent=2)+'\n')
 print('Delegated',len(report['delegated_source_rows']),'side rows; restored winding',len(report['side_orientation_flips']),'unmatched retained',len(report['unmatched_physical_side_rows_retained']),flush=True)
if __name__=='__main__':main(*sys.argv[1:])
