"""Small ROI checks of native integer bounds; prior results are immutable."""
import collections,copy,gc,json,math,resource,time
import author_facility_roofs as a
import finish_roofs as f
import expand_facilities as expand
OUT=f.OUT/'post_cell_bounds'

def rows(c):return {(*r[:3],r[5]) for r in c['cells']}
def cbounds(low,high):return {'min':[math.ceil(x/.05-.5-1e-8) for x in low],'max':[math.ceil(x/.05-.5-1e-8) for x in high]}
def compile_roi(master,low,high,rules):
 bounds=cbounds(low,high);lo=[i*.05 for i in bounds['min']];hi=[i*.05 for i in bounds['max']];spatial=f.layers.SpatialSource(master,.05,range_only=True);pruned=spatial.bounded_master(lo,hi);opts={'max_candidate_cells':rules['budgets']['roi_candidate_cells'],'max_output_cells':rules['budgets']['roi_output_cells'],'cell_bounds':bounds};sample=a.core.compile_master(pruned,{'pitch':.05},**opts);direct=a.core.compile_master(master,{'pitch':.05},**opts)
 if rows(sample)!=rows(direct):raise ValueError('bounded_prune_changed_original_shape_samples')
 return sample,pruned,bounds

def main():
 start=time.perf_counter();rules=f.limited();OUT.mkdir(parents=True,exist_ok=True);cat=a.read(expand.OUT/'layered_compile_catalog.json');bundle=f.layers.load_master(f.OUT/'shape_support_descriptors.v2.json.gz')['assets'];records={r['asset_key']:r for r in cat['assets']};pre=a.read(f.OUT/'compiler_pre_cell_bounds_evidence.json');evidence=[]
 for old in a.read(f.OUT/'roi_validation.json')['reports']:evidence.append((old['asset_key'],old['case'],old['bounds_m'],f.OUT/'roi'/(old['asset_key']+'.'+old['case']+'.master.json')))
 hip=a.read(f.OUT/'hip_cut_roi_validation.json');evidence.append((hip['asset_key'],'exact_hip_cut',hip['bounds_m'],f.OUT/'roi'/(hip['asset_key']+'.exact_hip_cut.master.json')))
 for record in cat['assets']:
  if record['covering']!='roof_tile' or not record['structure_validation'].get('compiler_pending'):continue
  d=bundle[record['native_asset_key']];p=next(p for p in d['planes'] if not f.layers.signed_permutation(a.core.compose(p['component_instances'][0]['transform'],p['operation_transform'])['basis']));t=a.core.compose(p['component_instances'][0]['transform'],p['operation_transform']);aa=p['x_min'];bb=min(aa+.75,p['x_max']);zz=p['z_min'];points=[a.core.apply(t,[x,p['slope']*x+p['intercept']-depth,z]) for x in [aa,bb] for depth in [0,p['vertical_skin_thickness_m']] for z in [zz,min(zz+.75,p['z_max'])]];evidence.append((record['asset_key'],'proper_rigid_rotated_roof',f.bounds(points),None))
 reports=[]
 for key,name,(low,high),legacy_path in evidence:
  record=records[key];d=bundle[record['native_asset_key']];master=f.layers.load_master(a.ROOT/record['emitted_master_path']);source=a.read(a.ROOT/record['source_master_path']);original=f.original_roof_only(d,source);near,pruned,cb=compile_roi(master,low,high,rules);old,_,_=compile_roi(original,low,high,rules);cells=rows(near);oldcells=rows(old);outside={r[:3] for r in cells}-{r[:3] for r in oldcells}
  if outside or not cells:raise ValueError(['new_native_bounds_outside_original_solid',key,name,len(outside)])
  legacy_diff=None
  if legacy_path:
   legacy=a.core.compile_master(a.read(legacy_path),{'pitch':.05},max_candidate_cells=rules['budgets']['roi_candidate_cells'],max_output_cells=rules['budgets']['roi_output_cells']);legacycells={r for r in rows(legacy) if all(cb['min'][j]<=r[j]<cb['max'][j] for j in range(3))};legacy_diff={'positions_materials_only_in_legacy_cropped_input':len(legacycells-cells),'positions_materials_only_in_native_unmodified_input':len(cells-legacycells),'comparison_note':'Prior immutable cropped master re-evaluated with the current unchanged shape predicates, filtered to identical half-open cell ownership.'}
  rp=OUT/(key+'.'+name+'.render.json');a.write(rp,a.make_render_data(near));report={'asset_key':key,'case':name,'status':'PASS_NATIVE_BOUNDED_ROI_ONLY','cell_bounds':cb,'cells':len(cells),'quads':a.make_render_data(near)['quad_count'],'near_candidates':near['candidate_cells'],'reference_candidates':old['candidate_cells'],'outside_original_solid_cells':len(outside),'pruned_and_unpruned_native_samples_identical':True,'legacy_crop_comparison':legacy_diff,'compiler_source_sha256_before':pre['compiler_source_sha256'],'compiler_source_sha256_after':near['compiler_source_hash'],'scoped_valid':near['valid'],'valid_scope':near.get('valid_scope'),'global_constraints_evaluated':near.get('global_constraints_evaluated'),'whole_asset_compile':False,'runtime_activation':False,'render':a.ref(rp)};reports.append(report);print(json.dumps({k:report[k] for k in ['asset_key','case','cells','near_candidates','legacy_crop_comparison']}),flush=True);master=None;original=None;pruned=None;gc.collect()
 changed=[v['path'] for v in pre['frozen_outputs'] if a.shared.sha(a.ROOT/v['path'])!=v['sha256']]
 if changed:raise ValueError(['frozen_prior_output_changed',changed])
 out={'schema':'riverstone.facility_roof.native_cell_bounds_compatibility.v1','status':'PASS_SMALL_ROIS_NOT_GLOBAL_APPROVAL','reports':reports,'legacy_outputs_hash_unchanged':True,'legacy_frozen_file_count':len(pre['frozen_outputs']),'core_before_sha256':pre['compiler_source_sha256'],'core_after':a.ref(a.core.__file__),'layered_after':a.ref(f.layers.__file__),'seconds':time.perf_counter()-start,'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'directory_bytes':f.disk(),'full_asset_compiles':0,'runtime_activation':False};a.write(OUT/'validation.json',out);print(json.dumps({'status':out['status'],'cases':len(reports),'max_rss_bytes':out['max_rss_bytes'],'directory_bytes':out['directory_bytes']}))

if __name__=='__main__':main()
