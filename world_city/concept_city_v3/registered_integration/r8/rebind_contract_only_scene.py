"""Reuse verified terrain/native output for a strict collision-source-only rebind."""
import copy,json,time,sys
from pathlib import Path
from .build_scene import a,verify
from .runtime_precision import zero_mask,canonical

def main(old_binding_path,new_binding_path,old_authored_path,old_runtime_path,old_ledger_path,dest):
 start=time.monotonic();old=a.load(old_binding_path);new=a.load(new_binding_path)
 changed={k for k in old.keys()|new.keys()if old.get(k)!=new.get(k)}
 if changed-{'collision_contracts','source_stage'}:raise ValueError('Not a strict contract-only rebind: '+str(changed))
 authored=a.load(old_authored_path);runtime=a.load(old_runtime_path);ledger=a.load(old_ledger_path)
 if authored['r8_provenance']['binding_sha256']!=a.digest(old)or runtime['r8_provenance']['binding_sha256']!=a.digest(old):raise ValueError('Old binding mismatch')
 for key,path in [('source',old_authored_path),('runtime_scene',old_runtime_path)]:
  if ledger[key]['sha256']!=a.sha(Path(path)):raise ValueError('Changed precision source')
 oldc=[verify(r)for r in old['collision_contracts']];newc=[verify(r)for r in new['collision_contracts']]
 if [c['id']for c in oldc]!=[c['id']for c in newc]:raise ValueError('Contract identity/order changed')
 mapping={c['id']:c for c in newc};expected={c['id']:c for c in oldc};removed=0
 for oldrow,newrow in zip(oldc,newc):
  flat=[v for t in oldrow['add_triangles_world_xyz_m']for v in t];_,_,_,zero=zero_mask(flat);kept=[t for i,t in enumerate(oldrow['add_triangles_world_xyz_m'])if not zero[i]]
  if kept!=newrow['add_triangles_world_xyz_m']:raise ValueError('Nonzero contract face changed')
  derived={'add_triangles_world_xyz_m','status','retained_native_triangle_count','walking_triangle_count','replacement_world_mesh'}
  for k in oldrow:
   if k not in derived and oldrow[k]!=newrow.get(k):raise ValueError('Existing contract field changed '+k)
  if oldrow!=newrow:
   if newrow['status']!='EXACT_FLOAT32_ZERO_AREA_NORMALIZED_RUNTIME_PENDING':raise ValueError('Unexpected precision wrapper status')
   if sum(oldrow[k]-newrow[k]for k in ('retained_native_triangle_count','walking_triangle_count'))!=int(zero.sum()):raise ValueError('Count metadata is not the exact removal total')
   verify(newrow['replacement_world_mesh']);verify(newrow['source_authored_contract'])
  removed+=int(zero.sum())
 def update(scene):
  out=dict(scene);out['collision_contracts']=[]
  for row in scene['collision_contracts']:
   if row['id']in expected:
    if row!=expected[row['id']]:raise ValueError('Changed composed contract')
    out['collision_contracts'].append(copy.deepcopy(mapping[row['id']]))
   else:out['collision_contracts'].append(row)
  out['r8_provenance']=dict(scene['r8_provenance']);out['r8_provenance']['binding_sha256']=a.digest(new)
  assert all(out[k]==scene[k]for k in scene if k not in ('collision_contracts','r8_provenance'))
  return out
 authored=update(authored);runtime=update(runtime);dest=Path(dest);assert not dest.exists();dest.mkdir(parents=True)
 write=lambda p,j:p.write_text(json.dumps(j,separators=(',',':'),allow_nan=False)+'\n')
 ref=lambda p:dict(path=a.rel(p),sha256=a.sha(p))
 ap=dest/'authored_scene.json';rp=dest/'scene.json';write(ap,authored);write(rp,runtime)
 ledger=copy.deepcopy(ledger);ledger['source']=ref(ap);ledger['runtime_scene']=ref(rp);ledger['collision_contract_precision_audit']=[]
 for c in runtime['collision_contracts']:
  tris=c.get('add_triangles_world_xyz_m',[])
  if not tris:continue
  _,_,_,zero=zero_mask([v for t in tris for v in t]);assert not zero.any();ledger['collision_contract_precision_audit'].append(dict(id=c['id'],triangles=len(tris),exact_zero_area_triangles=0))
 ledger['reused_unchanged_terrain_proof']=dict(precision_ledger=ref(Path(old_ledger_path)),old_authored_scene=ref(Path(old_authored_path)),old_runtime_scene=ref(Path(old_runtime_path)),all_terrain_arrays_and_native_inputs_unchanged=True,implementation=ref(Path(__file__)))
 lp=dest/'runtime_precision_ledger.json';write(lp,ledger)
 report=dict(status='strict_contract_only_rebind_ready_for_unchanged_controller_replay',authored=ref(ap),runtime=ref(rp),ledger=ref(lp),new_binding=ref(Path(new_binding_path)),exact_zero_contract_faces_removed=removed,terrain_and_native_unchanged=True,clean_full_rebuild='Still mandatory in final archive smoke',seconds=time.monotonic()-start);write(dest/'rebind_record.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main(*sys.argv[1:])
