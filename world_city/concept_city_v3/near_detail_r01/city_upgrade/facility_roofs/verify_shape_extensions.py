"""Exact-source checks and small, native-bounded roof surface samples only."""
import argparse,collections,copy,gc,itertools,json,math,resource,time
from pathlib import Path
import author_facility_roofs as a
import finish_roofs as f
import expand_facilities as e
import extend_roof_shapes as x
import recheck_cell_bounds as native
OUT=x.OUT

def original_reference(d,source):
 materials=set(d['suppression']['safe_material_groups_when_full_matching_near_resource_ready'])|{r['material'] for r in d['suppression']['unsafe_material_groups']}
 if source.get('assembly_cuts'):raise ValueError('unhandled_assembly_cut_reference')
 m=a.new_master(source['id']+'__exact_all_roof_source',source['materials']);world=a.instance_transforms(source)
 for c in source['components']:
  if any(o.get('material') in materials and o['action']=='paint' for o in c['operations']):
   q=copy.deepcopy(c);q['operations']=[o for o in q['operations'] if o['action']=='cut' or o.get('material') in materials];m['components'].append(q)
 ids={c['id'] for c in m['components']}
 m['instances']=[{'id':i['id'],'component':i['component'],'transform':world[i['id']]} for i in source['instances'] if i['component'] in ids]
 return f.flatten(m)

def roi_cases(record,source,extra):
 r=record['shape_extensions'][0];kind=r['type'];p=r['parameters'];c=next(c for c in source['components'] if c['id']==r['source_component']);op=next(o for o in c['operations'] if o['id']==r['source_operation']);ins=next(i for i in source['instances'] if i['component']==c['id']);t=a.core.compose(a.instance_transforms(source)[ins['id']],a.core.transform(op.get('transform')));cases=[]
 if kind=='solid_square_hip':
  w,base,top,s=p['half_span_m'],p['base_y_m'],p['apex_y_m'],p['slope'];u=-w/2;v=top+s*u
  cases=[('hip_slope_course',[u-.4,v-.8,-.4],[u+.4,v+.8,.4])]
  if extra:
   rr=w/3;v=top-s*rr;cases += [('hip_diagonal_cap',[rr-.35,v-.8,rr-.35],[rr+.35,v+.8,rr+.35]),('hip_eave',[-w,base-.05,-.5],[-w+.5,base+s*.5+.1,.5])]
 elif kind=='conical_spire':
  base,top,s=p['base_y_m'],p['apex_y_m'],p['radial_slope'];v=base+1;r0=s*(top-v)
  cases=[('cone_curved_course',[r0-.5,v-.4,-.4],[r0+.2,v+.4,.4])]
  if extra:
   cap=record['shape_extensions'][0]['cap_starts_y_m'];cases += [('cone_apex_cap',[-.35,cap-.15,-.35],[.35,top+.05,.35]),('cone_eave',[p['base_radius_m']-.5,base,-.4],[p['base_radius_m']+.05,base+.5,.4])]
 else:
  lo,hi=p['original_bounds']['min'],p['original_bounds']['max'];cx=(lo[0]+hi[0])/2;cz=(lo[2]+hi[2])/2;cases=[('flat_cover_courses',[max(lo[0],cx-.5),lo[1]-.05,max(lo[2],cz-.5)],[min(hi[0],cx+.5),hi[1]+.05,min(hi[2],cz+.5)])]
 for name,low,high in cases:
  points=[a.core.apply(t,list(v)) for v in itertools.product(*zip(low,high))];yield name,f.bounds(points)

def exact_proofs(master,source,record):
 if master['materials']!=source['materials']:raise ValueError('original_materials_changed')
 if source.get('assembly_cuts'):raise ValueError('unhandled_original_assembly_cuts')
 world=a.instance_transforms(source);count=0;cutcount=0
 for c in master['components']:
  md=c['metadata']
  if not md.get('subtractive_subset_proof'):continue
  ident=md['shared_row_source']['instance_metadata']['source_identity'];sc=next(q for q in source['components'] if q['id']==ident['component']);src=next(o for o in sc['operations'] if o['id']==md['source_operation']['id']);cuts=[o for o in sc['operations'] if o['action']=='cut'];ops=c['operations'];t=world[ident['instance']]
  if md['source_operation']!=src or md['source_cuts']!=cuts:raise ValueError('metadata_not_exact_source')
  if any(o['action']!='cut' for o in ops[1:]):raise ValueError('added_positive_geometry')
  for actual,original in zip(ops,[src]+cuts):
   if actual['shape']!=original['shape'] or actual.get('material')!=original.get('material') or actual['part']!=original['part'] or actual.get('selector',{})!=original.get('selector',{}) or actual['transform']!=a.core.compose(t,a.core.transform(original.get('transform'))):raise ValueError('source_operation_changed')
  if len(ops)<=1+len(cuts):raise ValueError('missing_new_surface_detail')
  count+=1;cutcount+=len(cuts)
 if not count:raise ValueError('no_subtractive_proof_components')
 return count,cutcount

