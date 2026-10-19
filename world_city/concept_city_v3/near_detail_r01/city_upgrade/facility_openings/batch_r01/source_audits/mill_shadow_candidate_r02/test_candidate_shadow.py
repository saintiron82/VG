"""Default bytes, source-bound operation selection and strict exclusion guards."""
from pathlib import Path
import copy,json,resource,sys
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));import candidate_shadow_helper as h

def main():
 tests=[];near=h.load(h.C/'playable_detail_r01/near_catalog.json')['assets'];key='registered_east_canal_small_mill_r01';m=h.load(h.ROOT/near[key]['composed_manifest_path']);contract=h.load(h.ROOT/m['replacement_contract_path']);src=h.load(h.ROOT/contract['source_master_path']);baseline=copy.deepcopy(src);data,evidence=h.derive(key);assert evidence['selection_mode']=='explicit_source_operations' and len(data['extrusions'])==2;tests.append({'name':'actual_mill_two_exact_source_operations','pass':True})
 for k in ['registered_main_gate_header','registered_arcade_8','registered_arcade_10','registered_cathedral_north_cloister_range']:
  d,e=h.derive(k);p=h.ROOT/near[k]['shadow_proxy_path'];raw=json.dumps(d,indent=2)+'\n';assert raw.encode()==p.read_bytes(),k;tests.append({'name':k+':existing_default_bytes_identical','pass':True,'path':str(p.relative_to(h.ROOT)),'sha256':h.sha(p)})
 def roof_cut(s,top):
  c=next(c for c in s['components'] if c['id']=='millhouse');o=next(o for o in c['operations'] if o['id']=='window_void_2.59');o['shape']={'kind':'box','min':[-5.7,2.4,2.59],'max':[-4.3,top,3.01]}
 def later_paint(s,bottom):
  c=next(c for c in s['components'] if c['id']=='millhouse');o=next(o for o in c['operations'] if o['id']=='drive_extension');o['shape']={'kind':'box','min':[-7,1,-3],'max':[-2,bottom,3]}
 for name,mut in [('cut_overlaps',lambda s:roof_cut(s,3.0)),('cut_exactly_touches',lambda s:roof_cut(s,2.9)),('cut_overlaps_below_old_epsilon',lambda s:roof_cut(s,2.9+1e-12)),('later_paint_overlaps',lambda s:later_paint(s,3.0)),('later_paint_exactly_touches',lambda s:later_paint(s,2.9))]:
  s=copy.deepcopy(src);mut(s)
  try:h.make_data(key,s,m['source_master_sha256'],near[key]['sha256'],contract)
  except AssertionError as e:tests.append({'name':name,'pass':True,'refusal':str(e)})
  else:raise AssertionError(name)
 for name,mut in [('contract_source_hash_wrong',lambda c:c.__setitem__('source_sha256','0'*64)),('duplicate_operation',lambda c:c['roof_replacement_scope']['source_roof_operations'].append(copy.deepcopy(c['roof_replacement_scope']['source_roof_operations'][0]))),('unknown_operation',lambda c:c['roof_replacement_scope']['source_roof_operations'][0].__setitem__('operation','unknown')),('operation_content_mutation',lambda c:c['roof_replacement_scope']['source_roof_operations'][0]['original_operation']['shape']['polygon'][0].__setitem__(1,99)),('world_transform_mutation',lambda c:c['roof_replacement_scope']['source_roof_operations'][0]['world_transform']['translation'].__setitem__(0,.05)),('exclusive_scope_unproven',lambda c:c['roof_replacement_scope'].__setitem__('exclusive_source_material_ownership_verified',False))]:
  c=copy.deepcopy(contract);mut(c)
  try:h.make_data(key,src,m['source_master_sha256'],near[key]['sha256'],c)
  except AssertionError as e:tests.append({'name':name,'pass':True,'refusal':str(e)})
  else:raise AssertionError(name)
 s=copy.deepcopy(src);roof_cut(s,2.89);h.make_data(key,s,m['source_master_sha256'],near[key]['sha256'],contract);tests.append({'name':'strict_positive_gap_accepted','pass':True});assert src==baseline;tests.append({'name':'inputs_immutable','pass':True})
 print(json.dumps({'schema':'riverstone.operation_shadow_candidate.tests.v1','all_pass':True,'count':len(tests),'tests':tests,'helper_sha256':h.sha(h.__file__),'test_sha256':h.sha(__file__),'compile_calls':0,'runtime_catalog_changed':False,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},separators=(',',':')))
if __name__=='__main__':resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));main()
