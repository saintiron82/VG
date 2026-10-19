"""Explicit finite stair walking-collision representation; native visuals unchanged."""
import pathlib,json,hashlib,math,sys,importlib.util,copy
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;OLD=H.parent/'bank_r01';ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());BASE=ROOT/'world_city/concept_city_v3/traversal_r5'
spec=importlib.util.spec_from_file_location('base',BASE/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def cross(a,c):return [a[1]*c[2]-a[2]*c[1],a[2]*c[0]-a[0]*c[2],a[0]*c[1]-a[1]*c[0]]
def normal(poly):return cross([poly[1][i]-poly[0][i]for i in range(3)],[poly[2][i]-poly[0][i]for i in range(3)])
def area(poly):
 if len(poly)<3:return 0.
 return sum(math.sqrt(sum(v*v for v in cross([poly[i][j]-poly[0][j]for j in range(3)],[poly[i+1][j]-poly[0][j]for j in range(3)])))/2 for i in range(1,len(poly)-1))
def clip(poly,axis,value,less):
 out=[]
 for a,c in zip(poly,poly[1:]+poly[:1]):
  ia=a[axis]<=value if less else a[axis]>=value;ic=c[axis]<=value if less else c[axis]>=value
  if ia:out.append(a)
  if ia!=ic:
   t=(value-a[axis])/(c[axis]-a[axis]);out.append([a[j]+t*(c[j]-a[j])for j in range(3)])
 return out if area(out)>1e-11 else []
def triangles(poly):return [[poly[0],poly[i+1],poly[i]]for i in range(1,len(poly)-1)] # native -> Godot
def height(z):
 if z<=1.2:return 0.
 if z<=5.1:return (z-1.2)*.5
 if z<=6.3:return 1.95
 if z<=10.2:return 1.95+(z-6.3)*.5
 return 3.9
def main():
 for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','PauseTraversal.gd','PauseTraversal.tscn','project.godot','run.sh','run_capture.py']:(H/n).write_bytes((OLD/n).read_bytes())
 d=b.read(H.parent/'step_candidate_r02/prepared.json');baseline=b.read(OLD/'prepared.json');assert len(d['routes'])==18
 d['implementation_hashes']=copy.deepcopy(baseline['implementation_hashes']);d['sources']=copy.deepcopy(baseline['sources'])
 p=d['placements']['PHASE02:real_neighborhood_stair:0'];old_asset=copy.deepcopy(d['assets'][p['asset_key']]);native_path=ROOT/old_asset['render_path'];assert b.sha(native_path)==old_asset['render_sha256'];render=b.read(native_path)
 retained=[];ledger=[];removed_area=0.;up_removed_projected=0.;source_area=0.;kept_area=0.
 for gi,g in enumerate(render['groups']):
  for qi,q in enumerate(g['quads']):
   n=normal(q);bounds=[[min(v[j]for v in q),max(v[j]for v in q)]for j in range(3)];original_area=area(q);source_area+=original_area
   top=n[1]>1e-9 and abs(bounds[1][1]-bounds[1][0])<1e-10 and bounds[1][0]>=-1e-10
   riser=abs(n[2])>1e-9 and abs(bounds[2][1]-bounds[2][0])<1e-10 and 1e-10<bounds[2][0]<11.4-1e-10 and bounds[1][1]>0
   pieces=[q]
   if top or riser:
    # Three disjoint retained half-space pieces; no changed height coordinates.
    pieces=[clip(q,0,-1.2,True),clip(q,0,1.2,False)]
    center=clip(clip(q,0,-1.2,False),0,1.2,True)
    if riser and center:pieces.append(clip(center,1,0,True))
    pieces=[v for v in pieces if v]
   kept=sum(area(v)for v in pieces);removed=original_area-kept;assert removed>=-1e-8
   if removed>1e-8:
    ledger.append({'group_index':gi,'quad_index':qi,'material':g['material'],'kind':'walking_top'if top else 'walking_riser','source_quad_xyz_m':q,'retained_polygons_xyz_m':pieces,'removed_surface_area_m2':removed});removed_area+=removed
    if top:up_removed_projected+=removed
   kept_area+=kept
   for poly in pieces:retained.extend(triangles(poly))
 assert abs(source_area-kept_area-removed_area)<1e-8
 assert abs(up_removed_projected-2.4*11.4)<1e-8
 sections=[('lower_landing',0,1.2,0,0),('first_flight',1.2,5.1,0,1.95),('middle_landing',5.1,6.3,1.95,1.95),('second_flight',6.3,10.2,1.95,3.9),('upper_landing',10.2,11.4,3.9,3.9)]
 top_tris=[];section_rows=[]
 for name,z0,z1,y0,y1 in sections:
  q=[[-1.2,y0,z0],[-1.2,y1,z1],[1.2,y1,z1],[1.2,y0,z0]];assert normal(q)[1]>0
  ts=triangles(q);top_tris.extend(ts);section_rows.append({'id':name,'local_bounds_z_m':[z0,z1],'height_local_m':[y0,y1],'grade':(y1-y0)/(z1-z0),'triangles_world_xyz_m':[[b.transform(v,p)for v in t]for t in ts]})
 combined=retained+top_tris;proxy_path=H/'geometry/stair_collision_local.json';b.write(proxy_path,{'schema':'riverstone.finite_stair_collision_replacement.v1','source_native_render_sha256':old_asset['render_sha256'],'triangles':combined,'retained_native_triangles':len(retained),'walking_proxy_triangles':len(top_tris),'winding':'direct Godot clockwise'})
 old_key=p['asset_key'];key='R8_STAIR_CONTINUOUS_WALKING_COLLISION';d['assets'][key]={'render_path':str(proxy_path.relative_to(ROOT)),'render_sha256':b.sha(proxy_path),'collision_format':'source_grade_proxy_triangles'};p['asset_key']=key;p['category']='explicit_stair_collision_representation'
 if not any(v['asset_key']==old_key for v in d['placements'].values()):d['assets'].pop(old_key)
 # Exact extremal error at every tread edge. The profile never extends above visible tops.
 error=[]
 for flight,zbase,ybase in [(1,1.2,0),(2,6.3,1.95)]:
  for i in range(13):
   z0=zbase+.3*i;z1=z0+.3;native=ybase+.15*(i+1);error.append({'flight':flight,'tread':i,'visual_height_local_m':native,'z_interval_m':[z0,z1],'visual_minus_collision_at_edges_m':[native-height(z0),native-height(z1)]})
 max_error=max(abs(v)for r in error for v in r['visual_minus_collision_at_edges_m']);assert max_error<=.15000001
 contract={'schema':'riverstone.explicit_stair_collision_contract.v1','id':'PHASE02_STAIR_FINITE_CONTINUOUS_WALKING','status':'CANDIDATE_AWAITING_ACTUAL_PHYSICS','scene':baseline['sources']['actual_r8_candidate'],'native_source':{'path':str(native_path.relative_to(ROOT)),'sha256':b.sha(native_path)},'native_placement_id':p['id'],'logical_collider_id_preserved':p['id'],'disable_native_mesh_collider_ids':[p['id']],'replacement_local_mesh':{'path':str(proxy_path.relative_to(ROOT)),'sha256':b.sha(proxy_path)},'replacement_transform':{k:p[k]for k in ['position_m','yaw_rad']},'add_triangles_world_xyz_m':[[b.transform(v,p)for v in t]for t in combined],'retained_native_triangle_count':len(retained),'walking_triangle_count':len(top_tris),'central_walking_bounds_local_xz_m':[-1.2,0,1.2,11.4],'walking_projected_area_m2':27.36,'native_base_projected_area_m2':34.2,'maximum_visual_above_collision_m':max_error,'maximum_collision_above_visual_m':0,'max_grade':.5,'max_angle_deg':math.degrees(math.atan(.5)),'sections':section_rows,'removed_native_face_ledger':ledger,'visual_native_asset_unchanged':True,'native_side_guards_end_faces_bottom_and_exterior_preserved':True,'original_riser_collision_overlap_inside_walk_prism_m2':0,'scene_promoted':False,'limits':['Two visible thirteen-riser flights remain unchanged; only their walking collision representation differs.','This finite representation is specific to the declared stair and must not be applied to unrelated stairs or walls.','Original controller, strict floor/ray acceptance and every positive route remain unchanged.']}
 b.write(H/'collision_contract.json',contract);b.write(H/'evidence/geometry_audit.json',{'status':'finite_geometry_pass_not_runtime','source_area_m2':source_area,'retained_native_area_m2':kept_area,'removed_native_area_m2':removed_area,'removed_walking_top_projected_area_m2':up_removed_projected,'proxy_top_area_projected_m2':27.36,'source_area_partition_error_m2':source_area-kept_area-removed_area,'profile_error_per_tread':error,'maximum_visual_collision_difference_m':max_error,'no_visual_geometry_edits':True,'native_endpoints_y_world_m':[8.1,12.0],'positive_route_points_verbatim':all(r['points']==next(q['points']for q in baseline['routes']if q['id']==r['id'])for r in d['routes']if r['id']in {q['id']for q in baseline['routes']}),'controller_hash_equal_to_original':b.sha(H/'Traversal.gd')==b.sha(BASE/'Traversal.gd')})
 d['sources']['stair_collision_contract']=b.ref(H/'collision_contract.json');d['sources']['bank_original_failure']=b.ref(OLD/'freeze_baseline.json');d['sources']['failed_step_candidates']=b.ref(H.parent/'evidence/final_candidate_comparison.json')
 d['coverage'].pop('capability_candidate',None)
 d['coverage'].update(cases=18,baseline_cases=16,stop_restart_cases=2,collision_representation={'contract_sha256':b.sha(H/'collision_contract.json'),'only_modified_native_collider':p['id'],'max_visual_collision_difference_m':max_error,'original_no_step_controller':True})
 d['assumptions']=['Unchanged no-step controller on explicitly authorized finite stair-only continuous walking collision.','Native visual treads, guards and bulk remain visible; retained native collision solids and finite walking profile are separately hash-bound.','Same sixteen source tests plus finite isolated overheight/low-headroom controls.','No whole-city, interior, cart or NPC approval.']
 d['implementation_hashes'].update({str(f.relative_to(ROOT)):b.sha(f)for f in H.iterdir()if f.is_file()and f.suffix in ['.py','.gd','.tscn','.godot','.sh']});b.write(H/'prepared.json',d);print(json.dumps({'contract_sha256':b.sha(H/'collision_contract.json'),'prepared_sha256':b.sha(H/'prepared.json'),'retained_triangles':len(retained),'walking_triangles':len(top_tris),'max_height_difference_m':max_error}))
if __name__=='__main__':main()