def main(representatives=False):
 rules=x.limited();start=time.perf_counter();catpath=OUT/('representative_catalog.json' if representatives else 'layered_compile_catalog.json');contractpath=OUT/('representative_contracts.json' if representatives else 'replacement_contracts.v4.json');cat=a.read(catpath);bundle=f.layers.load_master(f.OUT/'shape_support_descriptors.v2.json.gz')['assets'];reports=[];counts=collections.Counter();fail=[]
 for r in cat['assets']:
  key=r['asset_key'];d=bundle[r['native_asset_key']];m=f.layers.load_master(a.ROOT/r['emitted_master_path']);source=a.read(a.ROOT/r['source_master_path']);a.core.validate_master(m,.05);counts['schemas_revalidated']+=1
  if a.shared.sha(a.ROOT/r['emitted_master_path'])!=r['emitted_master_sha256'] or a.shared.sha(a.ROOT/r['source_master_path'])!=r['source_sha256'] or a.shared.sha(a.ROOT/r['source_render_path'])!=r['source_render_sha256']:raise ValueError('hash_mismatch:'+key)
  proven,kept=exact_proofs(m,source,r);counts['exact_subtractive_source_components']+=proven;counts['exact_original_component_cuts_retained']+=kept;counts['source_operations']+=r['operations'];original=original_reference(d,source)
  for name,(low,high) in roi_cases(r,source,key in rules['representatives']):
   near,_,cb=native.compile_roi(m,low,high,rules);old,_,_=native.compile_roi(original,low,high,rules);cells=native.rows(near);prior=native.rows(old);outside=cells-prior;removed=prior-cells
   if not cells or outside or not removed:raise ValueError(['roi_detail_or_containment_failed',key,name,len(cells),len(outside),len(removed)])
   render=OUT/'roi'/(key+'.'+name+'.render.json');a.write(render,a.make_render_data(near));rep={'asset_key':key,'case':name,'status':'PASS_SMALL_NATIVE_BOUNDED_SAMPLE','cell_bounds':cb,'cells':len(cells),'source_cells':len(prior),'removed_cells':len(removed),'outside_original_position_material_cells':len(outside),'quad_count':a.make_render_data(near)['quad_count'],'candidate_cells':near['candidate_cells'],'source_candidate_cells':old['candidate_cells'],'pruned_and_unpruned_native_samples_identical':True,'scoped_valid':near['valid'],'valid_scope':near.get('valid_scope'),'global_constraints_evaluated':near.get('global_constraints_evaluated'),'whole_asset_compile':False,'render':a.ref(render)};reports.append(rep);print(json.dumps({k:rep[k] for k in ['asset_key','case','cells','removed_cells','outside_original_position_material_cells','candidate_cells']}),flush=True)
  m=None;original=None;source=None;gc.collect()
 for contract in a.read(contractpath)['assets']:
  source=a.read(a.ROOT/contract['source_master']['path']);render=a.read(a.ROOT/contract['source_render']['path'])
  if not contract['replacement_contract_supported_for_all_roof_groups'] or contract['replacement_allowed']:raise ValueError('contract_state_invalid')
  for group in contract['render_groups']:
   original={(c['id'],o['id']) for c in source['components'] for o in c['operations'] if o.get('action')=='paint' and o.get('material')==group['material_id']};represented={(v['component'],v['operation']) for v in group['represented_roof_operations']};g=render['groups'][group['source_render_group_index']]
   if original!=represented or g['material']!=group['material_id'] or len(g['quads'])!=group['source_quad_count'] or a.core.digest(g)!=group['source_group_sha256_canonical']:raise ValueError(['whole_group_source_mismatch',contract['asset_key'],group['material_id'],original,represented])
   counts['original_render_groups_exhaustively_matched']+=1
 previous=a.read(e.OUT/'layered_compile_catalog.json')
 for r in previous['assets']:
  if a.shared.sha(a.ROOT/r['emitted_master_path'])!=r['emitted_master_sha256']:raise ValueError('previous_65_variant_changed')
 counts['previous_65_variant_hashes_preserved']=len(previous['assets'])
 for ref in a.read(f.OUT/'compiler_pre_cell_bounds_evidence.json')['frozen_outputs']:
  if a.shared.sha(a.ROOT/ref['path'])!=ref['sha256']:raise ValueError('legacy_frozen_output_changed')
  counts['legacy_frozen_output_hashes_preserved']+=1
 counts['native_bounded_roi_cases']=len(reports);counts['native_assets']=cat['native_asset_count'];counts['source_variants']=cat['variant_count'];counts['full_asset_compiles']=0
 if f.disk()>rules['budgets']['total_bytes_limit']:raise ValueError('disk_budget_exceeded')
 report={'schema':'riverstone.facility_roof.shape_extension_validation.v4','status':'PASS_SOURCE_AND_SMALL_ROIS_NOT_PLAYABLE_COMPLETION','checks':dict(counts),'roi_reports':reports,'failures':fail,'core':a.ref(a.core.__file__),'layered_engine':a.ref(f.layers.__file__),'author':a.ref(Path(__file__)),'catalog':a.ref(catpath),'contracts':a.ref(contractpath),'source_coverage_is_not_runtime_completion':True,'replacement_allowed':False,'runtime_activation':False,'global_constraints_evaluated':False,'remaining_checks':['Whole-asset native compilation','Whole-roof connectivity and hidden-face interfaces','Render-only original-group atomic replacement','In-engine visual, streaming and performance acceptance'],'seconds':time.perf_counter()-start,'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'directory_bytes_before_report':f.disk(),'added_bytes_from_task_baseline':f.disk()-rules['budgets']['baseline_bytes']};a.write(OUT/('representative_validation.json' if representatives else 'validation_report.json'),report);print(json.dumps({'status':report['status'],'checks':dict(counts),'max_rss_bytes':report['max_rss_bytes'],'added_bytes':report['added_bytes_from_task_baseline']}))

if __name__=='__main__':
 from pathlib import Path
 p=argparse.ArgumentParser();p.add_argument('--representatives',action='store_true');args=p.parse_args();main(args.representatives)
