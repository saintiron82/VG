extends "res://CityWorldDetail.gd"
## Bounded native-wall relief layer, assembled from common-compiled voxel modules.
## The sealed city, collisions, and near-house master remain independent inputs.
const Patch=preload("res://SurfacePatchMesh.gd")
const Transition=preload("res://SurfaceTransition.gdshader")
var surface_catalog: Dictionary={}
var surface_records: Dictionary={}
var surface_faces: Dictionary={}
var surface_modules: Dictionary={}
var surface_feature_regions: Dictionary={}
var surface_masked_faces: Dictionary={}
var surface_revised_faces: Dictionary={}
var surface_nodes: Dictionary={}
var surface_last:=Vector3(INF,INF,INF)
var surface_last_owners:=-1
var surface_last_detail_revision:=-1
var surface_elapsed:=0.0
var surface_material: ShaderMaterial
var surface_stats: Dictionary={"active_modules":0,"candidate_modules":0,"rebuilds":0,"face_cache_assets":0,"whole_city_upgrade_complete":false}

func configure(index_path: String,root: String,enable_render: bool=true) -> String:
	var problem:=super.configure(index_path,root,enable_render)
	if not problem.is_empty():return problem
	var parsed: Variant=JSON.parse_string(FileAccess.get_file_as_string("res://surface_catalog.json"))
	if not parsed is Dictionary or parsed.get("schema")!="riverstone.city.shared_surface_catalog.v1":return _fail("Invalid surface catalog")
	surface_catalog=parsed
	surface_material=ShaderMaterial.new();surface_material.shader=Transition
	if surface_catalog.source_city_index_sha256!=index_sha256:return _fail("Surface catalog city binding mismatch")
	for key in surface_catalog.assets:
		if not index.common_assets.has(key) or surface_catalog.assets[key].source_render_sha256!=index.common_assets[key].render_sha256:return _fail("Surface asset binding mismatch: "+key)
	for key in detail_catalog.assets:
		var entry: Dictionary=detail_catalog.assets[key]
		if not entry.has("surface_feature_mask_path"):continue
		var bytes:=_read_verified(entry.surface_feature_mask_path,entry.surface_feature_mask_sha256)
		if not error.is_empty():return error
		var mask: Variant=JSON.parse_string(bytes.get_string_from_utf8())
		if not mask is Dictionary or mask.get("schema","")!="riverstone.surface.feature_exclusions.v1" or mask.get("asset_key","")!=key or mask.get("source_master_sha256","")!=index.common_assets[key].master_sha256 or mask.get("source_render_sha256","")!=index.common_assets[key].render_sha256 or mask.get("composed_render_sha256","")!=entry.sha256 or not mask.get("all_source_operation_hashes_match",false) or mask.get("collision_changed",true) or mask.get("mesh_changed",true):return _fail("Unbound actual surface feature envelope: "+key)
		if entry.has("source_revision"):
			if mask.get("source_operations_master_sha256","")!=entry.source_revision.get("revised_master_sha256","") or mask.get("source_revision_sha256","")!=entry.get("source_revision_sha256","") or not _json_equivalent(mask.get("source_revision",{}),entry.source_revision) or not _validate_source_revision(key,entry):return _fail("Unverified revised wall feature source: "+key)
		for region in mask.get("regions",[]):
			if not region.has("min") or not region.has("max"):return _fail("Missing feature envelope bounds")
			var extent:=RD.vector(region.max)-RD.vector(region.min)
			if extent.x<=0 or extent.y<=0 or extent.z<=0:return _fail("Invalid feature envelope bounds")
		surface_feature_regions[key]=mask.regions
	return ""

func _add_native(parent: Node3D,p: Dictionary) -> bool:
	if not super._add_native(parent,p):return false
	var key:=str(p.asset_key)
	if not render_enabled or not surface_catalog.get("assets",{}).has(key):return true
	var id:=str(p.get("id",p.get("instance_id","unknown")))
	var bound: Dictionary=index.common_assets[key].bounds
	surface_records[id]={"owner":weakref(parent),"asset":key,"pose":_pose(p),"palette":p.get("palette_override",{}),"bounds":AABB(RD.vector(bound.min),RD.vector(bound.max)-RD.vector(bound.min))}
	return true

