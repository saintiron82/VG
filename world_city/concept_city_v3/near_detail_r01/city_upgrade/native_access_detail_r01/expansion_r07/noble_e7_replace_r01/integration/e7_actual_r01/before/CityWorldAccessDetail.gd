extends "res://CityWorldRoadDetail.gd"
## Source-native static stair/deck surface detail. No physics is added or moved.
const AccessProof=preload("res://validation/NativeAccessProof.gd")
var access_config: Dictionary={}
var access_assets: Dictionary={}
var access_module_data: Dictionary={}
var access_records: Dictionary={}
var access_meshes: Dictionary={}
var access_nodes: Dictionary={}
var access_material: ShaderMaterial
var access_last:=Vector3(INF,INF,INF)
var access_elapsed:=0.0
var access_stats: Dictionary={"active_modules":0,"collision_change":false,"whole_city_upgrade_complete":false}

func configure(index_path: String,root: String,enable_render: bool=true) -> String:
	var problem:=super.configure(index_path,root,enable_render)
	if not problem.is_empty():return problem
	var c: Variant=JSON.parse_string(FileAccess.get_file_as_string("res://native_access_catalog.json"))
	if not c is Dictionary or c.get("schema")!="riverstone.native_access_detail.runtime.v1" or c.get("source_city_index_sha256")!=index_sha256 or c.get("collision_change",true):return _fail("Unbound native access catalog")
	access_config=c
	var bytes:=_read_verified(c.source_plan_path,c.source_plan_sha256)
	if not error.is_empty():return error
	var plan: Variant=JSON.parse_string(bytes.get_string_from_utf8())
	if not plan is Dictionary or plan.get("schema")!="riverstone.native_access_detail.plan.v1" or plan.get("source_city_index_sha256")!=index_sha256:return _fail("Unbound native access plan")
	bytes=_read_verified(c.module_catalog_path,c.module_catalog_sha256)
	if not error.is_empty():return error
	var modules: Variant=JSON.parse_string(bytes.get_string_from_utf8())
	if not modules is Dictionary or modules.get("source_plan_sha256")!=c.source_plan_sha256 or modules.get("original_collision_unchanged")!=true:return _fail("Unbound native access modules")
	for row in modules.modules:access_module_data[row.id]=row
	var proof_cache: Dictionary={}
	for a in plan.assets:
		if plan.get("runtime_projection",false):
			var proof_error:=AccessProof.asset_error(a,repo_root,proof_cache)
			if not proof_error.is_empty():return _fail(proof_error)
		var key: String=a.asset_key
		if not index.common_assets.has(key) or index.common_assets[key].master_sha256!=a.source_master_sha256 or index.common_assets[key].render_sha256!=a.source_render_sha256 or not a.existing_collision_unchanged:return _fail("Native access source mismatch "+key)
		for p in a.placements:
			if not access_module_data.has(p.module_key) or p.get("collision_changed",true):return _fail("Unbound native access placement")
		access_assets[key]=a
	access_material=ShaderMaterial.new();access_material.shader=Transition
	return ""

func _add_native(parent: Node3D,p: Dictionary) -> bool:
	if not super._add_native(parent,p):return false
	var key:=str(p.asset_key)
	if render_enabled and access_assets.has(key):
		access_records[str(p.id)]={"owner":weakref(parent),"asset":key,"pose":_pose(p)}
		access_last=Vector3(INF,INF,INF)
	return true

func access_pose(t: Dictionary) -> Transform3D:
	# Master basis is row-major; Godot Basis constructor takes columns.
	var b: Array=t.basis
	return Transform3D(Basis(Vector3(b[0][0],b[1][0],b[2][0]),Vector3(b[0][1],b[1][1],b[2][1]),Vector3(b[0][2],b[1][2],b[2][2])),RD.vector(t.translation))

