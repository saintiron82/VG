"""Narrow source revision rule: existing window operations may move along Z.
All non-window data, transforms except Z, materials, instances and cuts stay exact.
"""
import copy

def validate(revision, original, revised):
    assert revision['change_kind']=='window_bay_relocation'
    allowed=revision['allowed_operation_ids'];assert allowed and len(allowed)==len(set(allowed))
    restored=copy.deepcopy(revised);old={c['id']:c for c in original['components']}
    changed=[]
    for component in restored['components']:
        assert component['id'] in old
        before={op['id']:op for op in old[component['id']]['operations']}
        for op in component['operations']:
            if op['id'] not in allowed:continue
            assert component['id']=='windows' and op['id'] in before
            source=before[op['id']];assert op['action']==source['action']=='paint'
            a=source['transform']['translation'];b=op['transform']['translation']
            assert len(a)==len(b)==3 and a[:2]==b[:2] and a[2]!=b[2]
            op['transform']['translation'][2]=a[2]
            assert op==source
            changed.append(op['id'])
    assert sorted(changed)==sorted(allowed)
    assert restored==original
    assert revision['unchanged_structure_proof']['no_fill_operations_added'] is True
    return len(changed)
