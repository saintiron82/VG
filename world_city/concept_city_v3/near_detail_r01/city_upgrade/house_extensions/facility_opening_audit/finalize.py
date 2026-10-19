"""Build audit-only plan examples and verify records. Never compiles geometry."""
from collections import Counter
import gzip,json,math,sys
from pathlib import Path
import jsonschema
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import audit as a

def rows(name):
    with gzip.open(HERE/name,'rt') as f:return [json.loads(x) for x in f]
def write(name,value):a.write(name,value)
summary=a.load(HERE/'summary.json');inventory=a.load(HERE/'asset_audit.json');assets={x['asset_key']:x for x in inventory['assets']};windows=rows('window_faces.jsonl.gz');entries=rows('door_and_entry_features.jsonl.gz')
schema=a.load(HERE/'module_input.schema.json')
schema['required'].append('activation_ready') if 'activation_ready' not in schema['required'] else None
schema['properties']['activation_ready']={'const':False,'description':'Planning input only. Runtime activation is outside this audit.'}
schema['properties']['frame']['properties']['local_to_master']={'$ref':'#/$defs/transform'}
schema['$defs']['transform']={'type':'object','required':['basis','translation'],'additionalProperties':False,'properties':{'basis':{'type':'array','minItems':3,'maxItems':3,'items':{'$ref':'#/$defs/vec3'}},'translation':{'$ref':'#/$defs/vec3'}}}
t=schema['properties']['treatment'];t['properties']['mullion_width_m']={'type':'number','minimum':0};t['properties']['sill_thickness_m']={'type':'number','exclusiveMinimum':0};t['properties']['surround_profile']={'enum':['rectangular_ring','exact_source_polygon_ring','recovered_rectangular_ring']};t['properties']['mullion_policy']={'enum':['preserve_source_and_review_dimensions','none_source_slit','explicit_design_required']};t['properties']['transom_policy']={'enum':['none_authored_design_review_required','explicit_design_required']}
for k in ['sill_thickness_m','surround_profile','mullion_policy','transom_policy']:
    if k not in t['required']:t['required'].append(k)
for k in ['source_profile_clipping','source_envelope_clearance','signed_permutation_frame']:
    if k not in schema['properties']['validation']['required']:schema['properties']['validation']['required'].append(k)
schema['properties']['preservation']['properties']['asset_footprint_and_envelope_unchanged']={'const':True}
if 'asset_footprint_and_envelope_unchanged' not in schema['properties']['preservation']['required']:schema['properties']['preservation']['required'].append('asset_footprint_and_envelope_unchanged')
write('module_input.schema.json',schema)

masters={};checked_ops=0
for x in assets.values():
    assert a.sha(a.ROOT/x['source_master_path'])==x['source_sha256']
    assert a.sha(a.ROOT/x['render_path'])==x['render_sha256']
    masters[x['asset_key']]=a.load(a.ROOT/x['source_master_path'])
assert len(assets)==72==summary['asset_count'] and len(windows)==1694==summary['glass_face_count']
assert len(entries)==1063==summary['door_entry_feature_records']
assert len({(w['asset_key'],w['component'],w['instance'],w['glass']['id']) for w in windows})==len(windows)
assert sum(x['city_placements'] for x in assets.values())==summary['city_placements']
assert sum(summary['source_profile_counts'].values())==len(windows)
assert all(not x['shared_component_instance_counts'] for x in assets.values())
for name in ['catalog','mapping','index']:assert a.sha(a.ROOT/inventory[name+'_path'])==inventory[name+'_sha256']
for w in windows:
    m=masters[w['asset_key']];comp=next(c for c in m['components'] if c['id']==w['component']);ops={o['id']:o for o in comp['operations']};ins=next(i for i in m['instances'] if i['id']==w['instance']);assert ins['component']==comp['id']
    for f in [w['glass']]+w['associated_features']:
        assert a.core.digest(ops[f['id']])==f['operation_sha256'];checked_ops+=1
        lo,hi=a.bounds(ops[f['id']]);assert a.extent(lo,hi)==f['dimensions_m']
    if w['associated_aperture']:
        ap=w['associated_aperture'];assert a.core.digest(ops[ap['id']])==ap['operation_sha256'];assert ops[ap['id']]['action']=='cut';checked_ops+=1
        assert ops[ap['id']].get('transform')==ops[w['glass']['id']].get('transform')
    tr=w['local_to_master'];assert all(sum(abs(z)>1e-7 for z in row)==1 and abs(sum(z*z for z in row)-1)<1e-7 for row in tr['basis'])
