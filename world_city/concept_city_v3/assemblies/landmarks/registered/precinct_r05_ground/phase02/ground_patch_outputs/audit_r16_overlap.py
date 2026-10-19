"""Compare immutable original-index keys; do not export or rebase a scene."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[7]
R16=ROOT/'world_city/concept_city_v3/registered_topography/revisions/r16_working_ranges/scene_patch.json'
EXPECTED='d124fba02cb44bf8fca9c8982474c1bc6abac5d000765c6fa702bb0f748d6109'
def load(p):return json.loads(p.read_bytes())
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def write(p,data):p.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
assert ref(R16)['sha256']==EXPECTED,'R16 patch changed; request its current reference'
phase=load(HERE/'surface_patch.json');other=load(R16)
assert phase['base_scene_sha256']==other['base_scene_sha256']
a={(r['material'],r['triangle_index']):r for r in phase['surface_edits']}
b={(r['material'],r['triangle_index']):r for r in other['surface_edits']}
assert len(a)==len(phase['surface_edits']) and len(b)==len(other['surface_edits'])
shared=sorted(set(a)&set(b));rows=[]
for key in shared:
 assert a[key]['source_triangle_sha256']==b[key]['source_triangle_sha256']
 rows.append({'material':key[0],'triangle_index':key[1],
              'source_triangle_sha256':a[key]['source_triangle_sha256'],
              'status':'Geometric composition on original source plane required; never concatenate duplicate edits.'})
result={'status':'PASS_ORIGINAL_INDEX_DISJOINT' if not shared else 'ORIGINAL_INDEX_OVERLAP_REQUIRES_GEOMETRIC_COMPOSITION',
        'base_scene_sha256':phase['base_scene_sha256'],'phase02_patch':ref(HERE/'surface_patch.json'),'r16_patch':ref(R16),
        'phase02_original_edit_count':len(a),'r16_original_edit_count':len(b),'shared_original_index_count':len(shared),
        'shared_original_indices':rows,'original_indices_disjoint':not shared,
        'current_active_scene':'R7 differs from frozen R6; parent composition/rebase still required before any activation.',
        'scene_exported':False,'activated':False}
write(HERE/'r16_overlap_audit.json',result)
for name in ('index_ledger.json','composition_ledger.json'):
 path=HERE/name;data=load(path);data['r16_original_index_audit']=ref(HERE/'r16_overlap_audit.json');data['current_scene_adoption']='R6-bound finite candidate. Parent composition/rebase against current R7 is required; no active-scene write.';write(path,data)
print(json.dumps(result,indent=2))
