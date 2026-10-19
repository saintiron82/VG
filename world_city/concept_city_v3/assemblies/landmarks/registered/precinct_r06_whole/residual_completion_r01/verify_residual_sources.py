"""Independent common regeneration and complete local reference closure."""
from pathlib import Path
import sys,json,time
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent

def main():
 t=time.monotonic();pack=load(OUT/'resolved_residual_placements.json');regen=[]
 for a in load(OUT/'compiled_assets.json')['assets']:
  master=load(ROOT/a['source']['path']);cache=load(ROOT/a['cache']['path']);compiled=coordinate_planes.compile_master(master,{'pitch':a['pitch_m']},max_candidate_cells=300000,max_output_cells=150000);fresh=render_data.make_render_data(compiled);regen.append({'id':a['id'],'source_hash_valid':sha(ROOT/a['source']['path'])==a['source']['sha256'],'cache_hash_valid':sha(ROOT/a['cache']['path'])==a['cache']['sha256'],'independent_regeneration_equal':core.digest(fresh)==core.digest(cache),'master_hash_bound':fresh['master_hash']==a['master_hash']})
 refs=[];missing=[];mismatch=[];outside=[]
 def scan(obj):
  if isinstance(obj,dict):
   if isinstance(obj.get('path'),str)and'sha256'in obj:
    p=ROOT/obj['path'];refs.append(obj)
    if Path(obj['path']).is_absolute()or'..'in Path(obj['path']).parts:outside.append(obj)
    if not p.is_file():missing.append(obj)
    elif sha(p)!=obj['sha256']:mismatch.append(obj)
   for v in obj.values():scan(v)
  elif isinstance(obj,list):
   for v in obj:scan(v)
 for name in ('resolved_residual_placements.json','residual_surface_patch.json','combined_ready21_residual_surface_patch.json','residual_crosspack_tests.json'):scan(load(OUT/name))
 for a in pack['assets']:scan(load(ROOT/a['source']['path']))
 common=load(BASE/'native_preflight.json')['source_dependencies']+load(OUT/'native_preflight.json')['common_dependencies']
 commonpass=all(sha(ROOT/r['path'])==r['sha256']for r in common)
 checks={'source_scene_unchanged':sha(terrain.SCENE_PATH)==terrain.SCENE_SHA256,'common_sources_unchanged':commonpass,'regeneration_pass':all(all(v for k,v in row.items()if k!='id')for row in regen),'all_local_references_valid':not(missing or mismatch or outside),'native_scale_one':all(p['scale']==[1,1,1]for p in pack['placements']),'crosspack_pass':load(OUT/'residual_crosspack_tests.json')['status']=='PASS','ground_pass':load(OUT/'residual_ground_tests.json')['status']=='PASS','training_static_pass':load(OUT/'training_walk_tests.json')['status']=='PASS'}
 report={'status':'PASS'if all(checks.values())else'FAIL','checks':checks,'independent_regeneration':regen,'reference_records_checked':len(refs),'missing':missing,'mismatched':mismatch,'outside_project':outside,'seconds':time.monotonic()-t,'actual_scene_or_runtime_replay':False};(OUT/'residual_source_cache_tests.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(refs),report['seconds'],mismatch[:2]);assert report['status']=='PASS'
if __name__=='__main__':main()
