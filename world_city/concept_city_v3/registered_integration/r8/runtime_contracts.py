"""Explicit source-bound representation overrides, without mutating visuals."""
import copy,math
from ..r6 import apply_packs as a,merge_patches as m

def append_collision_contracts(scene,contracts):
 result=dict(scene);result['collision_contracts']=copy.deepcopy(scene.get('collision_contracts',[]));byid={p['id']:p for p in scene['common_instances']}
 for c in contracts:
  pid=c['native_placement_id'];p=byid.get(pid)
  if p is None:raise ValueError('Collision target is absent')
  if p['position_m']!=c['replacement_transform']['position_m']or p['yaw_rad']!=c['replacement_transform']['yaw_rad']or p.get('scale',[1,1,1])!=[1,1,1]:raise ValueError('Collision pose changed')
  if scene['common_assets'][p['asset_key']]['render_sha256']!=c['native_source']['sha256']:raise ValueError('Collision source cache changed')
  for row in result['collision_contracts']:
   if c['id']==row['id']or set(c['disable_native_mesh_collider_ids'])&set(row.get('disable_native_mesh_collider_ids',[])):raise ValueError('Duplicate collider substitution')
  for triangle in c['add_triangles_world_xyz_m']:
   m.valid_vertices(triangle)
   if c.get('representation_kind')=='continuous_road_top':
    if c.get('triangle_convention')!='godot_clockwise_front':raise ValueError('Road collision convention must be explicit')
    u,v,w=triangle;ny=(v[2]-u[2])*(w[0]-u[0])-(v[0]-u[0])*(w[2]-u[2])
    if ny>=-1e-10:raise ValueError('Direct Godot road collision has reversed or degenerate winding')
  result['collision_contracts'].append(copy.deepcopy(c))
 return result

def append_water_extensions(scene,base,extensions):
 old=base['surfaces']['water']
 if scene['surfaces']['water']!=old:raise ValueError('Water mutation must use explicit extension')
 if not extensions:return scene
 result=dict(scene);result['surfaces']=dict(scene['surfaces']);result['surfaces']['water']=copy.deepcopy(old);instances={p['id']:p for p in scene['common_instances']};seen=set();ledger=[]
 for e in extensions:
  if e['base_water_sha256']!=m.canonical_sha(old):raise ValueError('Changed base water')
  if e.get('collision')is not False:raise ValueError('Water must not become an opaque collider')
  if set(e['owner_ids'])&seen:raise ValueError('Duplicate local water owner')
  if not set(e['owner_ids'])<=instances.keys():raise ValueError('Unplaced water owner')
  seen.update(e['owner_ids']);vertices=e['append_vertices_xyz_m'];m.valid_vertices(vertices)
  # Stored water must remain inside a declared native owner's actual cache bounds.
  for v in vertices:
   inside=False
   for pid in e['owner_ids']:
    p=instances[pid];b=scene['common_assets'][p['asset_key']]['bounds'];co=math.cos(p.get('yaw_rad',0));si=math.sin(p.get('yaw_rad',0));dx,dz=v[0]-p['position_m'][0],v[2]-p['position_m'][2];local=[co*dx-si*dz,v[1]-p['position_m'][1],si*dx+co*dz]
    if all(b['min'][k]-1e-8<=local[k]<=b['max'][k]+1e-8 for k in range(3)):inside=True;break
   if not inside:raise ValueError('Water outside declared native source bounds')
  result['surfaces']['water']+=copy.deepcopy(vertices);ledger.append(dict(owner_ids=e['owner_ids'],new_triangles=len(vertices)//3,existing_water_unchanged=True))
 result['local_water_extensions']=ledger
 return result
