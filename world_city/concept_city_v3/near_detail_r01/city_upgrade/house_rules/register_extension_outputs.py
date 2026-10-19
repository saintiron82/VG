"""Publish only verified extension outputs through the existing override contract."""
import json
import adapter as a
import compile_batch as b


def publish():
    root=b.HERE/'compiled';output=root/'extensions_r01'
    catalog_path=b.HERE.parent/'house_extensions/generated/active_catalog.json'
    catalog=a.load(catalog_path);path=root/'selection_overrides.json';overrides=a.load(path);added=[]
    for entry in catalog['assets']:
        key=entry['asset_key'];record=b.inspect_output(key,output)
        if not record or not record['status'].startswith('PASS'):continue
        if not record.get('independent_qa',{}).get('pass') or not record.get('independent_replay',{}).get('pass'):continue
        qa=record['independent_qa'];replay=record['independent_replay']
        replacement={'stats_path':record['stats_path'],'stats_sha256':record['stats_sha256'],
            'qa_path':qa['path'],'qa_sha256':qa['sha256'],'replay_path':replay['path'],'replay_sha256':replay['sha256'],
            'source_catalog_path':str(catalog_path.relative_to(a.ROOT)),'source_catalog_sha256':a.sha(catalog_path),
            'source_master_path':entry['source_master_path'],'source_master_sha256':entry['source_sha256'],
            'emitted_master_path':entry['emitted_master_path'],'emitted_master_sha256':entry['emitted_master_sha256'],
            'reason':'Verified native-bounds extension output; original source and city index remain unchanged.'}
        if key in overrides['assets'] and overrides['assets'][key]!=replacement:
            raise ValueError('Existing extension selection differs; review required: '+key)
        if key not in overrides['assets']:overrides['assets'][key]=replacement;added.append(key)
    if added:b.atomic_json(path,overrides)
    return {'added':added,'selection_overrides_path':str(path.relative_to(a.ROOT)),'sha256':a.sha(path)}

if __name__=='__main__':print(json.dumps(publish()))
