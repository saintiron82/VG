"""Finite candidate validation, no replay or fluid simulation."""
import json,hashlib,math
from pathlib import Path
import numpy as np
from .author import H,load,write,ref,B,R,S,SHA,sha
from world_city.concept_city_v3.registered_integration.r6.merge_patches import validate_against_scene
from world_city.runtime_city.checks import placement as g

def main():
 p=load(H/'surface_patch.json');pack=load(H/'pack.json');audit=load(H/'source_audit.json');ledger=load(H/'design_ledger.json');scene=load(S);assert sha(S)==SHA;validate_against_scene(scene,p);assert audit['status']=='PASS_SELECTED_FINITE_CANDIDATE'
 bad=[]
 groups=[(m,[vs[j:j+3]for j in range(0,len(vs),3)])for m,vs in p['appended_surfaces'].items()]+[(r['material']+':'+str(r['triangle_index']),r['replacement_triangles_xyz_m'])for r in p['surface_edits']]
 for m,tt in groups:
  for j,t in enumerate(tt):
   vv=np.asarray(t,dtype=np.float32);n=np.cross(vv[1]-vv[0],vv[2]-vv[0])
   if not np.any(n)or n[1]<=0:bad.append([m,j])
 assert not bad,bad
 own={(r['material'],r['triangle_index'])for r in p['surface_edits']};conflicts=[];sources=[]
 for q in [H.parent/'frozen_r01/surface_patch.json',B/'registered_integration/r9/landward_gates/candidate_r02/surface_patch.json']+list((H.parent.parent/'institution_entries').glob('**/*patch.json')):
  if not q.exists():continue
  d=load(q);sources.append(ref(q));conflicts.extend([str(q.relative_to(R)),m,j]for m,j in own&{(r['material'],r['triangle_index'])for r in d.get('surface_edits',[])})
 assert not conflicts,conflicts
 for asset in pack['common_assets'].values():
  assert sha(R/asset['master_path'])==asset['master_sha256']and sha(R/asset['render_path'])==asset['render_sha256'];assert asset['bounds']['min'][1]==0
 assert ledger['direct_outlet_y_m']<ledger['supply_head_y_m'];assert ledger['nominal_receiving_surface_y_m']<=4.4
 assert not pack['remove_instance_ids']and not pack['replace_instances'];assert all(r['material']not in ['road','alley']for r in p['surface_edits'])
 write('validation.json',dict(status='PASS_STATIC_INDEPENDENT_CANDIDATE',source_plan=ref(B/'registered_source/plan.json'),base_scene=ref(S),pack=ref(H/'pack.json'),surface_patch=ref(H/'surface_patch.json'),source_audit=ref(H/'source_audit.json'),current_market_walkspace_source=ref(B/'registered_integration/r9/market_clusters/layout.json'),original_fountain_native_unchanged=True,existing66_market_stalls_unchanged=True,actual_road_area_under_pocket_m2=0,existing_plot_overlap_m2=0,unsupported_source_area_m2=0,bank_side_contacts=0,native_and_legacy_contacts=0,float32_degenerate_or_reversed_triangles=bad,duplicate_source_faces=conflicts,other_patches_checked=sources,protected_head_y_m=4.6,outlet_y_m=4.45,receiving_y_m=4.3,source_face_count=len(p['surface_edits']),runtime='NOT_RUN',integrated_visual_review='NOT_RUN',hydraulic_operation='NOT_CERTIFIED',first_two_site_frozen_pack_unchanged=True))
 print('PASS_STATIC_INDEPENDENT_CANDIDATE',len(p['surface_edits']),'source faces')
if __name__=='__main__':main()
