extends SceneTree
const RD=preload("res://RenderData.gd")
func _initialize() -> void:
	var reports: Array=[]
	var all_pass:=true
	for path in OS.get_cmdline_user_args():
		var result: Dictionary=RD.read(path)
		if result.has("error"):
			reports.append({"path":path,"all_pass":false,"error":result.error});all_pass=false;continue
		var node: Node3D=RD.build(result.data)
		var triangles:=0;var degenerates:=0;var normal_errors:=0
		for child in node.get_children():
			var arrays: Array=child.mesh.surface_get_arrays(0)
			var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
			for i in range(0,vertices.size(),3):
				triangles+=1
				var cross_value: Vector3=(vertices[i+2]-vertices[i]).cross(vertices[i+1]-vertices[i])
				if cross_value.length_squared()<=0:degenerates+=1
				elif cross_value.normalized().dot(normals[i])<.9999:normal_errors+=1
		var okay:=degenerates==0 and normal_errors==0
		reports.append({"path":path,"all_pass":okay,"shared_RenderData_read_pass":true,"shared_RenderData_build_pass":true,"quad_count":result.data.quad_count,"triangles":triangles,"float32_degenerate_triangles":degenerates,"float32_normal_winding_errors":normal_errors,"bounds":result.data.bounds,"render_sha256":result.sha256,"actual_city_visual_reviewed":false})
		all_pass=all_pass and okay;node.free()
	var report: Dictionary={"all_pass":all_pass,"reports":reports}
	var file:=FileAccess.open("res://godot_validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");file.close()
	print(JSON.stringify(report));quit(0 if all_pass else 1)
