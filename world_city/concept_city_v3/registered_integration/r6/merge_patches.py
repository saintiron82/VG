"""Conservative composition of independently audited edits to ONE frozen scene.

No terrain resampling occurs here. Duplicate source triangle indices are rejected
rather than applying stale edits sequentially. Producers must geometrically
compose any overlapping edits before this merge. Inputs are never mutated.
"""
from __future__ import annotations
import copy,hashlib,json,math
from .apply_packs import BASE_SHA256

def canonical_sha(value):return hashlib.sha256(json.dumps(value,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def valid_vertices(vertices):
 if len(vertices)%3:raise ValueError('Surface is not a flat triangle list')
 for vertex in vertices:
  if len(vertex)!=3 or any(not isinstance(v,(float,int)) or not math.isfinite(v) for v in vertex):raise ValueError('Invalid XYZ vertex')

def merge(patches,base_scene_sha256=BASE_SHA256):
 edits={};hashes={};appended={};removals=set();ids=[];sources=[]
 for p in patches:
  identity=p['id']
  if identity in ids:raise ValueError('Duplicate patch ID: '+identity)
  ids.append(identity)
  expected=p.get('base_scene_sha256',p.get('base_scene',{}).get('sha256'))
  if expected!=base_scene_sha256:raise ValueError('Patch refers to another frozen scene: '+identity)
  if p.get('status','').lower().startswith(('fail','invalid','rejected')):raise ValueError('Rejected patch: '+identity)
  for key,digest in p['source_surface_hashes'].items():
   if key in hashes and hashes[key]!=digest:raise ValueError('Conflicting source surface hash: '+key)
   hashes[key]=digest
  for row in p['surface_edits']:
   key=row['material'],row['triangle_index']
   if row['material'] not in p['source_surface_hashes']:raise ValueError('Missing source surface hash')
   if key in edits:raise ValueError('Overlapping source triangle needs geometric composition: '+str(key))
   if not isinstance(key[1],int) or key[1]<0:raise ValueError('Invalid source triangle index')
   for triangle in row['replacement_triangles_xyz_m']:
    if len(triangle)!=3:raise ValueError('Replacement is not a triangle')
    valid_vertices(triangle)
   edits[key]=copy.deepcopy(row)
  for material,vertices in p['appended_surfaces'].items():
   valid_vertices(vertices);appended.setdefault(material,[]).extend(copy.deepcopy(vertices))
  removals.update(p.get('removed_foundation_proxy_ids',[]))
  sources.append(dict(id=identity,patch_sha256=canonical_sha(p),source_status=p.get('status'),edits=len(p['surface_edits']),appended_triangles=sum(len(v)//3 for v in p['appended_surfaces'].values())))
 return dict(schema='riverstone.frozen_scene_disjoint_patch_composition.v1',id='R6_COMPOSED_LOCAL_EDITS',
   base_scene_sha256=base_scene_sha256,status='composed_disjoint_source_edits_requires_producer_acceptance_and_scene_review',
   source_surface_hashes=hashes,surface_edits=[edits[k] for k in sorted(edits)],appended_surfaces=appended,
   removed_foundation_proxy_ids=sorted(removals),source_patches=sources,
   limit='A disjoint index ledger proves non-overwriting, not seam grades, support, public clearance or visual fidelity.')

def validate_against_scene(scene,patch):
 original=scene['surfaces']
 for material,digest in patch['source_surface_hashes'].items():
  if material not in original or canonical_sha(original[material])!=digest:raise ValueError('Changed source surface: '+material)
 for row in patch['surface_edits']:
  v=original[row['material']];start=row['triangle_index']*3
  if start+3>len(v) or canonical_sha(v[start:start+3])!=row['source_triangle_sha256']:raise ValueError('Changed source triangle')
 boxes={b['id'] for b in scene.get('boxes',[])}
 if not set(patch.get('removed_foundation_proxy_ids',[]))<=boxes:raise ValueError('Unknown foundation proxy retirement')
 return True
