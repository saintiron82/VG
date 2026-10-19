"""Run bounded sample tests and verify emitted artifact hashes."""
import datetime
import io
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import adapter as a
import test_adapter as tests

suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
checks=[]
catalog_path=HERE/'generated/active_catalog.json'
if catalog_path.exists():
    catalog=a.load(catalog_path)
    checks.append({'check':'catalog_engine_sha256','pass':catalog['engine_sha256']==a.sha(a.__file__)})
    checks.append({'check':'active_city_index_unchanged','pass':catalog['index_sha256']==a.sha(a.ROOT/catalog['index_path'])})
    for record in catalog['assets']:
        checks.append({'check':'source_unchanged','asset':record['asset_key'],'pass':record['source_sha256']==a.sha(a.ROOT/record['source_master_path'])})
        if record.get('emitted_master_path'):
            path=a.ROOT/record['emitted_master_path']
            checks.append({'check':'emitted_master_sha256','asset':record['asset_key'],'pass':record['emitted_master_sha256']==a.sha(path)})
            master=a.load(path)
            checks.append({'check':'emitted_master_engine_sha256','asset':record['asset_key'],'pass':master['provenance']['city_near_material']['engine_sha256']==a.sha(a.__file__)})
report={'schema':'riverstone.house_detail.tests.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'test_count':result.testsRun,'tests_passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),
        'tests_source_sha256':a.sha(tests.__file__),'engine_sha256':a.sha(a.__file__),
        'compiler_source_sha256':a.sha(a.core.__file__),'rules_sha256':a.sha(HERE/'rules.r04.v1.json'),
        'selectors_sha256':a.sha(HERE/'selectors.ordinary_r2.v1.json'),
        'bounded_probe_compiles':tests.PROBE_AUDIT,
        'max_probe_candidate_cells':max((p['candidate_cells'] for p in tests.PROBE_AUDIT),default=0),
        'full_house_compiles':0,'artifact_integrity_checks':checks,
        'pass':result.wasSuccessful() and all(c['pass'] for c in checks)}
a.write(HERE/'generated/tests.report.json',report)
(HERE/'generated/tests.log').write_text(stream.getvalue())
print(stream.getvalue())
print('Artifact integrity:',report['pass'],'| Bounded probes:',len(tests.PROBE_AUDIT),'| Max candidate cells:',report['max_probe_candidate_cells'])
raise SystemExit(0 if report['pass'] else 1)
