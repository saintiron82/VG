"""Local final24 retaining closure against accepted neighboring physical planes."""
import json,time
from pathlib import Path
from .prepare import HERE, ref, load, write
from .. import author as a
from .....registered_integration.r8 import finite_boundary_index
from .....registered_integration.r8.author_joint_boundaries import boundary_strip
from ...public_corridors_r18.height_field import fixed_sources

def run():
    start = time.monotonic()
    hand = json.loads((HERE/'physical_owner_handoff_r02.json').read_bytes())
    bindings = json.loads((HERE/'side_context_binding.json').read_bytes())
    context = load(bindings['current_scene'])
    public = load(bindings['public_field'])
    native = load(bindings['native_boundary_owners'])
    logical = hand['physical_earth_owners']
    outside = []
    # Finite newer public repairs have precedence over their superseded pieces.
    for binding in bindings.get('public_local_corrections', []):
        record = load(binding)
        outside.extend(record.get('records', record.get('owners', [])))
    outside.extend(public['records'])
    for binding in bindings['accepted_private_handoffs']:
        outside.extend(load(binding)['physical_earth_owners'])
    outside.extend(native['all_noble_physical_owners'])
    outside.extend(native['accepted_adjacent_physical_owners'])
    outside.extend(hand['public_fixed_regions'])
    fixed, segments, source_refs = fixed_sources()
    outside.extend(fixed)
    outside.extend(s for r in segments if (s := boundary_strip(r)))
    windows = [r['polygon_xz_m'] for r in logical]
    # The original scene supplies the exact side indices; current context only
    # supplies otherwise unchanged adjacent tops. No whole-city solve occurs.
    scene = a.load_scene()
    index = a.TriangleIndex(context, windows)
    result = finite_boundary_index.interfaces(scene, index, logical, outside)
    patch = dict(schema='riverstone.frozen_scene_patch.v1', id='R17_FINAL24_LOCAL_BOUNDARY_CLOSURE',
        base_scene_sha256=a.SCENE_SHA256,
        source_surface_hashes={m:a.canonical_sha(scene['surfaces'][m])
                              for m in sorted({r['material'] for r in result['side_surface_edits']})},
        surface_edits=result['side_surface_edits'],
        appended_surfaces={'bank':[v for t in result['appended_retaining_triangles_xyz_m'] for v in t]},
        removed_foundation_proxy_ids=[], source_references=[ref(HERE/'physical_owner_handoff_r02.json'),
        ref(HERE/'side_context_binding.json'),ref(Path(__file__)),ref(Path(finite_boundary_index.__file__))]+source_refs)
    review = dict(status='PASS_LOCAL_FINITE_BOUNDARY' if not result['unknown_exterior_segments'] else 'HELD_UNKNOWN_LOCAL_BOUNDARY',
        accepted_holding_ids=hand['accepted_holding_ids'],
        source_side_edits=len(result['side_surface_edits']),
        new_retaining_triangles=len(result['appended_retaining_triangles_xyz_m']),
        unknown_exterior_segments=result['unknown_exterior_segments'], boundary_seams=result['boundary_seams'],
        retired_sides=result['retired_sides'], indexed_execution=result['indexed_execution'],
        explicit_profile_riser_ledger=hand['explicit_profile_risers'],
        scope='Only the 24 new private physical owners retire source sides. Existing61 and public owners are query-only neighbors.',
        elapsed_s=time.monotonic()-start, activation=False)
    write('side_scene_patch_r01.json',patch)
    write('local_boundary_review_r01.json',review)
    print(review['status'],review['source_side_edits'],len(review['unknown_exterior_segments']),flush=True)

if __name__ == '__main__':
    run()
