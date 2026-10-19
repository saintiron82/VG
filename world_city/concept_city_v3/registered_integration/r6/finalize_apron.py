"""Finite physical apron over existing native flat surface; no visual edits."""
from . import apply_packs as a
import copy,json
VISUAL=a.CITY/'evidence/visual_registered_common_r6_winding_r01/scene.json'
VISUAL_SHA='b755195c3d66be1101f62c5974427d29618b8199b8f6664edca5d81cd5fc558b'
CONTRACT=a.CITY/'traversal_r5/revisions/r04_r6_winding/supplemental_apron_contract.json'
CONTRACT_SHA='e21a094b65ff8b513ebdb32a39ff0f0cd7afde9791e20144107d4dfa880166bb'
def apply_apron(scene):
    source=a.load(VISUAL,VISUAL_SHA)
    if scene!=source:raise ValueError('Changed visually reviewed source')
    data=a.load(CONTRACT,CONTRACT_SHA)
    result=dict(scene);result['collision_contracts']=copy.deepcopy(scene['collision_contracts'])+[copy.deepcopy(data['collision_contract'])]
    assert all(result[k]==scene[k] for k in scene if k!='collision_contracts')
    return result
def main():
    scene=a.load(VISUAL,VISUAL_SHA);out=apply_apron(scene)
    dest=a.CITY/'evidence/visual_registered_common_r6_apron_r01';dest.mkdir(exist_ok=True)
    path=dest/'scene.json';assert not path.exists();path.write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')
    record={'status':'finite_apron_composed_pending_physics','scene':{'path':a.rel(path),'sha256':a.sha(path)},
      'actual_rendered_source':{'path':a.rel(VISUAL),'sha256':VISUAL_SHA},'contract':{'path':a.rel(CONTRACT),'sha256':CONTRACT_SHA},
      'all_visual_fields_exactly_equal':True,'unchanged_original_collision_contracts':True,
      'supplemental_flat_apron_area_m2':0.4573139721,'supplemental_triangle_count':19,
      'screenshot_provenance':'Existing winding-r01 captures depict identical visual fields. This hash adds only the supplemental collision contract.',
      'whole_city_complete':False}
    (dest/'build_record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
