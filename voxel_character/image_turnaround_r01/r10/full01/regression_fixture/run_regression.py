"""TEST ONLY: bounded independent actual-pixel regression, never production art.
Reuses existing semantic, branch and cloth functions. No voxel compilation.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
from pathlib import Path
import sys,json,gzip,hashlib,copy,io,time,resource,re,itertools,contextlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];REPO=ROOT.parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import measure_semantic_views as semantic
import measure_surface_branches as branch
import build_measured_cloth as cloth
START=time.perf_counter();MAX_BYTES=int(1.7*1048576)
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(x):return hashlib.sha256(canon(x)).hexdigest()
def load(p):
 p=Path(p);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def gzwrite(p,x):Path(p).write_bytes(gzip.compress(canon(x),mtime=0))
def disk_budget():
 own=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file());report=ROOT/'full01/evidence/full_pixel_regression.json';own+=report.stat().st_size if report.exists() else 0
 assert own<=MAX_BYTES,f'Test output exceeds authorized 1.7 MiB: {own}'
 approved=load(ROOT/'data/resource_budget.json');total=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
 assert total<=approved['approved_total_mib']*1048576,f'Total r10 exceeds expanded approved budget: {total}'
 return total

def progress(stage):
 write(HERE/'progress.json',{'test_only':True,'stage':stage,'elapsed_seconds':round(time.perf_counter()-START,3),'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024});disk_budget()

def semantic_call(cp,ap,out):
 if (out/'full_measurements.json.gz').exists():
  return load(out/'full_measurements.json.gz'),{'overlays_written_to_disk':False,'reused_preserved_output_from_initial_test_attempt':True}
 # Preserve the production function. Only intermediate image I/O and its frozen
 # production-budget callback are adapted to this separately approved test.
 images={};original_save=Image.Image.save;original_sha=semantic.sha;original_budget=semantic.budget
 def save_in_memory(im,fp,format=None,**kwargs):
  dest=Path(fp).resolve();assert dest.is_relative_to(out.resolve())
  stream=io.BytesIO();fmt=format or ('JPEG' if dest.suffix.lower() in ('.jpg','.jpeg') else 'PNG');original_save(im,stream,format=fmt,**kwargs);images[str(dest)]=stream.getvalue()
 def source_or_memory_sha(p):
  key=str(Path(p).resolve());return hashlib.sha256(images[key]).hexdigest() if key in images else original_sha(p)
 try:
  Image.Image.save=save_in_memory;semantic.sha=source_or_memory_sha;semantic.budget=disk_budget
  with contextlib.redirect_stdout(io.StringIO()):result=semantic.measure_semantics(cp,ap,out)
 finally:Image.Image.save=original_save;semantic.sha=original_sha;semantic.budget=original_budget
 return result,{'overlays_written_to_disk':False,'image_count_held_temporarily':len(images),'image_bytes_held_temporarily':sum(map(len,images.values()))}

def mask_diff(original,mutant,crops,separator='_'):
 result={}
 for name in sorted(original.files if hasattr(original,'files') else original):
  a,b=np.asarray(original[name]),np.asarray(mutant[name]);diff=a!=b;view=name.split(separator)[0];x0,y0,_,_=crops[view];ys,xs=np.where(diff)
  outside=diff.copy();outside[max(0,ROI[1]-y0):max(0,ROI[3]-y0),max(0,ROI[0]-x0):max(0,ROI[2]-x0)]=False if view=='front' else outside[max(0,ROI[1]-y0):max(0,ROI[3]-y0),max(0,ROI[0]-x0):max(0,ROI[2]-x0)]
  # Source ROI is in front view only; all other changed-view pixels are nonlocal.
  nout=int(outside.sum()) if view=='front' else int(diff.sum())
  result[name]={'changed_pixels':int(diff.sum()),'changed_outside_source_roi_pixels':nout,'bbox_global_xyxy':[int(xs.min()+x0),int(ys.min()+y0),int(xs.max()+x0+1),int(ys.max()+y0+1)] if len(xs) else None,'changed_global_rows':(np.unique(ys)+y0).astype(int).tolist()}
 return result

def bounds(op):
 s=op['shape'];t=op.get('transform',{});basis=np.array(t.get('basis',np.eye(3)));shift=np.array(t.get('translation',[0,0,0]));p=np.array([[x,y,z] for x,y in s['polygon'] for z in (s['z_min'],s['z_max'])]);p=p@basis.T+shift
 return [p.min(0).tolist(),p.max(0).tolist()]
def ops_diff(base,new,base_mats,new_mats):
 left={o['id']:o for o in base};right={o['id']:o for o in new};common=set(left)&set(right);added=sorted(set(right)-set(left));removed=sorted(set(left)-set(right));changed=sorted(k for k in common if left[k]!=right[k]);geometry=sorted(k for k in common if left[k]['shape']!=right[k]['shape'] or left[k].get('transform')!=right[k].get('transform'));material_ids=sorted(k for k in set(base_mats)|set(new_mats) if base_mats.get(k)!=new_mats.get(k));appearance=sorted(k for k in common if left[k].get('material')!=right[k].get('material') or left[k].get('material') in material_ids)
 all_changed=[left[k] for k in removed]+[right[k] for k in added]+[o for k in geometry for o in (left[k],right[k])];bs=[bounds(o) for o in all_changed];parts={};anchors=[];outside=0
 for o in all_changed:
  part=o['part'];parts[part]=parts.get(part,0)+1;y=int(re.search(r'_y(\d+)_r',o['id']).group(1));anchors.append(y)
  if not (o['part'].startswith('front_') and ROI[1]<=y and y+PRIOR['row_step_px']<=ROI[3]):outside+=1
 return {'baseline_ops':len(base),'variant_ops':len(new),'added_count':len(added),'removed_count':len(removed),'changed_same_id_count':len(changed),'geometry_changed_same_id_count':len(geometry),'material_changed_ids':material_ids,'appearance_changed_same_id_count':len(appearance),'changed_geometry_source_row_anchor_range':[min(anchors),max(anchors)] if anchors else None,'changed_geometry_world_y_bounds_m':[min(b[0][1] for b in bs),max(b[1][1] for b in bs)] if bs else None,'changed_geometry_world_xyz_bounds':[np.min([b[0] for b in bs],axis=0).tolist(),np.max([b[1] for b in bs],axis=0).tolist()] if bs else None,'changed_geometry_occurrences_outside_roi_source_bands':outside,'affected_parts':parts,'added_ids':added,'removed_ids':removed,'geometry_changed_same_ids':geometry,'all_operation_dict_changes_same_ids':changed}

def max_numeric_delta(a,b):
 if isinstance(a,dict) and isinstance(b,dict):return max([max_numeric_delta(a[k],b[k]) for k in a.keys()&b.keys()]+[0.])
 if isinstance(a,list) and isinstance(b,list):return max([max_numeric_delta(x,y) for x,y in zip(a,b)]+[0.])
 if isinstance(a,(float,int)) and isinstance(b,(float,int)):return abs(a-b)
 return 0.

cp=ROOT/'data/measurement_contract.json';ap=ROOT/'data/violet_full_semantic_annotations_v02.json';bp=ROOT/'data/violet_surface_branch_annotations.json';pp=ROOT/'full01/data/cloth_depth_priors.json';bmfile=ROOT/'full_measurement/violet_branches/branch_measurements.json.gz';mfile=ROOT/'full_measurement/violet_branches/branch_masks.npz';frozenop=ROOT/'full01/generated/cloth_operations.json.gz'
CONTRACT=load(cp);PRIOR=load(pp);recipe=load(ROOT/'evidence/local_pixel_mutation_recipe.json');ROI=recipe['box_xyxy'];fixture=ROOT/'evidence/local_pixel_mutation_fixture.png';source=REPO/CONTRACT['source'];frozen_paths=[cp,ap,bp,pp,bmfile,mfile,frozenop,source,fixture,ROOT/'full_measurement/violet_v02/semantic_masks.npz',ROOT/'tools/measure_semantic_views.py',ROOT/'tools/measure_surface_branches.py',ROOT/'tools/build_measured_cloth.py'];frozen_hashes={str(p.relative_to(REPO)):sha(p) for p in frozen_paths}
assert sha(source)==recipe['parent_sha256'];assert sha(fixture)==recipe['mutant_sha256'];original=np.array(Image.open(source).convert('RGB'));mutant=np.array(Image.open(fixture).convert('RGB'));pixel_change=np.any(original!=mutant,axis=2);ys,xs=np.where(pixel_change);assert int(pixel_change.sum())==recipe['changed_pixel_count'];assert min(xs)>=ROI[0] and max(xs)<ROI[2] and min(ys)>=ROI[1] and max(ys)<ROI[3]
variant_c=copy.deepcopy(CONTRACT);variant_c['source']=str(fixture.relative_to(REPO));variant_c['source_sha256']=recipe['mutant_sha256'];variant_c['approval']={'status':'TEST_ONLY_NOT_APPROVED_ART','parent_source_sha256':recipe['parent_sha256']};variant_c['regression_variant']={'purpose':recipe['purpose'],'recipe_sha256':sha(ROOT/'evidence/local_pixel_mutation_recipe.json'),'approved_production_input':False}
variant_a=copy.deepcopy(load(ap));variant_a['source_sha256']=recipe['mutant_sha256'];variant_a['annotation_status']='TEST_ONLY_NOT_APPROVED_ART. Same numerical semantic annotations as frozen v02; only source provenance is changed.';variant_a['regression_parent_annotation_sha256']=sha(ap)
write(HERE/'test_variant_contract.json',variant_c);write(HERE/'test_variant_semantic_annotations.json',variant_a);progress('verified actual fixture and frozen inputs')
base_sem,base_io=semantic_call(cp,ap,HERE/'baseline_semantic');mut_sem,mut_io=semantic_call(HERE/'test_variant_contract.json',HERE/'test_variant_semantic_annotations.json',HERE/'variant_semantic')
base_sm=np.load(HERE/'baseline_semantic/semantic_masks.npz');frozen_sm=np.load(ROOT/'full_measurement/violet_v02/semantic_masks.npz');mut_sm=np.load(HERE/'variant_semantic/semantic_masks.npz');baseline_sem_exact=base_sm.files==frozen_sm.files and all(np.array_equal(base_sm[k],frozen_sm[k]) for k in frozen_sm.files);assert baseline_sem_exact
crops={k:v['crop'] for k,v in CONTRACT['views'].items()};semantic_diffs=mask_diff(base_sm,mut_sm,crops);progress('generic semantic source replay exact and fixture measured')
# Exact baseline branch replay uses its frozen input files; variant uses only test data.
baseline_bm,baseline_bmasks,unused,_=branch.measure(cp,bp,ROOT/'full_measurement/violet_v02/semantic_masks.npz');del unused
baseline_bm['branch_masks_sha256']=sha(mfile);stored_bm=load(bmfile);stored_bmasks=np.load(mfile);base_branch_exact=canon(baseline_bm)==canon(stored_bm) and all(np.array_equal(baseline_bmasks[k],stored_bmasks[k]) for k in stored_bmasks.files);assert base_branch_exact
variant_b=copy.deepcopy(load(bp));variant_b['source_sha256']=recipe['mutant_sha256'];variant_b['semantic_masks_sha256']=sha(HERE/'variant_semantic/semantic_masks.npz');variant_b['annotation_status']='TEST_ONLY_NOT_APPROVED_ART. Same seeds, ROIs and numerical geodesic rules as frozen source branches.';variant_b['regression_parent_annotation_sha256']=sha(bp);write(HERE/'test_variant_branch_annotations.json',variant_b)
variant_bm,variant_bmasks,unused,branch_checks=branch.measure(HERE/'test_variant_contract.json',HERE/'test_variant_branch_annotations.json',HERE/'variant_semantic/semantic_masks.npz');del unused
branch.deterministic_npz(HERE/'variant_branch_masks.npz',variant_bmasks);variant_bm['branch_masks_sha256']=sha(HERE/'variant_branch_masks.npz');gzwrite(HERE/'variant_branch_measurements.json.gz',variant_bm);branch_diffs=mask_diff(baseline_bmasks,variant_bmasks,crops,separator='__');progress('generic branch source replay exact and fixture measured')
base_ops,base_materials,base_evidence=cloth.build_cloth(CONTRACT,stored_bm,stored_bmasks,original,PRIOR);stored_ops=load(frozenop);base_cloth_exact=base_ops==stored_ops['operations'] and base_materials==stored_ops['materials']
stored_baseline_diff=ops_diff(stored_ops['operations'],base_ops,stored_ops['materials'],base_materials);stored_numeric_delta=max_numeric_delta(stored_ops['operations'],base_ops);gzwrite(HERE/'stored_baseline_comparison.json.gz',stored_baseline_diff)
write(HERE/'initial_exact_replay_failure.json',{'exact':base_cloth_exact,'generator_sha_matches':stored_ops['generator_sha256']==sha(ROOT/'tools/build_measured_cloth.py'),'prior_sha_matches':stored_ops['prior_sha256']==sha(pp),'max_absolute_numeric_field_delta':stored_numeric_delta,'original_test_attempt_stopped_before_mutant_cloth_build':True,'thread_context':'This test explicitly uses one BLAS thread. The production run thread context is not recorded here; cause is not asserted.'})
repeat_ops,repeat_materials,_=cloth.build_cloth(CONTRACT,stored_bm,stored_bmasks,original,PRIOR);same_context_repeat=repeat_ops==base_ops and repeat_materials==base_materials;del repeat_ops,repeat_materials
progress('same-source cloth replay compared; historical exact='+str(base_cloth_exact)+', fixed-thread repeat='+str(same_context_repeat))
variant_ops,variant_materials,variant_evidence=cloth.build_cloth(variant_c,variant_bm,variant_bmasks,mutant,PRIOR);diff=ops_diff(base_ops,variant_ops,base_materials,variant_materials);gzwrite(HERE/'changed_operations_index.json.gz',diff);progress('fixture cloth operations compared without compilation')
# Isolate the photometric/DCT prior from segmentation changes. This mixed-input
# diagnostic is intentionally not production geometry or a source-consistent fit.
fixed_ops,fixed_materials,fixed_evidence=cloth.build_cloth(CONTRACT,stored_bm,stored_bmasks,mutant,PRIOR);fixed_diff=ops_diff(base_ops,fixed_ops,base_materials,fixed_materials);gzwrite(HERE/'fixed_segmentation_photometric_index.json.gz',fixed_diff)
for p in frozen_paths:assert sha(p)==frozen_hashes[str(p.relative_to(REPO))],'Frozen file changed during regression: '+str(p)
fields=lambda d:{k:v for k,v in d.items() if k not in ('added_ids','removed_ids','geometry_changed_same_ids','all_operation_dict_changes_same_ids')}
changed_sem={k:v for k,v in semantic_diffs.items() if v['changed_pixels']};changed_branch={k:v for k,v in branch_diffs.items() if v['changed_pixels']}
untouched_views=all(not d['changed_pixels'] for k,d in semantic_diffs.items() if k.startswith(('side_','back_'))) and all(not d['changed_pixels'] for k,d in branch_diffs.items() if k.startswith(('side__','back__')))
hair_unchanged=all(not d['changed_pixels'] for k,d in semantic_diffs.items() if 'hair_visible' in k) and all(not d['changed_pixels'] for k,d in branch_diffs.items() if 'hair' in k)
body_unchanged=all(not d['changed_pixels'] for k,d in semantic_diffs.items() if any(cl in k for cl in ('face_skin','body_exposed_skin','bodice_gloves','stockings_shoes')))
report={'schema':'riverstone.actual_full_cloth_pixel_regression.v1','status':'PASS' if base_cloth_exact and not diff['changed_geometry_occurrences_outside_roi_source_bands'] and not any(d['changed_outside_source_roi_pixels'] for d in changed_branch.values()) else 'FAIL_NONLOCAL_AND_OR_REPLAY_EFFECTS_RETAINED','test_only_not_approved_art':True,'source_fixture':{'reference_path':str(fixture.relative_to(REPO)),'fixture_copied':False,'parent_source_sha256':recipe['parent_sha256'],'variant_source_sha256':recipe['mutant_sha256'],'actual_changed_pixels':int(pixel_change.sum()),'recipe_roi_xyxy':ROI,'actual_changed_bbox_xyxy':[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],'actual_changed_rows':np.unique(ys).astype(int).tolist(),'expected_source_world_y_range_m':[(CONTRACT['views']['front']['sole_y']-ROI[3])*CONTRACT['alignment']['character_height_m_for_test']/CONTRACT['views']['front']['scale_px_per_unit'],(CONTRACT['views']['front']['sole_y']-ROI[1])*CONTRACT['alignment']['character_height_m_for_test']/CONTRACT['views']['front']['scale_px_per_unit']]},'same_source_replay':{'semantic_masks_exact':baseline_sem_exact,'semantic_mask_file_byte_identical':sha(HERE/'baseline_semantic/semantic_masks.npz')==sha(ROOT/'full_measurement/violet_v02/semantic_masks.npz'),'branch_measurements_and_all_masks_exact':base_branch_exact,'cloth_operations_and_materials_exact':base_cloth_exact,'baseline_ops_sha256':digest(base_ops),'same_explicit_thread_context_repeat_exact':same_context_repeat,'stored_baseline_max_absolute_numeric_field_delta':stored_numeric_delta,'stored_baseline_comparison':fields(stored_baseline_diff),'generator_sha_matches':stored_ops['generator_sha256']==sha(ROOT/'tools/build_measured_cloth.py'),'prior_sha_matches':stored_ops['prior_sha256']==sha(pp)},'actual_variant':{'comparison_baseline':'Fresh same-source build in the same explicit one-thread context; historical stored exact mismatch is reported separately','operations_sha256':digest(variant_ops),'materials_sha256':digest(variant_materials),'semantic_mask_changes':changed_sem,'branch_mask_changes':changed_branch,'operations':fields(diff)},'fixed_segmentation_photometric_control':{'purpose':'Isolate image-luminance/normalization/DCT effect under frozen branch masks; mixed-input diagnostic only','operations':fields(fixed_diff)},'unaffected_inputs':{'side_and_back_semantic_and_branch_masks_exact':untouched_views,'all_hair_semantic_and_branch_masks_exact':hair_unchanged,'all_face_exposed_body_bodice_stocking_semantic_masks_exact':body_unchanged,'all_frozen_input_and_generator_files_unchanged':True,'frozen_sha256':frozen_hashes},'budget_adapter':{'basis':str((ROOT/'data/resource_budget.json').relative_to(REPO)),'approved_total_mib':load(ROOT/'data/resource_budget.json')['approved_total_mib'],'test_output_limit_bytes':MAX_BYTES,'frozen_12MiB_contract_not_modified':True,'semantic_production_budget_callback_replaced_only_in_test_process':True,'intermediate_overlays':{'baseline':base_io,'variant':mut_io},'semantic_and_branch_algorithms_unmodified':True},'runtime':{'elapsed_seconds':round(time.perf_counter()-START,3),'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'address_space_limit_mib':1024,'blas_threads':1,'external_wall_timeout_seconds':240},'compiled':False,'geometry_modified_to_force_locality_pass':False,'limitations':['Whole-branch DCT and median/contrast normalization are not compact-local operators.','Seeded geodesic watershed can reassign connected source pixels outside the changed ROI.','Changed Y bounds include full normal-thickness extrusion; source row-band tests separately detect nonlocal dependence.','This regression does not authorize or replace approved character art.']}
write(ROOT/'full01/evidence/full_pixel_regression.json',report);progress('complete: '+report['status']);report['budget_adapter']['actual_test_output_bytes']=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())+(ROOT/'full01/evidence/full_pixel_regression.json').stat().st_size;write(ROOT/'full01/evidence/full_pixel_regression.json',report);disk_budget();print(json.dumps({'status':report['status'],'same_source':report['same_source_replay'],'operations':report['actual_variant']['operations'],'unaffected_inputs':{k:v for k,v in report['unaffected_inputs'].items() if k!='frozen_sha256'},'runtime':report['runtime'],'bytes':report['budget_adapter']['actual_test_output_bytes']}))
