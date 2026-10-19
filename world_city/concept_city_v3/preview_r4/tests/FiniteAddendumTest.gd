extends SceneTree
const ADD=preload("res://FiniteSurfaceAddendum.gd")
var failures:Array[String]=[]
func source()->Dictionary:return {"materials":{"stone":"aaaaaa"},"surfaces":{"stone":[]}}
func patch()->Dictionary:return {"schema":"riverstone.frozen_scene_patch.v1","base_scene_sha256":"bound","surface_edits":[],"removed_foundation_proxy_ids":[],"source_surface_hashes":{},"appended_surfaces":{"stone":[[0,1,0],[0,1,1],[1,1,0]]}}
func check(ok:bool,label:String)->void:
	if not ok:failures.append(label)
func _initialize()->void:
	var data:=source();var p:=patch();var r:Dictionary=ADD.apply_to_scene(data,p,"bound");check(r.status=="pass" and data.surfaces.stone.size()==3,"valid")
	data=source();r=ADD.apply_to_scene(data,p,"wrong");check(r.status=="fail" and data.surfaces.stone.is_empty(),"base_identity")
	for issue in ["edit","material","winding","nan","rows","bad_edit_type","bad_hash_type","overflow"]:
		data=source();p=patch()
		match issue:
			"edit":p.surface_edits=[{"bad":1}]
			"bad_edit_type":p.surface_edits=12
			"bad_hash_type":p.source_surface_hashes=[]
			"material":p.appended_surfaces={"unknown":[[0,1,0],[0,1,1],[1,1,0]]}
			"winding":p.appended_surfaces.stone=[[0,1,0],[1,1,0],[0,1,1]]
			"nan":p.appended_surfaces.stone[0][0]=NAN
			"overflow":p.appended_surfaces.stone[0][0]=1e100
			"rows":p.appended_surfaces.stone.append([1,1,1])
		r=ADD.apply_to_scene(data,p,"bound");check(r.status=="fail" and data.surfaces.stone.is_empty(),issue)
	print(JSON.stringify({"status":"pass"if failures.is_empty()else"fail","checks":10,"failures":failures}));quit(0 if failures.is_empty()else 1)