func _surface_faces_for(key: String) -> Array:
	if surface_faces.has(key):return surface_faces[key]
	var faces: Array=[];var data: Dictionary=_asset(key)
	var rules: Dictionary=surface_catalog.assets[key].slots
	for group in data.groups:
		if not rules.has(group.material):continue
		var treatment: String=str(rules[group.material])
		if treatment not in ["ashlar","rubble","planks"]:continue
		for quad in group.quads:
			var face:=Patch.rectangular_face(quad,.25)
			if face.is_empty() or absf(face.n.y)>.001:continue
			face.material=group.material;face.kind=treatment;face.number=faces.size()
			faces.append(face)
	surface_faces[key]=faces;surface_stats.face_cache_assets=surface_faces.size()
	return faces

func _surface_faces_for_owner(id: String,key: String) -> Array:
	var base:=_surface_faces_for(key)
	if not surface_feature_regions.has(key) or not detail_records.has(id) or detail_records[id].fine==null:return base
	if not surface_masked_faces.has(key):
		var clipped: Array=[]
		for face in base:clipped.append_array(Patch.subtract_feature_regions(face,surface_feature_regions[key]))
		surface_masked_faces[key]=clipped
	return surface_masked_faces[key]

func _surface_module(id: String) -> ArrayMesh:
	if surface_modules.has(id):return surface_modules[id]
	var entry: Dictionary=surface_catalog.modules[id]
	var result:=RD.read(_path(entry.path))
	if result.has("error") or result.get("sha256","")!=entry.sha256:_fail("Shared surface module identity failure: "+id);return null
	if RD.vector(result.data.bounds.min).z<-.037501 or RD.vector(result.data.bounds.max).z>.000001:_fail("Unsafe surface envelope: "+id);return null
	var mesh:=Patch.module_mesh(result.data);surface_modules[id]=mesh
	return mesh

func update_near_detail(observer: Vector3,delta: float) -> void:
	super.update_near_detail(observer,delta)
	if not render_enabled or not error.is_empty():return
	surface_elapsed+=delta
	if surface_elapsed<float(surface_catalog.get("update_seconds",.5)):return
	surface_elapsed=0
	if observer.distance_to(surface_last)<.75 and loaded.size()==surface_last_owners and detail_revision==surface_last_detail_revision:return
	var started:=Time.get_ticks_usec();surface_last=observer;surface_last_owners=loaded.size();surface_last_detail_revision=detail_revision
	var candidates: Array=[];var radius:=float(surface_catalog.radius_m)
	for id in surface_records.keys():
		var r: Dictionary=surface_records[id]
		if not is_instance_valid(r.owner.get_ref()):surface_records.erase(id);continue
		if detail_records.has(id) and detail_records[id].fine!=null and not detail_catalog.assets[r.asset].get("retain_wall_surface_relief",false) and not detail_catalog.assets[r.asset].has("replace_source_groups"):continue
		var local: Vector3=r.pose.affine_inverse()*observer
		var bounds: AABB=r.bounds
		if local.distance_to(local.clamp(bounds.position,bounds.end))>radius:continue
		for face in _surface_faces_for_owner(str(id),r.asset):
			if face.n.dot(local)-float(face.plane)<0:continue # no hidden/back-facing interior patch
			var patches:=Patch.trimmed_patches(face,local,radius)
			if patches.is_empty():patches=Patch.full_patches(face,local,radius)
			for patch in patches:
				if not surface_feature_regions.has(r.asset) and _patch_intersects_active_window(str(id),patch):continue
				var seed_token:=surface_seed_token(str(id),face,patch)
				var trim_key:=str(patch.get("trim_key","w4_h4_x0_y0"))
				var ids: Array=[]
				if trim_key=="w4_h4_x0_y0":ids=surface_catalog.by_kind[face.kind]
				else:ids=surface_catalog.get("by_kind_trim",{}).get(face.kind,{}).get(trim_key,[])
				if ids.is_empty():continue # no geometry scaling or unsupported fallback
				patch.module=ids[posmod(seed_token.hash(),ids.size())];patch.pose=r.pose*patch.transform
				patch.base_color=RD.color_value(r.palette.get(face.material,_asset(r.asset).materials[face.material]))
				patch.color=patch.base_color*1.4
				patch.color.a=1;patch.source=id;patch.token=seed_token+"/"+trim_key;candidates.append(patch)
	candidates.sort_custom(func(a,b):return a.distance<b.distance if a.distance!=b.distance else a.token<b.token)
	surface_stats.candidate_modules=candidates.size()
	var groups: Dictionary={};var count:=0;var quads:=0
	var fade_end:=radius-1.0
	for patch in candidates:
		var q:=int(surface_catalog.modules[patch.module].quads)
		if count>=int(surface_catalog.max_modules) or quads+q>int(surface_catalog.max_submitted_quads):break
		if not groups.has(patch.module):groups[patch.module]=[]
		groups[patch.module].append(patch);count+=1;quads+=q
	if count<candidates.size() and count>0:fade_end=minf(fade_end,float(candidates[count-1].distance)-1.0)
	fade_end=maxf(fade_end,1.0)
	surface_material.set_shader_parameter("detail_observer",observer)
	surface_material.set_shader_parameter("fade_end_m",fade_end)
	surface_material.set_shader_parameter("fade_start_m",fade_end*.55)
	for id in surface_nodes:
		if not groups.has(id):surface_nodes[id].visible=false
	for id in groups:
		var mesh:=_surface_module(id)
		if mesh==null:return
		var node: MultiMeshInstance3D
		if surface_nodes.has(id):node=surface_nodes[id]
		else:
			node=MultiMeshInstance3D.new();node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF;node.material_override=surface_material;add_child(node);surface_nodes[id]=node
		var multi:=MultiMesh.new();multi.transform_format=MultiMesh.TRANSFORM_3D;multi.use_colors=true;multi.use_custom_data=true;multi.mesh=mesh;multi.instance_count=groups[id].size()
		for i in groups[id].size():multi.set_instance_transform(i,groups[id][i].pose);multi.set_instance_color(i,groups[id][i].color);multi.set_instance_custom_data(i,groups[id][i].base_color)
		node.multimesh=multi;node.visible=true
	surface_stats.active_modules=count;surface_stats.submitted_quads=quads;surface_stats.rebuilds+=1;surface_stats.last_update_ms=(Time.get_ticks_usec()-started)/1000.0
	surface_stats.mesh_resources=surface_modules.size();surface_stats.multimesh_groups=groups.size();surface_stats.original_collisions_unchanged=true;surface_stats.max_visual_projection_m=.0375
	surface_stats.border_trim_pending=false;surface_stats.unsupported_nonquarter_edges_fall_back_to_contained_full_modules=true;surface_stats.native_vertical_walls_only=true
	surface_stats.transition={"type":"source_color_contrast_fade_then_narrow_opaque_dither","start_m":fade_end*.55,"end_m":fade_end,"dither_band_m":.6,"max_offset_m":.0375,"new_collision":false}