for e in entries:
    m=masters[e['asset_key']]
    if e.get('scope')=='assembly':op=next(o for o in m['assembly_cuts'] if o['id']==e['operation']['id']);assert a.core.digest(op)==e['operation_sha256']
    else:
        c=next(c for c in m['components'] if c['id']==e['component']);op=next(o for o in c['operations'] if o['id']==e['feature']['id']);assert a.core.digest(op)==e['feature']['operation_sha256']
    checked_ops+=1

examples=[]
representatives=[('existing_aperture','c3_property_ordinary_r2_ffe48e455673c4ad','rectangular_cut_bay'),('pointed_cavity','registered_castle_west_residence','landmark_polygon_painted_panel'),('recovered_cavity',None,'recovered_flat_painted_panel'),('slit_cavity','registered_castle_rear_square_tower','landmark_polygon_painted_panel')]
for label,key,profile in representatives:
    w=next(w for w in windows if w['source_profile']==profile and (key is None or w['asset_key']==key));x=assets[w['asset_key']];m=masters[w['asset_key']];c=next(c for c in m['components'] if c['id']==w['component']);ops={o['id']:o for o in c['operations']};g=ops[w['glass']['id']];ap=w['associated_aperture'];has_mullion=any(f['role']=='mullion' for f in w['associated_features']);rect=profile=='rectangular_cut_bay';slit=label=='slit_cavity'
    def bind(f):return {'component':c['id'],'id':f['id'],'sha256':f['operation_sha256'],'role':f.get('role','aperture_cut')}
    treatment={'fine_pitch_m':.05,'glass_recess_m':.15,'glass_thickness_m':.05,'mullion_width_m':.1 if has_mullion else 0,'sill_projection_m':.15 if rect else 0,'sill_thickness_m':.1,'surround_profile':{'rectangular_cut_bay':'rectangular_ring','landmark_polygon_painted_panel':'exact_source_polygon_ring','recovered_flat_painted_panel':'recovered_rectangular_ring'}[profile],'mullion_policy':'none_source_slit' if slit else 'preserve_source_and_review_dimensions' if has_mullion else 'explicit_design_required','transom_policy':'none_authored_design_review_required','shutter_policy':'not_applicable_pointed_church_or_slit' if slit or profile=='landmark_polygon_painted_panel' else 'preserve_source_shutters' if any(f['role']=='shutter' for f in w['associated_features']) else 'explicit_design_required','material_slots':{'glass':g['material'],'surround':w['associated_features'][0]['material']}}
    candidate={'schema':'riverstone.facility_openings.module_candidate.v1','id':'audit_only_'+label,'activation_ready':False,'source':{'asset_key':x['asset_key'],'master_path':x['source_master_path'],'master_sha256':x['source_sha256'],'render_path':x['render_path'],'render_sha256':x['render_sha256'],'cache_pitch_m':x['cache_pitch_m']},'bindings':{'instance_ids':[w['instance']],'component_ids':[c['id']],'glass_operation':bind(w['glass']),'feature_operations':[bind(f) for f in w['associated_features']],'wall_operations':[],'aperture_operations':[bind(ap)] if ap else []},'frame':{'local_to_master':w['local_to_master'],'outward_normal_local':[0,0,w['local_outward_sign']],'surface_coordinate_m':w['source_surface_coordinate_m'],'profile_kind':profile},'opening':{'shape':ap['shape'] if ap else g['shape'],'source_aperture_exists':bool(ap),'source_frame_is_filled_panel':w['source_frame_is_filled_panel'],'depth_interval_m':[w['source_surface_coordinate_m']-.22,w['source_surface_coordinate_m']] if w['local_outward_sign']==1 else [w['source_surface_coordinate_m'],w['source_surface_coordinate_m']+.22],'width_m':w['glass']['dimensions_m'][0],'height_m':w['glass']['dimensions_m'][1]},'treatment':treatment,'coarse_patch_contract':{'mode':'pending_exact_binding','suppression_scope':'unresolved_do_not_activate','source_feature_hashes':[w['glass']['operation_sha256']]+[f['operation_sha256'] for f in w['associated_features']],'patch_boundary':{'coordinate_system':'operation_local','source_glass_envelope_m':w['glass']['bounds_m'],'status':'pending_finite_source_wall_and_cache_face_binding','required_route':w['upgrade_route'],'whole_asset_bounds_are_not_a_patch':True},'whole_material_group_removal':False,'atomic_activation':True,'keep_unrelated_wall_geometry':True,'existing_api_verified':False},'preservation':{k:True for k in schema['properties']['preservation']['required']},'validation':{k:'pending' for k in schema['properties']['validation']['required']}}
    candidate['validation']['source_hashes']='pass';candidate['validation']['signed_permutation_frame']='pass'
    jsonschema.Draft202012Validator(schema).validate(candidate);examples.append(candidate)
