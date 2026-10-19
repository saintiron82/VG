"""Two approved roof assets, exact native sampling, at most two timed executions.

The existing immutable facility finalizer is invoked only after successful full
sampling. Importing the engine bypasses only its house CLI pause, never its
exclusive common compiler lock, source validation, or checkpoint budget checks.
"""
import argparse
import json
from pathlib import Path
import sys
import adapter as a
import layered_compile as layer
import compile_batch as batch
import checkpoint_queue
import compile_facility_once as finalizer

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
    budget=actual_rules.pop('total_output_budget_bytes',None);guard=actual_rules.pop('facility_budget_guard',None)
    baseline_limit=baseline_rules.pop('total_output_budget_bytes')
    if actual_rules!=baseline_rules or not guard or not 0<budget<=baseline_limit:
        raise ValueError('Facility rules may only tighten the output budget')
    if guard.get('facility_output_cap_bytes')!=20_000_000 or guard.get('baseline_retained_bytes',-1)+20_000_000<budget:
        raise ValueError('Invalid shared facility output reservation')
    retained=lambda root:sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    fixed_roots=[layer.HERE/'compiled',layer.HERE/'replay_code',layer.HERE.parent/'facility_roofs/compiled_priority_r01']
    if sum(retained(root) for root in fixed_roots)<guard['baseline_retained_bytes']:
        raise ValueError('Pinned retained budget baseline shrank; explicit budget review required')
    if retained(expected)>=20_000_000:raise ValueError('Facility roof reservation exhausted')
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
    existing=batch.inspect_output(key,output)
    if existing and not existing['status'].startswith('PASS'):raise ValueError('Held facility output requires explicit review')
    if not existing:
        command=[sys.executable,str(Path(__file__).resolve()),key,'--catalog',str(catalog),'--output-dir',str(output),
                 '--checkpoint-policy',str(policy),'--rules',str(rules),'--worker']
        result=checkpoint_queue.execute(command,output,key,layer.HERE/'compile_logs/facility_expansion')
        if result['state']!='COMPILE_COMPLETE':
            print(json.dumps({'facility_pending':key,**result}),flush=True)
            return 2
    finalizer.run(key,catalog,output)
    return 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('key');p.add_argument('--catalog',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--checkpoint-policy',type=Path,required=True)
    p.add_argument('--rules',type=Path,required=True);p.add_argument('--worker',action='store_true');p.add_argument('--resume-checkpoint',action='store_true')
    x=p.parse_args();raise SystemExit(run(x.key,x.catalog,x.output_dir,x.checkpoint_policy,x.worker,x.resume_checkpoint,x.rules))
