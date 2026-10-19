"""Keep exact source evidence separate from a SHA-bound runtime data projection.
No runtime code changes. All placement fields except bulky proof dictionaries are
identical; evidence remains immutable and explicitly referenced per asset.
"""
from pathlib import Path
import argparse,copy,json,os,resource,subprocess,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import author_batch as p
R=p.R

def ref(path):return {'path':str(path.relative_to(R)),'sha256':p.sha(path)}
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(120,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def verify(rev):
 start=time.monotonic();full=H/rev;out=full/'compact_candidate';assert not out.exists();out.mkdir();source=full/'source_plan.json';catalog=full/'modules/catalog.json';plan=p.read(source);cat=p.read(catalog);proof=p.read(full/'candidate_geometry.json');assert proof['all_pass']and proof['source_plan']==ref(source)and proof['module_catalog']==ref(catalog)
 compact=copy.deepcopy(plan);rows=[]
 excluded_asset_fields=['source_polygon_owners','source_component_cuts','faces','excluded']
 for old,new in zip(plan['assets'],compact['assets']):
  for name in excluded_asset_fields:new.pop(name,None)
  for placement in new['placements']:placement.pop('source_semantic_cut_proof')
  new['full_source_proof']={**ref(source),'asset_key':old['asset_key'],'geometry_validation':ref(full/'candidate_geometry.json'),'source_application_audit':ref(full/'source_application_audit.json')}
  assert all(old[k]==new[k]for k in old if k not in excluded_asset_fields+['placements'])
  assert all({k:v for k,v in original.items()if k!='source_semantic_cut_proof'}==projected for original,projected in zip(old['placements'],new['placements']))
  rows.append({'asset_key':old['asset_key'],'all_nonproof_asset_fields_exact':True,'all_nonproof_placement_fields_exact':True,'source_identity_exact':True,'placements':len(new['placements'])})
 compact['provenance']={**compact['provenance'],'full_source_plan':ref(source),'compact_projection_author':ref(Path(__file__)),'removed_data':'Only inline source-ownership proof dictionaries and source-face/audit inventories; original evidence preserved by SHA references','runtime_consumed_fields_changed':False}
 cp=out/'source_plan.json';p.save(cp,compact);newcat=copy.deepcopy(cat);newcat['source_plan_sha256']=p.sha(cp);newcat['full_evidence_module_catalog']=ref(catalog);newcat['source_dependencies'][str(source.relative_to(R))]=p.sha(source);newcat['source_dependencies'][str(catalog.relative_to(R))]=p.sha(catalog);p.save(out/'modules.json',newcat);assert cat['modules']==newcat['modules']
 projection={'all_pass':True,'full_source_plan':ref(source),'full_module_catalog':ref(catalog),'compact_source_plan':ref(cp),'compact_module_catalog':ref(out/'modules.json'),'asset_rows':rows,'module_rows_exact':True,'runtime_fields_reviewed_against':ref(p.b.C/'playable_detail_r01/CityWorldAccessDetail.gd'),'omitted_fields_not_read_by_current_runtime':['source_semantic_cut_proof',*excluded_asset_fields],'full_plan_bytes':source.stat().st_size,'compact_plan_bytes':cp.stat().st_size,'production_binding_changed':False};p.save(out/'projection_identity.json',projection)
 env={**os.environ,'REPO_ROOT':str(R),'SOURCE_PLAN':str(cp),'MODULE_CATALOG':str(out/'modules.json'),'OUTPUT_REPORT':str(out/'godot_mesh_report.json'),'XDG_DATA_HOME':str(H/'xdg_data'),'XDG_CACHE_HOME':str(H/'xdg_cache'),'XDG_CONFIG_HOME':str(H/'xdg_config')}
 with (out/'godot_mesh.log').open('w')as log:proc=subprocess.run(['godot','--headless','--path',str(H/'mesh_validation'),'--script','res://verify.gd'],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120-(time.monotonic()-start),preexec_fn=limits)
 g=p.read(out/'godot_mesh_report.json')if(out/'godot_mesh_report.json').exists()else{};okay=proc.returncode==0 and g.get('all_pass',False)and g['placements']==sum(r['placements']for r in rows)and g['modules']==len(cat['modules']);result={'all_pass':okay,'exit_code':proc.returncode,'elapsed_seconds':time.monotonic()-start,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'address_space_limit_bytes':256*1024*1024,'wall_limit_seconds':120,'combined_output_bytes':p.output_bytes(),'projection_identity':ref(out/'projection_identity.json'),'source_geometry_rebuilt':False,'original_failure_preserved':(H/'validation'/(rev+'.unit_report.json')).is_file()}
 p.save(out/'process_report.json',result);print(json.dumps(result));print((out/'godot_mesh.log').read_text()[-200:]);return 0 if okay else 2
if __name__=='__main__':
 limits();ap=argparse.ArgumentParser();ap.add_argument('--revision',required=True,choices=list(p.BATCHES));args=ap.parse_args();raise SystemExit(verify(args.revision))
