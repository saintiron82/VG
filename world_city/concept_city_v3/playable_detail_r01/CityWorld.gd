extends Node3D
## Source-bound whole-city tiles. Loading is synchronous and precedes movement.
## No substitute floor, clipped boundary face, controller change or relocation.
const RD = preload("res://RenderData.gd")
var index: Dictionary = {}
var repo_root := ""
var render_enabled := true
var tiles: Dictionary = {}
var loaded: Dictionary = {}
var asset_cache: Dictionary = {}
var mesh_cache: Dictionary = {}
var shape_cache: Dictionary = {}
var material_cache: Dictionary = {}
var disabled: Dictionary = {}
var error := ""
var active_cell := Vector2i(2147483647,2147483647)
var active_radius := -1
var load_events: Array = []
var total_native_loads := 0
var total_terrain_faces := 0
var total_contract_faces := 0
var ready_for_movement := false
var index_sha256 := ""

func configure(index_path: String, root: String, enable_render: bool = true) -> String:
	repo_root = root.trim_suffix("/")
	render_enabled = enable_render
	var value: Variant = JSON.parse_string(FileAccess.get_file_as_string(index_path))
	if not value is Dictionary: return _fail("Missing city tile index")
	index = value
	if index.get("schema","")!="riverstone.playable.city_tile_index.v1": return _fail("Unsupported city tile schema")
	index_sha256=FileAccess.get_sha256(index_path)
	var raw: Variant = index.get("tiles", {})
	if raw is Array:
		for item in raw: tiles[str(item.id)] = item
	else: tiles = raw
	if tiles.is_empty(): return _fail("Empty city tile index")
	for contract in index.get("collision_contracts", []):
		for id in contract.get("disable_native_instance_ids", []): disabled[str(id)] = true
	for id in index.get("disabled_native_instance_ids", []): disabled[str(id)] = true
	return ""

func _fail(message: String) -> String:
	error = message
	ready_for_movement = false
	push_error(message)
	return message

func _path(relative: String) -> String:
	return relative if relative.is_absolute_path() else repo_root.path_join(relative)

func _read_verified(path: String, digest: String) -> PackedByteArray:
	var absolute := _path(path)
	if not FileAccess.file_exists(absolute) or FileAccess.get_sha256(absolute) != digest:
		_fail("City source hash mismatch: " + absolute)
		return PackedByteArray()
	return FileAccess.get_file_as_bytes(absolute)

func ensure_region(position_m: Vector3, radius_cells: int = 1) -> bool:
	if not error.is_empty(): return false
	var size := float(index.get("tile_size_m",64))
	var cell := Vector2i(floori(position_m.x / size),floori(position_m.z / size))
	if cell == active_cell and radius_cells == active_radius: return ready_for_movement
	var started := Time.get_ticks_usec()
	ready_for_movement = false
	var desired: Dictionary = {}
	for x in range(cell.x-radius_cells, cell.x+radius_cells+1):
		for z in range(cell.y-radius_cells, cell.y+radius_cells+1):
			var id := "%d_%d" % [x,z]
			if not tiles.has(id):
				return _fail("Outside exported city coverage: " + id).is_empty()
			desired[id] = true
			for owner in tiles[id].get("dependency_owner_tiles", []): desired[str(owner)] = true
	var added: Array = []
	for id in desired:
		if not loaded.has(id):
			if not tiles.has(id) or not _load_owner(id): return false
			added.append(id)
	# All replacement colliders exist before old nodes are released.
	var removed: Array = []
	for id in loaded.keys():
		if not desired.has(id):
			var old: Node = loaded[id]
			remove_child(old)
			old.queue_free()
			loaded.erase(id)
			removed.append(id)
	active_cell = cell
	active_radius = radius_cells
	ready_for_movement = true
	load_events.append({"cell":[cell.x,cell.y],"added":added,"removed":removed,"loaded_owners":loaded.size(),"wall_ms":(Time.get_ticks_usec()-started)/1000.0})
	return true

func _material(id: String) -> StandardMaterial3D:
	if not material_cache.has(id):
		var m := StandardMaterial3D.new()
		var colors: Dictionary = index.get("render_materials",index.materials)
		m.albedo_color = RD.color_value(colors.get(id,"808080"))
		m.roughness = 1
		m.metallic_specular = 0
		if id == "bank": m.cull_mode = BaseMaterial3D.CULL_DISABLED # Inherited explicit bank material policy.
		material_cache[id] = m
	return material_cache[id]

