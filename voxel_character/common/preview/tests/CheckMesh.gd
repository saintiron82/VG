extends SceneTree

const VoxelRenderData = preload("res://RenderData.gd")

func _initialize() -> void:
	call_deferred("check_mesh")

func check_mesh() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 1)
	var result := VoxelRenderData.read(args[0])
	assert(not result.has("error"))
	var data: Dictionary = result.data
	var asset: Node3D = VoxelRenderData.build(data)
	root.add_child(asset)
	var bounds := AABB()
	var first := true
	var triangles := 0
	for child in asset.get_children():
		assert(child is MeshInstance3D)
		assert(child.scale == Vector3.ONE and child.position == Vector3.ZERO)
		var arrays: Array = child.mesh.surface_get_arrays(0)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		for vertex in vertices:
			bounds = AABB(vertex, Vector3.ZERO) if first else bounds.expand(vertex)
			first = false
		for offset in range(0, vertices.size(), 3):
			var cross_product := (vertices[offset + 1] - vertices[offset]).cross(vertices[offset + 2] - vertices[offset])
			assert(cross_product.dot(normals[offset]) < 0.0, "Godot clockwise winding must face the explicit outward normal")
			triangles += 1
	assert(bounds.is_equal_approx(VoxelRenderData.bounds_of(data)), "world-space coordinates must not be multiplied by pitch or translated by grid_origin twice")
	assert(triangles == 12)
	print("COMMON_VIEWER_MESH_OK: 12 clockwise triangles, outward normals, unchanged world bounds and model scale")
	asset.free()
	quit(0)
