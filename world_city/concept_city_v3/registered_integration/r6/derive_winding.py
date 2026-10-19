"""Derive the orientation-only R6 review scene without changing geometry."""
from . import apply_packs as a
from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch.repair_winding_r01 import author
import json
def main():
    dest=a.CITY/'evidence/visual_registered_common_r6_winding_r01';dest.mkdir(exist_ok=True)
    path=dest/'scene.json';assert not path.exists()
    base=author.load_scene();patch_path=author.HERE/'scene_patch.json'
    patch=a.load(patch_path,'6f327c3caa7cb60eaa283a320a67a7583f43d8702698152771956f7a1f34ee85')
    fixed=author.apply_to_scene(base,patch)
    assert all(fixed[k]==base[k] for k in base if k!='surfaces')
    path.write_text(json.dumps(fixed,separators=(',',':'),allow_nan=False)+'\n')
    record={'status':'orientation_only_candidate_pending_actual_review','scene':{'path':a.rel(path),'sha256':a.sha(path)},
       'base_scene':{'path':a.rel(author.SCENE_PATH),'sha256':author.SCENE_SHA256},
       'patch':{'path':a.rel(patch_path),'sha256':a.sha(patch_path)},
       'changed_triangle_winding_count':3406,'all_non_surface_fields_unchanged':True,
       'same_vertex_sets_and_planes':True,'source_module':author.__name__,'whole_city_complete':False}
    (dest/'build_record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
