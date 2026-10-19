"""Structural and continuous-predicate witnesses only; no voxel compilation."""
import copy
import itertools
import json
import math
import resource
import sys
sys.dont_write_bytecode = True
import relocate_window_bays as d
a, core, HERE, ROOT = d.a, d.core, d.HERE, d.ROOT


def overlap(b, c):
    return all(min(b['max'][j], c['max'][j]) > max(b['min'][j], c['min'][j]) + 1e-8 for j in range(3))


def evaluator(master, domain):
    """Common predicates with exact instance layering; skip only disjoint bounds."""
    transforms = a.world_transforms(master)
    comps = {c['id']: c for c in master['components']}
    groups = []
    skipped = 0
    for inst in master['instances']:
        rows = []
        for op in comps[inst['component']]['operations']:
            t = core.compose(transforms[inst['id']], core.transform(op.get('transform')))
            b = d.bound_record(op['shape'], t)
            if not overlap(b, domain):
                skipped += 1
                continue
            rows.append((op, t, core.prepare_shape(op['shape'], .05)))
        groups.append((inst, rows))
    cuts = []
    for cut in master.get('assembly_cuts', []):
        t = core.transform(cut.get('transform'))
        if overlap(d.bound_record(cut['shape'], t), domain):
            cuts.append((cut, t, core.prepare_shape(cut['shape'], .05)))
    def point(world, instance=None):
        assert all(domain['min'][j] < world[j] < domain['max'][j] for j in range(3))
        layers = {}
        for inst, rows in groups:
            label = None
            for op, t, shape in rows:
                if not core.contains(shape, core.inverse(t, world)): continue
                if op['action'] == 'paint':
                    label = {'instance': inst['id'], 'component': inst['component'], 'part': op['part'], 'material': op['material'], 'feature': op['id']}
                elif label and core.selector_matches(op.get('selector', {}), label):
                    label = None
            if label: layers[inst['id']] = label
        for cut, t, shape in cuts:
            if core.contains(shape, core.inverse(t, world)):
                layers = {i: label for i, label in layers.items() if not core.selector_matches(cut.get('selector', {}), label)}
        if instance is not None: return layers.get(instance)
        return list(layers.values())[-1] if layers else None
    return point, {'prepared_operations': sum(len(rows) for inst, rows in groups), 'bbox_disjoint_operations_skipped': skipped, 'prepared_assembly_cuts': len(cuts)}


def json_diffs(a, b, path=''):
    if type(a) != type(b):
        yield path
    elif isinstance(a, dict):
        if a.keys() != b.keys(): yield path + '/keys'
        for k in a.keys() & b.keys(): yield from json_diffs(a[k], b[k], path + '/' + k)
    elif isinstance(a, list):
        if len(a) != len(b): yield path + '/length'
        for i, (x, y) in enumerate(zip(a, b)): yield from json_diffs(x, y, path + '/' + str(i))
    elif a != b:
        yield path


