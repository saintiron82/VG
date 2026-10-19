"""Bind reviewed geometry candidates; preserve fine mesh, source and colliders."""
from pathlib import Path
import json,gzip,hashlib,argparse
H=Path(__file__).resolve().parent;R=H.parents[3];C=H.parents[1]
def load(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,default=H/'far_roof_lod_r01/expansion_r01/integration_manifest.json');args=parser.parse_args();mp=args.manifest.resolve();assert mp.is_relative_to(H.resolve());m=load(mp);assert m['all_pass'];p=C/'playable_detail_r01/near_catalog.json';cat=load(p);idx=load(C/'playable_r01/generated/tile_r01/index.json')['common_assets'];results=[]
 for c in m['entries']:
  k=c['asset_key'];e=cat['assets'][k];source=idx[k];assert not e.get('source_revision')
  assert c['all_pass'] and all(c['tests'].values()) and not c['collision_reference_changed'] and not c['near_render_changed'] and not c['source_master_changed']
  for key,expected in [('master',source['master_sha256']),('render',source['render_sha256'])]:assert c['original_source_'+key+'_sha256']==expected
  assert c['near_render_identity_observed']['sha256']==e['sha256'] and sha(R/c['render_path'])==c['render_sha256']
  proof=c['candidate_provenance'];assert sha(R/proof['path'])==proof['sha256'];q=load(R/proof['path']);assert q['all_geometry_tests_pass'] and q['render']['sha256']==c['render_sha256'] and q['asset_key']==k and q['source_master']['sha256']==source['master_sha256'] and q['baseline_far_render']['sha256']==source['render_sha256'] and q['input_contract']==c['source_roof_input_contract']
  inp=c['source_roof_input_contract'];assert sha(R/inp['path'])==inp['sha256'];input_proof=load(R/inp['path']);assert input_proof['status']=='SUPPORTED_INPUT_UNBUILT' and input_proof['schema']=='riverstone.source_roof_lod_input.v1' and input_proof['asset_key']==k and input_proof['source_master']['sha256']==source['master_sha256'] and input_proof['baseline_far_render']['sha256']==source['render_sha256']
  old=load(R/source['render_path']);new=load(R/c['render_path']);roof=set(input_proof['materials']);assert new['materials']==old['materials']
  c=dict(c,owned_roof_materials=sorted(roof))
  assert {g['material']:g for g in old['groups']if g['material']not in roof}=={g['material']:g for g in new['groups']if g['material']not in roof}
  c=dict(c,schema='riverstone.source_roof_far_visual.v1',integration_manifest={'path':str(mp.relative_to(R)),'sha256':sha(mp)})
  out=mp.parent/k/'runtime.contract.json';encoded=json.dumps(c,indent=2)+'\n'
  if out.exists():assert out.read_text()==encoded
  else:out.write_text(encoded)
  e.update(far_visual_contract_path=str(out.relative_to(R)),far_visual_contract_sha256=sha(out),far_visual_render_path=c['render_path'],far_visual_render_sha256=c['render_sha256'])
  results.append({'asset':k,'quads':c['output_quad_count'],'fine_changed':False,'collision_changed':False})
 p.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n');print(json.dumps(results))
if __name__=='__main__':main()
