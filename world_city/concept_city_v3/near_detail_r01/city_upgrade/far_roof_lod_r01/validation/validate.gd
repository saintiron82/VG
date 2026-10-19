extends SceneTree
const RD=preload("res://RenderData.gd")
func _initialize() -> void:
	var path:=OS.get_environment("ROOF_CANDIDATE")
	var result: Dictionary=RD.read(path)
	if result.has("error"):
		print(JSON.stringify({"all_pass":false,"error":result.error}));quit(1);return
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
	var report: Dictionary={"all_pass":degenerates==0 and normal_errors==0,"shared_RenderData_read_pass":true,"shared_RenderData_build_pass":true,"quad_count":result.data.quad_count,"triangles":triangles,"float32_degenerate_triangles":degenerates,"float32_normal_winding_errors":normal_errors,"bounds":result.data.bounds,"render_sha256":result.sha256,"actual_city_visual_reviewed":false}
	var file:=FileAccess.open("res://godot_validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");file.close()
	print(JSON.stringify(report));node.free();quit(0 if report.all_pass else 1)
