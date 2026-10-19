"""Stage exact accepted private profiles; no source coordinates are resampled."""
import json
from .screen import HERE, write
from .. import author as a
REQUEST = HERE.parent / 'public_dependency_review_r01/next20_atomic_rebind_request_r01.json'
REQUEST_SHA = '92c5623d5861918fcd39040339a5499fea0d50160c15e1fdac00847521fc9205'

def run():
    assert a.sha(REQUEST) == REQUEST_SHA
    request = json.loads(REQUEST.read_bytes())
    output = HERE / 'profiles'
    output.mkdir(exist_ok=True)
    rows = []
    for holding_id, binding in request['profile_bindings'].items():
        source = a.ROOT / binding['path']
        assert a.sha(source) == binding['sha256']
        data = json.loads(source.read_bytes())
        result = dict(data['result'])
        assert result['status'] in ('PASSED_FINITE_TRIANGLE_GRADE', 'FINITE_PROFILE_WITH_COHERENT_DATUM_CANDIDATE')
        result['source_candidate_status'] = result['status']
        result['status'] = 'PASSED_FINITE_TRIANGLE_GRADE'
        result['grade_limit'] = 0.12
        group_id = 'PRIVATE_GROUP:' + holding_id
        record = dict(data, id=group_id, holding_ids=[holding_id], result=result,
                      status='PASSED_FINITE_TRIANGLE_GRADE', source_references=[binding],
                      native_source_rebind_required=True, activation=False)
        path = output / (group_id.replace(':', '_') + '.json')
        assert not path.exists()
        path.write_text(json.dumps(record, separators=(',', ':')) + '\n')
        rows.append(dict(id=group_id, holding_ids=[holding_id], status=record['status'],
                         path=str(path.relative_to(a.ROOT)), sha256=a.sha(path)))
    write('private_profiles_summary_r02.json', dict(groups=rows,
          accepted_candidate_holding_ids=request['matched_next_batch_holding_ids'],
          source_request=dict(path=str(REQUEST.relative_to(a.ROOT)), sha256=REQUEST_SHA), activation=False))
    source = HERE.parent / 'public_dependency_review_r01/next20_fixed_public_regions_r01.json'
    write('resolved_public_inputs_r01.json', json.loads(source.read_bytes()))
    print('Staged', len(rows), 'exact private fields', flush=True)

if __name__ == '__main__':
    run()
