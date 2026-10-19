"""District-scale finite placement orchestration over sealed R7; no new engine."""
import copy,json,time,sys
from pathlib import Path
from ..r6 import apply_packs as a,merge_patches
from ..r7 import surface_guard
from .promotion import palette_catalog,resolve_palettes,explicit_retirements
from .compose_finite_patches import compose
from .runtime_contracts import append_collision_contracts,append_water_extensions
from ...registered_topography.revisions.r15_merchant_local_patch import frozen
BASE_SHA='1429ae51b7c72b12940dcf0dd7e12c2684cab95f81735d228bba64dc819317c1'
HERE=Path(__file__).resolve().parent

def verify(row):return a.load(a.source_file(row['path']),row['sha256'])
def build(binding):
 start=time.monotonic()
 def progress(label):
  if binding.get('trace_build_progress',False):print('R8 build',label,'seconds',round(time.monotonic()-start,3),flush=True)
 if binding['base_scene']['sha256']!=BASE_SHA:raise ValueError('Expected sealed actual R7')
 scene=verify(binding['base_scene'])
 progress('base loaded')
 for row in binding['evidence']:verify(row)
 patches=[verify(r) for r in binding['patches']]
 for patch in patches:surface_guard.audit_patch(patch)
 progress('producer patches verified')
 merged=compose(scene,patches,base_scene_sha256=BASE_SHA,physical_side_retirements=binding.get('finite_physical_side_retirement_union',False));merged['id']='R8_DISTRICT_COMPOSED_LOCAL_EDITS';merge_patches.validate_against_scene(scene,merged)
 progress('finite source ownership composed')
 out=frozen.apply_edits(scene,merged);out['local_terrain_patch']['base_scene_sha256']=BASE_SHA
 catalog=palette_catalog(scene);ledgers=[];palette_bindings=[]
 for row in binding['packs']:
  pack=verify(row);pack,resolutions=resolve_palettes(pack,catalog);palette_bindings+=resolutions
  out,ledger=a.apply_pack(out,pack,row['name'],dict(path=row['path'],sha256=row['sha256']),extra_retire_ids=explicit_retirements(pack));ledgers.append(ledger)
  if pack.get('collision_contracts'):out['collision_contracts']=copy.deepcopy(out.get('collision_contracts',[]))+copy.deepcopy(pack['collision_contracts'])
  progress('native pack '+row['name'])
 out['materials']=copy.deepcopy(scene['materials'])
 for k,v in binding.get('new_materials',{}).items():
  if k in out['materials'] and out['materials'][k]!=v:raise ValueError('Protected material changed')
  out['materials'][k]=v
 if set(out['surfaces'])-set(out['materials']):raise ValueError('Missing terrain material')
 out=append_collision_contracts(out,[verify(r)for r in binding.get('collision_contracts',[])])
 out=append_water_extensions(out,scene,[verify(r)for r in binding.get('water_extensions',[])])
 if binding.get('residual_land_use_plans'):
  from .landuse_dispositions import apply_bound
  out,reports=apply_bound(out,binding['residual_land_use_plans'])
  out['r8_residual_land_use']=[{k:v for k,v in report.items()if k!='seconds'}for report in reports]
  progress('finite same-plane residual land uses applied')
 out['inspection_cameras']=copy.deepcopy(scene['inspection_cameras'])
 for k,v in binding.get('review_cameras',{}).items():
  if k in out['inspection_cameras']:raise ValueError('Protected camera overwrite')
  out['inspection_cameras'][k]=copy.deepcopy(v)
 out['counts']=dict(out['counts']);out['counts'].update(common_instances=len(out['common_instances']),actual_remaining_proxy_boxes=len(out['boxes']),support_proxies=len(out['boxes']),terrain_triangles=sum(len(v)//3 for v in out['surfaces'].values()),r8_local_patches=len(patches))
 used={p['asset_key'] for p in out['common_instances']}|set(out['bridge_mechanism']['asset_keys']);out['common_assets']={k:v for k,v in out['common_assets'].items() if k in used};out['counts']['common_unique_assets']=len(used)
 a.validate_instances(out);guard=surface_guard.audit_scene(out)
 progress('instance and top winding guards passed')
 assert scene['inspection_cameras']['registered']==out['inspection_cameras']['registered']
 assert scene['surfaces']['water']==out['surfaces']['water'][:len(scene['surfaces']['water'])] and scene['bridge_mechanism']==out['bridge_mechanism']
 out['status']='r8_district_candidate_pending_actual_view_and_traversal';out['limits']=binding['limits'];out['r8_provenance']=dict(binding_sha256=a.digest(binding),base_scene=binding['base_scene'],pack_ledgers=ledgers,palette_bindings=palette_bindings,whole_city_complete=False)
 return out,merged,guard

def main(binding_path,destination):
 start=time.monotonic();dest=Path(destination);dest.mkdir(parents=True,exist_ok=True);p=dest/'scene.json';assert not p.exists(),'Preserve prior candidate'
 binding=a.load(binding_path);scene,patch,guard=build(binding)
 for name,data in [('scene.json',scene),('patch.json',patch),('surface_guard.json',guard)]:
  (dest/name).write_text(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n')
 report=dict(status=scene['status'],scene_sha256=a.sha(p),counts=scene['counts'],seconds=time.monotonic()-start);(dest/'build_record.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main(*sys.argv[1:])
