"""One parent-approved facility at a paused house-queue boundary."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import adapter as a
import layered_compile as layer
import compile_batch as batch
import compile_house_queue as queue


def run(key,catalog,output):
    catalog=Path(catalog).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    if not (layer.HERE/'.compile_pause').exists():raise ValueError('House queue must be paused at an asset boundary')
    budget=50_000_000
    used=lambda:sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    if used()>=budget-2_000_000:raise ValueError('Additional facility budget margin exhausted')
    entry=next(r for r in a.load(catalog)['assets'] if r['asset_key']==key)
    existing=batch.inspect_output(key,output)
    if not existing:layer.run(key,output,catalog_path=catalog,render_only=True)
    # The complete output already exists, so this call only performs QA and manifest updates.
    if batch.run([key],catalog,output,render_only=True):raise ValueError('Facility structural QA failed')
    stats_path=output/(key+'.layered.stats.json');replay=output/(key+'.layered.replay.json')
    logs=layer.HERE/'compile_logs/facility_expansion';logs.mkdir(exist_ok=True)
    queue.checked_report([sys.executable,str(layer.HERE/'replay_certificate_qa.py'),'--stats',str(stats_path),'--output',str(replay)],logs/(key+'.replay.log'),replay)
    stats=a.load(stats_path);master=layer.load_master(a.ROOT/entry['emitted_master_path'])
    source=layer.SpatialSource(master,.05,range_only=True)
    plan=layer.chunk_enumeration.enumerate_paint_chunks(source,master.get('grid_origin',[0,0,0]),stats['compiled_header']['chunk_edge_fine_cells'],a.core.EPS)
    expected={tuple(v//stats['compiled_header']['chunk_edge_fine_cells'] for v in low) for low in plan['owned_lows']}
    actual=[tuple(r['chunk']) for r in stats['chunks']]
    checks={'all_source_domain_chunks_compiled':len(actual)==len(expected) and set(actual)==expected,
            'original_native_bounds':stats['spatial_sampling_contract']=='original_shapes_integer_cell_bounds_v1',
            'all_chunk_exterior_face_match':stats['all_chunks_exact_exterior_face_match'],
            'all_chunk_overlap_free':stats['all_chunks_overlap_free'],
            'all_global_constraints_pass':all(r['pass'] for r in stats['constraints']),
            'materials_preserved':master['materials']==a.load(a.ROOT/entry['source_master_path'])['materials'],
            'independent_replay_pass':a.load(replay)['pass']}
    if not all(checks.values()):raise ValueError('Facility full domain verification failed: '+str(checks))
    record={**entry,**batch.inspect_output(key,output),'complete_authored_source_domain_coverage':True,
            'compile_checks':checks,'source_bounds_analytic':{'min':source.bounds[0],'max':source.bounds[1]},
            'global_constraints':stats['constraints'],'baseline_structure_unchanged':True,'runtime_activation':False,
            'replacement_group_and_original_cut_qa':'Requires source authoring handoff contract; full authored domain compile does not replace that separate check.'}
    path=output/'handoff_manifest.json';manifest=a.load(path) if path.exists() else {'schema':'riverstone.facility_roof.compiled_expansion.v1','assets':[]}
    manifest['assets']=[r for r in manifest['assets'] if r['asset_key']!=key]+[record]
    manifest.update(updated_utc=batch.now(),additional_output_budget_bytes=budget,retained_voxel_payload=False,single_heavy_compiler=True)
    if used()+len(json.dumps(manifest).encode())+65536>budget:raise ValueError('Additional facility output budget exceeded')
    batch.atomic_json(path,manifest);print(json.dumps({'facility_complete':key,'stats_path':str(stats_path.relative_to(a.ROOT)),
        'quads':stats['quads'],'cells':stats['reference_full_fine_cells'],'elapsed_seconds':stats['elapsed_seconds'],
        'max_rss_kib':stats['max_rss_kib'],'files':stats['files'],'manifest':str(path.relative_to(a.ROOT))}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('key');p.add_argument('--catalog',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    args=p.parse_args();run(args.key,args.catalog,args.output_dir)