func _collision(parent: Node3D, points: PackedVector3Array, id: String) -> void:
	if points.is_empty(): return
	var shape := ConcavePolygonShape3D.new()
	shape.backface_collision = false
	shape.set_faces(points)
	var body := StaticBody3D.new()
	body.name = id.validate_node_name()
	body.collision_layer = 1
	body.collision_mask = 0
	body.set_meta("source_id",id)
	var node := CollisionShape3D.new()
	node.shape = shape
	body.add_child(node)
	parent.add_child(body)

func _load_owner(id: String) -> bool:
	var record: Dictionary = tiles[id]
	var binary := _read_verified(record.terrain_path,record.terrain_sha256)
	if not error.is_empty(): return false
	var bytes := _read_verified(record.instances_path,record.instances_sha256)
	if not error.is_empty(): return false
	var content: Variant = JSON.parse_string(bytes.get_string_from_utf8())
	if not content is Dictionary: _fail("Bad tile companion " + id); return false
	if binary.size() != int(record.face_count)*88: _fail("Bad binary length " + id); return false
	var root := Node3D.new()
	root.name = "SourceTile_"+id
	var groups: Dictionary = {}
	var normals: Dictionary = {}
	var collision := PackedVector3Array()
	var render_skip: Dictionary = {}
	var collision_skip: Dictionary = {}
	for i in content.get("render_skip_indices",[]): render_skip[int(i)] = true
	for i in content.get("collision_skip_indices",[]): collision_skip[int(i)] = true
	for i in int(record.face_count):
		var o := i*88
		var a := Vector3(binary.decode_double(o),binary.decode_double(o+8),binary.decode_double(o+16))
		var b := Vector3(binary.decode_double(o+24),binary.decode_double(o+32),binary.decode_double(o+40))
		var c := Vector3(binary.decode_double(o+48),binary.decode_double(o+56),binary.decode_double(o+64))
		var mat: String = str(index.material_ids[binary.decode_u32(o+76)])
		var face := PackedVector3Array([a,c,b])
		if mat != "water" and not collision_skip.has(i): collision.append_array(face)
		if render_enabled and not render_skip.has(i):
			if not groups.has(mat): groups[mat]=PackedVector3Array();normals[mat]=PackedVector3Array()
			var n := (b-a).cross(c-a).normalized()
			groups[mat].append_array(face)
			normals[mat].append_array(PackedVector3Array([n,n,n]))
	for mat in groups:
		var ar: Array = []; ar.resize(Mesh.ARRAY_MAX)
		ar[Mesh.ARRAY_VERTEX]=groups[mat]; ar[Mesh.ARRAY_NORMAL]=normals[mat]
		var mesh := ArrayMesh.new(); mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,ar)
		mesh.surface_set_material(0,_material(mat))
		var node := MeshInstance3D.new();node.mesh=mesh
		if mat not in ["bank","wall","support","boundary"]: node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(node)
	_collision(root,collision,"Surface_"+id)
	var contract_faces := PackedVector3Array()
	var contract_skip: Dictionary = {}
	for i in content.get("contract_collision_skip_indices",[]): contract_skip[int(i)]=true
	var contract_raw: Array = content.get("contract_triangles",[])
	for i in contract_raw.size():
		if not contract_skip.has(i):
			for point in contract_raw[i]: contract_faces.append(RD.vector(point))
	_collision(root,contract_faces,"ExplicitCollisionContract_"+id)
	for p in content.get("common_instances",[]):
		if not _add_native(root,p): root.free(); return false
	for box in content.get("boxes",[]): _add_box(root,box)
	add_child(root)
	loaded[id] = root
	total_terrain_faces += int(record.face_count)
	total_contract_faces += contract_faces.size()/3
	return true

func _asset(key: String) -> Dictionary:
	if asset_cache.has(key): return asset_cache[key]
	var record: Dictionary = index.common_assets[key]
	var result: Dictionary = RD.read(_path(record.render_path))
	if result.has("error") or result.get("sha256","") != record.render_sha256:
		_fail("Native asset identity failure: " + key)
		return {}
	asset_cache[key] = result.data
	return result.data

func _flatten(node: Node3D, transform_m: Transform3D, vertices: PackedVector3Array, normals: PackedVector3Array, colors: PackedColorArray) -> void:
	var tr := transform_m * node.transform
	if node is MeshInstance3D:
		var ar: Array = node.mesh.surface_get_arrays(0)
		var color: Color = node.mesh.surface_get_material(0).albedo_color
		for i in ar[Mesh.ARRAY_VERTEX].size():
			vertices.append(tr*ar[Mesh.ARRAY_VERTEX][i])
			normals.append(tr.basis*ar[Mesh.ARRAY_NORMAL][i])
			colors.append(color)
	for child in node.get_children():
		if child is Node3D: _flatten(child,tr,vertices,normals,colors)

