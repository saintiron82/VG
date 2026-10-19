"""Create new tiny synthetic examples; refuses overwriting an existing catalog."""
from __future__ import annotations
import copy
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE/'tests'))
from fixture_factory import build, write_json, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replace-synthetic-fixtures',action='store_true',help='Replace only this new test fixture, never existing production assets')
    args=parser.parse_args()
    output=HERE/'examples/synthetic_evidence'
    if output.exists() and not args.replace_synthetic_fixtures:raise SystemExit('Synthetic evidence already exists; preserve it or explicitly replace this test-only fixture.')
    c=build(output)
    for a in c['artifacts'].values():a['path']=str((output/a['path']).relative_to(REPO))
    write_json(HERE/'examples/technical_fixture_NOT_character_approval.json',c)
    cases=[]
    missing=copy.deepcopy(c)
    missing['model_renders']=[r for r in missing['model_renders'] if not(r['stage']=='compiled_mesh' and r['view']=='back')]
    cases.append(('fail_missing_compiled_back.json',missing,'render_views'))
    observed=copy.deepcopy(c);observed['references'][1]['origin']='observed'
    cases.append(('fail_inferred_side_as_observed.json',observed,'artifact_kind'))
    coverage=copy.deepcopy(c);coverage['claims']['coverage_pass']=True
    cases.append(('fail_numeric_coverage_claim.json',coverage,'automatic_quality_claim'))
    flat=copy.deepcopy(c)
    profile=json.loads((output/'profile.json').read_text())
    profile['parts'][0]['sections'][1]['depth_m']=0
    badpath=output/'invalid_zero_depth_profile.json';write_json(badpath,profile)
    flat['artifacts']['profile'].update(path=str(badpath.relative_to(REPO)),sha256=sha(badpath))
    cases.append(('fail_zero_volume_depth.json',flat,'section_volume'))
    checks=[]
    spec=importlib.util.spec_from_file_location('contract',REPO/'voxel_character/common/validation/multiview_contract.py')
    validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
    result=validator.validate_contract(c,REPO)
    assert result['technical_contract_pass'],result
    checks.append({'input':'technical_fixture_NOT_character_approval.json','technical_contract_pass':True,
                   'automatic_art_acceptance':False,'asset_complete':False})
    for name,value,code in cases:
        write_json(HERE/'examples'/name,value)
        result=validator.validate_contract(value,REPO)
        assert not result['technical_contract_pass'] and code in [e['code'] for e in result['errors']],result
        checks.append({'input':name,'technical_contract_pass':False,'expected_failure':code,
                       'observed_errors':result['errors'],'automatic_art_acceptance':False,'asset_complete':False})
    write_json(HERE/'examples/example_checks.json',{'fixture_scope':'Synthetic 64-cell box; no character quality or human approval claimed.',
               'checks':checks,'compiler_snapshot_sha256':c['artifacts']['compiler']['sha256']})
    print(json.dumps({'examples':len(checks),'expected_failures':len(cases),'synthetic_technical_only':True}))

if __name__=='__main__':main()
