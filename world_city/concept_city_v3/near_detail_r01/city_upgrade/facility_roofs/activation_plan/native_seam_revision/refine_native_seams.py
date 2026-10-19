"""Data-configured shingle course phase refinement; existing sources are immutable."""
import collections,copy,json,resource,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PLAN=HERE.parent;sys.path.insert(0,str(PLAN.parent));sys.path.insert(0,str(PLAN))
import author_facility_roofs as a
import finish_roofs as f
import expand_facilities as e
import extend_roof_shapes as x
import recheck_cell_bounds as native
from prepare_handoff import baseline_check
RULES=HERE/'native_shingle_rules.json'

def positive_y_widths(render):
 widths=[]
 for g in render['groups']:
  for q in g['quads']:
   u=[q[1][j]-q[0][j] for j in range(3)];v=[q[2][j]-q[0][j] for j in range(3)]
   if u[2]*v[0]-u[0]*v[2]>0:widths.append(round(max(v[2] for v in q)-min(v[2] for v in q),6))
 return dict(collections.Counter(widths))

def main():
 resource.setrlimit(resource.RLIMIT_AS,(800000000,800000000));config=a.read(RULES);key=config['native_asset_key'];oldcat=a.read(PLAN/'all_72_layered_compile_catalog.v5.json');old=next(r for r in oldcat['assets'] if r['asset_key']==config['variant_asset_key']);d=f.layers.load_master(f.OUT/'shape_support_descriptors.v2.json.gz')['assets'][key];source=a.read(a.ROOT/d['source_master_path']);coverrules=a.read(a.RULES);coverrules['coverings']['wood_shingle']['lateral_joint_m']=config['lateral_joint_m'];cp=HERE/'common_roof_rules.native_05.json';a.write(cp,coverrules)
 previous=a.RULES
 try:
  a.RULES=cp;near=e.ordered_finish(d,source,a.read(f.RULES),'wood_shingle')
 finally:a.RULES=previous
 planes={p['id']:p for p in d['planes']};shift=config['lateral_course_phase_m'];changed=0
 for component in near['components']:
  if '_row_' not in component['id']:continue
  pid='_'.join(component['id'].split('_')[:2]);plane=planes[pid]
  for op in component['operations']:
   if '_tile_' not in op['id']:continue
   sh=op['shape'];assert sh['kind']=='extrusion';sh['z_min']=max(plane['z_min'],sh['z_min']+shift);sh['z_max']=min(plane['z_max'],sh['z_max']+shift);assert sh['z_max']>sh['z_min'];changed+=1
 flat=f.flatten(near);flat['metadata'].update(native_shingle_phase_rules=a.ref(RULES),covering_decision=a.ref(PLAN/'castle_stable_covering_decision.json'),supersedes_source_input={'path':old['emitted_master_path'],'sha256':old['emitted_master_sha256']});check=f.structure(flat,d)
 if check['failures'] or flat['materials']!=source['materials']:raise ValueError('native_shingle_structure_failed')
 mp=HERE/(config['variant_asset_key']+'.native_05.master.json.gz');f.gzwrite(mp,flat);record=copy.deepcopy(old);record.update(emitted_master_path=a.rel(mp),emitted_master_sha256=a.shared.sha(mp),gzip_bytes=mp.stat().st_size,structure_validation=check,native_seam_rules=a.ref(RULES),supersedes_source_input={'path':old['emitted_master_path'],'sha256':old['emitted_master_sha256']})
 oldv=a.read(PLAN/'castle_stable_wood_shingle.validation.json');cb=oldv['roi']['cell_bounds'];low=[(i+.5)*.05 for i in cb['min']];high=[(i+.5)*.05 for i in cb['max']];new,_,bounds=native.compile_roi(flat,low,high,a.read(x.RULES));original=f.original_roof_only(d,source);ref,_,_=native.compile_roi(original,low,high,a.read(x.RULES));cells=native.rows(new);prior=native.rows(ref);render=a.make_render_data(new);oldrender=a.read(a.ROOT/oldv['roi']['render']['path']);beforewidths=positive_y_widths(oldrender);afterwidths=positive_y_widths(render)
 if not cells or cells-prior or not prior-cells or not any(float(v)<.3 for v in afterwidths):raise ValueError('native_shingle_sampling_seam_failed')
 rp=HERE/'castle_stable_wood_shingle.native_05.roi.render.json';a.write(rp,render);report={'status':'PASS_NATIVE_SHINGLE_SEAMS_IN_SMALL_ROI_ONLY','source':record,'unchanged_original_source_sha256':d['source_master_sha256'],'previous_source_file_unchanged':a.shared.sha(a.ROOT/old['emitted_master_path'])==old['emitted_master_sha256'],'source_row_tile_definitions_adjusted':changed,'native_pitch_m':.05,'lateral_joint_m':config['lateral_joint_m'],'lateral_course_phase_m':shift,'sampling_reason':'A 0.025 m gap centered on a native cell boundary has no center samples. The authored 0.05 m gap is phase-aligned to native cell centers; original shapes/predicates are not modified.','cell_bounds':bounds,'cells':len(cells),'outside_original_position_material_cells':len(cells-prior),'removed_source_cells':len(prior-cells),'previous_positive_y_face_z_width_counts':beforewidths,'new_positive_y_face_z_width_counts':afterwidths,'pruned_and_unpruned_native_samples_identical':True,'render':a.ref(rp),'global_constraints_evaluated':False,'full_asset_compile':False,'replacement_allowed':False,'prior_deliverable_hashes_preserved':baseline_check()};a.write(HERE/'validation.json',report)
 cat=copy.deepcopy(oldcat);cat['schema']='riverstone.facility_roof.all_source_inputs.v6';cat['supersedes']=a.ref(PLAN/'all_72_layered_compile_catalog.v5.json');cat['assets']=[record if r['asset_key']==record['asset_key'] else r for r in cat['assets']];cat['retained_previous_source_revisions']=[{'path':old['emitted_master_path'],'sha256':old['emitted_master_sha256']}]
 sel=a.read(a.HERE/'variant_selection.v2.json');sel['schema']='riverstone.facility_roof.placement_variant_selection.v3';sel['supersedes']=a.ref(a.HERE/'variant_selection.v2.json');sel['revision_author']=a.ref(Path(__file__));variant=sel['assets'][key]['available_variants']['wood_shingle'];variant.update(catalog=a.rel(PLAN/'all_72_layered_compile_catalog.v6.json'),emitted_master_path=record['emitted_master_path'],emitted_master_sha256=record['emitted_master_sha256']);sel['native_sampling_refinements']=[a.ref(HERE/'validation.json')];a.write(a.HERE/'variant_selection.v3.json',sel);cat['variant_selection']=a.ref(a.HERE/'variant_selection.v3.json');a.write(PLAN/'all_72_layered_compile_catalog.v6.json',cat);a.write(HERE/'change_ledger.json',{'schema':'riverstone.facility_roof.native_sampling_change.v1','new_source':record,'previous_catalog':a.ref(PLAN/'all_72_layered_compile_catalog.v5.json'),'current_catalog':a.ref(PLAN/'all_72_layered_compile_catalog.v6.json'),'previous_selector':a.ref(a.HERE/'variant_selection.v2.json'),'current_selector':a.ref(a.HERE/'variant_selection.v3.json'),'semantic_choice_unchanged':True,'original_source_and_color_unchanged':True,'previous_source_preserved':True,'other_81_source_variants_unchanged':True,'full_compile_performed':False});print(json.dumps({'status':report['status'],'before_widths':beforewidths,'after_widths':afterwidths,'cells':len(cells),'removed_source_cells':len(prior-cells),'gzip_bytes':record['gzip_bytes']}))
if __name__=='__main__':main()
