extends SceneTree
const F=preload("res://FiniteSurfaceReplacement.gd")
var checks:int=0
var failures:int=0
func check(value:bool,label:String)->void:
 checks+=1
 if not value:failures+=1;push_error(label)
func base()->Dictionary:return {"materials":{"road":"aaaaaa","bank":"888888"},"surfaces":{"road":[[0,0,0],[0,0,2],[2,0,0]]},"boxes":[{"id":"old"}]}
func patch()->Dictionary:return {"schema":"riverstone.frozen_scene_patch.v1","id":"test","base_scene_sha256":"base","surface_edits":[{"material":"road","triangle_index":0,"source_triangle_xyz_m":[[0,0,0],[0,0,2],[2,0,0]],"replacement_triangles_xyz_m":[[[0,.1,0],[0,.1,2],[2,.1,0]]]}],"appended_surfaces":{},"removed_foundation_proxy_ids":[]}
func _initialize()->void:
 var d:Dictionary=base();var p:Dictionary=patch();var r:Dictionary=F.apply_to_scene(d,p,"base")
 check(r.status=="pass" and d.surfaces.road[0][1]==.1,"finite replacement")
 p=patch();p.base_scene_sha256="wrong";d=base();check(F.apply_to_scene(d,p,"base").status=="fail" and d.surfaces.road[0][1]==0,"base identity atomic")
 p=patch();p.surface_edits[0].source_triangle_xyz_m[0][0]=.01;d=base();check(F.apply_to_scene(d,p,"base").status=="fail" and d.surfaces.road[0][1]==0,"source coordinate atomic")
 p=patch();p.surface_edits.append(p.surface_edits[0]);d=base();check(F.apply_to_scene(d,p,"base").status=="fail","duplicate edit")
 p=patch();p.surface_edits[0].triangle_index=1;d=base();check(F.apply_to_scene(d,p,"base").status=="fail","source face range")
 p=patch();p.surface_edits[0].replacement_triangles_xyz_m=[[[0,0,0],[2,0,0],[0,0,2]]];d=base();check(F.apply_to_scene(d,p,"base").status=="fail","reject winding reversal")
 p=patch();p.surface_edits[0].replacement_triangles_xyz_m[0][0][0]=NAN;d=base();check(F.apply_to_scene(d,p,"base").status=="fail","nonfinite rejection")
 p=patch();p.removed_foundation_proxy_ids=["missing"];d=base();check(F.apply_to_scene(d,p,"base").status=="fail" and d.boxes.size()==1,"unknown proxy atomic")
 p=patch();p.removed_foundation_proxy_ids=["old"];p.surface_edits[0].replacement_triangles_xyz_m=[];d=base();r=F.apply_to_scene(d,p,"base");check(r.status=="pass" and d.boxes.is_empty() and d.surfaces.road.is_empty(),"explicit face/proxy retirement")
 p=patch();p.appended_surfaces={"unknown":[[0,0,0],[0,0,2],[2,0,0]]};d=base();check(F.apply_to_scene(d,p,"base").status=="fail","unknown material atomic")
 p=patch();p.appended_surfaces={"road":[[0,0,0],[2,0,0],[0,0,2]]};d=base();check(F.apply_to_scene(d,p,"base").status=="fail","append top winding")
 print("PASS " if failures==0 else "FAIL ",checks," finite replacement checks; failures=",failures);quit(0 if failures==0 else 1)
