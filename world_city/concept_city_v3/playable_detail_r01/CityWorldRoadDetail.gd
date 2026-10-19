extends "res://CityWorldSurfaces.gd"
## Hash-bound public traffic surfaces only. Original physics stays authoritative.
const RoadSource=preload("res://RoadSurfaceSource.gd")
var road_source=RoadSource.new()
var road_catalog: Dictionary={}
var road_nodes: Dictionary={}
var road_binaries: Dictionary={}
var road_material: ShaderMaterial
var road_last:=Vector3(INF,INF,INF)
var road_last_owners:=-1
var road_elapsed:=0.0
var road_stats: Dictionary={"whole_city_upgrade_complete":false,"active_modules":0}

func configure(index_path: String,root: String,enable_render: bool=true) -> String:
	var problem:=super.configure(index_path,root,enable_render)
	if not problem.is_empty():return problem
	var parsed: Variant=JSON.parse_string(FileAccess.get_file_as_string("res://road_catalog.json"))
	if not parsed is Dictionary or parsed.get("schema")!="riverstone.city.road_detail_catalog.v1":return _fail("Invalid road detail catalog")
	road_catalog=parsed
	if road_catalog.source_city_index_sha256!=index_sha256:return _fail("Road detail source index mismatch")
	var bytes:=_read_verified(road_catalog.policy_path,road_catalog.policy_sha256)
	if not error.is_empty():return error
	if not road_source.configure(JSON.parse_string(bytes.get_string_from_utf8()),index,index_sha256):return _fail(road_source.error)
	road_material=ShaderMaterial.new();road_material.shader=Transition
	return ""

func update_near_detail(observer: Vector3,delta: float) -> void:
	super.update_near_detail(observer,delta)
	if not render_enabled or not error.is_empty():return
	road_elapsed+=delta
	if road_elapsed<float(road_catalog.update_seconds):return
	road_elapsed=0
	if observer.distance_to(road_last)<float(road_catalog.observer_refresh_distance_m) and loaded.size()==road_last_owners:return
	road_last=observer;road_last_owners=loaded.size()
	var started:=Time.get_ticks_usec();var nearby: Array=[];var needed: Dictionary={}
	for key in road_catalog.eligible_source_bounds:
		if not loaded.has(key):continue
		var bound: Dictionary=road_catalog.eligible_source_bounds[key]
		var low:=RD.vector(bound.min);var high:=RD.vector(bound.max)
		if observer.distance_to(observer.clamp(low,high))>12:continue
		nearby.append(key);needed[key]=true
	for key in road_binaries.keys():
		if not needed.has(key):road_binaries.erase(key)
	nearby.sort()
	var faces: Array=[];var bytes_held:=0;var face_budget_truncated:=false
	for bytes in road_binaries.values():bytes_held+=bytes.size()
	for key in nearby:
		var bytes: PackedByteArray
		if road_binaries.has(key):bytes=road_binaries[key]
		else:
			bytes=_read_verified(tiles[key].terrain_path,tiles[key].terrain_sha256)
			if not error.is_empty():return
			if bytes_held+bytes.size()<=int(road_catalog.binary_cache_budget_bytes):road_binaries[key]=bytes;bytes_held+=bytes.size()
		var result: Dictionary=road_source.near_faces_for_tile(key,bytes,observer,12,4096)
		if result.has("error"):_fail(result.error);return
		faces.append_array(result.faces)
		if faces.size()>4096:faces.resize(4096);face_budget_truncated=true;break
	var plan: Dictionary=road_source.plan_local_modules(faces,observer,10,256,120)
	if plan.has("error"):_fail(plan.error);return
	var groups: Dictionary={};var farthest:=0.0
	var base_color: Color=RD.color_value(index.get("render_materials",index.materials).get("road","85817c"))*1.4
	base_color.a=1
	for p in plan.modules:
		var module_id:="surface_safe_offset_r01_paving_s"+str(p.seed)
		if not groups.has(module_id):groups[module_id]=[]
		groups[module_id].append(p)
		farthest=maxf(farthest,(p.transform*Vector3(.5,.5,0)).distance_to(observer))
	var fade_end:=minf(9.0,maxf(1.0,farthest-.8)) if plan.truncated else 9.0
	road_material.set_shader_parameter("detail_observer",observer)
	road_material.set_shader_parameter("fade_end_m",fade_end)
	road_material.set_shader_parameter("fade_start_m",fade_end*.55)
	for key in road_nodes:
		if not groups.has(key):road_nodes[key].visible=false
	var quads:=0
	for key in groups:
		var mesh:=_surface_module(key)
		if mesh==null:return
		var node: MultiMeshInstance3D
		if road_nodes.has(key):node=road_nodes[key]
		else:
			node=MultiMeshInstance3D.new();node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF;node.material_override=road_material;add_child(node);road_nodes[key]=node
		var multi:=MultiMesh.new();multi.transform_format=MultiMesh.TRANSFORM_3D;multi.use_colors=true;multi.use_custom_data=true;multi.mesh=mesh;multi.instance_count=groups[key].size()
		for n in groups[key].size():multi.set_instance_transform(n,groups[key][n].transform);multi.set_instance_color(n,base_color);multi.set_instance_custom_data(n,Color(base_color.r/1.4,base_color.g/1.4,base_color.b/1.4,1))
		node.multimesh=multi;node.visible=true
		quads+=groups[key].size()*int(surface_catalog.modules[key].quads)
	road_stats={"active_modules":plan.modules.size(),"face_budget_truncated":face_budget_truncated,"submitted_quads":quads,"source_faces":faces.size(),"source_tiles":nearby,"binary_cache_bytes":bytes_held,"plan_usec":plan.elapsed_usec,"wall_ms":(Time.get_ticks_usec()-started)/1000.0,"truncated":plan.truncated,"truncated_reason":plan.reason,"collision_change":false,"maximum_visual_collision_difference_m":.0375,"whole_city_upgrade_complete":false,"supported_public_source_only":true}

func debug_state() -> Dictionary:
	var value:=super.debug_state();value.public_paving=road_stats.duplicate(true);return value
