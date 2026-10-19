"""Read-only source/geometry checks and explicit runtime replacement contracts.
No asset compilation, renderer integration or original file mutation.
"""
import collections, copy, json, math, resource, sys, time
from pathlib import Path
import author_facility_roofs as a

def shape_vertices(op):
 s=op['shape']
 if s['kind']=='extrusion':return [[x,y,z] for x,y in s['polygon'] for z in [s['z_min'],s['z_max']]]
 if s['kind']=='box':
  import itertools
  return [list(p) for p in itertools.product(*zip(s['min'],s['max']))]
 raise ValueError('unexpected_emitted_shape:'+s['kind'])

def main():
 start=time.perf_counter();rules=a.read(a.RULES);resource.setrlimit(resource.RLIMIT_AS,(rules['budgets']['memory_limit_bytes'],)*2);cat=a.read(a.HERE/'catalog.json');checks=collections.Counter();failures=[];contracts=[];materials=[]
 for record in cat['assets']:
  d=a.read(a.ROOT/record['descriptor']['path']);srcpath=a.ROOT/d['source_master_path'];source=a.read(srcpath);renderpath=a.ROOT/d['source_render_path'];render=a.read(renderpath)
  if a.shared.sha(srcpath)!=d['source_master_sha256'] or a.shared.sha(renderpath)!=d['source_render_sha256']:failures.append([record['asset_key'],'source_hash_changed'])
  checks['source_master_and_render_pairs_rehashed']+=1
  operations={(c['id'],o['id']):o for c in source['components'] for o in c['operations']}
  plans={p['id']:p for p in d['planes']};roofrefs=collections.defaultdict(list)
  for p in plans.values():
   for oid in p['source_operations']:
    old=operations[(p['component'],oid)];aa,bb,ya,yb,th=a.shared.roof_geometry(old)
    if max(abs(p['slope']*aa+p['intercept']-ya),abs(p['slope']*bb+p['intercept']-yb),abs(p['vertical_skin_thickness_m']-th))>1e-8:failures.append([record['asset_key'],p['id'],'merged_plane_mismatch'])
    roofrefs[p['material']].append({'component':p['component'],'operation':oid,'role':'supported_sloped_plane'})
    checks['original_plane_operations_checked']+=1
  for x in d['retained_ridge_boxes']:roofrefs[x['operation']['material']].append({'component':x['component'],'operation':x['operation']['id'],'role':'unchanged_source_ridge_box_near_resample_pending'})
  for variant in record['variants']:
   if 'master' not in variant:continue
   p=a.ROOT/variant['master']['path'];m=a.read(p);a.core.validate_master(m,rules['near_pitch_m']);checks['near_masters_schema_validated']+=1
   if m['materials']!=source['materials']:failures.append([record['asset_key'],'palette_changed'])
   comps={c['id']:c for c in m['components']}
   for ins in m['instances']:
    if not ins['component'].startswith('plane_'):continue
    pid='_'.join(ins['component'].split('_')[:2]);plane=plans[pid]
    srcins=next((s for s in plane['component_instances'] if ins['id'].endswith('_'+s['id'])),None)
    if srcins is None:failures.append([record['asset_key'],ins['id'],'missing_source_instance']);continue
    base=a.core.compose(srcins['transform'],plane['operation_transform']);t=a.core.transform(ins.get('transform'))
    for op in comps[ins['component']]['operations']:
     for v in shape_vertices(op):
      w=a.core.inverse(base,a.core.apply(t,v));x,y,z=w;h=plane['slope']*x+plane['intercept'];eps=1e-7
      if not (plane['x_min']-eps<=x<=plane['x_max']+eps and plane['z_min']-eps<=z<=plane['z_max']+eps and h-plane['vertical_skin_thickness_m']-eps<=y<=h+eps):
       failures.append([record['asset_key'],ins['id'],op['id'],'vertex_outside_original_roof_solid',w]);break
     checks['expanded_roof_prisms_contained']+=1
  safe=set(d['suppression']['safe_material_groups_when_full_matching_near_resource_ready']);unsaf={x['material']:x for x in d['suppression']['unsafe_material_groups']};groups=[]
  for gi,g in enumerate(render['groups']):
   mat=g['material']
   if mat not in safe and mat not in unsaf:continue
   refs=roofrefs.get(mat,[]);allpaint=[{'component':c['id'],'operation':o['id'],'part':o['part'],'shape':o['shape']['kind']} for c in source['components'] for o in c['operations'] if o.get('action')=='paint' and o.get('material')==mat]
   points=[q for quad in g['quads'] for q in quad];bounds={'min':[min(v[j] for v in points) for j in range(3)],'max':[max(v[j] for v in points) for j in range(3)]} if points else None
   group={'material_id':mat,'source_render_group_index':gi,'source_quad_index_range_inclusive':[0,len(g['quads'])-1] if g['quads'] else None,'source_quad_count':len(g['quads']),'source_group_sha256_canonical':a.core.digest(g),'source_group_bounds_m':bounds,'source_master_paint_operations':allpaint,'represented_roof_operations':refs,'group_replacement_supported':mat in safe,'replacement_allowed':False,'unsupported_refs':unsaf.get(mat,{}).get('unhandled_operation_refs',[]),'face_provenance':'Exact indexed group and quad range in hash-pinned original render. Original exporter retains material only, so no invented per-quad component ownership. Whole-group support requires every source paint operation for this material to be represented.'}
   groups.append(group);checks['source_render_groups_fingerprinted']+=1
  complete=bool(groups) and all(g['group_replacement_supported'] for g in groups) and not d['pending']
  contracts.append({'asset_key':record['asset_key'],'replacement_allowed':False,'replacement_contract_supported_for_all_roof_groups':complete,'replacement_contract_supported_material_ids':[g['material_id'] for g in groups if g['group_replacement_supported']],'source_master':{'path':d['source_master_path'],'sha256':d['source_master_sha256']},'source_render':{'path':d['source_render_path'],'sha256':d['source_render_sha256']},'source_pitch_m':d['source_pitch_m'],'render_groups':groups,'pending_shape_operations':d['pending'],'atomic_activation_requirements':['Every selected material group has a complete, validated near render resource covering all original operation domains and instances.','All roof underlay, tile rows, trim boundaries and retained ridge boxes for the selected group are present.','Near materials inherit the same instance palette; wood_brown/b13_wood_brown choose wood_shingle geometry.','Stage near layer and hide the exact hash-pinned original render groups together. Remove every normal direction, including coarse risers, undersides and edge faces.','Do not remove owner collision, window/door/glass/nonroof material groups, or unmatched roof groups.','Switch the full matching original groups back on atomically before removing the near layer.','Audit remaining masonry/gable/chimney intersections separately; unchanged nonroof geometry has not been claimed upgraded.'],'current_blocker':'Only bounded common ROI renders are compiled. Full-group streaming/render resources and visual acceptance remain pending.','per_face_partial_replacement_allowed':False,'no_partial_roi_can_disable_full_group':True})
 a.write(a.HERE/'replacement_contracts.json',{'schema':'riverstone.facility_roof.replacement_contracts.v1','runtime_active':False,'assets':contracts,'runtime_selection':'For each asset/variant, require exact source render SHA, group index, material ID and group digest before atomically hiding the original group. Unsupported or partially supplied groups stay unchanged.','no_shader_substitute':True})
 reports=[a.read(p) for p in (a.HERE/'roi').glob('*.validation.json')]
 checks['roi_compile_passes']=sum(r['status']=='PASS' for r in reports);checks['full_asset_compiles']=0;checks['assets_with_all_roof_groups_contract_supported']=sum(c['replacement_contract_supported_for_all_roof_groups'] for c in contracts)
 for r in reports:
  if r['candidate_cells']>rules['budgets']['roi_max_candidate_cells'] or r['cells']>rules['budgets']['roi_max_output_cells'] or r['max_rss_bytes']>rules['budgets']['memory_limit_bytes']:failures.append([r['asset_key'],'roi_budget_exceeded'])
 size=sum(p.stat().st_size for p in a.HERE.rglob('*') if p.is_file());checks['artifact_bytes_before_report']=size
 if size>rules['budgets']['max_artifact_bytes']:failures.append(['disk_budget_exceeded',size])
 summary={'schema':'riverstone.facility_roof.validation.v1','status':'PASS_SOURCE_AUTHORING_AND_BOUNDED_ROI' if not failures else 'FAIL','checks':dict(checks),'failures':failures,'seconds':time.perf_counter()-start,'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'memory_limit_bytes':rules['budgets']['memory_limit_bytes'],'catalog':a.ref(a.HERE/'catalog.json'),'replacement_contracts':a.ref(a.HERE/'replacement_contracts.json'),'author':a.ref(Path(a.__file__)),'validator':a.ref(Path(__file__)),'all_source_masters_and_renders_preserved':not any('source_hash_changed' in str(f) for f in failures),'roi_reports':[{k:r[k] for k in ['asset_key','plane_id','covering','status','cells','quads','candidate_cells','max_rss_bytes']} for r in reports],'not_verified':['Full roof chunk compilation','Runtime integration or atomic replacement','Runtime performance','In-engine visual approval','Roof intersections and ridge-cap finish','Hip/conical/cut intersecting roofs']}
 a.write(a.HERE/'validation_report.json',summary);print(json.dumps({'status':summary['status'],'checks':summary['checks'],'failures':failures[:8]}));return bool(failures)
if __name__=='__main__':raise SystemExit(main())
