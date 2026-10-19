"""Verify r02 against its own pinned common compiler, never mix r01 compiler."""
from pathlib import Path
import copy,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'evidence/compiler_snapshot/common'))
from core import compile_master,digest
from render_data import make_render_data
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def run():
 d=ROOT/'generated/violet';m=read(d/'master.json');ext=m['extensions'];manifest=read(d/'manifest.json');r=read(d/'character.render.json');measurement=ROOT.parent/'image_measured_r01/measurements/violet';a=read(ROOT/'data/annotations.json')['assets'][0]
 assert sha((ROOT/'data'/a['source']).resolve())==a['expected_sha256']==ext['source_sha256']
 assert sha(measurement/'measurements.json')==ext['measurement_sha256'];assert sha(measurement/'pixels.npz')==ext['pixel_data_sha256']
 assert sha(ROOT/'data/annotations.json')==ext['annotation_sha256'];assert sha(ROOT/'data/continuous_rules.json')==ext['rules_sha256']
 assert sha(ROOT/'tools/build_volume.py')==ext['generator_sha256'];assert sha(ROOT/'tools/continuous_fields.py')==ext['continuous_field_source_sha256']
 assert digest(m)==manifest['master_hash']
 for name,want in manifest['files'].items():assert sha(d/name)==want,name
 groups=[];records=[]
 for entry in r['provenance']['layers']:
  layer=copy.deepcopy(m);ids=set(ext['tier_operation_ids'][entry['tier']]);layer['components'][0]['operations']=[o for o in layer['components'][0]['operations'] if o['id'] in ids]
  c=compile_master(layer,{'pitch':entry['pitch']},max_candidate_cells=800000,max_output_cells=120000);expected=json.loads(gzip.decompress((d/entry['file']).read_bytes()))
  assert c==expected;render=make_render_data(c);assert render['provenance']==entry['common'];groups.extend(render['groups']);records.append({'tier':entry['tier'],'exact_recompile':True,'cells':len(c['cells']),'payload_hash':c['payload_hash']})
 assert groups==r['groups']
 result={'pass':True,'source_sha256':ext['source_sha256'],'master_hash':digest(m),'render_sha256':sha(d/'character.render.json'),'compiler_sha256':sha(ROOT/'evidence/compiler_snapshot/common/core.py'),'original_r01_compiler_sha256':'c4cc126554425211c7c670fefd0f97c22534ee5e489886354e0e00dd913f19e6','layers':records,'mesh_exact_match':True,'depth_is_assumed':True,'complete_character':False}
 (ROOT/'evidence/verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':run()
