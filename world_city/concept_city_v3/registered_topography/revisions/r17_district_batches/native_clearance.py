"""Exact native provenance and retained-plan clearance for a district batch.

This is a conservative plan-volume screen. It does not replace the independent
3D retained-side audit or native door-path replay.
"""
import argparse,json,math,time
from . import author as a
PROJECTION=a.CITY/'registered_integration/r8/coverage_plan/native_projection.json'

def transform(poly,position,yaw):
 c,s=math.cos(yaw),math.sin(yaw)
 return [[position[0]+c*x+s*z,position[2]-s*x+c*z] for x,z in poly]

def require_ref(ref):
 path=a.ROOT/ref['path']
 if a.sha(path)!=ref['sha256']:raise ValueError('Changed source '+str(path))
 return json.loads(path.read_bytes())

def check(layout):
 start=time.monotonic();projection=json.loads(PROJECTION.read_bytes())
 if projection['scene']['sha256']!=a.SCENE_SHA256:raise ValueError('Stale native projection')
 native=require_ref(layout['native_local'])['assets'];retired=set(layout['retired_source_ids']);active={r['id']for r in projection['instances']}
 if not retired<=active:raise ValueError('Unknown retired native IDs')
 retained=[];index=a.geo._SpatialIndex(16)
 for inst in projection['instances']:
  if inst['id']in retired:continue
  for j,p in enumerate(inst['native_owner_parts_xz_m']):
   index.add(len(retained),p);retained.append(dict(instance_id=inst['id'],part_index=j,polygon_xz_m=p))
 owners=[];provenance=[];native_refs=[]
 for p in layout['placements']:
  n=native[p['asset_key']];asset=n['asset']
  for kind in ('master','render'):
   path=a.ROOT/asset[kind+'_path']
   if a.sha(path)!=asset[kind+'_sha256']:raise ValueError('Changed native '+str(path))
   native_refs.append(dict(path=str(path.relative_to(a.ROOT)),sha256=a.sha(path)))
  if p['scale']!=[1,1,1]:raise ValueError('Scaled native')
  if abs(p['position_m'][1]+n['finished_floor_local_y_m']-p['finished_floor_y_m'])>1e-9:raise ValueError('Native threshold datum mismatch')
  for local_key,world_key in [('foundation_local_polygons_xz_m','native_foundation_polygons_xz_m'),('walking_local_polygons_xz_m','native_walking_obstacles_xz_m'),('roof_local_polygons_xz_m','native_roof_polygons_xz_m')]:
   expected=[transform(q,p['position_m'],p['yaw_rad'])for q in n[local_key]];actual=p[world_key]
   if len(expected)!=len(actual)or any(len(x)!=len(y)for x,y in zip(expected,actual)):raise ValueError('Native mask topology mismatch')
   delta=max((math.dist(x,y)for q,r in zip(expected,actual)for x,y in zip(q,r)),default=0.)
   if delta>1e-8:raise ValueError('Native mask transform mismatch')
   provenance.append(dict(placement_id=p['id'],mask_kind=world_key,polygons=len(actual),maximum_vertex_delta_m=delta))
  for j,q in enumerate(p['native_roof_polygons_xz_m']):owners.append(dict(id=p['id']+':ROOF:'+str(j),kind='new_native_roof',polygon_xz_m=q))
 for h in layout['holdings']:
  owners.append(dict(id=h['id']+':HOLDING',kind='holding',polygon_xz_m=h['holding_polygon_xz_m']))
  for j,q in enumerate(h['external_route_polygons_xz_m']):owners.append(dict(id=h['id']+':EXTERNAL:'+str(j),kind='external_route',polygon_xz_m=q))
 for h in layout['shared_private_routes']:
  for j,q in enumerate(h['polygons_xz_m']):owners.append(dict(id=h['id']+':'+str(j),kind='shared_route',polygon_xz_m=q))
 conflicts=[]
 for owner in owners:
  q=owner['polygon_xz_m']
  for j in index.candidates(q):
   r=retained[j];part=a.clip(q,r['polygon_xz_m']);area=a.geo.polygon_area(part)if part else 0.
   if area>1e-7:conflicts.append(dict(owner_id=owner['id'],owner_kind=owner['kind'],retained_instance_id=r['instance_id'],retained_part_index=r['part_index'],area_m2=area,polygon_xz_m=part))
 doors={d['id']:d for d in layout['actual_doors']};door_proof=[]
 for p in layout['placements']:
  n=native[p['asset_key']]
  if len(p['actual_door_ids'])!=len(n['doors']):raise ValueError('Door count mismatch')
  for local in n['doors']:
   key=p['id']+':'+local['id'];d=doors[key];v=local['actual_local_xyz_m'];xz=transform([[v[0],v[2]]],p['position_m'],p['yaw_rad'])[0];xyz=[xz[0],p['position_m'][1]+v[1],xz[1]];delta=math.dist(xyz,d['actual_door_xyz_m'])
   if delta>1e-8 or abs(xyz[1]-p['finished_floor_y_m'])>1e-8:raise ValueError('Actual native door pose mismatch')
   door_proof.append(dict(id=key,actual_door_xyz_m=xyz,delta_m=delta,render_sha256=n['asset']['render_sha256']))
 return dict(schema='riverstone.r17.native_batch_clearance.v1',base_scene_sha256=a.SCENE_SHA256,native_projection=dict(path=str(PROJECTION.relative_to(a.ROOT)),sha256=a.sha(PROJECTION)),native_references=list({r['path']:r for r in native_refs}.values()),native_mask_provenance=provenance,door_provenance=door_proof,retained_native_conflicts=conflicts,summary=dict(placements=len(layout['placements']),actual_doors=len(door_proof),retired_native_ids=len(retired),tested_plan_owners=len(owners),retained_native_pieces=len(retained),conflicts=len(conflicts),seconds=time.monotonic()-start),passes_source_gate=not conflicts,scope='Exact transforms, cache hashes, threshold datums and conservative actual retained-native projection clearance. Interior walking routes and finite side clear volumes have separate tests.',activation=False)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',default='layout_draft_r01');args=p.parse_args();folder=a.HERE/args.folder;out=folder/'native_clearance.json'
 if out.exists():raise SystemExit('Preserve prior native audit')
 d=check(json.loads((folder/'selected_layout.json').read_bytes()));out.write_text(json.dumps(d,separators=(',',':'))+'\n');print(d['summary']);print(a.sha(out))
