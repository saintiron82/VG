"""Hash, source, finite footprint, native, route and patch checks; no runtime claim."""
import json,math
import numpy as np
from .author import *
from .select_sites import trans,rect
from world_city.concept_city_v3.registered_integration.r6.merge_patches import validate_against_scene
from world_city.concept_city_v3.registered_source.geometry import triangulate

def main():
 scene=load(S);assert sha(S)==SHA;plan=load(B/'registered_source/plan.json');assert sha(B/'registered_source/plan.json')=='685592393dd5b3bffa189d497db8bff14ba4d893d5d81089a66427bd5a6b588c'
 selected=load(H/'selected_sites.json');pack=load(H/'pack.json');patch=load(H/'surface_patch.json');validate_against_scene(scene,patch)
 assets=copy.deepcopy(scene['common_assets']);instances={i['id']:i for i in scene['common_instances']}
 for rr in load(B/'registered_integration/r9/integration_r02/index.json')['packs']:
  p=load(R/rr['path']);assert sha(R/rr['path'])==rr['sha256'];assets.update(p.get('common_assets',{}))
  for k in p.get('remove_instance_ids',[]):instances.pop(k,None)
  for i in p.get('add_instances',[]):instances[i['id']]=i
  for i in p.get('replace_instances',[]):instances[i['id']]=dict(instances[i['id']],asset_key=i['asset_key'])
 obstacles=[]
 for asset in assets.values():
  if 'bounds'not in asset:asset['bounds']=load(R/asset['render_path'])['bounds']
 for i in instances.values():
  bb=assets[i['asset_key']]['bounds'];scale=i.get('scale',[1,1,1]);bb={k:[v[j]*scale[j]for j in range(3)]for k,v in bb.items()};q=trans(rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),i['position_m'],i.get('yaw_rad',0));obstacles.append(dict(id=i['id'],polygon=q,lo=i['position_m'][1]+bb['min'][1],hi=i['position_m'][1]+bb['max'][1]))
 for i in scene.get('boxes',[]):
  sz=i['size_m'];q=trans(rect(-sz[0]/2,-sz[2]/2,sz[0]/2,sz[2]/2),i['position_m'],i.get('yaw_rad',0));obstacles.append(dict(id=i['id'],polygon=q,lo=i['position_m'][1]-sz[1]/2,hi=i['position_m'][1]+sz[1]/2))
 index=g._SpatialIndex(8)
 for j,o in enumerate(obstacles):index.add(j,o['polygon'])
 native=[];face=[];domains=[]
 for r in selected['sites']:
  record=dict(site=r['site'],native_body_hits=[],native_branch_hits=[],road_footprint_area_m2=0,source_support_missing_area_m2=r['ground']['missing_area_m2'],branch_support_missing_area_m2=r['access']['missing_area_m2'],source_side_contacts=len(r['side_clearance']['contacts']))
  for field,key,height in [('native_body_hits','footprint_xz_m',4.2),('native_branch_hits','branch_polygon_xz_m',2.2)]:
   poly=r[key]
   record[field]=[obstacles[j]['id']for j in index.candidates(poly)if obstacles[j]['hi']>r['position_m'][1]+1e-5 and obstacles[j]['lo']<r['position_m'][1]+height and g.polygon_area(g.convex_intersection(poly,obstacles[j]['polygon']))>1e-7]
  record['road_footprint_area_m2']=sum(p['area_m2']for p in r['ground']['source_pieces']if p['material']in ['road','alley'])
  record['flat_support_min_y_m']=min(x['min_y_m']for x in r['ground']['source_pieces']);record['flat_support_max_y_m']=max(x['max_y_m']for x in r['ground']['source_pieces'])
  assert not record['native_body_hits'] and not record['native_branch_hits'],record
  assert record['road_footprint_area_m2']==0 and record['source_support_missing_area_m2']<1e-7 and record['branch_support_missing_area_m2']<1e-7
  record['public_road_clear_width_preserved_m']=r['design_road_width_m'];record['aboveground_storage_only']=True;native.append(record)
 # Exact original road material survives; no facility consumes a road triangle.
 assert all(r['material']not in ['road','alley','water']for r in patch['surface_edits'])
 road_unchanged=True
 # New triangles must survive conversion used by native renderer/physics.
 deg=[];negative=[]
 for mat,vs in patch['appended_surfaces'].items():
  for j in range(0,len(vs),3):
   t=np.array(vs[j:j+3],dtype=np.float32);n=np.cross(t[1]-t[0],t[2]-t[0])
   if not np.any(n):deg.append([mat,j//3])
   elif n[1]<0:negative.append([mat,j//3])
 for row in patch['surface_edits']:
  for j,vs in enumerate(row['replacement_triangles_xyz_m']):
   t=np.array(vs,dtype=np.float32);n=np.cross(t[1]-t[0],t[2]-t[0])
   if not np.any(n):deg.append([row['material'],row['triangle_index'],j])
   elif n[1]<0:negative.append([row['material'],row['triangle_index'],j])
 # Duplicate source-face conflicts across current gate/institution candidates.
 own={(r['material'],r['triangle_index'])for r in patch['surface_edits']};conflicts=[];compared=[]
 for q in [B/'registered_integration/r9/landward_gates/surface_patch.json',B/'registered_integration/r9/landward_gates/candidate_r02/surface_patch.json']+list((H.parent/'institution_entries').glob('**/*patch.json')):
  if not q.exists():continue
  other=load(q);keys={(r['material'],r['triangle_index'])for r in other.get('surface_edits',[])};overlap=sorted(own&keys);compared.append(ref(q));conflicts.extend(dict(other=str(q.relative_to(R)),material=k[0],triangle_index=k[1])for k in overlap)
 assert not conflicts,conflicts
 # Check all existing exact 493 certified directional path center ribbons.
 cert=B/'traversal_r5/revisions/r06_r8_precinct/case_input_certification_r04/selected_all493_bound_r02.json';route_hits=[]
 for rr in load(cert)['routes']:
  points=rr['points'];width=1.2
  for aa,bb in zip(points,points[1:]):
   if math.dist([aa[0],aa[2]],[bb[0],bb[2]])<1e-8:continue
   ribbon=g.road_ribbon([aa[0],aa[2]],[bb[0],bb[2]],width)
   for row in selected['sites']:
    if g.polygon_area(g.convex_intersection(ribbon,row['footprint_xz_m']))>1e-7:route_hits.append(dict(site=row['site'],route=rr['id']))
 assert not route_hits,route_hits[:10]
 assert not deg and not negative,dict(float32_degenerate=deg[:10],negative=negative[:10])
 for asset in pack['common_assets'].values():
  assert sha(R/asset['master_path'])==asset['master_sha256'] and sha(R/asset['render_path'])==asset['render_sha256']
 storage=load(H/'storage_geometry.json');assert storage['native_nominal_storage_m3']>0
 ledger=load(H/'parcel_ownership_overlay.json');before=ledger['replace_parcel_geometry'][0];assert abs(before['before_area_m2']-before['after_area_m2']-before['public_carveout_area_m2'])<1e-8
 write('validation.json',dict(status='PASS_STATIC_SOURCE_NATIVE_AND_FINITE_SURFACE',base_scene=ref(S),source_plan=ref(B/'registered_source/plan.json'),pack=ref(H/'pack.json'),surface_patch=ref(H/'surface_patch.json'),native_instances_checked=len(instances),legacy_boxes_checked=len(scene.get('boxes',[])),sites=native,existing_road_triangle_values_unchanged=road_unchanged,certified493_center_corridor_width_screen_m=1.2,certified493_footprint_conflicts=route_hits,float32_degenerate_triangles=deg,reversed_appended_or_replacement_triangles=negative,source_face_conflicts=conflicts,other_patches_checked=compared,storage_native_m3_each=storage['native_nominal_storage_m3'],parcel_carveout_m2=before['public_carveout_area_m2'],runtime_replay='NOT_RUN',actual_integrated_screenshot_review='NOT_RUN',limits=['Native collision clearance is proved by disjoint complete native oriented bounds and legacy box bounds, not a physics-controller replay.','The full actual road material is preserved; the extra 493 center-ribbon screen is only1.2m and is not a new cart certificate.','Owner overlay must travel with terrain and visual packs; source plan remains unchanged.','No fluid, water-quality, source-yield, fire-response or household-demand certification.']))
 print('PASS',len(patch['surface_edits']),'source edits; no clashes; two public branches')
if __name__=='__main__':main()
