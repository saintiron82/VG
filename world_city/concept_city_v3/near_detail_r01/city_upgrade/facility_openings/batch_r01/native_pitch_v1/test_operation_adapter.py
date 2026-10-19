"""Actual six-source structural tests and explicit negative contracts; no compile."""
import copy,json
from pathlib import Path
import operation_roof_adapter_v1 as a
HERE=Path(__file__).resolve().parent;B=HERE.parent

def main():
 policy=a.load(B/'gate_headers_r01/rules.json')['policy'];catalog={r['asset_key']:r for r in a.load(B.parent.parent/'facility_roofs/activation_plan/all_72_layered_compile_catalog.v6.json')['assets']};tests={};summaries=[];keys=a.load(HERE/'sources_r01/rules.json')['assets']
 for key in keys:
  r=catalog[key];src=a.checked_load(a.ROOT/r['source_master_path'],r['source_sha256']);roof=a.checked_load(a.ROOT/r['emitted_master_path'],r['emitted_master_sha256']);render=a.checked_load(a.ROOT/r['source_render_path'],r['source_render_sha256']);combined,proof=a.compose_master(src,src,roof,policy);scope=a.replacement_scope(src,render,proof,policy);selected={(x['component'],x['operation']) for x in proof['selected_source_operations']};out={c['id']:c for c in combined['components']};unchanged=all([o for o in c['operations'] if (c['id'],o['id']) not in selected]==[o for o in out[c['id']]['operations'] if not any(o['id']==x for row in proof['selected_source_operations'] if row['component']==c['id'] for x in row['replacement_operation_ids'])] for c in src['components']);tests[key+'_nonroof_order_and_cuts_exact']=unchanged;tests[key+'_instances_constraints_exact']=src['instances']==combined['instances'] and src.get('constraints')==combined.get('constraints') and src.get('assembly_cuts')==combined.get('assembly_cuts');tests[key+'_source_component_parts_exact']=all({k:v for k,v in c.items() if k!='operations'}=={k:v for k,v in out[c['id']].items() if k!='operations'} for c in src['components']);summaries.append({'asset_key':key,'source_sha256':r['source_sha256'],'roof_sha256':r['emitted_master_sha256'],'selected_original_operations':len(selected),'preserved_original_operations':len(proof['preserved_original_operations']),'preserved_cuts':sum(x['action']=='cut' for x in proof['preserved_original_operations']),'max_world_error_m':proof['max_world_geometry_error_m'],'source_groups':len(scope['exact_source_roof_groups'])})
 for key in ['registered_main_gate_header','registered_service_gate_header','registered_arcade_8']:
  r=catalog[key];src=a.load(a.ROOT/r['source_master_path']);roof=a.load(a.ROOT/r['emitted_master_path']);tests[key+'_default_master_and_proof_bytes_exact']=json.dumps(a.compose_master(src,src,roof,policy),sort_keys=True,separators=(',',':'))==json.dumps(a.old_compose(src,src,roof,policy),sort_keys=True,separators=(',',':'))
 r=catalog['registered_east_canal_small_mill_r01'];s=a.load(a.ROOT/r['source_master_path']);f=a.load(a.ROOT/r['emitted_master_path']);target=f['components'][0]['metadata']['provenance']['source_component'];original_id=f['components'][0]['metadata']['provenance']['source_operations'][0]
 def reject(name,src,window,roof):
  try:a.compose_master(src,window,roof,policy)
  except (a.base.UnsupportedContract,ValueError,KeyError):tests[name]=True
  else:tests[name]=False
 bad=copy.deepcopy(s);next(c for c in bad['components'] if c['id']==target).setdefault('metadata',{})['dynamic']=True;reject('reject_dynamic_component',bad,bad,f)
 bad=copy.deepcopy(s);new=copy.deepcopy(next(i for i in bad['instances'] if i['component']==target));new['id']+='__duplicate';bad['instances'].append(new);reject('reject_shared_source_instance',bad,bad,f)
 bad=copy.deepcopy(f);bad['components'][0]['metadata']['provenance']['source_operations']=['unknown'];reject('reject_unknown_source_operation',s,s,bad)
 bad=copy.deepcopy(f);bad['components'][0]['metadata']['provenance']['source_operations']=[original_id,original_id];reject('reject_multi_source_operation_binding',s,s,bad)
 bad=copy.deepcopy(f);bad['components'][0]['operations'][0]['material']='stone';reject('reject_changed_finished_material',s,s,bad)
 bad=copy.deepcopy(s);next(c for c in bad['components'] if c['id']==target)['operations'].append({'id':'feature_cut','action':'cut','part':'solid','selector':{'feature':original_id},'shape':{'kind':'box','min':[-1,-1,-1],'max':[1,1,1]}});reject('reject_feature_selector_on_roof',bad,bad,f)
 bad=copy.deepcopy(s);bad['id']+='__window_revision';reject('reject_changed_window_source',s,bad,f)
 combined,proof=a.compose_master(s,s,f,policy);bad=copy.deepcopy(s);next(c for c in bad['components'] if c['id']==target)['operations'][0]['material']='slate'
 try:a.replacement_scope(bad,a.load(a.ROOT/r['source_render_path']),proof,policy)
 except a.base.UnsupportedContract:tests['reject_nonselected_roof_material_overlap']=True
 r=catalog['r10_market_low_head_draw'];ms=a.load(a.ROOT/r['source_master_path']);mf=a.load(a.ROOT/r['emitted_master_path']);bad=copy.deepcopy(mf);bad['components'][0]['operations'].append({'id':'invalid_body_cut','action':'cut','part':'solid','shape':{'kind':'box','min':[-.2,.5,-.7],'max':[.2,1.3,-.4]},'metadata':{'subtractive_only':True}});reject('reject_detail_cut_over_prior_body',ms,ms,bad)
 assert all(tests.values()),tests
 report={'schema':'riverstone.operation_roof_adapter.tests.v1','all_pass':True,'tests':tests,'actual_sources':summaries,'compile_calls':0,'source_or_existing_cache_modified':False,'implementation_references':[{'path':str(p.relative_to(a.ROOT)),'sha256':a.sha(p)} for p in [Path(__file__),Path(a.__file__),Path(a.base.__file__),Path(a.core.__file__)]],'scope':'Structural source preservation and rejection checks; no occupancy, complete contact or runtime geometry acceptance claimed.'};(HERE/'operation_adapter_tests.json').write_text(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps({'all_pass':True,'tests':len(tests),'sources':summaries}))
if __name__=='__main__':main()
