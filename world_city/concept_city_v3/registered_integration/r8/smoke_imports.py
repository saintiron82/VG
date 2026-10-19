"""Rebuild the exact chosen R8 binding without any original workspace reads."""
import hashlib,json,sys,pathlib
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def main(report_path,forbidden_original_root):
 root=ROOT.resolve();forbidden=pathlib.Path(forbidden_original_root).resolve();events=[]
 def audit(event,args):
  if event=='open'and args and isinstance(args[0],(str,bytes)):
   try:p=pathlib.Path(args[0]).resolve()
   except (ValueError,TypeError):return
   if p.is_relative_to(forbidden)and not p.is_relative_to(root):events.append(str(p));raise PermissionError('Hidden original workspace dependency: '+str(p))
 sys.addaudithook(audit)
 from . import build_scene
 manifest=json.loads((root/'INTEGRATED_R8_MANIFEST.json').read_text());ref=manifest['build_binding'];p=root/ref['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==ref['sha256']
 binding=json.loads(p.read_text());scene,patch,guard=build_scene.build(binding);raw=(json.dumps(scene,separators=(',',':'),allow_nan=False)+'\n').encode();authored=hashlib.sha256(raw).hexdigest();expected=manifest.get('authored_scene',manifest['actual_scene']);assert authored==expected['sha256'],(authored,expected['sha256'])
 runtime_proof=None
 if manifest.get('runtime_precision_ledger'):
  from .runtime_precision import normalize_surfaces
  ref=manifest['runtime_precision_ledger'];p=root/ref['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==ref['sha256'];ledger=json.loads(p.read_text());assert ledger['source']==expected
  precision_expected=manifest['actual_scene']
  if manifest.get('runtime_winding_ledger'):
   wr=manifest['runtime_winding_ledger'];wp=root/wr['path'];assert hashlib.sha256(wp.read_bytes()).hexdigest()==wr['sha256'];winding=json.loads(wp.read_bytes());precision_expected=winding['source_scene']
  assert ledger['runtime_scene']==precision_expected
  surfaces,records,summary,index_map=normalize_surfaces(scene['surfaces']);scene['counts']=dict(scene['counts']);scene['counts']['authored_terrain_triangles']=sum(len(v)//3 for v in scene['surfaces'].values());scene['surfaces']=surfaces;scene['counts']['terrain_triangles']=sum(len(v)//3 for v in surfaces.values())
  assert records==ledger['removals'] and summary==ledger['material_summary'];ref=ledger['retained_source_index_map'];p=root/ref['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==ref['sha256'];assert index_map==json.loads(p.read_text());runtime_proof=dict(exact_float32_removals=len(records),all_nonzero_triangles_preserved=True)
 if manifest.get('runtime_winding_ledger'):
  from ...registered_topography.revisions.r17_district_batches.final23_precision_continuation_r01.runtime_winding import apply_runtime
  raw=(json.dumps(scene,separators=(',',':'),allow_nan=False)+'\n').encode();assert hashlib.sha256(raw).hexdigest()==winding['source_scene']['sha256']
  scene=apply_runtime(scene,winding);assert winding['derived_scene']==manifest['actual_scene'];runtime_proof['source_bound_winding_rows']=len(winding['rows'])
 raw=(json.dumps(scene,separators=(',',':'),allow_nan=False)+'\n').encode();actual=hashlib.sha256(raw).hexdigest();assert actual==manifest['actual_scene']['sha256'],(actual,manifest['actual_scene']['sha256'])
 report=dict(status='pass',exact_authored_scene_rebuild_sha256=authored,exact_scene_rebuild_sha256=actual,runtime_precision=runtime_proof,original_workspace_reads=events,common_assets=len(scene['common_assets']),counts=scene['counts'],terrain_guard=guard)
 pathlib.Path(report_path).write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main(*sys.argv[1:])
