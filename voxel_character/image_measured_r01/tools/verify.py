"""Independently recompile every tier, verify hashes, occupancy and mesh geometry."""
from pathlib import Path
import copy,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT.parent/'common'))
from core import compile_master,digest
from render_data import make_render_data
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(aid):
 d=ROOT/'generated'/aid;m=read(d/'master.json');manifest=read(d/'manifest.json');ext=m['extensions'];measure=ROOT/'measurements'/aid;measurement=read(measure/'measurements.json');a=next(x for x in read(ROOT/'data/annotations.json')['assets'] if x['id']==aid)
 assert sha((ROOT/'data'/a['source']).resolve())==a['expected_sha256']==ext['source_sha256']==manifest['source_sha256']
 assert sha(measure/'measurements.json')==ext['measurement_sha256'];assert sha(measure/'pixels.npz')==ext['pixel_data_sha256']
 assert sha(ROOT/'data/annotations.json')==ext['annotation_sha256']==measurement['annotation_sha256']
 assert sha(ROOT/'tools/measure.py')==measurement['extraction_code_sha256']
 assert sha(ROOT/'data/volume_rules.json')==ext['rules_sha256'];assert sha(ROOT/'tools/build_volume.py')==ext['generator_sha256']
 assert digest(m)==manifest['master_hash']
 for name,want in measurement['files'].items():assert sha(measure/name)==want,(aid,name)
 for name,want in manifest['files'].items():assert sha(d/name)==want,(aid,name)
 render=read(d/'character.render.json');layers=[];groups=[];count=0;cells=[]
 for entry in render['provenance']['layers']:
  layer=copy.deepcopy(m);ids=set(ext['tier_operation_ids'][entry['tier']]);layer['components'][0]['operations']=[o for o in layer['components'][0]['operations'] if o['id'] in ids]
  rebuilt=compile_master(layer,{'pitch':entry['pitch']},max_candidate_cells=600000,max_output_cells=120000)
  original=json.loads(gzip.decompress((d/entry['file']).read_bytes()))
  assert rebuilt==original,'Independent common compile mismatch'
  newrender=make_render_data(rebuilt);assert newrender['provenance']==entry['common'];groups.extend(newrender['groups']);count+=len(rebuilt['cells']);cells.extend([(r,entry['pitch']) for r in rebuilt['cells']]);layers.append({'tier':entry['tier'],'cell_count':len(rebuilt['cells']),'payload_hash':rebuilt['payload_hash'],'exact_recompile':True})
 assert groups==render['groups'];assert count==render['cell_count']==manifest['cells']
 assert render['bounds']['max'][2]-render['bounds']['min'][2]>.20
 assert all(len(q)==4 for g in groups for q in g['quads'])
 return {'id':aid,'pass':True,'layers':layers,'total_cells':count,'quads':render['quad_count'],'depth_extent_m':render['bounds']['max'][2]-render['bounds']['min'][2],'common_mesh_exact_match':True,'textures_or_image_planes':False,'rigged_character':False,'depth_accuracy_validated':False,'source_sha256':manifest['source_sha256'],'master_hash':manifest['master_hash'],'render_sha256':sha(d/'character.render.json')}

if __name__=='__main__':
 report={'schema':'riverstone.image_measured_verification.v1','pass':True,'assets':[verify(a) for a in ['violet','cyan']],'code_sha256':sha(Path(__file__))}
 (ROOT/'evidence/verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
