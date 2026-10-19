"""Explicit finite repair fixture and visual scene patch. Never edits sealed R5."""
import copy,json,pathlib,hashlib,sys,math,shutil,collections
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5';A=CITY/'assemblies/waterworks/registered_bridge/south_approach_r02'
from world_city.runtime_city.checks import placement as g
import frozen_bookkeeping as f
read=lambda p:json.loads(pathlib.Path(p).read_bytes())
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(p.resolve()),'sha256':sha(p)}
def write(p,d):
 with p.open('x') as fh:json.dump(d,fh,separators=(',',':'),allow_nan=False);fh.write('\n')
def norm(poly):
 out=[]
 for p in poly:
  if not out or math.dist(p,out[-1])>1e-9:out.append(p)
 if len(out)>1 and math.dist(out[0],out[-1])<1e-9:out.pop()
 return out

def clip(tri,masks):
 poly=[[v[0],v[2]] for v in tri];bb=f.bounds(poly);near=[m for m in masks if f.overlap(bb,f.bounds(m))]
 if not near:return [tri],0.
 if g.polygon_area(poly)<1e-10:
  return [tri],0. # Preserve actual vertical bank/retaining geometry, including below the cover.
 parts=[poly];gx,gz,c=f.affine_plane(tri)
 for m in near:
  new=[]
  for q in parts:
   if g.intersection_area(q,m)<=1e-10:new.append(q);continue
   new.extend(norm(z) for z in g.convex_difference(q,m))
  parts=[q for q in new if len(q)>2 and g.polygon_area(q)>1e-10]
 sign=g.signed_polygon_area(poly);out=[]
 for q in parts:
  if sign*g.signed_polygon_area(q)<0:q=list(reversed(q))
  vv=[[x,gx*x+gz*z+c,z] for x,z in q]
  out.extend([vv[0],vv[i],vv[i+1]] for i in range(1,len(vv)-1))
 ar=g.polygon_area(poly)-sum(g.polygon_area([[v[0],v[2]] for v in q]) for q in out)
 if abs(ar)<1e-10:return [tri],0.
 return out,ar

