"""Two approved roof assets, exact native sampling, at most two timed executions.

The existing immutable facility finalizer is invoked only after successful full
sampling. Importing the engine bypasses only its house CLI pause, never its
exclusive common compiler lock, source validation, or checkpoint budget checks.
"""
import argparse
import json
from pathlib import Path
import sys
import fcntl
import adapter as a
import layered_compile_v2_r02 as layer
import compile_batch as batch
import checkpoint_queue
import finalize_facility_v2 as finalizer

ALLOWED={'registered_cathedral_north_cloister_range','registered_castle_front_gate_wing'}


def validate(key,catalog,output,policy,rules=None):
    if key not in ALLOWED:raise ValueError('Facility is outside the approved two-asset execution scope')
    if not (layer.HERE/'.compile_pause').exists():raise ValueError('House queue must be held at an asset boundary')
    recipe=a.load(policy)
    if (set(recipe.get('enabled_asset_keys',[]))!=ALLOWED or recipe.get('max_sessions')!=2 or
        recipe.get('per_session_wall_seconds')!=900 or recipe.get('soft_stop_seconds')!=840):
        raise ValueError('Facility checkpoint policy must retain the approved limits')
    if recipe.get('input_catalog_sha256')!=a.sha(catalog):raise ValueError('Frozen facility catalog changed')
    entry=next(r for r in a.load(catalog)['assets'] if r['asset_key']==key)
    pinned=recipe['approved_inputs'][key]
    if any(entry.get(k)!=pinned[k] for k in ('source_sha256','emitted_master_sha256')):
        raise ValueError('Facility source/master hash differs from approved input')
    if any(a.sha(a.ROOT/entry[p])!=entry[k] for p,k in [('source_master_path','source_sha256'),('emitted_master_path','emitted_master_sha256')]):
        raise ValueError('Facility original/authored input bytes changed')
    expected=(layer.HERE.parent/'facility_roofs/compiled_expansion_r01').resolve()
    if Path(output).resolve()!=expected:raise ValueError('Unexpected facility output scope')
    if rules is None:raise ValueError('An immutable budget-only facility rules file is required')
    actual_rules=a.load(rules);baseline_rules=a.load(layer.HERE/'layer_rules.v1.json')
    for field,value in baseline_rules.items():
        if field not in ('memory_limit_bytes','total_output_budget_bytes') and actual_rules.get(field)!=value:
            raise ValueError('Facility v2 rules cannot alter source geometry or sampling limits: '+field)
    if actual_rules['memory_limit_bytes']!=738197504 or actual_rules['total_output_budget_bytes']!=350_000_000:
        raise ValueError('Unexpected approved facility memory/shared cap')
    shared=actual_rules['shared_output_reservation'];published=a.load(layer.HERE/'shared_output_budget.v2.json')
    if any(shared.get(k)!=published[k] for k in ('book_path','retained_roots','limit_bytes','min_free_disk_bytes')) or shared['asset_cap_bytes']!=8_000_000:
        raise ValueError('Facility must use the shared350MB/1GiB guard and its8MB asset cap')
    retained=lambda root:sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if retained(expected)>=20_000_000:raise ValueError('Facility roof20MB allocation exhausted')
    return entry


def run(key,catalog,output,policy,worker=False,resume=False,rules=None):
    catalog=Path(catalog).resolve();output=Path(output).resolve();policy=Path(policy).resolve()
    rules=Path(rules).resolve() if rules else None
    validate(key,catalog,output,policy,rules)
    if worker:
        result=layer.run(key,output,catalog_path=catalog,render_only=True,
                         checkpoint_policy_path=policy,resume_checkpoint=resume,rules_path=rules)
        return {'PENDING_RESUMABLE_CHECKPOINT':75,'PENDING_CHECKPOINT_SESSION_LIMIT':76}.get(result.get('status'),0)
    if resume:raise ValueError('Manager derives resume exclusively from the committed ledger')
    output.mkdir(parents=True,exist_ok=True)
    controller=(layer.HERE/'queue.lock').open('a')
    try:fcntl.flock(controller,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:controller.close();raise ValueError('House controller owns the full-asset boundary')
    existing=batch.inspect_output(key,output)
    if existing and not existing['status'].startswith('PASS'):raise ValueError('Held facility output requires explicit review')
    if not existing:
        command=[sys.executable,str(Path(__file__).resolve()),key,'--catalog',str(catalog),'--output-dir',str(output),
                 '--checkpoint-policy',str(policy),'--rules',str(rules),'--worker']
        result=checkpoint_queue.execute(command,output,key,layer.HERE/'compile_logs/facility_v2_expansion')
        if result['state']!='COMPILE_COMPLETE':
            print(json.dumps({'facility_pending':key,**result}),flush=True)
            return 2
    finalizer.run(key,catalog,output)
    fcntl.flock(controller,fcntl.LOCK_UN);controller.close()
    return 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('key');p.add_argument('--catalog',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--checkpoint-policy',type=Path,required=True)
    p.add_argument('--rules',type=Path,required=True);p.add_argument('--worker',action='store_true');p.add_argument('--resume-checkpoint',action='store_true')
    x=p.parse_args();raise SystemExit(run(x.key,x.catalog,x.output_dir,x.checkpoint_policy,x.worker,x.resume_checkpoint,x.rules))
