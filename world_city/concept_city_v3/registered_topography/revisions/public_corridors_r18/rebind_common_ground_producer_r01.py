"""Copy the actual producer patch, replacing only uniquely matched appended faces."""
import json, collections, copy
from .height_field import HERE
from .revise_native_emission_r07 import ref
from ..r17_district_batches import author as a

def main():
 bp=a.CITY/'registered_integration/r8/district_bound_r04.json';binding=json.loads(bp.read_bytes());rp=HERE/'current_common_top_retirement_review_r01.json';review=json.loads(rp.read_bytes());patch_path=HERE/'current_common_top_retirement_r01.json';patch=json.loads(patch_path.read_bytes());edits={(r['material'],r['triangle_index']):r for r in patch['surface_edits']};wanted={(r['material'],tuple(map(tuple,r['source_triangle_xyz_m']))):r for r in review['records']};found=collections.defaultdict(list);loaded={}
 for source in binding['patches']:
  p=a.ROOT/source['path'];assert a.sha(p)==source['sha256'];d=json.loads(p.read_bytes());loaded[source['path']]=d
  for m,flat in d.get('appended_surfaces',{}).items():
   for i in range(0,len(flat),3):
    key=(m,tuple(map(tuple,flat[i:i+3])))
    if key in wanted:found[key].append(dict(producer_path=source['path'],material=m,triangle_index=i//3))
 assert set(found)==set(wanted),('missing producers',set(wanted)-set(found))
 assert all(len(v)==1 for v in found.values()),'Ambiguous producer triangle'
 modifications=collections.defaultdict(dict);ledger=[]
 for key,hits in found.items():
  hit=hits[0];r=wanted[key];replacement=edits[(r['material'],r['triangle_index'])]['replacement_triangles_xyz_m'];modifications[hit['producer_path']][(hit['material'],hit['triangle_index'])]=replacement;ledger.append(dict(current_R04_material=r['material'],current_R04_triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],source_triangle_xyz_m=r['source_triangle_xyz_m'],producer=hit,replacement_triangles_xyz_m=replacement))
 outputs=[]
 for j,(path,mods)in enumerate(modifications.items()):
  original=loaded[path];out=copy.deepcopy(original)
  for m,flat in original['appended_surfaces'].items():
   new=[]
   for i in range(0,len(flat),3):
    replacement=mods.get((m,i//3));new.extend(flat[i:i+3]if replacement is None else[v for t in replacement for v in t])
   out['appended_surfaces'][m]=new
  assert out['surface_edits']==original['surface_edits'];assert out['source_surface_hashes']==original['source_surface_hashes'];out['id']=original['id']+':R18_COMMON_TOP_RETIREMENT_R01';out['status']='APPENDED_TOP_REBOUND_ONLY_PENDING_COMPOSED_REPLAY';out['r18_common_top_retirement']=dict(original_producer=ref(a.ROOT/path),contextual_patch=ref(patch_path),review=ref(rp),base_surface_edits_value_identical=True)
  target=HERE/('common_ground_producer_rebound_r01_'+str(j)+'.json');target.write_text(json.dumps(out,separators=(',',':'))+'\n');outputs.append(dict(original=ref(a.ROOT/path),replacement=ref(target),matched_appended_triangles=len(mods),base_surface_edits_sha256=a.canonical_sha(out['surface_edits']),base_surface_edits_identical=True,unchanged_appended_triangle_count=sum(len(v)//3 for v in original['appended_surfaces'].values())-len(mods)))
 out=dict(status='PASS_EXACT_APPENDED_PRODUCER_REBIND',sources=[ref(bp),ref(patch_path),ref(rp),ref(__import__('pathlib').Path(__file__))],producer_replacements=outputs,matched_current_triangles=len(wanted),matching_policy='unique full ordered XYZ match in exactly one bound producer appended_surfaces array',matching_ledger=ledger,retired_area_m2=review['retired_area_m2'],scope='Parent can replace only the listed producer reference in its binding. Original producer files and base-R7 edits remain unchanged. No global floor suppression or additional patch layer is required.')
 target=HERE/'common_ground_producer_rebound_review_r01.json';target.write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps(dict(review=ref(target),producer_replacements=outputs,matched_current_triangles=len(wanted))))
if __name__=='__main__':main()
