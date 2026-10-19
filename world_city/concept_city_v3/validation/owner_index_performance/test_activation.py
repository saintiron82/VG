"""Bounded process-local activation controls. No source/module-file writes."""
import sys,pathlib,json,hashlib
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import upstream as source
from world_city.concept_city_v3.validation.owner_index_performance.activate_r5 import activate
checks=[];original=source.owner_at
for args in [dict(),dict(opt_in=True),dict(opt_in=True,export_revision='r4'),dict(opt_in=1,export_revision='r5')]:
 try:activate(source,**args)
 except ValueError:checks.append('rejected missing/wrong opt-in '+repr(args))
 else:raise AssertionError('accepted bad opt-in')
 assert source.owner_at is original
points=json.loads((H/'fixtures.json').read_text())['benchmark_points'][::20]
expected=[source.owner_at.__wrapped__(*p) for p in points]
with activate(source,opt_in=True,export_revision='r5') as active:
 assert source.owner_at is active.lookup.owner_at
 checks.append('installed only approved callable')
 assert [source.owner_at(*p) for p in points]==expected
 checks.append('1000 explicitly activated results equal original')
 try:activate(source,opt_in=True,export_revision='r5')
 except ValueError:checks.append('nested activation rejected')
 else:raise AssertionError('accepted nested activation')
assert source.owner_at is original and active.report['status']=='restored'
checks.append('exact original restored on normal context exit')
active.restore();checks.append('repeat restoration is harmless')
try:
 with activate(source,opt_in=True,export_revision='r5') as failure_context:raise LookupError('deliberate export failure')
except LookupError:checks.append('original export exception preserved')
assert source.owner_at is original and failure_context.report['status']=='restored';checks.append('exact original restored after exception')
report=dict(status='pass',checks=checks,normal_activation=active.report,exception_activation=failure_context.report,checker_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),limits=['Activation test process only; no accepted scene or current r4 exporter was modified.','R14 finite-layer parity remains pending its sealed source.'])
(H/'activation_test_report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(checks))
