"""Read-only projections of the fixed r5 candidate's immutable native caches.

Roof: union of roof/canopy-material exterior horizontal face projections.
Body: native solid occupancy in the open band primary_floor + (0.8, 1.8) m.
The body metric is occupied structure, NOT enclosed building floor area.
No compilation, scene loading, cache mutation, or AABB area substitution occurs.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from voxel_character.common.core import digest
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
DEFAULT_INPUT = HERE / 'input/draft_candidate.json'
BODY_PACKS = {'ordinary', 'ordinary_density', 'ordinary_density_b15', 'merchant_compounds'}
EPS = 1e-8


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ref(path, root=ROOT):
    path = Path(path).resolve()
    return {'path': str(path.relative_to(root)), 'sha256': sha(path)}


def area(polygons):
    return sum(abs(sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(p, p[1:]+p[:1])))/2 for p in polygons)


def cells_to_rectangles(cells, pitch, origin=(0, 0, 0)):
    """Merge actual occupied XZ lattice squares, never their bounding envelope."""
    rows = defaultdict(list)
    for x, z in cells:
        rows[z].append(x)
    if not rows:
        return []
    active, out = {}, []
    for z in range(min(rows), max(rows)+2):
        runs = []
        for x in sorted(rows.get(z, [])):
            if runs and runs[-1][1] == x:
                runs[-1] = (runs[-1][0], x+1)
            else:
                runs.append((x, x+1))
        for run, start in list(active.items()):
            if run not in runs:
                x0, x1 = (origin[0]+i*pitch for i in run)
                z0, z1 = origin[2]+start*pitch, origin[2]+z*pitch
                out.append([[x0,z0], [x1,z0], [x1,z1], [x0,z1]])
                del active[run]
        for run in runs:
            active.setdefault(run, z)
    assert abs(area(out)-len(cells)*pitch*pitch) < 1e-6
    return out


def classify_roof_materials(master, render, source_packs=()):
    """Retain semantic slate slots and verified color-baked roof component slots."""
    users = defaultdict(set)
    operations = []
    roof_components = set()
    roof_materials = set()
    for component in master['components']:
        cid = component['id']
        if 'roof' in cid.lower():
            roof_components.add(cid)
        for op in component.get('operations', []):
            operations.append((cid, op))
            if op.get('action') == 'paint' and op.get('material'):
                users[op['material']].add(cid)
                if cid in roof_components:
                    roof_materials.add(op['material'])
    rendered = {g['material'] for g in render['groups']}
    selected = {m for m in rendered if m.startswith('slate')}
    selected.update(m for m in roof_materials & rendered if m.startswith('rgb_'))
    # Generic urban-fabric modules preserve role in operation.feature and metadata,
    # not component.id. Select the actual cache faces of each market canopy box;
    # selecting all timber_light would also select the trading counter.
    operation_selectors, unresolved, excluded = [], [], []
    spec = master.get('metadata', {}).get('spec', {})
    matched_cover_ops = []
    for cid, op in operations:
        words = ' '.join((cid, op.get('id', ''), op.get('feature', ''))).lower()
        if not any(word in words for word in ('roof', 'canopy', 'awning', 'shelter', 'cover')):
            continue
        record = {'component_id': cid, 'operation_id': op.get('id'),
                  'feature': op.get('feature'), 'material': op.get('material')}
        if op.get('feature') == 'rounded_canopy_lobe':
            excluded.append({**record, 'reason': 'vegetation crown, not architectural cover'})
            continue
        matched_cover_ops.append(record)
        if op.get('feature') in ('canopy_post', 'center_support_for_long_market_canopy'):
            excluded.append({**record, 'reason': 'canopy support, not cover surface'})
            continue
        if op.get('action') == 'paint' and op.get('material') not in rendered:
            excluded.append({**record, 'reason': 'No exterior cache group for this source material; no rendered surface exists to project.'})
            continue
        if 'masonry' in cid.lower() and 'gable' in op.get('id', '').lower():
            excluded.append({**record, 'reason': 'Masonry gable wall supporting named roof, not roof or canopy cover.'})
            continue
        if op.get('feature') == 'market_canopy':
            shape = op.get('shape', {})
            instances = [i for i in master['instances'] if i['component'] == cid]
            identity = lambda t: not t or (t.get('translation', [0,0,0]) == [0,0,0]
                and t.get('basis', [[1,0,0],[0,1,0],[0,0,1]]) == [[1,0,0],[0,1,0],[0,0,1]]
                and set(t) <= {'translation', 'basis'})
            valid = ('market' in source_packs and spec.get('kind') == 'market_stall'
                and op.get('action') == 'paint' and shape.get('kind') == 'box'
                and identity(op.get('transform')) and len(instances) == 1
                and identity(instances[0].get('transform')))
            if valid:
                lo, hi = shape['min'], shape['max']
                pitch, origin = render['pitch'], render.get('grid_origin', [0,0,0])
                valid = all(isinstance(v, (int, float)) and math.isfinite(v)
                            for v in lo+hi)
                valid = valid and all(abs(origin[k]+round((v-origin[k])/pitch)*pitch-v) < EPS
                                      for k in range(3) for v in (lo[k], hi[k]))
            if valid:
                shared_excluded = []
                for other_cid, other in operations:
                    if other is op or other.get('action') != 'paint' or other.get('material') != op['material']:
                        continue
                    other_shape = other.get('shape', {})
                    other_instances = [i for i in master['instances'] if i['component'] == other_cid]
                    separated = (other_shape.get('kind') == 'box' and identity(other.get('transform'))
                        and len(other_instances) == 1 and identity(other_instances[0].get('transform'))
                        and any(other_shape['max'][k] < lo[k]-EPS or other_shape['min'][k] > hi[k]+EPS
                                for k in range(3)))
                    if not separated:
                        valid = False
                        break
                    shared_excluded.append(other['id'])
            if valid:
                operation_selectors.append({**record, 'instance_id': instances[0]['id'],
                    'source_box_min_m': lo, 'source_box_max_m': hi,
                    'identity_source_transforms_verified': True, 'source_box_native_lattice_aligned': True,
                    'same_material_operations_excluded_by_geometry': shared_excluded,
                    'selector': 'Actual cached horizontal faces of this material fully inside the authored, native-lattice-aligned canopy box. Source box is a selector, never an area surrogate.'})
            else:
                unresolved.append({**record, 'reason': 'market canopy source transforms, lattice alignment, or same-material separation not proven'})
            continue
        if op.get('action') == 'paint' and op.get('material') not in selected:
            # Roof-component RGBs and semantic slate are covered already; other
            # named covers stay visible as unresolved instead of silently zero.
            unresolved.append({**record, 'reason': 'nonsemantic source cover operation requires a verified geometry selector'})
    ambiguity = []
    for material in sorted(selected):
        # Canopies/front galleries use the same semantic roof slot intentionally.
        other = [cid for cid in users[material]
                 if not any(word in cid.lower() for word in ('roof', 'canopy', 'gallery'))]
        if other:
            ambiguity.append({'material': material, 'nonroof_component_ids': sorted(other)})
    unsupported = sorted(m for m in roof_materials & rendered if m not in selected)
    status = ('ambiguous' if ambiguity or unsupported else 'unresolved_cover_geometry' if unresolved
              else 'classified_market_canopy' if operation_selectors else 'classified' if selected
              else 'excluded_vegetation' if excluded else 'no_roof_identified')
    return selected, {
        'selected_materials': sorted(selected | {s['material'] for s in operation_selectors}),
        'material_wide_selected_materials': sorted(selected),
        'operation_geometry_selectors': operation_selectors,
        'source_cover_operation_candidates': matched_cover_ops,
        'unresolved_cover_operations': unresolved,
        'explicitly_excluded_operation_roles': excluded,
        'source_metadata_kind': spec.get('kind'),
        'roof_component_ids': sorted(roof_components),
        'material_component_users': {m: sorted(users[m]) for m in sorted(selected)},
        'ambiguous_shared_materials': ambiguity,
        'unclassified_roof_component_materials': unsupported,
        'classification_status': status,
        'rule': 'slate* semantic roof/canopy slots; rgb_* paint materials used by master roof components; market_stall feature=market_canopy selected by verified material plus native operation box. Audit component IDs, operation IDs/features, and metadata, excluding vegetation crowns and canopy posts. No named roof found is not proof that all cover geometry is classified.',
    }


def roof_rectangles(render, selected_materials, operation_selectors=()):
    pitch, origin = render['pitch'], render.get('grid_origin', [0, 0, 0])
    cells, horizontal, vertical = set(), 0, 0
    for group in render['groups']:
        selectors = [s for s in operation_selectors if s['material'] == group['material']]
        if group['material'] not in selected_materials and not selectors:
            continue
        for q in group['quads']:
            if group['material'] not in selected_materials and not any(
                all(s['source_box_min_m'][k]-EPS <= v[k] <= s['source_box_max_m'][k]+EPS
                    for v in q for k in range(3)) for s in selectors):
                continue
            if max(v[1] for v in q)-min(v[1] for v in q) > EPS:
                # Existing common meshes are orthogonal voxel surfaces.
                assert any(max(v[k] for v in q)-min(v[k] for v in q) < EPS for k in (0, 2))
                vertical += 1
                continue
            horizontal += 1
            bounds = []
            for k in (0, 2):
                lo, hi = min(v[k] for v in q), max(v[k] for v in q)
                il, ih = round((lo-origin[k])/pitch), round((hi-origin[k])/pitch)
                assert abs(origin[k]+il*pitch-lo) < EPS and abs(origin[k]+ih*pitch-hi) < EPS
                bounds.append((il, ih))
            cells.update((x, z) for x in range(*bounds[0]) for z in range(*bounds[1]))
    return cells_to_rectangles(cells, pitch, origin), {
        'horizontal_quads': horizontal, 'vertical_zero_plan_area_quads': vertical,
        'union_native_xz_cells': len(cells), 'native_lattice_pitch_m': pitch,
        'native_grid_origin_m': origin,
    }


def primary_floor(asset, master):
    for where, metadata in [('asset.author_metadata', asset.get('author_metadata', {})),
                            ('asset.native_metadata', asset.get('native_metadata', {})),
                            ('master.metadata', master.get('metadata', {}))]:
        if 'floor_local_y_m' in metadata:
            return float(metadata['floor_local_y_m']), where+'.floor_local_y_m'
        if metadata.get('entrance', {}).get('position'):
            return float(metadata['entrance']['position'][1]), where+'.entrance.position[1]'
    return None, None


def compiled_candidates(asset, root=ROOT):
    render = root / asset['render_path']
    possible = []
    if asset.get('compiled_path'):
        possible.append(root / asset['compiled_path'])
    if render.name.endswith('.render.json'):
        possible.append(render.with_name(render.name.replace('.render.json', '.compiled.json')))
    if render.parent.name == 'renders':
        possible.append(render.parent.parent / 'cache' / render.name)
    return list(dict.fromkeys(possible))


def occupied_body_projection(asset, master, render, source_packs, root=ROOT):
    """Same finite height-band solid-occupancy metric for cells and mesh fallback."""
    if not BODY_PACKS.intersection(source_packs):
        return None, {'status': 'not_in_ordinary_body_scope', 'reason': 'Compound court, landmark, furniture, infrastructure, and landscape body semantics are not inferred.'}
    floor, floor_source = primary_floor(asset, master)
    if floor is None:
        return None, {'status': 'missing_primary_floor_metadata', 'reason': 'No metadata-body-bounds or other envelope substitute is used.'}
    low, high = floor+.8, floor+1.8
    proof = {'primary_floor_local_y_m': floor, 'primary_floor_source': floor_source,
             'open_slab_local_y_m': [low, high], 'rejected_cell_sources': []}
    for path in compiled_candidates(asset, root):
        if not path.exists():
            proof['rejected_cell_sources'].append({'path': str(path.relative_to(root)), 'reason': 'absent'})
            continue
        compiled = json.loads(path.read_text())
        if 'cells' not in compiled or 'instances' not in compiled:
            proof['rejected_cell_sources'].append({'source': ref(path, root), 'reason': 'manifest_only_no_cell_payload'})
            continue
        if asset.get('compiled_path') and path == root/asset['compiled_path'] and asset.get('compiled_sha256'):
            assert sha(path) == asset['compiled_sha256']
        assert compiled['valid']
        assert digest(compiled['cells']) == compiled['payload_hash'] == render['payload_hash']
        for key in ('source_id', 'master_hash', 'pitch', 'grid_origin'):
            assert compiled[key] == render[key], (path, key)
        pitch, origin = compiled['pitch'], compiled['grid_origin']
        imap = {i['id']: i['component'] for i in compiled['instances']}
        selected = [r for r in compiled['cells'] if origin[1]+(r[1]+1)*pitch > low+EPS and origin[1]+r[1]*pitch < high-EPS]
        occupied = {(r[0], r[2]) for r in selected}
        # Height-band occupancy is deliberately NOT component-envelope filling.
        components = Counter(imap[r[3]] for r in selected)
        roof_cells = sum(n for cid, n in components.items() if 'roof' in cid.lower())
        assert not roof_cells, ('roof enters ordinary body band', path, roof_cells)
        polygons = cells_to_rectangles(occupied, pitch, origin)
        proof.update(status='verified_native_occupied_structure', method='actual_compiled_cells_in_open_height_band',
                     compiled=ref(path, root), compiled_payload_hash=compiled['payload_hash'],
                     selected_3d_cells=len(selected), selected_native_xz_cells=len(occupied),
                     selected_component_cell_counts=dict(sorted(components.items())),
                     roof_cells_in_band=roof_cells)
        return polygons, proof
    # Closed oriented native mesh crossings recover exactly the same solid volume.
    try:
        polygons = slab_rectangles(render, low, high)
    except (ValueError, AssertionError) as exc:
        proof.update(status='unclassifiable_native_body', reason=str(exc))
        return None, proof
    proof.update(status='verified_native_occupied_structure', method='actual_oriented_native_mesh_slab_crossings',
                 cell_payload_available=False,
                 helper='world_city/concept_city_v3/validation/check_landmark_access_candidate.py::slab_rectangles')
    return polygons, proof


def extract_asset(asset_key, asset, source_packs=(), root=ROOT):
    root = Path(root).resolve()
    master_path, render_path = root/asset['master_path'], root/asset['render_path']
    assert sha(master_path) == asset['master_sha256'], (asset_key, 'master hash mismatch')
    assert sha(render_path) == asset['render_sha256'], (asset_key, 'render hash mismatch')
    master, render = json.loads(master_path.read_text()), json.loads(render_path.read_text())
    selected, classification = classify_roof_materials(master, render, source_packs)
    roofs, roof_proof = roof_rectangles(render, selected, classification['operation_geometry_selectors'])
    bodies, body_proof = occupied_body_projection(asset, master, render, set(source_packs), root)
    return {
        'asset_key': asset_key, 'source_packs': sorted(source_packs),
        'master': ref(master_path, root), 'render': ref(render_path, root),
        'render_payload_hash': render['payload_hash'], 'render_quad_count': render['quad_count'],
        'roof_rectangles_local_xz_m': roofs,
        'roof_projection_area_m2': area(roofs),
        'roof_proof': {**classification, **roof_proof},
        'body_rectangles_local_xz_m': bodies,
        'body_occupied_structure_area_m2': None if bodies is None else area(bodies),
        'body_proof': body_proof,
    }


def build(input_path=DEFAULT_INPUT, root=ROOT):
    root, input_path = Path(root).resolve(), Path(input_path).resolve()
    snapshot = json.loads(input_path.read_text())
    by_asset = defaultdict(set)
    for inst in snapshot['common_instances']:
        assert inst.get('scale', [1,1,1]) == [1,1,1]
        by_asset[inst['asset_key']].add(inst['source_pack'])
    assets = {key: extract_asset(key, asset, by_asset[key], root)
              for key, asset in sorted(snapshot['common_assets'].items())}
    return {
        'schema': 'riverstone.r5_native_asset_plan_projection.v2',
        'input': ref(input_path, root), 'extractor': ref(Path(__file__), root),
        'status': 'native_asset_projections_only_not_whole_city_area_or_scene_certification',
        'definitions': {
            'roof': 'Disjoint local XZ union of actual cached horizontal roof/canopy exterior quads, including downward faces; semantic materials and verified market-canopy operation-geometry selectors are used. Vertical faces have zero plan area.',
            'roof_classification_scope': 'Cover candidates are audited through component IDs, operation IDs/features and source metadata. no_roof_identified is not a universal absence proof; unresolved cover operations are explicit and omitted from quantified roof area.',
            'body': 'Disjoint projection of actual native solid occupancy anywhere in open primary-floor +0.8 to +1.8 m band. Hollow interiors are not filled; not enclosed building floor area or habitation area.',
            'body_scope': sorted(BODY_PACKS),
            'missing': 'Null body polygons/area mean missing or outside scope; never interpret null as zero.',
            'placement': 'x = px + cos(yaw)*x_local + sin(yaw)*z_local; z = pz - sin(yaw)*x_local + cos(yaw)*z_local. Native scale only.',
        },
        'summary': {
            'assets': len(assets), 'instances': len(snapshot['common_instances']),
            'roof_bearing_assets': sum(bool(a['roof_rectangles_local_xz_m']) for a in assets.values()),
            'market_canopy_instances': sum(bool(assets[i['asset_key']]['roof_proof']['operation_geometry_selectors']) for i in snapshot['common_instances']),
            'unresolved_cover_assets': [key for key, a in assets.items() if a['roof_proof']['unresolved_cover_operations']],
            'roof_classification_status_counts': dict(Counter(a['roof_proof']['classification_status'] for a in assets.values())),
            'body_status_counts': dict(Counter(a['body_proof']['status'] for a in assets.values())),
            'body_method_counts': dict(Counter(a['body_proof'].get('method','none') for a in assets.values())),
        },
        'assets': assets,
        'limits': [
            'Projection uses frozen sampled native geometry, not concept-image segmentation, visible-surface occlusion, source continuous envelopes, or AABBs.',
            'R5 is a draft candidate. This extraction does not bind terrain or certify walking, floors, interior enclosure, households, structural engineering, or visual completion.',
            'Roof/canopy area and occupied wall/structural-body area are different metrics and should not be compared to the same target.',
            'Compound court slabs are never treated as ordinary building bodies. Non-ordinary body scope is explicitly incomplete.',
            'Do not render or separately add provenance component placements on top of candidate common_instances.',
            'Unresolved nonsemantic cover geometry is not counted; see per-asset unresolved_cover_operations. Vegetation crowns are explicitly excluded from architectural roof coverage.',
        ],
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output', type=Path, default=HERE/'asset_projection_proofs.json')
    args = parser.parse_args()
    result = build(args.input)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps(result['summary'], indent=2))
