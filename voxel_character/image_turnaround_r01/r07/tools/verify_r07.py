from pathlib import Path
import copy,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'r07';sys.path.insert(0,str(ROOT/'evidence/compiler_snapshot/common'))
from core import compile_master,digest
from render_data import make_render_data
CLOTH={'left_petal','right_petal','back_left_petal','back_right_petal','back_center_petal','front_short_panel'}
def read(p):return json.loads(gzip.decompress(p.read_bytes())) if p.suffix=='.gz' else json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
results=[]
for a in sys.argv[1:]:
 d=OUT/'generated'/(a+'_r07c');base=read(ROOT/'generated'/(a+'_curved06b')/'master.json.gz');m=read(d/'master.json.gz');e=m['extensions']['cloth_r07'];assert e['source_master_hash']==digest(base);assert e['adapter_sha256']==sha(OUT/'tools/fix_cloth.py');before=[o for o in base['components'][0]['operations'] if o['part'] not in CLOTH];after=[o for o in m['components'][0]['operations'] if o['part'] not in CLOTH];assert before==after;assert digest(after)==e['all_noncloth_operations_digest'];expected=read(d/'compiled.cells.json.gz');c=compile_master(m,{'pitch':.025},max_candidate_cells=3000000,max_output_cells=120000);assert c==expected;r=make_render_data(c);actual=read(d/'character.render.json.gz');assert r['groups']==actual['groups'] and r['provenance']==actual['provenance'];results.append({'asset':a,'exact_recompile':True,'exact_common_mesh':True,'noncloth_source_operations_unchanged':True,'base_master_hash':digest(base),'master_hash':digest(m),'payload_hash':c['payload_hash'],'compiler_sha256':c['compiler_source_hash'],'cells':len(c['cells']),'quads':r['quad_count'],'all_appearance_approved':False})
(OUT/'evidence/verification.json').write_text(json.dumps({'pass':True,'assets':results},indent=2)+'\n');print(json.dumps(results))
