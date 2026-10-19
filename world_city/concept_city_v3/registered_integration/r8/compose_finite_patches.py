"""Compose disjoint finite edits that happen to share coarse source triangles.

No source resampling, priority override or acceptance relaxation. Removed regions
must be disjoint in the original triangle's own plane. New-height replacements
remain owned by their producer and may only project inside that producer's mask.
"""
import copy,math
from ..r6 import merge_patches as m
from ...registered_topography.revisions.r16_working_ranges import author as a

def dot(u,v):return sum(x*y for x,y in zip(u,v))
def sub(u,v):return [x-y for x,y in zip(u,v)]
def cross(u,v):return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
def project_frame(triangle):
 n=cross(sub(triangle[1],triangle[0]),sub(triangle[2],triangle[0]));length=math.sqrt(dot(n,n))
 if length<1e-12:raise ValueError('Degenerate shared source triangle')
 axis=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3)if i!=axis];d=dot(n,triangle[0])
 def project(p):return [p[i]for i in axes]
 def unproject(p):
  q=[0.,0.,0.]
  for i,v in zip(axes,p):q[i]=v
  q[axis]=(d-sum(n[i]*q[i]for i in axes))/n[axis];return q
 return n,length,d,project,unproject

def compound_row(scene,key,rows,physical_side_retirements=False):
 material,index=key;source=scene['surfaces'][material][index*3:index*3+3];n,length,d,project,unproject=project_frame(source);original=[project(p)for p in source];original_area=a.geo.polygon_area(original)
 masks=[];raised=[];ledger=[];shared_retire_area=0.
 if physical_side_retirements:
  from ...registered_topography.revisions.r17_district_batches.side_clearance import physical_side
  physical_side_retirements=physical_side(source,material)
 for patchid,row in rows:
  if m.canonical_sha(source)!=row['source_triangle_sha256']:raise ValueError('Changed shared original triangle')
  retained=[];changed=[]
  for tri in row['replacement_triangles_xyz_m']:
   nn=cross(sub(tri[1],tri[0]),sub(tri[2],tri[0]))
   # Orientation is a sign test. A fixed area-product cutoff incorrectly
   # rejects positively wound finite slivers from exact source clipping.
   if dot(nn,n)<=0:raise ValueError('Reversed or degenerate replacement face')
   p=[project(v)for v in tri]
   if sum(a.geo.polygon_area(q)for q in a.subtract([p],[original]))>1e-7:raise ValueError('Replacement projects outside original source triangle')
   if max(abs(dot(n,v)-d)/length for v in tri)<=1e-8:retained.append(p)
   else:changed.append((tri,p))
  removed=a.subtract([original],retained)
  overlaps=[a.geo.convex_intersection(p,q)for p in removed for q in masks];overlap_area=sum(a.geo.polygon_area(p)for p in overlaps)
  if overlap_area>1e-7:
   if not physical_side_retirements or changed or raised:raise ValueError('Finite ownership overlap at '+str(key)+' from '+patchid)
   # Two local repairs can retire the same old near-vertical wall fragment.
   # They cannot both own new-height replacement geometry. The resulting
   # removal is the explicit finite union, never an entire bank-array hide.
   shared_retire_area+=overlap_area
   removed=a.subtract(removed,masks)
  for tri,p in changed:
   if sum(a.geo.polygon_area(q)for q in a.subtract([p],removed))>1e-7:raise ValueError('Changed-height face outside producer ownership')
   raised.append(tri)
  masks+=removed;ledger.append(dict(patch_id=patchid,removed_source_plane_area=sum(a.geo.polygon_area(p)for p in removed),changed_height_faces=len(changed)))
 leftover=a.subtract([original],masks);out=[]
 for poly in leftover:
  verts=[unproject(p)for p in poly]
  for i in range(1,len(verts)-1):
   tri=[verts[0],verts[i],verts[i+1]]
   if dot(cross(sub(tri[1],tri[0]),sub(tri[2],tri[0])),n)<0:tri=[tri[0],tri[2],tri[1]]
   out.append(tri)
 out+=copy.deepcopy(raised)
 proof=dict(material=material,triangle_index=index,source_projected_area=original_area,owners=ledger,remaining_original_plane_area=sum(a.geo.polygon_area(p)for p in leftover),policy='Disjoint finite source-plane ownership; no last-writer priority')
 if shared_retire_area:proof.update(shared_retired_source_projection_area_m2=shared_retire_area,policy='Explicit union of same-plane finite physical-side retirements; no changed-height overlap allowed')
 return dict(material=material,triangle_index=index,source_triangle_sha256=m.canonical_sha(source),replacement_triangles_xyz_m=out),proof

def compose(scene,patches,base_scene_sha256,physical_side_retirements=False):
 # First validate every independent source binding and all non-overlap syntax.
 ids={p['id']for p in patches}
 prerequisite_hashes={}
 for patch in patches:
  if not set(patch.get('requires_patch_ids',[]))<=ids:raise ValueError('Missing finite retirement prerequisite for '+patch['id'])
  for pid,expected in patch.get('requires_patch_canonical_sha256',{}).items():
   if pid not in ids:raise ValueError('Missing hash-bound finite retirement prerequisite')
   if pid not in prerequisite_hashes:prerequisite_hashes[pid]=m.canonical_sha(next(p for p in patches if p['id']==pid))
   if prerequisite_hashes[pid]!=expected:raise ValueError('Changed finite retirement prerequisite: '+pid)
 groups={}
 for patch in patches:
  m.merge([patch],base_scene_sha256);m.validate_against_scene(scene,patch)
  for row in patch['surface_edits']:groups.setdefault((row['material'],row['triangle_index']),[]).append((patch['id'],row))
 normalized=copy.deepcopy(patches);byid={p['id']:p for p in normalized};ledger=[];extra=[];shared_keys=set()
 for key,rows in groups.items():
  if len(rows)<2:continue
  row,proof=compound_row(scene,key,rows,physical_side_retirements);ledger.append(proof);extra.append(row);shared_keys.add(key)
 # Filter once per producer rather than rescanning a district-sized list for
 # every shared original face. Ownership and the compound-row proof are equal.
 for patch in normalized:
  patch['surface_edits']=[r for r in patch['surface_edits']if(r['material'],r['triangle_index'])not in shared_keys]
 if extra:
  mats={r['material']for r in extra}
  normalized.append(dict(id='R8_SHARED_SOURCE_TRIANGLE_FINITE_COMPOSITION',base_scene_sha256=base_scene_sha256,source_surface_hashes={k:m.canonical_sha(scene['surfaces'][k])for k in mats},surface_edits=extra,appended_surfaces={},removed_foundation_proxy_ids=[]))
 result=m.merge(normalized,base_scene_sha256);result['finite_shared_triangle_composition']=ledger
 return result