func update_near_detail(observer: Vector3,delta: float) -> void:
	super.update_near_detail(observer,delta)
	if not render_enabled or not error.is_empty():return
	access_elapsed+=delta
	if access_elapsed<float(access_config.update_seconds):return
	access_elapsed=0
	for id in access_records.keys():
		if not is_instance_valid(access_records[id].owner.get_ref()):access_records.erase(id);access_last=Vector3(INF,INF,INF)
	if observer.distance_to(access_last)<float(access_config.observer_refresh_distance_m):return
	access_last=observer
	var candidates: Array=[]
	for id in access_records.keys():
		var record: Dictionary=access_records[id]
		if not is_instance_valid(record.owner.get_ref()):access_records.erase(id);continue
		var source: Dictionary=access_assets[record.asset]
		var color: Color=RD.color_value(_asset(record.asset).materials[source.rule.material]);color.a=1
		for p in source.placements:
			var tr: Transform3D=record.pose*access_pose(p.transform)
			var m: Dictionary=access_module_data[p.module_key]
			var center: Vector3=tr*Vector3(float(m.trim.width_m)*.5,float(m.trim.height_m)*.5,0)
			var dist:=center.distance_to(observer)
			if dist<=float(access_config.radius_m):candidates.append({"key":p.module_key,"transform":tr,"distance":dist,"color":color,"owner":id})
	candidates.sort_custom(func(a,b):return a.distance<b.distance)
	var truncated:=candidates.size()>int(access_config.maximum_active_modules)
	if truncated:candidates.resize(int(access_config.maximum_active_modules))
	var groups: Dictionary={};var used_bytes:=0;var budget_skips:=0
	for p in candidates:
		var key: String=p.key
		if not groups.has(key):
			var bytes:=int(access_module_data[key].quads)*144
			if used_bytes+bytes>int(access_config.maximum_mesh_bytes):budget_skips+=1;continue
			groups[key]=[];used_bytes+=bytes
		groups[key].append(p)
	for key in access_nodes.keys():
		if not groups.has(key):access_nodes[key].free();access_nodes.erase(key);access_meshes.erase(key)
	access_material.set_shader_parameter("detail_observer",observer)
	access_material.set_shader_parameter("fade_start_m",float(access_config.fade_start_m))
	access_material.set_shader_parameter("fade_end_m",float(access_config.fade_end_m))
	var active:=0;var quads:=0
	for key in groups:
		if not access_meshes.has(key):
			var entry: Dictionary=access_module_data[key];var result:=RD.read(_path(entry.render_path))
			if result.has("error") or result.get("sha256")!=entry.render_sha256:_fail("Native access module hash mismatch");return
			if RD.vector(result.data.bounds.min).z<-.037501 or RD.vector(result.data.bounds.max).z>.000001:_fail("Native access detail projection exceeded");return
			access_meshes[key]=Patch.module_mesh(result.data)
		var node: MultiMeshInstance3D
		if access_nodes.has(key):node=access_nodes[key]
		else:node=MultiMeshInstance3D.new();node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF;node.material_override=access_material;add_child(node);access_nodes[key]=node
		var multi:=MultiMesh.new();multi.transform_format=MultiMesh.TRANSFORM_3D;multi.use_colors=true;multi.use_custom_data=true;multi.mesh=access_meshes[key];multi.instance_count=groups[key].size()
		for i in groups[key].size():
			var p: Dictionary=groups[key][i];var color: Color=p.color
			var bright:=color*1.4;bright.a=1
			multi.set_instance_transform(i,p.transform);multi.set_instance_color(i,bright);multi.set_instance_custom_data(i,color)
		node.multimesh=multi;active+=groups[key].size();quads+=groups[key].size()*int(access_module_data[key].quads)
	access_stats={"active_modules":active,"mesh_resources":access_meshes.size(),"geometry_estimated_bytes":used_bytes,"submitted_quads":quads,"source_records":access_records.size(),"truncated":truncated,"budget_skips":budget_skips,"collision_change":false,"maximum_additional_visual_offset_from_source_m":.0375,"existing_source_proxy_contracts_unchanged":true,"whole_city_upgrade_complete":false}

func debug_state() -> Dictionary:
	var result:=super.debug_state();result.native_access=access_stats.duplicate(true);return result