func debug_state() -> Dictionary:
	var value:=super.debug_state();value.shared_surfaces=surface_stats.duplicate(true);return value

static func surface_seed_token(instance: String,face: Dictionary,patch: Dictionary) -> String:
	# Preserve exact support plane. Adjacent quads on the same plane share a seed.
	return JSON.stringify([instance,face.kind,face.material,face.n.x,face.n.y,face.n.z,face.plane,patch.x,patch.y])

func _patch_intersects_active_window(id: String,patch: Dictionary) -> bool:
	if not detail_records.has(id):return false
	var record: Dictionary=detail_records[id]
	if record.fine==null or not is_instance_valid(record.fine.get_ref()):return false
	var entry: Dictionary=detail_catalog.assets[record.asset]
	return patch_intersects_regions(patch,entry.get("surface_exclusion_regions",entry.get("window_regions",[])))

static func patch_intersects_regions(patch: Dictionary,regions: Array) -> bool:
	var size: Vector2=patch.get("size",Vector2.ONE)
	var pose: Transform3D=patch.transform
	var low:=Vector3(INF,INF,INF);var high:=Vector3(-INF,-INF,-INF)
	for x in [0.0,size.x]:
		for y in [0.0,size.y]:
			for z in [-.0375,0.0]:
				var point:=pose*Vector3(x,y,z);low=low.min(point);high=high.max(point)
	# Reject a whole module at the finite cavity edge. Do not scale, crop or refill
	# a window with a wall overlay, including its outward 3.75cm relief envelope.
	for region in regions:
		var a:=RD.vector(region.min);var b:=RD.vector(region.max)
		if low.x<=b.x+.00001 and high.x>=a.x-.00001 and low.y<=b.y+.00001 and high.y>=a.y-.00001 and low.z<=b.z+.00001 and high.z>=a.z-.00001:return true
	return false
