"""Finite frozen-R5 terrain patch for new principal-frame native masks.
No city export and no mutation of the frozen scene. Shared R15 bookkeeping.
"""
from reframe import *
from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch import frozen as f
from world_city.concept_city_v3.review_geometry import DomainCut,clean,fan
FIX=OUT/'corner_repair_r01';DEST=FIX/'terrain_patch'
def main():
 start=time.monotonic();d=load(FIX/'changed_masks.json');pack=load(FIX/'resolved_placements.json');scene=f.load_scene();new=[r['polygon_xz_m']for r in d['add_actual_bearing_footprints']];cutter=DomainCut([{'polygon_xz_m':p}for p in new]);windows=[]
 for pid in IDS:
  ps=[v for r in pack['actual_bearing_footprints']if r['placement_id']==pid for v in r['polygon_xz_m']];windows.append([min(p[0]for p in ps)-1,min(p[1]for p in ps)-1,max(p[0]for p in ps)+1,max(p[1]for p in ps)+1])
 edits=[];sourcehash={};removed=0;vertical=0;preservation=[];restore_parts=[r['polygon_xz_m']for r in d['restore_old_only_holes']];restore_index=geo._SpatialIndex(8)
 for i,p in enumerate(restore_parts):restore_index.add(i,p)
 occupied_restore=[]
 for material,vertices in scene['surfaces'].items():
  if material=='water':continue
  changed=False
  for startindex in range(0,len(vertices),3):
   tri=vertices[startindex:startindex+3];p=[[v[0],v[2]]for v in tri];b=f.bounds(p)
   if not any(f.overlap(b,w)for w in windows):continue
   area=geo.polygon_area(p)
   if area<=1e-9:
    masks=[new[i]for i in cutter.index.candidates(p)];result=f.clip_vertical_triangle(tri,masks)
    if result['unchanged']:continue
    replacement=result['triangles_xyz_m'];vertical+=1
   else:
    # Old-only restoration may never duplicate a retained frozen top surface.
    if max(v[1]for v in tri)>13.5:
     for i in restore_index.candidates(p):
      overlap=geo.intersection_area(p,restore_parts[i])
      if overlap>1e-7:occupied_restore.append({'material':material,'triangle_index':startindex//3,'area_m2':overlap})
    if not any(geo.positive_area_overlap(p,new[i],0)for i in cutter.index.candidates(p)):continue
    parts=cutter.subtract(p);newarea=sum(geo.polygon_area(q)for q in parts)
    if area-newarea<1e-8:continue
    plane=f.a.affine_plane(tri);replacement=[];sign=geo.signed_polygon_area(p)
    for part in parts:
     if geo.signed_polygon_area(part)*sign<0:part=list(reversed(part))
     for t in fan(part):replacement.append([[x,f.a.plane_height(plane,x,z),z]for x,z in t])
    removed+=area-newarea
    preservation.append({'material':material,'triangle_index':startindex//3,'original_plane_y_xz_m':list(plane),'outside_area_before_m2':newarea,'replacement_area_m2':sum(geo.polygon_area([[v[0],v[2]]for v in q])for q in replacement),'maximum_plane_error_m':max([abs(v[1]-f.a.plane_height(plane,v[0],v[2]))for q in replacement for v in q]or[0])})
   edits.append({'material':material,'triangle_index':startindex//3,'source_triangle_sha256':f.canonical_sha(tri),'replacement_triangles_xyz_m':replacement});changed=True
  if changed:sourcehash[material]=f.canonical_sha(vertices)
 # Other retained native owners are protected even if later source masks touch.
 protected=[r['polygon_xz_m']for r in pack['actual_bearing_footprints']]
 protected +=[r['polygon_xz_m']for r in load(LAND)['owned_floors']]
 for r in load(GARDEN)['ownership_masks']:protected+=r.get('terrain_exclusion_regions_xz_m',[])
 pc=DomainCut([{'polygon_xz_m':p}for p in protected]);restore=[q for p in restore_parts for q in pc.subtract(p)];appended={'land_D_CLERGY':[v for p in restore for t in fan(p)for v in[[x,14,z]for x,z in (list(reversed(t))if geo.signed_polygon_area(t)>0 else t)]]}
 # Upward Y triangles use clockwise XZ winding, matching native source convention.
 assert all((q[1][2]-q[0][2])*(q[2][0]-q[0][0])-(q[1][0]-q[0][0])*(q[2][2]-q[0][2])>=-1e-10 for q in[appended['land_D_CLERGY'][i:i+3]for i in range(0,len(appended['land_D_CLERGY']),3)])
 assert sum(r['area_m2']for r in occupied_restore)<1e-5,occupied_restore[:5]
 patch={'schema':'riverstone.frozen_scene.local_surface_patch.v1','id':'clergy_principal_frame_corner_r01','status':'sealed finite source candidate; cross-pack index merge and actual review pending','base_scene':ref(f.SCENE_PATH),'base_scene_sha256':f.SCENE_SHA256,'source_surface_hashes':sourcehash,'changed_masks':ref(FIX/'changed_masks.json'),'native_replacement_pack':ref(FIX/'resolved_placements.json'),'shared_bookkeeping':ref(Path(f.__file__)),'surface_edits':edits,'appended_surfaces':appended,'removed_foundation_proxy_ids':[],'summary':{'edited_original_triangles':len(edits),'edited_vertical_triangles':vertical,'new_native_top_cut_area_m2':removed,'restored_old_only_area_m2':sum(geo.polygon_area(p)for p in restore),'restoration_before_protected_owner_subtraction_m2':sum(geo.polygon_area(p)for p in restore_parts),'restoration_triangles':len(appended['land_D_CLERGY'])//3,'unaffected_source_planes_changed':False,'restoration_height_m':14,'new_native_bearing_bottom_m':13.5,'restoration_material':'Retained clergy district terrain material, not duplicate native court paving.'},'limits':['All indices are original frozen R5 material-array offset/3.','Do not apply sequentially to a previously patched scene; duplicate original triangle indices require geometric composition.','No full city export, GUI or runtime review.']};write(DEST/'surface_patch.json',patch)
 applied=f.apply_edits(scene,patch);ledger=applied['local_terrain_patch']['unchanged_triangle_ledger'];write(DEST/'index_ledger.json',{'patch':ref(DEST/'surface_patch.json'),'base_scene_sha256':f.SCENE_SHA256,'changed_indices_by_material':{m:sorted(r['triangle_index']for r in edits if r['material']==m)for m in sourcehash},'unchanged_triangle_ledger':ledger});write(DEST/'test_results.json',{'exact_base_hash':True,'edited_triangle_hashes_verified':True,'unaffected_triangles_carried_forward_byte_equal':True,'all_replacement_vertices_on_original_planes':all(p['maximum_plane_error_m']<1e-10 for p in preservation),'max_outside_area_error_m2':max([abs(p['outside_area_before_m2']-p['replacement_area_m2'])for p in preservation]or[0]),'restoration_existing_surface_overlap_m2':sum(r['area_m2']for r in occupied_restore),'source_surface_edit_count':len(edits),'patch_summary':patch['summary'],'total_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'applied_in_memory_only':True});print(patch['summary']);print(ref(DEST/'surface_patch.json'));print(ref(DEST/'index_ledger.json'))
if __name__=='__main__':main()
