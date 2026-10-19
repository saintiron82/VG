extends SceneTree
const Patch=preload("res://SurfacePatchMesh.gd")
const RD=preload("res://RenderData.gd")
const World=preload("res://CityWorldAccessDetail.gd")
const BASE="res://../near_detail_r01/city_upgrade/native_access_detail_r01/"
func _init() -> void:
	var repo:=ProjectSettings.globalize_path("res://../../..")
	var path:=BASE+"generated/modules_r03/catalog_r03.json";var catalog: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(path))
	var plan_path:=BASE+"generated/source_plan_r03.json";var plan: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(plan_path));var poses: Array=JSON.parse_string(FileAccess.get_file_as_string(BASE+"validation/poses.json"))
	var rows: Array=[];var wrong:=0;var degenerate:=0;var total:=0
	for m in catalog.modules:
		var r:=RD.read(repo.path_join(m.render_path))
		assert(r.sha256==m.render_sha256)
		var mesh:=Patch.module_mesh(r.data);var ar:=mesh.surface_get_arrays(0);var vertices: PackedVector3Array=ar[Mesh.ARRAY_VERTEX];var normals: PackedVector3Array=ar[Mesh.ARRAY_NORMAL];var bad:=0;var zero:=0
		for i in range(0,vertices.size(),3):
			var n: Vector3=(vertices[i+1]-vertices[i]).cross(vertices[i+2]-vertices[i]);total+=1
			if n.length_squared()<1e-18:zero+=1
			elif n.normalized().dot(normals[i])>-.99999:bad+=1
		wrong+=bad;degenerate+=zero;rows.append({"id":m.id,"triangles":vertices.size()/3,"wrong_clockwise_winding":bad,"degenerate":zero})
	var w:=World.new();var placements:=0;var transform_bad:=0
	for i in plan.assets.size():
		for p in plan.assets[i].placements:
			var tr: Transform3D=w._pose(poses[i])*w.access_pose(p.transform);placements+=1
			if absf(tr.basis.determinant()-1)>1e-5 or (tr.basis*Vector3(0,0,1)).dot(Vector3.UP)<.99999:transform_bad+=1
	w.free()
	var report:={"all_pass":catalog.modules.size()==84 and placements==226 and wrong==0 and degenerate==0 and transform_bad==0 and FileAccess.get_sha256(plan_path)==catalog.source_plan_sha256,"modules":catalog.modules.size(),"triangles":total,"wrong_clockwise_winding":wrong,"degenerate":degenerate,"actual_pose_placements":placements,"invalid_actual_transforms":transform_bad,"catalog_sha256":FileAccess.get_sha256(path),"plan_sha256":FileAccess.get_sha256(plan_path),"module_results":rows,"runtime_binding_changed":false,"new_colliders":0,"scope":"Existing shared Patch.module_mesh and runtime pose helpers, candidate data only. No production catalog load/override or GUI."}
	var f:=FileAccess.open(BASE+"r03/godot_mesh_report.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 3)
