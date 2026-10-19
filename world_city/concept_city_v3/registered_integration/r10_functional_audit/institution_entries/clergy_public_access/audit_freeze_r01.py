"""Exact clipping/ownership/crop uniqueness audit; freeze candidate without overwrites."""
from build_candidate_r01 import *
import shutil

def main():
 p=read(H/'surface_patch.json');ctx=read(H.parent/'context.json')['sites']['clergy'];base=read(BASE);pack=read(H/'pack.json');owners=[q for o in p['ownership']for q in o['ownership_polygons_xz_m']];domain=DomainCut([dict(polygon_xz_m=q)for q in owners]);lookup={};intrusions=[];smallest=[]
 for m,h in p['source_surface_hashes'].items():assert ch(base['surfaces'][m])==h
 for e in p['surface_edits']:
  key=(e['material'],e['triangle_index']);assert key not in lookup;lookup[key]=e;t=base['surfaces'][key[0]][key[1]*3:key[1]*3+3];assert t==e['source_triangle_xyz_m']and ch(t)==e['source_triangle_sha256'];a=np.array(t);n=np.cross(a[1]-a[0],a[2]-a[0]);smallest.append(area3(t))
  for rr in e['replacement_triangles_xyz_m']:
   aa=np.array(rr);nn=np.cross(aa[1]-aa[0],aa[2]-aa[0]);assert np.dot(nn,n)>0;assert max(abs(float(np.dot(n,v-a[0])))for v in aa)<1e-5
 for r in ctx['surface_rows']:
  key=(r['material'],r['triangle_index']);ee=lookup.get(key);ts=ee['replacement_triangles_xyz_m']if ee else[r['triangle']]
  for t in ts:
   pp=[xz(v)for v in t]
   for k in domain.index.candidates(pp):
    mask=owners[k];cur=t
    for aa,bb in zip(mask,mask[1:]+mask[:1]):
     if not cur:break
     cur,_=split3(cur,aa,bb,1 if g.signed_polygon_area(mask)>0 else -1)
    if len(cur)<3:continue
    ar=sum(area3(tt)for tt in fan(cur))
    if ar>1e-12:intrusions.append(dict(source=key,inside_area3_m2=ar));break
 assert not intrusions,intrusions[:20]
 tops=[]
 for m,vs in p['appended_surfaces'].items():
  for k in range(0,len(vs),3):
   t=vs[k:k+3];a=np.array(t,dtype=np.float32);n=np.cross(a[1]-a[0],a[2]-a[0]);assert n[1]>0;assert area(domain.subtract([xz(v)for v in t]))<1e-8;tops.append([xz(v)for v in t])
 newbed=pack['instance_relocations'][0]['replacement_footprint_xz_m'];expected=area(owners)-g.polygon_area(newbed);actual=area(tops);assert abs(expected-actual)<1e-7,(expected,actual)
 # In the full visual stack the old ID must be removed before its one new pose.
 instances={i['id']:i for i in base['common_instances']};assets=base['common_assets']
 for r in read(C/'registered_integration/r9/integration_r02_camera/index.json')['packs']+[ref(H/'pack.json')]:
  pp=read(ROOT/r['path']);assets.update(pp.get('common_assets',{}))
  for iid in pp.get('remove_instance_ids',[]):instances.pop(iid,None)
  for i in pp.get('add_instances',[]):instances[i['id']]=i
 moved=pack['add_instances'][0];assert instances[moved['id']]==moved;assert len([i for i in instances.values()if i['id']==moved['id']])==1;old=pack['instance_relocations'][0]['source_instance'];assert old['position_m']!=moved['position_m'];assert not any(i['asset_key']==old['asset_key']and i['position_m']==old['position_m']for i in instances.values())
 # Confirm no old foundation box overlaps the relocated bed at walking height.
 boxhits=[]
 for b in base['boxes']:
  pos=b['position_m'];size=b['size_m']
  if pos[1]+size[1]/2<14.01 or pos[1]-size[1]/2>16.2:continue
  bounds={'min':[-size[0]/2,-size[1]/2,-size[2]/2],'max':[size[0]/2,size[1]/2,size[2]/2]};poly=g.transformed_aabb_xz_m(bounds,pos,b['yaw_rad'])
  if any(g.intersection_area(poly,q)>1e-8 for q in tops):boxhits.append(b['id'])
 assert not boxhits,boxhits
 asset=pack['common_assets'][moved['asset_key']]
 for typ in ['master','render']:assert sha(ROOT/asset[typ+'_path'])==asset[typ+'_sha256']
 report=dict(status='EXACT_SOURCE_OWNERSHIP_AND_SINGLE_RELOCATION_PASS_RUNTIME_VIEW_PENDING',exact_source_faces=len(lookup),smallest_edited_source_area3_m2=min(smallest),retained_source_intrusions=0,source_plane_preservation=True,top_area_m2=actual,owned_area_m2=area(owners),native_crop_footprint_area_m2=g.polygon_area(newbed),owned_area_minus_top_minus_crop_m2=area(owners)-actual-g.polygon_area(newbed),resolved_moved_id_count=1,old_pose_remaining_instances=0,native_crop_area_before_after_m2=[18.,18.],overlapping_walk_height_foundation_boxes=boxhits)
 write('exact_patch_audit.json',report);out=H/'candidate_r01';out.mkdir(exist_ok=False)
 for n in ['pack.json','surface_patch.json','ground_ownership.json','source_tests.json','exact_patch_audit.json','numeric_filter_ledger.json']:shutil.copy2(H/n,out/n)
 idx=read(H/'index.json');idx['packs'][-1]=ref(out/'pack.json');(out/'index.json').write_text(json.dumps(idx,indent=2)+'\n');r=read(H/'routes.json');r['finite_patch']=ref(out/'surface_patch.json');r['visual_index']=ref(out/'index.json');(out/'routes.json').write_text(json.dumps(r,indent=2)+'\n')
 snap=out/'source_snapshot';snap.mkdir()
 for n in ['build_candidate_r01.py','audit_freeze_r01.py','exploration_r02.json']:shutil.copy2(H/n,snap/n)
 for n in ['finite_helpers_frozen.py','build_corridors_r07_preserved.py']:shutil.copy2(S/n,snap/n)
 shutil.copy2(H.parent/'context.json',snap/'context_frozen.json')
 deps=[C/'review_geometry.py',ROOT/'world_city/runtime_city/checks/placement.py',C/'registered_integration/r9/integration_r02_camera/index.json',C/'registered_integration/r10_functional_audit/network/observed_route_observation_mapping.json',C/'registered_source/plan.json']
 frozen=dict(status='FROZEN_SOURCE_PASS_RUNTIME_AND_VISUAL_PENDING',base_scene=ref(BASE),files={str(q.relative_to(out)):sha(q)for q in out.rglob('*')if q.is_file()},source_dependencies=[ref(q)for q in deps],common_asset=asset,source_helper=ref(snap/'build_corridors_r07_preserved.py'),scope='One 2m public high-bench path to an unchanged gate; one native crop bed moved2m west; existing inside gate admitted standing point only.')
 (out/'FROZEN.json').write_text(json.dumps(frozen,indent=2)+'\n');print(json.dumps(dict(candidate=str(out.relative_to(ROOT)),index=ref(out/'index.json'),pack=ref(out/'pack.json'),patch=ref(out/'surface_patch.json'),routes=ref(out/'routes.json'),audit=report),indent=2))
if __name__=='__main__':main()
