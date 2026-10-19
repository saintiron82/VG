"""Compose small common-asset/finite-ground candidates without re-exporting city.
A duplicate source face is rejected: producer-side geometric reconciliation is required.
"""
import argparse,hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[4];sys.path.insert(0,str(R))
from world_city.concept_city_v3.registered_integration.r9.integrate_packs import integrate,BASE,BASE_SHA
from world_city.concept_city_v3.registered_integration.r6.merge_patches import merge,validate_against_scene

def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def resolve(s):
 p=(R/s).resolve();assert p.is_relative_to(R), 'Outside repository';return p

def compose(indices,packs,patches,output):
 out=resolve(output);assert not out.exists(),'Preserve earlier candidate'
 selected=[];seen={};sources=[]
 for name in indices:
  p=resolve(name);d=json.loads(p.read_text());assert d['base_scene_sha256']==BASE_SHA
  sources.append({'kind':'visual_index','path':str(p.relative_to(R)),'sha256':sha(p)})
  for ref in d['packs']:
   f=resolve(ref['path']);assert sha(f)==ref['sha256'],'Changed indexed pack'
   if ref['path']in seen:assert seen[ref['path']]==ref['sha256'],'Conflicting indexed pack'
   else:selected.append(ref['path']);seen[ref['path']]=ref['sha256']
 for name in packs:
  p=resolve(name);n=str(p.relative_to(R));digest=sha(p)
  if n in seen:assert seen[n]==digest
  else:selected.append(n);seen[n]=digest
 ground=[]
 for name in patches:
  p=resolve(name);ground.append(json.loads(p.read_text()));sources.append({'kind':'finite_patch','path':str(p.relative_to(R)),'sha256':sha(p)})
 merged=merge(ground,BASE_SHA);merged['id']='R10_COMPOSED_FUNCTIONAL_CANDIDATE'
 assert sha(BASE)==BASE_SHA
 scene=json.loads(BASE.read_bytes());validate_against_scene(scene,merged)
 for row in merged['surface_edits']:
  assert scene['surfaces'][row['material']][row['triangle_index']*3:row['triangle_index']*3+3]==row['source_triangle_xyz_m']
 del scene
 # Source validation above completes before writing the new directory.
 integrate(selected,output)
 (out/'surface_patch.json').write_text(json.dumps(merged,separators=(',',':'),allow_nan=False)+'\n')
 ledger={'status':'SOURCE_COMPOSED_RUNTIME_AND_VISUAL_REVIEW_PENDING','base_scene_sha256':BASE_SHA,'input_sources':sources,'surface_patch_sha256':sha(out/'surface_patch.json'),'visual_index_sha256':sha(out/'index.json'),'source_faces_modified':len(merged['surface_edits']),'appended_triangles':sum(len(v)//3 for v in merged['appended_surfaces'].values()),'limits':['No source triangle edited twice','No new whole-city mesh/collider export','Source disjointness does not prove cross-pack collision, support, paths or water service','Existing old493 does not certify this candidate']}
 (out/'candidate_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
 return ledger
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--index',action='append',default=[]);p.add_argument('--pack',action='append',default=[]);p.add_argument('--patch',action='append',default=[]);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(compose(a.index,a.pack,a.patch,a.output),indent=2))
