"""Hash-pinned roof-only compile handoff; preserves the original nonroof baseline."""
from __future__ import annotations
import itertools
import copy
import json
import gzip
import math
from pathlib import Path
import adapter as a
import compile_batch as batch
import layered_compile as layer

FACILITY=layer.HERE.parent/'facility_roofs'
CATALOG=FACILITY/'finished/layered_compile_catalog.json'
CONTRACTS=FACILITY/'finished/replacement_contracts.v2.json'
OUTPUT=FACILITY/'compiled_priority_r01'


def ref(path):return {'path':str(Path(path).relative_to(a.ROOT)),'sha256':a.sha(path)}


def build():
    catalog=a.load(CATALOG);contracts={e['asset_key']:e for e in a.load(CONTRACTS)['assets']};assets=[]
    for entry in catalog['assets']:
        key=entry['asset_key'];contract=contracts[key]
        source=a.load(a.ROOT/entry['source_master_path']);master=layer.load_master(a.ROOT/entry['emitted_master_path'])
        source_render=a.load(a.ROOT/entry['source_render_path'])
        checks={'source_master_hash':a.sha(a.ROOT/entry['source_master_path'])==entry['source_sha256'],
            'emitted_master_hash':a.sha(a.ROOT/entry['emitted_master_path'])==entry['emitted_master_sha256'],
            'baseline_render_hash':a.sha(a.ROOT/entry['source_render_path'])==entry['source_render_sha256'],
            'roof_only_declared':master.get('metadata',{}).get('roof_only') is True,
            'original_material_palette':master['materials']==source['materials'],
            'all_selected_roof_groups_authored':entry['source_authoring_complete_for_all_roof_groups'] is True,
            'no_pending_original_roof_operations':not contract['pending_shape_operations']}
        material_map=[];required=set()
        for g in contract['render_groups']:
            original={(c['id'],o['id']) for c in source['components'] for o in c['operations'] if o['action']=='paint' and o.get('material')==g['material_id']}
            represented={(r['component'],r['operation']) for r in g['represented_roof_operations']};required|=original
            group=source_render['groups'][g['source_render_group_index']]
            checks['exhaustive_'+g['material_id']]=original==represented and not g['unsupported_refs']
            checks['baseline_group_'+g['material_id']]=group['material']==g['material_id'] and len(group['quads'])==g['source_quad_count'] and a.core.digest(group)==g['source_group_sha256_canonical']
            material_map.append({k:g[k] for k in ('material_id','source_render_group_index','source_quad_count','source_quad_index_range_inclusive','source_group_sha256_canonical','represented_roof_operations')})
        selected_materials=set(entry['whole_group_material_ids'])
        required={(c['id'],o['id']) for c in source['components'] for o in c['operations'] if o['action']=='paint' and o.get('material') in selected_materials}
        mapped_materials={g['material_id'] for g in material_map}
        for material in sorted(selected_materials-mapped_materials):
            material_map.append({'material_id':material,'source_render_group_index':None,'source_quad_count':0,
                'baseline_group_absent':True,'activation':'Add near geometry; there is no original render group to suppress.',
                'represented_roof_operations':[{'component':c['id'],'operation':o['id']} for c in source['components'] for o in c['operations'] if o['action']=='paint' and o.get('material')==material]})
        represented=set();instances=set()
        for c in master['components']:
            meta=c['metadata'];provenance=meta['provenance'];identity=meta['shared_row_source']['instance_metadata']['source_identity']
            for op in provenance['source_operations']:
                represented.add((provenance['source_component'],op));instances.add((identity['instance'],provenance['source_component'],op))
        expected_instances={(i['id'],c,o) for c,o in required for i in source['instances'] if i['component']==c}
        checks['all_source_operation_ids_in_emitted_provenance']=represented==required
        checks['all_original_roof_instances_in_emitted_provenance']=instances==expected_instances
        selected_components={c for c,o in required}
        original_roof=copy.deepcopy(source)
        original_roof['components']=[c for c in original_roof['components'] if c['id'] in selected_components]
        original_roof['instances']=[i for i in original_roof['instances'] if i['component'] in selected_components]
        original_roof['constraints']=[];original_roof['assembly_cuts']=[]
        original_roof_bounds=layer.SpatialSource(original_roof,.05,range_only=True).bounds
        roof_points=[v for group in source_render['groups'] if group['material'] in selected_materials for quad in group['quads'] for v in quad]
        cache_roof_bounds={'min':[min(v[j] for v in roof_points) for j in range(3)],'max':[max(v[j] for v in roof_points) for j in range(3)]}
        roof_cuts=[(c['id'],o['id']) for c in source['components'] if c['id'] in selected_components for o in c['operations'] if o['action']=='cut']
        # These priority sources have no component-local roof cuts. Omitted global cuts must be strictly disjoint.
        roof_bounds=layer.SpatialSource(master,.05,range_only=True).bounds;disjoint_cuts=[]
        for cut in source.get('assembly_cuts',[]):
            shape=a.core.prepare_shape(cut['shape'],.05);low,high=a.core.shape_bounds(shape);transform=a.core.transform(cut.get('transform'))
            corners=[a.core.apply(transform,v) for v in itertools.product(*zip(low,high))]
            low=[min(v[j] for v in corners) for j in range(3)];high=[max(v[j] for v in corners) for j in range(3)]
            disjoint=any(high[j]<roof_bounds[0][j] or low[j]>roof_bounds[1][j] for j in range(3))
            disjoint_cuts.append({'id':cut['id'],'source_cut':cut,'world_bounds':[low,high],'strictly_disjoint_from_complete_roof_bounds':disjoint})
        checks['priority_roof_cut_contract']=not roof_cuts and not master.get('assembly_cuts') and all(c['strictly_disjoint_from_complete_roof_bounds'] for c in disjoint_cuts)
        source_nonroof_cuts=[{'component':c['id'],'operation':o['id']} for c in source['components'] if c['id'] not in selected_components for o in c['operations'] if o['action']=='cut']
        if not all(checks.values()):raise ValueError('Facility source preservation check failed: '+key+' '+str([k for k,v in checks.items() if not v]))
        record={'asset_key':key,'native_asset_key':key,'status':'COMPILE_PENDING','source_master_sha256':entry['source_sha256'],
            'authored_master_sha256':entry['emitted_master_sha256'],'emitted_master_path':entry['emitted_master_path'],
            'source_master_path':entry['source_master_path'],'source_render_path':entry['source_render_path'],'source_render_sha256':entry['source_render_sha256'],
            'scope':'complete selected roof material groups only; original nonroof structure and collision remain the baseline',
            'original_roof_material_mapping':material_map,
            'bounds_contract':{'original_selected_roof_analytic':{'min':original_roof_bounds[0],'max':original_roof_bounds[1]},
                'original_cache_whole_asset':source_render['bounds'],'original_cache_selected_roof_groups':cache_roof_bounds,
                'cache_is_not_source_geometry_envelope':True,'source_geometry_cropped_to_cache_bounds':False},
            'added_source_materials':[{'material':material,'source_operations':[{'component':c['id'],'operation':o['id']} for c in source['components'] for o in c['operations'] if o['action']=='paint' and o.get('material')==material],
                'source_master_sha256':entry['source_sha256'],'material_definition':source['materials'][material]} for material in sorted(selected_materials-mapped_materials)],
            'source_operation_ids':[{'component':c,'operation':o} for c,o in sorted(required)],
            'source_instance_operation_ids':[{'instance':i,'component':c,'operation':o} for i,c,o in sorted(instances)],
            'source_preservation_checks':checks,'selected_roof_source_cuts':roof_cuts,'original_assembly_cuts_proven_disjoint':disjoint_cuts,'nonroof_cuts_preserved_in_original_baseline':source_nonroof_cuts,
            'declared_authoring_seed':a.load(FACILITY/'inputs/roof_rules.v1.json')['seed'],'seed_rules':ref(FACILITY/'inputs/roof_rules.v1.json'),'seed_embedded_in_finished_master':False,'baseline_structure_unchanged':True,'baseline_source_constraints_preserved':source.get('constraints',[]),'constraints':master.get('constraints',[]),'runtime_activation':'PENDING_PARENT_VISUAL_ACCEPTANCE',
            'replacement_contract':ref(CONTRACTS),'source_validation':ref(FACILITY/'finished/all_supported/validation_report.json'),
            'native_roi_validation':ref(FACILITY/'finished/post_cell_bounds/validation.json')}
        compiled=batch.inspect_output(key,OUTPUT)
        if compiled:
            stats=a.load(a.ROOT/compiled['stats_path']);source_bounds=layer.SpatialSource(master,.05,range_only=True).bounds
            header=stats['compiled_header'];edge=header['chunk_edge_fine_cells'];origin=header['grid_origin']
            lo=[math.floor((source_bounds[0][j]-origin[j])/.05+a.core.EPS) for j in range(3)]
            hi=[math.ceil((source_bounds[1][j]-origin[j])/.05-a.core.EPS) for j in range(3)]
            expected=set(itertools.product(*(range(lo[j]//edge,(hi[j]+edge-1)//edge) for j in range(3))))
            if 'chunk_enumeration' in stats:
                plan=layer.chunk_enumeration.enumerate_paint_chunks(layer.SpatialSource(master,.05,range_only=True),origin,edge,a.core.EPS)
                expected={tuple(v//edge for v in low) for low in plan['owned_lows']}
                record['chunk_enumeration']={k:v for k,v in plan.items() if k!='owned_lows'}
            actual=[tuple(c['chunk']) for c in stats['chunks']]
            coverage_checks={'all_original_shape_domain_chunks_compiled':len(actual)==len(expected) and set(actual)==expected,
                'native_integer_sample_bounds':stats['spatial_sampling_contract']=='original_shapes_integer_cell_bounds_v1',
                'independent_render_qa_pass':compiled.get('independent_qa',{}).get('pass') is True,
                'all_chunk_exterior_faces_exact':stats['all_chunks_exact_exterior_face_match'] is True,
                'all_chunks_overlap_free':stats['all_chunks_overlap_free'] is True,
                'constraints_globally_aggregated':all(c['pass'] for c in stats['constraints'])}
            if not all(coverage_checks.values()):raise ValueError('Facility compile coverage failed: '+key)
            record.update(compiled)
            uncompressed=0
            with gzip.open(a.ROOT/record['files']['.render.json']['path'],'rb') as stream:
                while data:=stream.read(1024*1024):uncompressed+=len(data)
            record['files']['.render.json']['uncompressed_bytes']=uncompressed
            with gzip.open(a.ROOT/record['files']['.render.json']['path'],'rt') as stream:fine_render=json.load(stream)
            fine_bounds=fine_render['bounds'];outside=0;vertex_count=0
            for group in fine_render['groups']:
                for quad in group['quads']:
                    for vertex in quad:
                        vertex_count+=1
                        outside+=not all(original_roof_bounds[0][j]-1e-8<=vertex[j]<=original_roof_bounds[1][j]+1e-8 for j in range(3))
            record['bounds_contract'].update(actual_fine_roof=fine_bounds,render_vertices_tested=vertex_count,
                render_vertices_outside_original_analytic_roof_aabb=outside,
                aabb_check_scope='All actual render vertices against the original roof analytic AABB; this is not a whole-solid containment proof.',
                fine_minus_cache_max=[fine_bounds['max'][j]-cache_roof_bounds['max'][j] for j in range(3)])
            del fine_render

            record['compile_coverage_checks']=coverage_checks;record['complete_selected_source_coverage']=True
            record['global_constraint_results']=stats['constraints'];record['unverified']=['Visual roof intersections and appearance','Atomic runtime material-group switch','Original nonroof near-detail upgrade']
        assets.append(record)
    result={'schema':'riverstone.facility_roof.compiled_priority_catalog.v1','updated_utc':batch.now(),'catalog':ref(CATALOG),
            'assets':assets,'summary':{'requested':2,'compiled':sum(r['status'].startswith('PASS') for r in assets)},
            'single_heavy_compiler':True,'retained_voxel_payload':False,'source_operations_actually_sampled':True,
            'runtime_activation':False,'collision_and_nonroof_structure_policy':'Keep original baseline unchanged.'}
    batch.atomic_json(OUTPUT/'handoff_manifest.json',result);return result

if __name__=='__main__':
    import json
    print(json.dumps(build()['summary']))