jsonschema.Draft202012Validator.check_schema(schema)
zero=[{'asset_key':w['asset_key'],'component':w['component'],'instance':w['instance'],'operation':w['glass']['id'],'dimensions_m':w['glass']['dimensions_m'],'cache_lattice_counts':w['glass']['cache']['aabb_lattice_counts']} for w in windows if w['glass']['cache']['status']=='source_present_cache_absent_zero_axis_sample']
plan={'schema':'riverstone.facility_openings.candidate_plan.v1','status':'audit_only_no_authoring_or_activation','scope':{'assets':72,'city_placements':332,'glass_faces':1694,'catalog_sha256':inventory['catalog_sha256']},'decision_order':[{'stage':1,'scope':'Existing authored aperture windows','window_faces':1254,'priority':'Manor/property 224 faces and ordinary-derived cathedral/monastery ranges first','required_geometry':'Generic depth-defined glazing, ring frame, physical mullion where appropriate, sill and style-gated shutters inside the existing aperture and source envelope.','patch_requirement':'Bind old glazing and frame cache faces exactly, split only finite window patches, replace atomically. Existing aperture does not make a pure overlay sufficient.'},{'stage':2,'scope':'Landmark polygon panels: 348 pointed and 9 rectangular','window_faces':357,'priority':'9 sub-grid tower slit panes plus castle, cathedral, monastery and port panels','required_geometry':'Exact source-polygon ring; local wall and filled-surround cavity; inset pane with unobstructed reveal. Preserve narrow slit design; no automatic central bars or shutters.','patch_requirement':'Identify every intersecting wall and filled-surround owner before bounded cuts; retain unrelated stone and other source layers.'},{'stage':3,'scope':'Recovered flat painted panels','window_faces':83,'priority':'Recovered precinct ranges after safe cavity binding exists','required_geometry':'Source has no recess or mullion. Author bounded cavity and ring; any new bars or shutters require explicit style and clearance review.','patch_requirement':'Same local wall and filled-panel replacement requirement as pointed panels; source front/back signs differ.'},{'stage':4,'scope':'Doors and entrances','feature_records':1063,'required_geometry':'Reuse existing leaf/frame/portal profiles; audit local material depth if a door enhancement is later commissioned.','preservation':'Open loading bays and portals must remain open; retain source cuts, entrance clear dimensions, thresholds and floors. Do not fill a doorless opening.'}],'hard_gates':['Exact cache face provenance or finite spatial splitting must be implemented and verified before activation; current render groups alone do not identify source operations.','Never suppress a whole stone, timber or glass material group or full coarse wall.','Preserve source component operation ordering, cuts, transforms, grid origin, placement IDs, footprints and entrance metadata.','Profile clipping must use the original common predicate; no arbitrary rectangularization of pointed windows.','All local detail must fit the authored asset envelope and preserve city neighbor/walkway clearance.','No decorative closure of authentic slits, open shelters, loading bays or portals.','Later common .05 ROI comparison and visual checks must prove old coarse face removal, actual depth, visibility, seams and atomic near/far switching.'],'evidence_limits':['1694 rows count source component instances per unique asset, not multiplication by 332 city placements.','Zero conservative AABB-axis sample count proves a feature cannot be sampled; nonzero counts and nearby matching quads do not prove exact feature ownership.','193 glass rows without a matching exterior patch remain occlusion/sampling unresolved.','No source transoms were found; absence is not evidence every style needs a transom.','No source master, render cache, runtime integration or collision file changed.'],'guaranteed_absent_glass':zero,'planning_examples':examples}
write('candidate_plan.json',plan)
checks={'schema':'riverstone.facility_openings.audit_checks.v1','passed':True,'source_and_render_file_hashes_checked':144,'catalog_index_mapping_hashes_checked':3,'unique_glass_records_checked':len(windows),'door_entry_records_checked':len(entries),'source_operation_bindings_checked':checked_ops,'schema_check':'Draft202012Validator.check_schema passed','schema_examples_validated':len(examples),'aperture_glass_frame_alignment':'all existing aperture operations share their glass operation transform','signed_permutation_glass_frames':len(windows),'shared_component_multiple_instances':0,'compile_count':0,'source_edits':0,'runtime_edits':0,'conservative_cache_absence':'inclusive epsilon-expanded AABB; boundary-touching samples are retained as possible rather than falsely marked missing','summary_counts_reconciled':True}
write('checks.json',checks)
size=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file());assert size<1024*1024,size
print(json.dumps({'checked':checks,'directory_bytes':size},sort_keys=True))
