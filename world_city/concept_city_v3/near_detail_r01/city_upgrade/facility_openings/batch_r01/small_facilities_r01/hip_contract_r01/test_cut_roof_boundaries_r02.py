"""Exact source-prefix restoration, rigid rotation and boundary refusal cases."""
import copy,json,resource,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));import compose_cut_roof as a
R=a.base.ROOT;B=HERE.parents[1];cat=a.base.load(B.parent.parent/'facility_roofs/activation_plan/all_72_layered_compile_catalog.v6.json');policy=a.base.load(B/'native_pitch_v1/sources_r03/rules.json')['policy']
def main():
 reports=[];cases=[]
 for key in ['r9_city_roofed_bartizan','r9_castle_roofed_bartizan']:
  r=next(r for r in cat['assets'] if r['asset_key']==key);s=a.base.checked_load(R/r['source_master_path'],r['source_sha256']);roof=a.base.checked_load(R/r['emitted_master_path'],r['emitted_master_sha256']);m,p=a.compose_master(s,s,roof,policy);restored=copy.deepcopy(m)
  for c in restored['components']:
   old=next(x for x in s['components'] if x['id']==c['id']);c['operations']=c['operations'][:len(old['operations'])]
  restored['id']=s['id']
  if 'provenance' in s:restored['provenance']=copy.deepcopy(s['provenance'])
  else:restored.pop('provenance',None)
  assert restored==s
  cuts=[]
  for bind in p['bindings']:
   c=next(x for x in m['components'] if x['id']==bind['source_component']);orig=next(x for x in s['components'] if x['id']==c['id']);t=a.base.transforms(m)[bind['source_instance']]
   for op in c['operations'][len(orig['operations']):]:
    sh=a.core.prepare_shape(op['shape'],.05);lo,hi=a.core.shape_bounds(sh);tr=a.core.compose(t,a.core.transform(op.get('transform')));points=[a.core.apply(tr,pt) for pt in a.base.itertools.product(*zip(lo,hi))];cuts.append({'id':op['id'],'operation_sha256':a.core.digest(op),'world_aabb':{'min':[min(v[j] for v in points) for j in range(3)],'max':[max(v[j] for v in points) for j in range(3)]}})
  reports.append({'asset_key':key,'original_master_sha256':r['source_sha256'],'finished_roof_sha256':r['emitted_master_sha256'],'original_complete_prefix_restored_semantic_sha256':a.core.digest(restored),'source_semantic_sha256':a.core.digest(s),'whole_source_equal_before_appended_detail':True,'added_cut_count':len(cuts),'added_cuts':cuts,'cut_scope':'Same original unique roof component and original part only. Cuts remove from that layer and cannot add any outside occupancy or erase other components. AABBs are actual finite cut ranges, not claims every bounding-box cell is occupied.'})
  for turn,basis in [('quarter_y',[[0,0,1],[0,1,0],[-1,0,0]]),('half_y',[[-1,0,0],[0,1,0],[0,0,-1]])]:
   ss=copy.deepcopy(s);rr=copy.deepcopy(roof);t={'basis':basis,'translation':[-12.5,-.25,-8.0]};next(i for i in ss['instances'] if i['id']=='roof')['transform']=t;rr['instances'][0]['transform']=t;rr['components'][0]['metadata']['shared_row_source']['instance_metadata']['source_identity']['transform']=t;mm,pp=a.compose_master(ss,ss,rr,policy);assert pp['max_world_geometry_error_m']<1e-12;cases.append({'name':key+':'+turn+':negative_position','pass':True})
  for name,mut in [('cut_boundary_epsilon',lambda rr:rr['components'][0]['operations'][1]['shape']['polygon'][0].__setitem__(1,rr['components'][0]['operations'][1]['shape']['polygon'][0][1]+1e-6)),('world_rotation_mismatch',lambda rr:rr['instances'][0].__setitem__('transform',{'basis':[[0,0,1],[0,1,0],[-1,0,0]],'translation':[0,0,0]})),('prefix_translation_half_fine_cell',lambda rr:rr['components'][0]['operations'][0]['transform']['translation'].__setitem__(0,.025))]:
   rr=copy.deepcopy(roof);mut(rr)
   try:a.compose_master(s,s,rr,policy)
   except a.base.UnsupportedContract as e:cases.append({'name':key+':'+name,'pass':True,'refusal':str(e)})
   else:raise AssertionError(name)
 print(json.dumps({'schema':'riverstone.original_cut_roof_contract.boundary_tests.v1','all_pass':True,'compile_calls':0,'actual_source_assets':reports,'cases':cases,'test_count':len(cases)+len(reports),'adapter_sha256':a.base.sha(a.__file__),'test_sha256':a.base.sha(__file__),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},separators=(',',':')))
if __name__=='__main__':resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));main()
