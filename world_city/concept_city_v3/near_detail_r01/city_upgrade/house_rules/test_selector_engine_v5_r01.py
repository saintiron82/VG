"""Separate v5 selector-cache candidate: exact original-core and resume fixtures.
No production job uses this candidate. The normal primary queue/compile leases apply.
"""
import argparse, ast, contextlib, fcntl, io, json, resource, time, unittest
from pathlib import Path
import test_frontier_engine_integration_r01 as fixture
import layered_compile_frontier_v4_r01 as original
import layered_compile_selector_v5_r01 as candidate
import semantic_selector_cache_v1 as cache

a=fixture.a;HERE=Path(__file__).resolve().parent
class Static(unittest.TestCase):
    def test_no_sampling_mesh_or_fingerprint_helper_change(self):
        def functions(module):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(module.__file__).read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        old,new=functions(original),functions(candidate)
        self.assertEqual(set(old),set(new))
        for key in old:
            if key not in ('run','verified_sampler_provenance'):self.assertEqual(old[key],new[key],key)
        self.assertEqual(a.sha(cache.__file__),candidate.EXPECTED_SELECTOR_SHA256)
    def test_no_change_to_frozen_production(self):
        for path,digest in fixture.FROZEN.items():self.assertEqual(a.sha(path),digest,str(path))

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-engine-fixtures',action='store_true');p.add_argument('--proof',type=Path,required=True);x=p.parse_args()
    if x.proof.exists():raise ValueError('Preserve prior evidence')
    resource.setrlimit(resource.RLIMIT_AS,(fixture.MEMORY_LIMIT,fixture.MEMORY_LIMIT))
    fixture.native=candidate;fixture.RUN_ENGINES=x.run_engine_fixtures
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Static)
    if x.run_engine_fixtures:
        for name in ('test_native_soft_stop_projection_resume_exact','test_incomplete_global_coverage_never_publishes_pass','test_missing_nonempty_constraint_never_publishes_pass'):
            suite.addTest(fixture.RealEngineIntegration(name))
    begin=time.perf_counter()
    with (HERE/'queue.lock').open('a') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with contextlib.redirect_stdout(io.StringIO()):result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'schema':'riverstone.selector_cache_engine_candidate_tests.v1','pass':result.wasSuccessful(),'tests':result.testsRun,'failures':[str(e[1]) for e in result.failures+result.errors],'actual_engine_fixtures_run':x.run_engine_fixtures,'elapsed_seconds':time.perf_counter()-begin,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_engine_sha256':a.sha(original.__file__),'candidate_engine_sha256':a.sha(candidate.__file__),'selector_helper_sha256':a.sha(cache.__file__),'test_sha256':a.sha(__file__),'evidence':fixture.EVIDENCE,'production_jobs_changed':False}
    a.write(x.proof,report);print(json.dumps({k:v for k,v in report.items() if k!='evidence'}));return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
