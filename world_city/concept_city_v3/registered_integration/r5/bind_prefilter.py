"""Bind explicit r5 acceleration only after exact effective-layer parity."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PROOFS=ROOT/'world_city/concept_city_v3/validation/owner_index_performance'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    paths=[PROOFS/('r14_final_'+m+'.json') for m in ('original','both')]
    a,b=[json.loads(p.read_bytes()) for p in paths]
    assert a['status']==b['status']=='pass_run_complete'
    for key in ('target_module','target_contract_sha256','case_count','cases',
                'total_owner_queries','supplemental_corner_side_count','supplemental_corner_digest'):
        assert a[key]==b[key],('Effective-layer parity mismatch',key)
    assert not a['failures'] and not b['failures']
    assert b['exclusion_restored_exact_original']
    inputs={}
    for record in (a,b):
        for name,h in record['verified_inputs'].items():
            assert name not in inputs or inputs[name]==h,('Compared different inputs',name)
            assert sha(ROOT/name)==h,('Changed sealed input',name)
            inputs[name]=h
    for p in paths:inputs[str(p.relative_to(ROOT))]=sha(p)
    out=dict(schema='riverstone.r5_explicit_owner_prefilter_binding.v1',
             status='exact_representative_effective_layer_parity_pass',
             verified_inputs=inputs,case_count=a['case_count'],
             total_owner_queries=a['total_owner_queries'],
             original_seconds=a['wall_seconds'],both_seconds=b['wall_seconds'],
             limits=['Only opt-in r5 child process hooks; source modules remain unchanged.',
                     'Representative effective-layer parity is not a complete city gameplay pass.'])
    dest=HERE/'owner_prefilter_binding.json';assert not dest.exists()
    dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='verified_inputs'},indent=2))
    print('binding_sha256',sha(dest))
if __name__=='__main__':main()
