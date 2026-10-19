"""Apply only after the current compiler exits; source hashes are immutable in-run."""
from pathlib import Path
p=Path(__file__).with_name('layered_compile.py');s=p.read_text()
if 'def commit_progress(' not in s:
    at=s.index('\ndef run(asset_key,')
    s=s[:at]+'''\ndef commit_progress(path,value):
    temporary=path.with_name(path.name+'.tmp')
    a.write(temporary,value);os.replace(temporary,path)

'''+s[at:]
    s=s.replace("    a.fail(not any(p.exists() for p in list(paths.values())+list(partial.values())),'layer_existing_outputs_preserved')", "    progress_path=output/(asset_key+'.layered.progress.json')\n    protected=list(paths.values())+list(partial.values())+[progress_path,output/(asset_key+'.layered.blocked.json')]\n    a.fail(not any(p.exists() for p in protected),'layer_existing_outputs_preserved')")
    needle="                if number%10==0 or number+1==chunk_count:\n                    print(json.dumps({'phase':'layer_chunk','asset_key':asset_key,'completed':number+1,'chunks':chunk_count,'stored_fine':total_fine,'stored_core':total_core,'seconds':time.perf_counter()-start}),flush=True)"
    replacement="""                progress={'schema':'riverstone.house_detail.chunk_progress.v1','status':'RUNNING','phase':'layer_chunk','asset_key':asset_key,
                    'completed':number+1,'chunks':chunk_count,'dense_bbox_chunks':chunk_plan['dense_bbox_chunks'],
                    'proven_empty_chunks_skipped':chunk_plan['proven_empty_chunks_skipped'],'current_chunk':row['chunk'],
                    'current_chunk_quads':len(quads),'current_chunk_fingerprint':fp.value(),'stored_fine':total_fine,'stored_core':total_core,
                    'fine_equivalent_cells':all_fp.count,'quads':sum(len(g) for g in groups.values()),'visible_unit_faces':face_fp.count,
                    'seconds':time.perf_counter()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'memory_limit_bytes':rules['memory_limit_bytes'],'wall_time_limit_seconds':wall_limit,
                    'authored_master_sha256':header['authored_master_sha256'],'compiler_source_sha256':header['compiler_source_sha256'],'layer_engine_sha256':header['layer_engine_sha256']}
                commit_progress(progress_path,progress)
                if number%10==0 or number+1==chunk_count:print(json.dumps(progress),flush=True)"""
    assert needle in s;s=s.replace(needle,replacement)
    s=s.replace('        checks=[]\n',"        a.fail(all_fp.count>0,'layer_no_visible_occupancy')\n        checks=[]\n")
    s=s.replace("        os.replace(partial['.stats.json'],paths['.stats.json'])", "        actual_stored_bytes=sum(p.stat().st_size for root in budget_roots for p in root.rglob('*') if p.is_file())+sum(p.stat().st_size for p in (HERE/'replay_code').rglob('*') if p.is_file())\n        a.fail(actual_stored_bytes+2048<=rules['total_output_budget_bytes'],'layer_final_artifact_budget_exceeded',{'bytes':actual_stored_bytes,'limit':rules['total_output_budget_bytes']})\n        os.replace(partial['.stats.json'],paths['.stats.json'])\n        progress.update(status='COMPLETE',stats_path=str(paths['.stats.json'].relative_to(a.ROOT)),stats_sha256=a.sha(paths['.stats.json']))\n        commit_progress(progress_path,progress)")
    s=s.replace("'partial_files':[str(p.relative_to(a.ROOT)) for p in partial.values() if p.exists()]", "'partial_files':[str(p.relative_to(a.ROOT)) for p in partial.values() if p.exists()],'progress_path':str(progress_path.relative_to(a.ROOT)) if progress_path.exists() else None")
    p.write_text(s)