def main():
 assert read(H/'evidence/native_audit.json')['status']=='pass_bounded_native_geometry'
 p=read(A/'profile.json');pack=read(A/'resolved_placements.json');base=read(BASE/'prepared.json');b=p['frame']['basis'];t=p['frame']['translation'];world=lambda v:[t[i]+sum(b[i][j]*v[j] for j in range(3)) for i in range(3)]
 collision_masks=[[[v[0],v[2]] for v in r['triangle_xyz_m']] for r in p['triangles']]
 up=read(H/'geometry/visible_upward_faces.json')['local_upward_faces'];visual_masks=[]
 for face in up:
  visual_masks.append([[world([x,face['y'],z])[i] for i in [0,2]] for x,z in face['polygon_xz_m']])
 source=read(BASE/'geometry/SOUTH_NATIVE_TERMINAL_TO_COUNTRY.json');triangles=[];collision_removed=0.;changed=[]
 for i,tri in enumerate(source['triangles']):
  out,ar=clip(tri,collision_masks);triangles.extend(out);collision_removed+=ar
  if out!=[tri]:changed.append(i)
 geometry=H/'geometry/south_with_finite_cover.json';write(geometry,{'schema':'riverstone.r5.r02.finite_collision_replacement.v1','base_geometry':ref(BASE/'geometry/SOUTH_NATIVE_TERMINAL_TO_COUNTRY.json'),'continuous_profile':ref(A/'profile.json'),'triangles':triangles,'exact_outside_original_planes':True,'changed_source_indices':changed,'removed_projected_area_m2':collision_removed})
 proxy=H/'geometry/continuous_cover.json';write(proxy,{'schema':'riverstone.finite_source_profile_collision.v1','source':ref(A/'profile.json'),'triangles':[r['triangle_xyz_m'] for r in p['triangles']],'native_visual_cover':ref(ROOT/pack['assets']['visible_cover']['render']['path']),'visible_only_native_cover':True,'no_infinite_plane':True})
 # Actual-view patch removes only native-cover-owned floor masks from the exact frozen scene.
 scene_path=CITY/'evidence/visual_registered_common_r5/bridge_scene.json';assert sha(scene_path)==source['scene_sha256'];scene=read(scene_path);edits=[];surface_hashes={};by_material=collections.Counter();removed=0.;source_indices=source['source_face_indices'];mask_bounds=[f.bounds(q) for q in visual_masks]
 for material,index in source_indices:
  original=scene['surfaces'][material][index*3:index*3+3];out,ar=clip(original,visual_masks)
  if out==[original]:continue
  assert material not in ['water','bank'], ('Protected surface cut',material,index)
  edits.append({'material':material,'triangle_index':index,'source_triangle_sha256':f.canonical_sha(original),'replacement_triangles_xyz_m':out});by_material[material]+=1;removed+=ar
 for mat in by_material:surface_hashes[mat]=f.canonical_sha(scene['surfaces'][mat])
 patch={'schema':'riverstone.frozen_scene_finite_patch.v1','id':'SOUTH_APPROACH_R02_SUPPORTED_NATIVE_COVER','status':'candidate_pending_capsule_and_parent_visual_review','base_scene_sha256':sha(scene_path),'source_surface_hashes':surface_hashes,'surface_edits':edits,'appended_surfaces':{},'removed_foundation_proxy_ids':[],'native_replacement_pack':ref(A/'resolved_placements.json'),'continuous_physics_profile':ref(A/'profile.json'),'native_owned_masks_world_xz_m':visual_masks,'removed_projected_ground_area_m2':removed,'new_display_geometry':'Native common visible cover in replacement pack. No coplanar surface overlay is appended.','limits':['This patch does not activate the repair or modify the frozen scene.','Native visual top differs from continuous collision by the separately measured bounded sampling error.']}
 patch_path=H/'scene_patch.json';write(patch_path,patch)
 # Validate the patch against original arrays. No full scene is written.
 patched=f.apply_edits(scene,patch);assert patched['common_instances'] is scene['common_instances'];assert len(edits)==len({(e['material'],e['triangle_index']) for e in edits})
 ledger={'source_scene':ref(scene_path),'patch':ref(patch_path),'per_material_edit_count':dict(by_material),'edited_original_indices':{m:[e['triangle_index'] for e in edits if e['material']==m] for m in by_material},'exact_outside_original_planes':True,'removed_projected_area_m2':removed,'unchanged_triangle_ledger':patched['local_terrain_patch']['unchanged_triangle_ledger'],'source_masks_are_actual_native_upfaces':True}
 write(H/'evidence/scene_patch_audit.json',ledger)
 # Explicit byte-for-byte reuse, including the complete controller and collision loader.
 for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:shutil.copy2(BASE/name,H/name);assert sha(H/name)==sha(BASE/name)
 fixed='BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED';base['assets']['south_recessed_fixed']={'render_path':pack['assets']['recessed_fixed']['render']['path'],'render_sha256':pack['assets']['recessed_fixed']['render']['sha256']};base['placements'][fixed]['asset_key']='south_recessed_fixed'
 key='SCENE:SOUTH_NATIVE_TERMINAL_TO_COUNTRY';base['assets'][key]={'render_path':str(geometry.relative_to(ROOT)),'render_sha256':sha(geometry),'collision_format':'actual_scene_triangles'}
 key='SOUTH_CONTINUOUS_SUPPORTED_COVER';base['assets'][key]={'render_path':str(proxy.relative_to(ROOT)),'render_sha256':sha(proxy),'collision_format':'source_grade_proxy_triangles'};base['placements'][key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'declared_supported_continuous_road_cover','collision_layer':1}
 for r in base['routes'][:2]:
  r['placement_ids'].append(key);r['test_scope']='Original southern route XZ, supported continuous 73.375 m² road cover plus unchanged actual country road. No central moving span.'
  for point in r['points']:
   if math.dist([point[0],point[2]],[base['routes'][0]['points'][0][0],base['routes'][0]['points'][0][2]])<1e-8:point[1]=2.
   elif math.dist([point[0],point[2]],[p['sections_world_xyz_m'][3][0][i]*.5+p['sections_world_xyz_m'][3][1][i]*.5 for i in [0,2]])<1e-8:point[1]=p['sections_world_xyz_m'][3][0][1]
  r['length_m']=sum(math.dist(a,b) for a,b in zip(r['points'],r['points'][1:]))
 base['schema']='riverstone.r5.r02.prepared_supported_continuous_cover.v1';base['sources'].update({'repair_profile':ref(A/'profile.json'),'repair_pack':ref(A/'resolved_placements.json'),'repair_native_audit':ref(H/'evidence/native_audit.json'),'repair_scene_patch':ref(patch_path),'baseline_failure_seal':ref(BASE/'freeze_initial.json')})
 for key1 in ['recessed_fixed','visible_cover']:
  for typ in ['master','compiled','render']:base['sources'][key1+'_'+typ]=ref(ROOT/pack['assets'][key1][typ]['path'])
 base['implementation_hashes']={str((H/name).relative_to(ROOT)):sha(H/name) for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh','prepare.py','check_native.py']};base['implementation_hashes'].update({str(pathlib.Path(m.__file__).relative_to(ROOT)):sha(pathlib.Path(m.__file__)) for m in [f,g]})
 base['coverage']['southern_repair']={'source_area_m2':p['source_area_m2'],'visual_top_area_m2':sum(g.polygon_area(q) for q in visual_masks),'source_grade_max':p['maximum_grade'],'collision_clipped_source_triangles':len(changed),'collision_retained_triangles':len(triangles),'profile_triangles':len(p['triangles']),'visual_cover_collidable':False,'actual_recessed_fixed_mesh_collidable':True}
 base['assumptions']=['Identical baseline generic no-step controller and common RenderData loader, byte-for-byte.','Only declared finite supported main-road cover uses continuous collision; actual sampled matching cover is visual.','Actual derived bridge structural mesh and original scene outside finite profile retained; actual market fixture and both negative controls unchanged.','Spawn source Y corrected to actual accepted deck height; no within-route teleports or extra step-up.','No full-width, cart, moving-span, production-controller or NPC guarantee.']
 write(H/'prepared.json',base);write(H/'reuse_manifest.json',{'baseline_failure':ref(BASE/'freeze_initial.json'),'files_identical_to_baseline':{name:sha(H/name) for name in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']},'routes_xz_identical':all([[v[0],v[2]] for v in a['points']]==[[v[0],v[2]] for v in b['points']] for a,b in zip(base['routes'],read(BASE/'prepared.json')['routes'])),'geometry_policy':base['assumptions']})
 print(json.dumps({'prepared':ref(H/'prepared.json'),'visual_scene_edits':dict(by_material),'visual_removed_area_m2':removed,'collision_changed':len(changed),'source_area_m2':p['source_area_m2']}))
if __name__=='__main__':main()
