"""Verify copied shared source remains exact; no asset reconstruction hidden here."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[2]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    binding = json.loads((HERE / 'character/source_binding.json').read_text())
    checked = []
    for item in binding['files']:
        source, copy = REPO / item['source'], HERE / item['copy']
        assert sha(source) == item['sha256'], ('original changed', str(source))
        assert sha(copy) == item['sha256'], ('copy changed', str(copy))
        checked.append(item['copy'])
    common_source = REPO / 'world_city/concept_city_v3/preview_r9/RenderData.gd'
    assert sha(HERE / 'RenderData.gd') == sha(common_source)
    return {'status': 'PASS', 'byte_identical_character_files': len(checked),
            'files': checked, 'shared_render_adapter_sha256': sha(common_source),
            'scope': 'Source identity, not physics or visual acceptance'}

if __name__ == '__main__':
    result = verify()
    out = HERE / 'evidence/runtime_source_identity.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
