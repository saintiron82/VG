"""Structural and refusal regressions; no voxel compiler is called."""
from pathlib import Path
import copy,json,resource,sys
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));import compose_cut_roof as a
B=HERE.parents[1];R=a.base.ROOT;cat=a.base.load(B.parent.parent/'facility_roofs/activation_plan/all_72_layered_compile_catalog.v6.json');policy=a.base.load(B/'native_pitch_v1/sources_r03/rules.json')['policy'];tests=[]
def run():
 fixtures=[]
 for key in ['r9_city_roofed_bartizan','r9_castle_roofed_bartizan']:
  r=next(r for r in cat['assets'] if r['asset_key']==key);s=a.base.checked_load(R/r['source_master_path'],r['source_sha256']);roof=a.base.checked_load(R/r['emitted_master_path'],r['emitted_master_sha256']);m,p=a.compose_master(s,s,roof,policy);assert p['max_world_geometry_error_m']==0 and p['original_roof_operations_byte_preserved'];assert m['components'][:-1]==s['components'][:-1] and m['instances']==s['instances'];assert m['components'][-1]['operations'][:3]==s['components'][-1]['operations'];a.replacement_scope(s,a.base.load(R/r['source_render_path']),p,policy);tests.append({'name':key+':actual_source_preservation_and_scope','pass':True});fixtures.append((s,roof))
 s,roof=fixtures[0]
 mutations={
 'changed_original_cut_shape':lambda q:q['components'][0]['operations'][1]['shape']['polygon'][0].__setitem__(1,17.9),
 'changed_original_cut_order':lambda q:q['components'][0]['operations'].__setitem__(slice(1,3),list(reversed(q['components'][0]['operations'][1:3]))),
 'unknown_paint_after_prefix':lambda q:q['components'][0]['operations'].__setitem__(3,copy.deepcopy(q['components'][0]['operations'][0])|{'id':'newpaint'}),
 'unclassified_added_cut':lambda q:q['components'][0]['operations'][3]['metadata'].__setitem__('subtractive_only',False),
 'changed_prefix_transform':lambda q:q['components'][0]['operations'][1]['transform']['translation'].__setitem__(0,.05),
 'changed_source_cut_metadata':lambda q:q['components'][0]['metadata']['source_cuts'][0]['shape']['polygon'][0].__setitem__(1,17.9),
 'unknown_source_identity':lambda q:q['components'][0]['metadata']['shared_row_source']['instance_metadata']['source_identity'].__setitem__('instance','unknown'),
 'detail_selector':lambda q:q['components'][0]['operations'][3].__setitem__('selector',{}|{'part':'solid'}),
 'extra_finished_instance':lambda q:q['instances'].append(copy.deepcopy(q['instances'][0])|{'id':'duplicate'}),
 }
 for name,fn in mutations.items():
  q=copy.deepcopy(roof);fn(q)
  try:a.compose_master(s,s,q,policy)
  except a.base.UnsupportedContract as e:tests.append({'name':name,'pass':True,'refusal':str(e)})
  else:raise AssertionError(name)
 for name,fn in {'nonroof_source_mutation':lambda q:q['components'][0]['operations'][0]['shape']['max'].__setitem__(0,99),'extra_unknown_component':lambda q:q['components'].append(copy.deepcopy(q['components'][0])|{'id':'alien'}),'original_constraints_removed':lambda q:q.__setitem__('constraints',[])}.items():
  q=copy.deepcopy(s);fn(q)
  try:a.compose_master(s,q,roof,policy)
  except a.base.UnsupportedContract as e:tests.append({'name':name,'pass':True,'refusal':str(e)})
  else:raise AssertionError(name)
 print(json.dumps({'all_pass':True,'count':len(tests),'tests':tests,'compile_calls':0,'adapter_sha256':a.base.sha(a.__file__),'test_sha256':a.base.sha(__file__),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},separators=(',',':')))
if __name__=='__main__':resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));run()
