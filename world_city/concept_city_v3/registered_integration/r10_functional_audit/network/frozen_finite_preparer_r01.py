#!/usr/bin/env python3
"""Hash-bound finite R9 gate collision crops. Never exports a whole-city copy.

The source scene is resolved in memory with the exact finite patch and native
addenda used by preview_r9. All source triangles are preserved whole, with only
City.gd's a,c,b winding and an exactly reversible local-origin translation.
"""
import argparse,copy,hashlib,importlib.util,json,math,pathlib,sys,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir())
sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_integration.r6 import merge_patches
from world_city.concept_city_v3.registered_integration.r8.collision_local_origin import rebase
import numpy as np
BASE=ROOT/'world_city/concept_city_v3/traversal_r5'
spec=importlib.util.spec_from_file_location('base_preparer',BASE/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
BASE_SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def ref(p):return {'path':str(pathlib.Path(p).resolve()),'sha256':sha(p)}
def resolve(r):
 p=pathlib.Path(r['path']);p=p if p.is_absolute()else ROOT/p
 p=p.resolve();assert p.is_relative_to(ROOT),'Source outside repo';assert sha(p)==r['sha256'],f'Changed source: {p}'
 return p

def write(p,v):
 with pathlib.Path(p).open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')

def compose_natives(scene,index,source_refs):
 assert index['schema']=='riverstone.city.visual_pack_index.v1'and index['base_scene_sha256']==BASE_SHA
 assets=dict(scene['common_assets']);original={p['id']:p for p in scene['common_instances']};ids=set(original);removed=set();replaced={};added=[]
 for n,entry in enumerate(index['packs']):
  p=resolve(entry);source_refs[f'visual_pack_{n}']=ref(p);pack=read(p)
  assert pack['schema']=='riverstone.city.visual_addendum.v1'and pack['base_scene_sha256']==BASE_SHA
  for key,a in pack.get('common_assets',{}).items():
   assert key not in assets or assets[key]['render_sha256']==a['render_sha256'],'Asset conflict'
   for kind in ['render','master']:
    if kind+'_path'in a:resolve({'path':a[kind+'_path'],'sha256':a[kind+'_sha256']})
   assets[key]=a
  for pid in pack.get('remove_instance_ids',[]):
   assert pid in ids and pid not in removed and pid not in replaced,'Unknown/conflicting native removal';removed.add(pid)
  for item in pack.get('replace_instances',[]):
   pid=item['id'];assert pid in original and pid not in replaced and pid not in removed
   o=original[pid];assert item['expected_asset_key']==o['asset_key']and item['expected_position_m']==o['position_m']and item.get('expected_yaw_rad',0)==o.get('yaw_rad',0)
   proof=resolve({'path':item['proof_path'],'sha256':item['proof_sha256']});source_refs[f'replacement_proof_{pid}']=ref(proof)
   replaced[pid]=dict(o,asset_key=item['asset_key'],palette_id=item['palette_id'],palette_override=item.get('palette_override',{}))
  for item in pack.get('add_instances',[]):
   assert item['id']not in ids,'Duplicate native ID';ids.add(item['id']);added.append(item)
 instances=[replaced.get(p['id'],p)for p in scene['common_instances']if p['id']not in removed]+[p for p in added if p['id']not in removed]
 for p in instances:
  assert p['asset_key']in assets and p.get('scale',[1,1,1])==[1,1,1]
  assert all(math.isfinite(v)for v in p['position_m'])and math.isfinite(p.get('yaw_rad',0))
 return assets,instances,dict(base_instances=len(original),added=len(added),removed=sorted(removed),replaced=sorted(replaced),resolved_instances=len(instances))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--request',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);args=ap.parse_args();start=time.monotonic()
 request_path=args.request.resolve();request=read(request_path);out=args.output.resolve();assert out.is_relative_to(H)and not out.exists(),'New owned output required'
 source=resolve(request['base_scene']);assert request['base_scene']['sha256']==BASE_SHA
 patch_path=resolve(request['finite_patch']);index_path=resolve(request['visual_index']);scene=read(source);patch=read(patch_path)
 assert patch['base_scene_sha256']==BASE_SHA
 merge_patches.merge([patch],BASE_SHA);merge_patches.validate_against_scene(scene,patch)
 edits={}
 for row in patch['surface_edits']:
  mat,i=row['material'],row['triangle_index'];tri=scene['surfaces'][mat][i*3:i*3+3]
  assert tri==row['source_triangle_xyz_m'],'Renderer exact-source triangle parity'
  n=np.cross(np.asarray(tri[1])-tri[0],np.asarray(tri[2])-tri[0])
  for t in row['replacement_triangles_xyz_m']:
   assert np.dot(n,np.cross(np.asarray(t[1])-t[0],np.asarray(t[2])-t[0]))>0,'Replacement winding'
   lo=b.bounds(tri);tb=b.bounds(t);assert tb[0]>=lo[0]-1e-7 and tb[1]>=lo[1]-1e-7 and tb[2]<=lo[2]+1e-7 and tb[3]<=lo[3]+1e-7,'Source finite edit extends beyond source XZ bounds; require exhaustive altered-face selection'
  edits[(mat,i)]=row['replacement_triangles_xyz_m']
 for mat,verts in patch['appended_surfaces'].items():
  assert mat in scene['materials']and len(verts)%3==0
  a=np.asarray(verts,dtype=np.float32).reshape(-1,3,3);n=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);assert np.all(np.any(n!=0,axis=1))
  if mat!='bank':assert np.all(n[:,1]>0),'Renderer appended winding parity'
 sources={'base_scene':ref(source),'finite_patch':ref(patch_path),'visual_index':ref(index_path),'request':ref(request_path),'original_controller':ref(BASE/'Traversal.gd'),'common_render_loader':ref(ROOT/'voxel_character/common/preview/RenderData.gd')}
 for key,r in request.get('producer_sources',{}).items():sources['producer_'+key]=ref(resolve(r))
 assets_in,instances,native_composition=compose_natives(scene,read(index_path),sources)
 routes=[]
 for r0 in request['routes']:
  pts=r0['points'];assert len(pts)>=2 and all(len(p)==3 and all(math.isfinite(v)for v in p)for p in pts)
  if 'gate_waypoint_index'in r0:
   gi=r0['gate_waypoint_index'];assert isinstance(gi,int)and 0<gi<len(pts)-1,'Gate must be an interior waypoint of the full route'
   gate=next(g for g in request['gates']if g['id']==r0['gate_id']);assert math.dist(pts[gi],gate['opening_center_xyz_m'])<1e-7,'Full route must use exact opening center'
  r=b.route(r0['id'],pts,r0.get('source_road_ids',[]),r0['test_scope']);r.update({k:v for k,v in r0.items()if k!='both_directions'})
  r['length_m']=sum(math.dist(a,c)for a,c in zip(pts,pts[1:]));r['cart_test']=r0.get('cart_test',True);routes.append(r)
  if r0.get('both_directions',True):
   rev=copy.deepcopy(r);rev.update(id=r['id']+'_REVERSE',points=list(reversed(pts)));routes.append(rev)
 assert routes and len({r['id']for r in routes})==len(routes)
 groups={}
 for r in routes:groups.setdefault(r['group'],[]).append(r)
 out.mkdir();(out/'geometry').mkdir();(out/'evidence').mkdir();(out/'source_snapshots').mkdir()
 assets={};placements={};buildings={};audit=[];cache={};disabled={pid for c in scene.get('collision_contracts',[])for pid in c.get('disable_native_mesh_collider_ids',[])}
 def get_native(key):
  if key not in cache:
   a=assets_in[key];p=resolve({'path':a['render_path'],'sha256':a['render_sha256']});cache[key]=read(p)
  return cache[key]
 # Select all groups simultaneously so the 1.4M scene faces are examined once per material.
 selections={}
 for group,rs in groups.items():
  pts=[p for r in rs for p in r['points']];bb=b.bounds(pts);margin=float(request.get('collision_margin_m',6));bb=[bb[0]-margin,bb[1]-margin,bb[2]+margin,bb[3]+margin]
  selections[group]={'points':pts,'bounds':bb,'triangles':[],'faces':[],'water':0}
 for mat,verts in scene['surfaces'].items():
  arr=np.asarray(verts,dtype=np.float64).reshape(-1,3,3);xmin=arr[:,:,0].min(1);xmax=arr[:,:,0].max(1);zmin=arr[:,:,2].min(1);zmax=arr[:,:,2].max(1)
  for group,s in selections.items():
   bb=s['bounds'];chosen=np.nonzero((xmin<=bb[2])&(xmax>=bb[0])&(zmin<=bb[3])&(zmax>=bb[1]))[0]
   for raw in chosen:
    i=int(raw);ts=edits.get((mat,i),[verts[i*3:i*3+3]])
    for j,t in enumerate(ts):
     if not b.overlaps(b.bounds(t),bb):continue
     if mat=='water':s['water']+=1;continue
     s['triangles'].append([t[0],t[2],t[1]]);s['faces'].append({'material':mat,'base_triangle_index':i,'replacement_index':j if(mat,i)in edits else None})
  del arr,xmin,xmax,zmin,zmax
 for mat,verts in patch['appended_surfaces'].items():
  for i in range(0,len(verts),3):
   t=verts[i:i+3]
   for s in selections.values():
    if not b.overlaps(b.bounds(t),s['bounds']):continue
    if mat=='water':s['water']+=1;continue
    s['triangles'].append([t[0],t[2],t[1]]);s['faces'].append({'material':mat,'appended_triangle_index':i//3})
 removed_boxes=set(patch.get('removed_foundation_proxy_ids',[]))
 for group,s in selections.items():
  rs=groups[group];bb=s['bounds'];local,origin,proof=rebase(s['triangles'],s['points']);assert proof['applied_world_roundtrip_error_m']==0
  path=out/'geometry'/(group+'.json');write(path,{'schema':'riverstone.actual_scene_collision_triangles.v1','base_scene_sha256':BASE_SHA,'finite_patch_sha256':sha(patch_path),'visual_index_sha256':sha(index_path),'source_face_indices':s['faces'],'triangles':local,'selection_bounds_xz_m':bb,'local_origin_proof':proof,'whole_triangles_only':True,'height_resampling':False})
  key='SCENE:R9:GATE:'+group;assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':sha(path),'collision_format':'actual_scene_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':origin,'category':'actual_r9_resolved_scene_surface','collision_layer':1};ids=[key];natives=[];boxids=[]
  for item in instances:
   key=item['asset_key'];a=assets_in[key];bounds=a.get('bounds')or get_native(key)['bounds']
   if not b.overlaps(b.instance_bounds(item,bounds),bb):continue
   assert item['id']not in disabled,'Local native replacement policy requires explicit extraction: '+item['id']
   data=get_native(key);assert not data.get('rigid_parts'),'Explicit dynamic rigid-part state required'
   assets[key]={'render_path':a['render_path'],'render_sha256':a['render_sha256']};placements[item['id']]=dict(item,category='actual_native_common_mesh',collision_layer=3,yaw_deg=math.degrees(item.get('yaw_rad',0)));ids.append(item['id']);natives.append(item['id'])
  for item in scene['boxes']:
   if item['id']in removed_boxes:continue
   bounds={'min':[-v/2 for v in item['size_m']],'max':[v/2 for v in item['size_m']]}
   if not b.overlaps(b.instance_bounds(item,bounds),bb):continue
   buildings[item['id']]={'id':item['id'],'position_m':item['position_m'],'yaw_rad':item.get('yaw_rad',0),'boxes':[bounds],'collision_layer':3};boxids.append(item['id'])
  for contract in scene.get('collision_contracts',[]):
   assert not any(b.overlaps(b.bounds(t),bb)for t in contract.get('add_triangles_world_xyz_m',[])),'Local existing special collision contract requires explicit extraction: '+contract['id']
  for r in rs:r.update(placement_ids=ids,building_ids=boxids,collision_bounds_xz_m=bb)
  audit.append({'group':group,'bounds_xz_m':bb,'scene_triangles':len(local),'native_ids':natives,'box_ids':boxids,'excluded_water_display_triangles':s['water'],'local_origin_proof':proof})
 # Exact retained baseline controls. No invented wall/gap geometry.
 controls_path=BASE/'revisions/r04_r6_winding/prepared.json';controls=read(controls_path);sources['unchanged_control_manifest']=ref(controls_path)
 for ident in ['NEGATIVE_UNBRIDGED_RIVER','NEGATIVE_ACTUAL_SOLID_WALL']:
  r=copy.deepcopy(next(r for r in controls['routes']if r['id']==ident));r['cart_test']=False;r['group']='ISOLATED_CONTROL';routes.append(r)
  for pid in r['placement_ids']:
   p=copy.deepcopy(controls['placements'][pid]);a=copy.deepcopy(controls['assets'][p['asset_key']]);resolve({'path':a['render_path'],'sha256':a['render_sha256']});placements[pid]=p;assets[p['asset_key']]=a
 # Native collider wall control also runs the cart shape without support certification,
 # because its retained floor fixture is only 2 m wide, less than a full cart length.
 implementations=[pathlib.Path(__file__),ROOT/'world_city/concept_city_v3/registered_integration/r6/merge_patches.py',ROOT/'world_city/concept_city_v3/registered_integration/r8/collision_local_origin.py',ROOT/'world_city/concept_city_v3/registered_integration/r8/runtime_precision.py',BASE/'prepare.py',ROOT/'world_city/concept_city_v3/preview_r9/VisualAddendum.gd',ROOT/'world_city/concept_city_v3/preview_r9/FiniteSurfaceReplacement.gd']
 for name,src in [('Traversal.gd',BASE/'Traversal.gd'),('RenderData.gd',ROOT/'voxel_character/common/preview/RenderData.gd'),('Traversal.tscn',BASE/'Traversal.tscn'),('project.godot',BASE/'project.godot'),('run.sh',BASE/'run.sh'),('CartClearance.gd',H/'CartClearance.gd'),('CartClearance.tscn',H/'CartClearance.tscn')]:
  target=out/name;target.write_bytes(src.read_bytes());implementations.append(target)
 assert sha(out/'Traversal.gd')==sha(BASE/'Traversal.gd')and sha(out/'RenderData.gd')==sha(ROOT/'voxel_character/common/preview/RenderData.gd')
 snapshots={}
 for p in implementations:
  snapshot=out/'source_snapshots'/(sha(p)[:12]+'_'+p.name)
  if not snapshot.exists():snapshot.write_bytes(p.read_bytes())
  snapshots[str(p.relative_to(ROOT))]=ref(snapshot)
 d={'schema':'riverstone.r9.gate_bounded_physics.v1','repo_root':str(ROOT),'sources':sources,'implementation_hashes':{str(p.relative_to(ROOT)):sha(p)for p in implementations},'implementation_snapshots':snapshots,'assets':assets,'placements':placements,'buildings':buildings,'routes':routes,'cart_fixture':request['cart_fixture'],'coverage':{'cases':len(routes),'collision_audit':audit,'native_composition':native_composition,'new_gate_routes':request.get('gates',[])},'assumptions':['Hash-bound in-memory resolved base + exact finite patch + visual packs; no whole-city export.','Unchanged traversal_r5 capsule radius 0.3 m, height 1.8 m and movement; no step-up or support snapping.','Whole scene triangles with exact City.gd winding and exactly reversible local translation; original cached native mesh quads through unchanged RenderData.','Water display triangles are not support; all local special collision policies must be explicitly handled or preparation rejects.','Cart fixture is kinematic rigid-envelope clearance and four ground supports only; no vehicle dynamics, suspension, wheel rolling, traction or steering-radius claim.','Bounded routes and probes do not certify every possible city traversal.']}
 write(out/'prepared.json',d);write(out/'evidence/preparation.json',{'status':'prepared_not_executed','prepared':ref(out/'prepared.json'),'source_refs':sources,'coverage':d['coverage'],'elapsed_s':time.monotonic()-start})
 print(json.dumps({'output':str(out),'cases':len(routes),'groups':[{'group':r['group'],'triangles':r['scene_triangles'],'native_instances':len(r['native_ids'])}for r in audit],'elapsed_s':time.monotonic()-start},indent=2))
if __name__=='__main__':main()
