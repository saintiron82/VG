"""Validate small common-assembly addenda without copying the 203 MB base scene."""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'world_city/concept_city_v3/evidence/r8_final110_runtime_r01/scene.json'
BASE_SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def resolved(path):
 p=(ROOT/path).resolve()
 if not p.is_relative_to(ROOT):raise ValueError('Outside repository '+str(path))
 return p
def pose(p):
 v=p.get('position_m',[])
 if len(v)!=3 or not all(isinstance(n,(int,float))and math.isfinite(n)for n in v):raise ValueError('Nonfinite pose '+p['id'])
 if not math.isfinite(p.get('yaw_rad',0))or p.get('scale',[1,1,1])!=[1,1,1]:raise ValueError('Invalid yaw/scale '+p['id'])
def integrate(paths,out):
 if sha(BASE)!=BASE_SHA:raise ValueError('Base changed')
 base=json.loads(BASE.read_bytes());assets=dict(base['common_assets']);ids={p['id']for p in base['common_instances']};adds=[];removes=set();refs=[];palettes={};replacements={};base_instances={p["id"]:p for p in base["common_instances"]}
 for p in base['common_instances']:palettes[(p['asset_key'],p['palette_id'])]=p.get('palette_override',{})
 for name in paths:
  f=resolved(name);pack=json.loads(f.read_bytes())
  if pack['schema']!='riverstone.city.visual_addendum.v1'or pack['base_scene_sha256']!=BASE_SHA:raise ValueError('Pack binding '+name)
  for key,a in pack.get('common_assets',{}).items():
   if key in assets and assets[key]['render_sha256']!=a['render_sha256']:raise ValueError('Asset collision '+key)
   for kind in ('master','render'):
    if sha(resolved(a[kind+'_path']))!=a[kind+'_sha256']:raise ValueError('Changed '+kind+' '+key)
   if not all(math.isfinite(n)for side in ('min','max')for n in a['bounds'][side]):raise ValueError('Asset bounds '+key)
   assets[key]=a
  for id in pack.get('remove_instance_ids',[]):
   if id not in ids or id in removes or id in replacements:raise ValueError('Unknown/duplicate removal '+id)
   removes.add(id)
  for p in pack.get('add_instances',[]):
   if p['id']in ids:raise ValueError('Duplicate instance '+p['id'])
   pose(p)
   if p['asset_key']not in assets:raise ValueError('Missing asset '+p['asset_key'])
   palette_key=(p['asset_key'],p['palette_id']);override=p.get('palette_override',{})
   if palette_key in palettes and palettes[palette_key]!=override:raise ValueError('Material-cache identity collision '+str(palette_key))
   palettes[palette_key]=override;ids.add(p['id']);adds.append(p)
  for row in pack.get('replace_instances',[]):
   id=row['id'];original=base_instances.get(id)
   if original is None or id in replacements or id in removes:raise ValueError('Unknown/duplicate replacement '+id)
   if row['expected_asset_key']!=original['asset_key']or row['expected_position_m']!=original['position_m']or row.get('expected_yaw_rad',0)!=original.get('yaw_rad',0):raise ValueError('Replacement alters source pose '+id)
   if sha(resolved(row['proof_path']))!=row['proof_sha256']:raise ValueError('Changed replacement proof '+id)
   if row['asset_key']not in assets:raise ValueError('Missing replacement asset '+id)
   palette_key=(row['asset_key'],row['palette_id']);override=row.get('palette_override',{})
   if palette_key in palettes and palettes[palette_key]!=override:raise ValueError('Replacement palette alias '+id)
   palettes[palette_key]=override;replacements[id]=row
  refs.append({'path':name,'sha256':sha(f),'added_instances':len(pack.get('add_instances',[])),'removed_instances':len(pack.get('remove_instance_ids',[]))})
 out=resolved(out);out.mkdir(parents=True,exist_ok=False)
 index={'schema':'riverstone.city.visual_pack_index.v1','base_scene_sha256':BASE_SHA,'packs':[{'path':p['path'],'sha256':p['sha256']}for p in refs]}
 (out/'index.json').write_text(json.dumps(index,indent=2)+'\n')
 review={'status':'PASS_SOURCE_IDENTITY_AND_COMPOSITION','base_scene_sha256':BASE_SHA,'base_instances':len(base['common_instances']),'added_instances':len(adds),'removed_instances':len(removes),'total_instances':len(base['common_instances'])+len(adds)-len(removes),'pack_refs':refs,'terrain_faces_changed':0,'base_native_poses_modified':0,'same_pose_geometry_replacement_instances':len(replacements),'scale_policy':'Rigid native scale 1 only','material_cache_conflicts':0,'limits':'Source/bounds/ID/cache checks only. Per-pack static public-route and overlap checks and actual new visual review remain separately required. Existing493 is not silently re-labeled as an r9 runtime pass.'}
 (out/'composition.json').write_text(json.dumps(review,indent=2)+'\n');print(json.dumps(review,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--pack',action='append',required=True);a.add_argument('--output',required=True);o=a.parse_args();integrate(o.pack,o.output)