func _native_mesh(data: Dictionary, override: Dictionary) -> ArrayMesh:
	var copy: Dictionary = data.duplicate(false)
	copy.materials = data.materials.duplicate(true)
	for key in override:
		if copy.materials.has(key): copy.materials[key] = override[key]
	var root: Node3D = RD.build(copy)
	var vertices := PackedVector3Array(); var normals := PackedVector3Array(); var colors := PackedColorArray()
	_flatten(root,Transform3D.IDENTITY,vertices,normals,colors)
	root.free()
	var ar: Array=[];ar.resize(Mesh.ARRAY_MAX)
	ar[Mesh.ARRAY_VERTEX]=vertices;ar[Mesh.ARRAY_NORMAL]=normals;ar[Mesh.ARRAY_COLOR]=colors
	var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,ar)
	var mat:=StandardMaterial3D.new();mat.vertex_color_use_as_albedo=true;mat.roughness=1;mat.metallic_specular=0
	mesh.surface_set_material(0,mat)
	return mesh

func _pose(p: Dictionary) -> Transform3D:
	var basis := Basis(Vector3.UP,float(p.get("yaw_rad",0)))
	if p.has("transform") and p.transform.has("basis"):
		var rows: Array = p.transform.basis
		basis = Basis(RD.vector(rows[0]),RD.vector(rows[1]),RD.vector(rows[2])).transposed()
	return Transform3D(basis,RD.vector(p.position_m))

func _add_native(parent: Node3D, p: Dictionary) -> bool:
	var key: String = str(p.asset_key)
	var data := _asset(key)
	if data.is_empty(): return false
	var id := str(p.get("id",p.get("instance_id","unknown")))
	var pose := _pose(p)
	if not disabled.has(id) and bool(p.get("collision_enabled",true)):
		if not shape_cache.has(key):
			var faces:=PackedVector3Array()
			var groups: Array=data.groups.duplicate()
			for part in data.get("rigid_parts",[]):groups.append_array(part.groups)
			for group in groups:
				for quad in group.quads:
					for j in RD.TRIANGLE_ORDER: faces.append(RD.vector(quad[j]))
			var shape:=ConcavePolygonShape3D.new();shape.backface_collision=false;shape.set_faces(faces);shape_cache[key]=shape
		var body:=StaticBody3D.new();body.transform=pose;body.collision_layer=1;body.collision_mask=0;body.set_meta("source_id",id)
		var collision:=CollisionShape3D.new();collision.shape=shape_cache[key];body.add_child(collision);parent.add_child(body)
	if render_enabled:
		var override: Dictionary = p.get("palette_override",{})
		var palette_key := key+"/"+JSON.stringify(override)
		if not mesh_cache.has(palette_key):mesh_cache[palette_key]=_native_mesh(data,override)
		var node:=MeshInstance3D.new();node.mesh=mesh_cache[palette_key];node.transform=pose;parent.add_child(node)
	total_native_loads += 1
	return true

func _add_box(parent: Node3D, box: Dictionary) -> void:
	var pose:=Transform3D(Basis(Vector3.UP,float(box.get("yaw_rad",0))),RD.vector(box.position_m))
	var size:=RD.vector(box.size_m)
	var body:=StaticBody3D.new();body.transform=pose;body.collision_layer=1;body.collision_mask=0
	var shape:=BoxShape3D.new();shape.size=size
	var collision:=CollisionShape3D.new();collision.shape=shape;body.add_child(collision);parent.add_child(body)
	if render_enabled:
		var mesh:=BoxMesh.new();mesh.size=size;mesh.material=_material(str(box.material))
		var node:=MeshInstance3D.new();node.mesh=mesh;node.transform=pose;parent.add_child(node)

func debug_state() -> Dictionary:
	return {"ready":ready_for_movement,"error":error,"tile_index_sha256":index_sha256,"active_cell":[active_cell.x,active_cell.y],"loaded_owners":loaded.keys(),"load_events":load_events,"native_asset_cache":asset_cache.size(),"palette_mesh_cache":mesh_cache.size(),"native_loads_cumulative":total_native_loads,"terrain_faces_loaded_cumulative":total_terrain_faces,"contract_faces_loaded_cumulative":total_contract_faces,"world_coordinates_unchanged":true,"render_enabled":render_enabled}
