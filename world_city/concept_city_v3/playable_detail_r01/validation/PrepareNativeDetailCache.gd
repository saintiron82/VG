extends SceneTree
## Offline transport cache of the exact common-render geometry. Never new geometry.
const World=preload("res://CityWorldDetail.gd")
func _init() -> void:call_deferred("run")
func own(node: Node,scene_root: Node) -> void:
	for child in node.get_children():child.owner=scene_root;own(child,scene_root)
func geometry_digest(node: Node) -> String:
	var hash:=HashingContext.new();hash.start(HashingContext.HASH_SHA256)
	var queue: Array=[node]
	while not queue.is_empty():
		var current: Node=queue.pop_front()
		if current is MeshInstance3D:
			var ar: Array=current.mesh.surface_get_arrays(0)
			hash.update(ar[Mesh.ARRAY_VERTEX].to_byte_array());hash.update(ar[Mesh.ARRAY_NORMAL].to_byte_array())
			var slot: String=str(current.get_meta("material_slot",""))
			if not slot.is_empty():hash.update(slot.to_utf8_buffer())
		queue.append_array(current.get_children())
	return hash.finish().hex_encode()
func run() -> void:
	var world:=World.new();root.add_child(world)
	var problem:=world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),true)
	if not problem.is_empty():quit(2);return
	var directory:="res://generated/native_near_r03"
	var selected: Array=[]
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="):directory=argument.trim_prefix("--output=")
		if argument.begins_with("--assets="):selected=Array(argument.trim_prefix("--assets=").split(","))
	for key in selected:
		if not world.detail_catalog.assets.has(key):push_error("Requested native asset missing from detail catalog: "+str(key));quit(4);return
	if FileAccess.file_exists(directory.path_join("manifest.json")):push_error("Preserve existing native cache: choose a new output revision");quit(3);return
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(directory))
	var report:={"schema":"riverstone.native_detail_transport.v1","source_city_index_sha256":world.index_sha256,"assets":{},"all_pass":true}
	for key in world.detail_catalog.assets:
		if not selected.is_empty() and key not in selected:continue
		var entry: Dictionary=world.detail_catalog.assets[key]
		# Always independently build from canonical common-render transport.
		entry.erase("native_scene_path");entry.erase("native_scene_sha256")
		var cache: Dictionary=world._cache_asset(key)
		if cache.is_empty():report.all_pass=false;continue
		var prefab: Node3D=cache.prefab
		prefab.set_meta("composition_contract_sha256",world.composition_contract_hash(entry));prefab.set_meta("source_render_sha256",entry.sha256);prefab.set_meta("material_definitions",cache.materials);prefab.set_meta("geometry_estimated_bytes",cache.bytes)
		own(prefab,prefab)
		var fingerprint:=geometry_digest(prefab);var scene:=PackedScene.new();var status:=scene.pack(prefab)
		var path:=directory.path_join(str(key)+".scn")
		if status==OK:status=ResourceSaver.save(scene,path,ResourceSaver.FLAG_COMPRESS)
		var loaded:=load(path) as PackedScene
		var rebuilt: Node3D=loaded.instantiate() if loaded!=null else null
		var valid: bool=status==OK and rebuilt!=null and geometry_digest(rebuilt)==fingerprint and rebuilt.get_meta("source_render_sha256")==entry.sha256
		if rebuilt!=null:rebuilt.free()
		var file:=FileAccess.open(path,FileAccess.READ)
		report.assets[key]={"source_render_sha256":entry.sha256,"binding_inputs":world.composition_contract_data(entry),"composition_contract_sha256":world.composition_contract_hash(entry),"native_scene_path":path,"native_scene_sha256":FileAccess.get_sha256(path),"native_scene_bytes":file.get_length() if file else 0,"geometry_fingerprint":fingerprint,"geometry_estimated_bytes":cache.bytes,"exact_reload_pass":valid}
		report.all_pass=report.all_pass and valid
		world._evict(key)
	if report.assets.is_empty():report.all_pass=false
	var out:=FileAccess.open(directory.path_join("manifest.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 3)
