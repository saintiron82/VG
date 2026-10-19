"""Independent regeneration against the preserved shared compiler snapshot."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'evidence/compiler_snapshot/common'))
from core import compile_master,digest
from render_data import make_render_data
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def verify(tag):
 aid=tag.split('_')[0];d=ROOT/'generated'/tag;m=json.loads(gzip.decompress((d/'master.json.gz').read_bytes()));ex=m['extensions'];ann=next(a for a in read(ROOT/'data/measurement_annotations.json')['assets'] if a['id']==aid)
 assert sha((ROOT/'data'/ann['original']).resolve())==ex['original_sha256']==ann['original_sha256'];assert sha((ROOT/'data'/ann['sheet']).resolve())==ex['turnaround_sha256']==ann['sheet_sha256'];assert sha(ROOT.parent/'reference_turnarounds_r01/prompts.json')==ex['prompt_sha256']
 assert sha(ROOT/'data/refinement_annotations.json')==ex['refinement_annotations_sha256'];assert sha(ROOT/'tools/refine_head.py')==ex['head_refiner_sha256']
 assert sha(ROOT/'measurements'/aid/'measurements.json')==ex['measurement_sha256'];assert sha(ROOT/'data/shared_rules.json')==ex['rules_sha256'];assert sha(ROOT/'data'/(aid+'_fitted_preset.json'))==ex['preset_sha256'];assert sha(ROOT/'tools/curved_master.py')==ex['generator_sha256']
 expected=json.loads(gzip.decompress((d/'compiled.cells.json.gz').read_bytes()));c=compile_master(m,{'pitch':.025},max_candidate_cells=1800000,max_output_cells=120000);assert c==expected,'Common recompile differs';r=make_render_data(c);actual=json.loads(gzip.decompress((d/'character.render.json.gz').read_bytes())) if (d/'character.render.json.gz').exists() else read(d/'character.render.json');assert r['groups']==actual['groups'];assert r['provenance']==actual['provenance']
 # All transformed grammar bases were validated by the unchanged common compiler.
 result={'tag':tag,'pass':True,'source_chain_verified':True,'independent_common_recompile_exact':True,'common_mesh_exact':True,'master_hash':digest(m),'payload_hash':c['payload_hash'],'source_sha256':ex['original_sha256'],'turnaround_sha256':ex['turnaround_sha256'],'compiler_sha256':c['compiler_source_hash'],'master_geometry':ex['geometry'],'depth_status':ex['hidden_views'],'appearance_approved':False,'cells':len(c['cells']),'quads':r['quad_count']};return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('tags',nargs='+');args=p.parse_args();results=[verify(tag) for tag in args.tags];(ROOT/'evidence/verification.json').write_text(json.dumps({'pass':True,'assets':results,'verifier_sha256':sha(Path(__file__))},indent=2)+'\n');print(json.dumps(results))