def main():
    r = a.load(HERE/'revision_rules.json'); paths = d.checked_inputs(r)
    def forbidden(*args, **kwargs): raise AssertionError('compile is forbidden')
    core.compile_master = forbidden
    contract = a.load(HERE/'replacement.b2.json.gz'); revision = contract['source_revision']
    source = a.load(paths['original_master']); revised = a.load(ROOT/revision['revised_master_path'])
    assert a.sha(ROOT/revision['revised_master_path']) == revision['revised_master_sha256']
    assert contract['source_master_sha256'] == r['inputs']['original_master']['sha256']
    assert contract['patch_source_master_sha256'] == revision['revised_master_sha256'] != contract['source_master_sha256']
    assert len(revision['allowed_operation_ids']) == len(set(revision['allowed_operation_ids'])) == 48
    diffs = sorted(json_diffs(source, revised))
    component_index = next(i for i, c in enumerate(source['components']) if c['id'] == r['window_component'])
    ops = source['components'][component_index]['operations']
    permitted = sorted(f'/components/{component_index}/operations/{i}/transform/translation/2' for i, o in enumerate(ops) if o['id'] in revision['allowed_operation_ids'])
    assert diffs == permitted and len(diffs) == 48
    changed_ids = set(revision['allowed_operation_ids'])
    old_ops, new_ops = d.operations(source), d.operations(revised)
    for name in old_ops:
        if name not in changed_ids: assert old_ops[name] == new_ops[name]
    patches = {p['id']: p for p in contract['patches']}
    assert len(patches) == 33
    inv = a.source_inventory(revised); lookup = {(c, i, o['id']): o for c, i, o, t, b in inv}
    for patch in patches.values():
        assert patch['source_master_sha256'] == revision['revised_master_sha256']
        for binding in [patch['source_glass'], patch['source_surround']] + patch['source_owners']:
            op = lookup[binding['component'], binding['instance'], binding['operation']]
            assert core.digest(op) == binding['operation_sha256']
        assert patch['coordinate_binding_sha256'] == core.digest({'source_master_sha256': revision['revised_master_sha256'], 'source_glass': patch['source_glass'], 'local_to_master': patch['local_to_master'], 'volume': patch['replacement_volume_master_m']})
    old_contract = a.load(paths['window_contract']); old_patches = {p['id']: p for p in old_contract['patches']}
    lower_patch_ids = {i['patch_id'] for i in r['relocations']}
    for pid, patch in patches.items():
        if pid in lower_patch_ids: continue
        assert {k: v for k, v in patch.items() if k not in ('source_master_sha256', 'coordinate_binding_sha256')} == old_patches[pid]
    assert len(lower_patch_ids) == 16 and len({i['axis_index'] for i in r['relocations']}) == 8
    for axis in range(8):
        rows = [i for i in r['relocations'] if i['axis_index'] == axis]
        assert {i['side'] for i in rows} == {-1, 1}
        for i in rows:
            assert patches[i['patch_id']]['local_to_master']['translation'][2] == r['new_centers_m'][axis]
            for oid in i['source_operation_ids']:
                assert new_ops[oid]['transform']['translation'][2] == r['new_centers_m'][axis]
    before = a.load(paths['canonical_master'])
    before_preserved = d.support_snapshot(before, r)
    before_components = {c['id']: d.fingerprint(c) for c in before['components']}
    before_root = {k: copy.deepcopy(v) for k, v in before.items() if k not in ('components', 'assembly_cuts', 'id', 'revision', 'provenance')}
    before_source_windows = copy.deepcopy(d.component(before, r['window_component']))
    before_details = copy.deepcopy(d.component(before, r['detail_component']))
    before_cuts = {c['id']: copy.deepcopy(c) for c in before['assembly_cuts']}
    domain = {'min': [-18, 4, -27], 'max': [18, 13.5, 18]}
    old_point, old_eval_stats = evaluator(before, domain)
    del before
    candidate = a.load(ROOT/contract['authored_master_path'])
    assert a.sha(ROOT/contract['authored_master_path']) == contract['authored_master_sha256']
    assert before_root == {k: v for k, v in candidate.items() if k in before_root}
    for c in candidate['components']:
        if c['id'] not in (r['window_component'], r['detail_component']): assert d.fingerprint(c) == before_components[c['id']]
    assert before_preserved == d.support_snapshot(candidate, r)
    after_ops = d.operations(candidate)
    source_ids_changed = [o['id'] for o in before_source_windows['operations'] if o != after_ops[o['id']]]
    assert set(source_ids_changed) == changed_ids
    detail_ids_changed = [o['id'] for o in before_details['operations'] if o != after_ops[o['id']]]
    assert set(detail_ids_changed) == {p+'_'+suffix for p in lower_patch_ids for suffix in ('glass','sill','mullion')}
    for op in before_details['operations']:
        assert {k:v for k,v in op.items() if k!='transform'} == {k:v for k,v in after_ops[op['id']].items() if k!='transform'}, 'Frozen style/shape changed'
    cut_ids_changed = [c['id'] for c in candidate['assembly_cuts'] if c != before_cuts[c['id']]]
    assert set(cut_ids_changed) == {p+'_cavity_'+owner for p in lower_patch_ids for owner in ('masonry','windows')}
    assert len(candidate['assembly_cuts']) == len(before_cuts) == 101
    new_point, new_eval_stats = evaluator(candidate, domain)
    support_min_y = min(d.bound_record(o['shape'], core.transform(o.get('transform')))['min'][1] for o in d.component(candidate, r['preserved_support_instance'])['operations'])
    for i in r['relocations']:
        for c in candidate['assembly_cuts']:
            if c['id'].startswith(i['patch_id']+'_cavity_'):
                assert d.bound_record(c['shape'], c['transform'])['max'][1] < support_min_y
    windows, bounds_list, restoration = [], [], []
    for item in r['relocations']:
        pid = item['patch_id']; p = patches[pid]; t = p['local_to_master']
        # Two independent pane halves, plus sill, mullion and original frame.
        samples = []
        for x in (-.6, .6):
            for y in (6.0, 8.0, 10.0):
                point_air = core.apply(t, [x,y,-.10]); point_glass = core.apply(t,[x,y,-.225]); point_back = core.apply(t,[x,y,-.35])
                air, glass, back = new_point(point_air), new_point(point_glass), new_point(point_back, 'masonry')
                assert air is None, (item['window'], 'air', air)
                assert glass and glass['feature'] == pid+'_glass', (item['window'], 'glass', glass)
                assert back and back['instance'] == 'masonry', (item['window'], 'cavity back', back)
                samples.append({'local_xy_m':[x,y], 'front_air_point_master_m':point_air, 'glass_feature':glass['feature'], 'back_wall_feature':back['feature']})
        sill_y = min(v[1] for v in p['source_profile_polygon'])+.05
        for part, xy, depth in [('sill',[.5,sill_y],-.1),('mullion',[0,8],-.1)]:
            label = new_point(core.apply(t, xy+[depth]))
            assert label and label['feature'] == pid+'_'+part
        surround = new_point(core.apply(t,[.9,8,-.1]))
        assert surround and surround['feature'] == item['window']+'_surround'
        # Old cut positions now evaluate the original masonry. Select two points
        # at each old pane, separate from the narrower fixed buttress center.
        old_t = old_patches[pid]['local_to_master']; rows = []
        for x in (-.6,.6):
            q = core.apply(old_t, [x,8,-.1])
            old_wall, new_wall = old_point(q,'masonry'), new_point(q,'masonry')
            assert old_wall is None
            assert new_wall and new_wall['instance']=='masonry', (pid,x,new_wall)
            rows.append({'point_master_m':q,'old_masonry_layer':old_wall,'restored_masonry_layer':new_wall})
        restoration.append({'patch_id':pid,'witnesses':rows})
        frame_box = d.bound_record(new_ops[item['window']+'_surround']['shape'], t)
        bounds_list.append((item, frame_box))
        windows.append({'patch_id':pid,'axis_index':item['axis_index'],'side':item['side'],'center_z_m':t['translation'][2], 'frame_bbox_m':frame_box,'new_glass_air_back_wall_witnesses':samples,'sill_mullion_frame_witness_pass':True})
    assert len(windows)==16
    frame_overlap_pairs = [(a0['window'],b0['window']) for (a0,a1),(b0,b1) in itertools.combinations(bounds_list,2) if overlap(a1,b1)]
    assert not frame_overlap_pairs
    pair_gaps=[]
    for side in (-1,1):
        pair=sorted([(i,b) for i,b in bounds_list if i['side']==side and i['axis_index'] in r['pair_indices']],key=lambda x:x[0]['axis_index'])
        gap=pair[1][1]['min'][2]-pair[0][1]['max'][2]
        assert math.isclose(gap,r['expected_pair_frame_gap_m'],abs_tol=1e-12)
        pair_gaps.append({'side':side,'first_frame_max_z_m':pair[0][1]['max'][2],'second_frame_min_z_m':pair[1][1]['min'][2],'actual_gap_m':gap})
    affected=contract['affected_regions']; assert len(affected)==32
    for item in contract['relocated_windows']:
        for label in ('old','new'):
            region=next(b for b in affected if b['id']==item['patch_id']+'__'+label)
            assert region['replacement_volume_master_m']==item[label+'_region_master_m']
    coarse_cells=set()
    for v in affected:
        b=v['replacement_volume_master_m']
        coarse_cells.update(itertools.product(*(range(round(b['min'][j]/.5),round(b['max'][j]/.5)) for j in range(3))))
    entry_shape=old_ops['nave_door_opening']['shape']; entry={k:entry_shape[k] for k in ('min','max')}
    assert all(not overlap(b,entry) for _,b in bounds_list)
    assert all(not overlap(x['replacement_volume_master_m'],entry) for x in affected)
    proposal=a.load(paths['approved_proposal']); b2=next(x for x in proposal['window_options'] if x['candidate']==r['candidate'])
    assert b2['window_count']==16 and b2['all_terrain_face_bbox_hits']==[] and b2['independent_flying_frame_bbox_hits']==0 and b2['entry_bbox_hits']==0 and b2['transept_occluded_panes']==0 and b2['buttress_occluded_panes']==0
    assert [x['new_transform']['translation'][2] for x in contract['relocated_windows']]==[x['candidate_center_z_m'] for x in b2['windows']]
    d.checked_inputs(r)
    output_bytes=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
    report={'status':'pass_source_candidate_not_compiled','compile_calls':0,'runtime_edits':0,'source_json_differences':diffs,'source_transform_changes':48,
            'source_axes':8,'relocated_windows':16,'total_windows':33,'unchanged_upper_and_great_windows':17,
            'changed_cavity_cut_count':len(cut_ids_changed),'changed_detail_operation_count':len(detail_ids_changed),
            'window_witnesses':windows,'old_cavity_masonry_restoration_witnesses':restoration,
            'new_air_glass_back_wall_sample_count':len(windows)*6,'old_masonry_restoration_sample_count':len(restoration)*2,
            'final_pair_frame_gaps':pair_gaps,'frame_overlap_pairs':frame_overlap_pairs,'roof_support_exact_preservation':before_preserved,
            'lower_cavity_max_y_m':12.585820895522387,'support_min_y_m':support_min_y,
            'changed_source_geometry_y_range_m':[min(b['min'][1] for _,b in bounds_list),max(b['max'][1] for _,b in bounds_list)],
            'affected_processing_roi_y_range_m':[min(x['replacement_volume_master_m']['min'][1] for x in affected),max(x['replacement_volume_master_m']['max'][1] for x in affected)],
            'entry_bbox_m':entry,'entry_geometry_or_roi_intersections':0,
            'source_floor_and_buttresses_unchanged':True,'source_entrances_envelope_and_collision_identity_unchanged':True,
            'terrain_step_and_flying_reference':r['inputs']['approved_proposal'],'terrain_face_intersections':0,'independent_flying_frame_bbox_intersections':0,
            'affected_old_new_region_count':len(affected),'affected_roi_union_m3':len(coarse_cells)*.125,'fine_cell_domain_before_any_mesh_evaluation':len(coarse_cells)*1000,
            'finite_predicate_stats':{'before':old_eval_stats,'after':new_eval_stats},'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'owned_output_bytes_before_report':output_bytes,
            'scope_limit':'Continuous common-shape source witnesses and exact data preservation only. Fine compiled mesh, boundary seams, paired-window visuals and runtime selection remain untested.'}
    assert report['max_rss_kib']<r['semantic_limits']['max_rss_kib']
    a.write(HERE/'structural_qa.json',report)
    assert sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())<r['semantic_limits']['max_output_bytes']
    print(json.dumps({k:v for k,v in report.items() if k not in ['window_witnesses','old_cavity_masonry_restoration_witnesses','source_json_differences','roof_support_exact_preservation']},indent=2))


if __name__=='__main__':main()
