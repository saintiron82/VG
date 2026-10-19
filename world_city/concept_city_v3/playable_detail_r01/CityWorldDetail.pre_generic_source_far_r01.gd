extends "res://CityWorld.gd"
## Opt-in quality layer. Original world loading, placement and collision are inherited.
## Only explicit source-derived closed-door corrections add physical geometry.
var detail_catalog: Dictionary={}
var detail_catalog_path: String="res://near_catalog.json"
var detail_records: Dictionary={}
var detail_cache: Dictionary={}
var detail_materials: Dictionary={}
var detail_events: Array=[]
var detail_elapsed:=0.0
var detail_cached_bytes:=0
var detail_clock:=0
var detail_builds:=0
var detail_evictions:=0
var detail_deferred:=0
var detail_revision:=0
var composed_contracts: Dictionary={}
var revised_far_meshes: Dictionary={}
var revised_far_source_data: Dictionary={}

func configure(index_path: String, root: String, enable_render: bool=true) -> String:
	var problem:=super.configure(index_path,root,enable_render)
	if not problem.is_empty():return problem
	var value: Variant=JSON.parse_string(FileAccess.get_file_as_string(detail_catalog_path))
	if not value is Dictionary or value.get("schema")!="riverstone.city.near_detail_catalog.v1":return _fail("Invalid near-detail catalog")
	detail_catalog=value
	if detail_catalog.source_city_index_sha256!=index_sha256:return _fail("Near-detail city binding mismatch")
	for key in detail_catalog.assets:
		if not index.common_assets.has(key) or detail_catalog.assets[key].source_master_sha256!=index.common_assets[key].master_sha256:return _fail("Near-detail master binding mismatch: "+key)
	return ""

func _add_native(parent: Node3D,p: Dictionary) -> bool:
	var start:=parent.get_child_count()
	if not super._add_native(parent,p):return false
	var key:=str(p.asset_key)
	if not detail_catalog.get("assets",{}).has(key):return true
	var id:=str(p.get("id",p.get("instance_id","unknown")))
	var entry: Dictionary=detail_catalog.assets[key]
	if not disabled.has(id) and bool(p.get("collision_enabled",true)):
		for repair in entry.get("collision_repairs",[]):
			var body:=StaticBody3D.new();body.transform=_pose(p)*_local_transform(repair.get("transform",{}));body.collision_layer=1;body.collision_mask=0;body.set_meta("source_id",id+"/"+str(repair.id))
			var shape:=BoxShape3D.new();shape.size=RD.vector(repair.max)-RD.vector(repair.min)
			var node:=CollisionShape3D.new();node.shape=shape;node.position=(RD.vector(repair.max)+RD.vector(repair.min))*.5
			body.add_child(node);parent.add_child(body)
	if render_enabled:
		var coarse: MeshInstance3D=null
		for i in range(start,parent.get_child_count()):
			if parent.get_child(i) is MeshInstance3D:coarse=parent.get_child(i)
		if coarse==null:return _fail("Missing original visual for "+id).is_empty()
		if entry.has("far_visual_contract_path"):
			var revised_mesh: ArrayMesh=_revised_far_mesh(key,p.get("palette_override",{}))
			if revised_mesh==null:return false
			coarse.mesh=revised_mesh
		var bounds: Dictionary=index.common_assets[key].bounds
		var distance_bounds:=AABB(RD.vector(bounds.min),RD.vector(bounds.max)-RD.vector(bounds.min))
		if entry.has("visual_bounds"):
			var fine_bound: Dictionary=entry.visual_bounds
			distance_bounds=distance_bounds.merge(AABB(RD.vector(fine_bound.min),RD.vector(fine_bound.max)-RD.vector(fine_bound.min)))
		detail_records[id]={"owner":weakref(parent),"coarse":weakref(coarse),"fine":null,"asset":key,"pose":_pose(p),"palette":p.get("palette_override",{}),"bounds":distance_bounds,"distance":INF}
	return true

func _revised_far_mesh(key: String,palette: Dictionary) -> ArrayMesh:
	var entry: Dictionary=detail_catalog.assets[key]
	var identity:=str(entry.get("far_visual_contract_sha256",""))+"/"+JSON.stringify(palette)
	if revised_far_meshes.has(identity):return revised_far_meshes[identity]
	if not entry.has("source_revision") or not _validate_composed_contract(key,entry):return null
	var bytes:=_read_verified(str(entry.get("far_visual_contract_path","")),str(entry.get("far_visual_contract_sha256","")))
	if not error.is_empty():return null
	var contract: Variant=JSON.parse_string(bytes.get_string_from_utf8())
	var result:=RD.read(_path(str(entry.get("far_visual_render_path",""))))
	if result.has("error"):_fail(str(result.error));return null
	var problem: String=preload("res://validation/RevisedFarVisualContract.gd").validate(key,entry,index.common_assets[key],contract,result.data,str(result.sha256))
	if not problem.is_empty():_fail("Invalid revised far visual: "+problem);return null
	if contract.get("schema","")=="riverstone.revised_far_visual.v2":
		var proof_bytes:=_read_verified(str(contract.get("union_provenance_path","")),str(contract.get("union_provenance_sha256","")))
		if not error.is_empty():return null
		var proof: Variant=JSON.parse_string(proof_bytes.get_string_from_utf8())
		if not proof is Dictionary or not proof.get("all_geometry_tests_pass",false) or proof.get("asset_key","")!=key or proof.get("render",{}).get("sha256","")!=result.sha256 or proof.get("changed_collision",true):_fail("Invalid source roof union proof");return null
	if not _json_equivalent(result.data.materials,_asset(key).materials):_fail("Far source palette changed");return null
	# Only this visual mesh changes. Source collider cache, pose and public terrain stay untouched.
	var mesh:=_native_mesh(result.data,palette)
	revised_far_meshes[identity]=mesh
	revised_far_source_data[key]=result.data
	return mesh

func _distance(record: Dictionary,observer: Vector3) -> float:
	var local: Vector3=record.pose.affine_inverse()*observer
	var b: AABB=record.bounds
	return local.distance_to(local.clamp(b.position,b.end))

func _release_detail(record: Dictionary) -> void:
	if record.fine!=null:detail_revision+=1
	var coarse: Object=record.coarse.get_ref()
	if is_instance_valid(coarse):coarse.visible=true
	if record.fine!=null:
		var fine: Object=record.fine.get_ref()
		if is_instance_valid(fine):fine.visible=false;fine.queue_free()
	record.fine=null

func _cache_asset(key: String) -> Dictionary:
	if detail_cache.has(key):detail_cache[key].last=detail_clock;return detail_cache[key]
	var entry: Dictionary=detail_catalog.assets[key]
	var need:=int(entry.geometry_estimated_bytes)
	if entry.has("composed_manifest_path") and not _validate_composed_contract(key,entry):return {}
	var active: Dictionary={}
	for r in detail_records.values():
		if r.fine!=null and is_instance_valid(r.fine.get_ref()):active[r.asset]=true
	while detail_cached_bytes+need>int(detail_catalog.cache_budget_vertex_normal_bytes):
		var oldest: String="";var stamp:=2147483647
		for k in detail_cache:
			if not active.has(k) and int(detail_cache[k].last)<stamp:oldest=k;stamp=detail_cache[k].last
		if oldest.is_empty():detail_deferred+=1;return {}
		_evict(oldest)
	var started:=Time.get_ticks_usec()
	if entry.has("native_scene_path"):
		var path:=_path(entry.native_scene_path)
		if FileAccess.get_sha256(path)!=entry.native_scene_sha256:_fail("Near native cache identity mismatch: "+key);return {}
		var packed:=load(path) as PackedScene
		if packed==null:_fail("Unreadable native detail scene: "+key);return {}
		var prefab: Node3D=packed.instantiate()
		if prefab.get_meta("source_render_sha256","")!=entry.sha256 or int(prefab.get_meta("geometry_estimated_bytes",-1))!=need or prefab.get_meta("composition_contract_sha256","")!=composition_contract_hash(entry):
			prefab.free();_fail("Native cache/source binding mismatch: "+key);return {}
		var item: Dictionary={"prefab":prefab,"last":detail_clock,"bytes":need,"materials":prefab.get_meta("material_definitions")}
		detail_cache[key]=item;detail_cached_bytes+=need;detail_builds+=1
		detail_events.append({"event":"build","asset":key,"ms":(Time.get_ticks_usec()-started)/1000.0,"estimated_geometry_bytes":need,"transport":"verified_native_exact_mesh_cache"})
		return item
	var result:=RD.read(_path(entry.render_path))
	if result.has("error") or result.get("sha256","")!=entry.sha256:_fail("Near-detail render identity failure: "+key);return {}
	var data: Dictionary=result.data
	if entry.has("replace_source_groups"):
		data=_compose_replacement(key,data,entry)
		if data.is_empty():return {}
	if int(RD.stats(data).quads)*144!=need:_fail("Near-detail memory contract mismatch: "+key);return {}
	var prefab:=RD.build(data)
	var groups: Array=data.groups
	for i in range(groups.size()):
		prefab.get_child(i).set_meta("material_slot",str(groups[i].material))
		if entry.has("shadow_proxy_path") and str(groups[i].material).begins_with("slate"):prefab.get_child(i).cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if entry.has("shadow_proxy_path"):
		var bytes:=_read_verified(entry.shadow_proxy_path,entry.shadow_proxy_sha256)
		if not error.is_empty():prefab.free();return {}
		_add_shadow_proxy(prefab,JSON.parse_string(bytes.get_string_from_utf8()))
	var item: Dictionary={"prefab":prefab,"last":detail_clock,"bytes":need,"materials":data.materials}
	detail_cache[key]=item;detail_cached_bytes+=need;detail_builds+=1
	detail_events.append({"event":"build","asset":key,"ms":(Time.get_ticks_usec()-started)/1000.0,"estimated_geometry_bytes":need})
	return item

func _compose_replacement(key: String,fine: Dictionary,entry: Dictionary) -> Dictionary:
	# A whole matching near layer must exist before any original group is hidden.
	# Original non-target groups, materials and coordinates are copied unchanged.
	if entry.get("replacement_source_render_sha256","")!=index.common_assets[key].render_sha256:
		_fail("Partial detail source identity mismatch: "+key);return {}
	var original:=_asset(key)
	if original.has("rigid_parts") or fine.has("rigid_parts"):
		_fail("Rigid-part group replacement unsupported: "+key);return {}
	var remove: Dictionary={};var materials: Dictionary={}
	for contract in entry.replace_source_groups:
		var n:=int(contract.group_index)
		if n<0 or n>=original.groups.size() or remove.has(n):
			_fail("Invalid/duplicate original replacement group: "+key);return {}
		var group: Dictionary=original.groups[n]
		if group.material!=contract.material_id or group.quads.size()!=int(contract.quad_count) or not bool(contract.get("complete_source_operation_coverage",false)):
			_fail("Incomplete/mismatched replacement group: "+key);return {}
		remove[n]=true;materials[group.material]=true
	if remove.is_empty():_fail("Empty partial replacement contract");return {}
	if not _authorize_added_materials(key,entry,materials):return {}
	for group in fine.groups:
		if not materials.has(group.material):_fail("Near layer contains uncontracted material: "+key);return {}
	var combined: Dictionary=fine.duplicate(false)
	combined.groups=fine.groups.duplicate();combined.materials=original.materials.duplicate(true)
	for material in fine.materials:
		if not original.materials.has(material) or RD.color_value(fine.materials[material])!=RD.color_value(original.materials[material]):
			_fail("Partial layer changes source material palette: "+key);return {}
	for n in original.groups.size():
		if not remove.has(n):combined.groups.append(original.groups[n])
	combined.bounds=original.bounds
	return combined

func _validate_composed_contract(key: String,entry: Dictionary) -> bool:
	var signature:=str(entry.get("composed_manifest_sha256",""))
	var binding:=composition_contract_hash(entry)
	if composed_contracts.get(key,"")==binding:return true
	var bytes:=_read_verified(entry.composed_manifest_path,signature)
	if not error.is_empty():return false
	var contract: Variant=JSON.parse_string(bytes.get_string_from_utf8())
	if not contract is Dictionary:return _fail("Unreadable composed geometry contract: "+key).is_empty()
	if contract.get("schema","")!="riverstone.facility.composed_render.v1" or contract.get("asset_key","")!=key or not bool(contract.get("all_pass",false)) or bool(contract.get("collision_reference_changed",true)):
		return _fail("Unverified composed geometry contract: "+key).is_empty()
	var source: Dictionary=index.common_assets[key]
	if contract.has("source_revision"):
		if not _json_equivalent(contract.source_revision,entry.get("source_revision",{})) or contract.get("source_revision_sha256","")!=entry.get("source_revision_sha256",""):return _fail("Source revision entry/manifest mismatch").is_empty()
		if not _validate_source_revision(key,entry):return false
	elif entry.has("source_revision"):return _fail("Unexpected source revision").is_empty()
	if contract.get("source_master_sha256","")!=source.master_sha256 or contract.get("source_render_sha256","")!=source.render_sha256 or contract.get("render_sha256","")!=entry.sha256 or contract.get("render_path","")!=entry.render_path:
		return _fail("Composed geometry source/output binding mismatch: "+key).is_empty()
	if int(contract.get("output_quad_count",-1))*144!=int(entry.geometry_estimated_bytes) or (JSON.stringify(contract.get("window_regions",[]))!=JSON.stringify(entry.get("window_regions",[])) or JSON.stringify(contract.get("surface_exclusion_regions",[]))!=JSON.stringify(entry.get("surface_exclusion_regions",[]))):
		return _fail("Composed geometry bounds/size binding mismatch: "+key).is_empty()
	for field in ["surface_source_render_path","surface_source_render_sha256","surface_source_render_schema"]:
		if contract.get(field,"")!=entry.get(field,""):return _fail("Unbound revised wall support").is_empty()
	for region in contract.get("window_regions",[])+contract.get("surface_exclusion_regions",[]):
		if not region is Dictionary or not region.has("min") or not region.has("max"):return _fail("Malformed composed window region").is_empty()
		var extent:=RD.vector(region.max)-RD.vector(region.min)
		if extent.x<=0 or extent.y<=0 or extent.z<=0:return _fail("Empty composed window region").is_empty()
	if entry.has("visual_bounds"):
		var proof: Dictionary=contract.get("bounds_contract",{})
		if not _json_equivalent(proof,entry.get("bounds_contract",{})):
			return _fail("Unbound source-derived visual bounds: "+key).is_empty()
		var replay: Dictionary={}
		if proof.has("voxel_cell_envelope"):
			var replay_bytes:=_read_verified(str(proof.get("cell_envelope_proof_path","")),str(proof.get("cell_envelope_proof_sha256","")))
			if not error.is_empty():return false
			var parsed: Variant=JSON.parse_string(replay_bytes.get_string_from_utf8())
			if not parsed is Dictionary:return _fail("Unreadable source cell-envelope proof").is_empty()
			replay=parsed
			if replay.get("asset_key","")!=key or replay.get("render_path","")!=entry.render_path or replay.get("render_sha256","")!=entry.sha256:return _fail("Wrong cell-envelope render binding").is_empty()
			_read_verified(str(replay.get("canonical_master_path","")),str(replay.get("canonical_master_sha256","")))
			if not error.is_empty():return false
		var bounds_error: String=preload("res://validation/SourceBoundsContract.gd").validate(proof,entry.visual_bounds,source.bounds,source.master_sha256,replay)
		if not bounds_error.is_empty():return _fail("Unverified source-derived visual bounds: "+key+": "+bounds_error).is_empty()
	composed_contracts[key]=binding
	return true

func _validate_source_revision(key: String,entry: Dictionary) -> bool:
	if not entry.has("source_revision"):return true
	var revision: Dictionary=entry.source_revision
	var source: Dictionary=index.common_assets[key]
	if revision.get("original_master_path","")!=source.master_path or revision.get("original_master_sha256","")!=source.master_sha256:return _fail("Wrong original source revision binding").is_empty()
	var sidecar_bytes:=_read_verified(str(entry.get("source_revision_path","")),str(entry.get("source_revision_sha256","")))
	if not error.is_empty():return false
	var sidecar: Variant=JSON.parse_string(sidecar_bytes.get_string_from_utf8())
	if not sidecar is Dictionary or sidecar.get("schema","")!="riverstone.source_revision.v1" or not _json_equivalent(sidecar.get("source_revision",{}),revision):return _fail("Unbound source revision sidecar").is_empty()
	var original_bytes:=_read_verified(source.master_path,source.master_sha256)
	var revised_bytes:=_read_verified(str(revision.get("revised_master_path","")),str(revision.get("revised_master_sha256","")))
	if not error.is_empty():return false
	if str(source.master_path).ends_with(".gz"):original_bytes=original_bytes.decompress_dynamic(16777216,FileAccess.COMPRESSION_GZIP)
	if str(revision.revised_master_path).ends_with(".gz"):revised_bytes=revised_bytes.decompress_dynamic(16777216,FileAccess.COMPRESSION_GZIP)
	var original: Variant=JSON.parse_string(original_bytes.get_string_from_utf8())
	var revised: Variant=JSON.parse_string(revised_bytes.get_string_from_utf8())
	if not original is Dictionary or not revised is Dictionary:return _fail("Unreadable source revision masters").is_empty()
	var revision_error: String=preload("res://validation/WindowRevisionContract.gd").validate(revision,original,revised)
	if not revision_error.is_empty():return _fail("Invalid source revision: "+revision_error).is_empty()
	return true

static func _json_equivalent(a: Variant,b: Variant) -> bool:
	# JSON input normalizes numbers to float. Canonicalize in-memory fixtures too;
	# int(0) and parsed float(0.0) are the same contract value, not a new shape.
	return JSON.stringify(JSON.parse_string(JSON.stringify(a)))==JSON.stringify(JSON.parse_string(JSON.stringify(b)))

func _authorize_added_materials(key: String,entry: Dictionary,allowed: Dictionary) -> bool:
	var added: Array=entry.get("added_source_materials",[])
	if added.is_empty():return true
	var source_record: Dictionary=index.common_assets[key]
	var bytes:=_read_verified(source_record.master_path,source_record.master_sha256)
	if not error.is_empty():return false
	var master: Variant=JSON.parse_string(bytes.get_string_from_utf8())
	if not master is Dictionary:return _fail("Unreadable source master for added material").is_empty()
	var components: Dictionary={}
	for component in master.components:components[component.id]=component
	for addition in added:
		if addition.get("source_master_sha256","")!=source_record.master_sha256 or addition.get("source_operations",[]).is_empty():return _fail("Unbound extra near material: "+key).is_empty()
		var material:=str(addition.material)
		if not master.materials.has(material):return _fail("Unknown extra source material: "+material).is_empty()
		for reference in addition.source_operations:
			if not components.has(reference.component):return _fail("Missing source material component").is_empty()
			var found:=false
			for operation in components[reference.component].operations:
				if operation.id==reference.operation and operation.action=="paint" and operation.get("material","")==material:found=true;break
			if not found:return _fail("Missing source material paint operation").is_empty()
		allowed[material]=true
	return true

func composition_contract_data(entry: Dictionary) -> Dictionary:
	var data:={"source_render":entry.get("replacement_source_render_sha256",""),"source_master":entry.get("source_master_sha256",""),"fine_render":entry.sha256,"replace_groups":entry.get("replace_source_groups",[]),"added_source_materials":entry.get("added_source_materials",[]),"composed_manifest":entry.get("composed_manifest_sha256",""),"window_regions":entry.get("window_regions",[]),"surface_exclusion_regions":entry.get("surface_exclusion_regions",[]),"window_contract":entry.get("window_contract_sha256",""),"shadow_proxy":entry.get("shadow_proxy_sha256","")}
	if entry.has("visual_bounds"):data.visual_bounds=entry.visual_bounds;data.bounds_contract=entry.get("bounds_contract",{})
	if entry.has("source_revision"):data.source_revision=entry.source_revision;data.source_revision_sha256=entry.source_revision_sha256
	if entry.has("surface_source_render_path"):data.surface_source_render_sha256=entry.surface_source_render_sha256
	return data

func composition_contract_hash(entry: Dictionary) -> String:
	return JSON.stringify(composition_contract_data(entry)).sha256_text()

func _add_shadow_proxy(parent: Node3D,data: Dictionary) -> void:
	var st:=SurfaceTool.new();st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for ex in data.get("extrusions",[]):
		var p: Array=ex.polygon;var faces: Array=[]
		faces.append([Vector3(p[3][0],p[3][1],ex.z_min),Vector3(p[2][0],p[2][1],ex.z_min),Vector3(p[1][0],p[1][1],ex.z_min),Vector3(p[0][0],p[0][1],ex.z_min)])
		faces.append([Vector3(p[0][0],p[0][1],ex.z_max),Vector3(p[1][0],p[1][1],ex.z_max),Vector3(p[2][0],p[2][1],ex.z_max),Vector3(p[3][0],p[3][1],ex.z_max)])
		for i in range(4):
			var j: int=(i+1)%4
			faces.append([Vector3(p[i][0],p[i][1],ex.z_min),Vector3(p[j][0],p[j][1],ex.z_min),Vector3(p[j][0],p[j][1],ex.z_max),Vector3(p[i][0],p[i][1],ex.z_max)])
		var tr:=_local_transform(ex.get("transform",{}))
		for f in faces:
			for idx in [0,2,1,0,3,2]:st.add_vertex(tr*f[idx])
	st.generate_normals();var node:=MeshInstance3D.new();node.mesh=st.commit();node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY;parent.add_child(node)

func _local_transform(data: Dictionary) -> Transform3D:
	var rows: Array=data.get("basis",[[1,0,0],[0,1,0],[0,0,1]])
	return Transform3D(Basis(RD.vector(rows[0]),RD.vector(rows[1]),RD.vector(rows[2])).transposed(),RD.vector(data.get("translation",[0,0,0])))

func _evict(key: String) -> void:
	var item: Dictionary=detail_cache[key];detail_cached_bytes-=int(item.bytes);item.prefab.free();detail_cache.erase(key);detail_evictions+=1
	detail_events.append({"event":"evict","asset":key})

func update_near_detail(observer: Vector3,delta: float) -> void:
	if not render_enabled or not error.is_empty():return
	detail_elapsed+=delta
	if detail_elapsed<float(detail_catalog.update_interval_seconds):return
	detail_elapsed=0;detail_clock+=1
	var sorted: Array=[]
	for id in detail_records.keys():
		var r: Dictionary=detail_records[id]
		if not is_instance_valid(r.owner.get_ref()):detail_records.erase(id);continue
		r.distance=_distance(r,observer)
		if r.distance>float(detail_catalog.exit_distance_m):_release_detail(r)
		sorted.append({"id":id,"distance":r.distance})
	sorted.sort_custom(func(a,b):return a.distance<b.distance)
	var active:=0;var built:=0;var retained: Dictionary={}
	for ranked in sorted:
		var r: Dictionary=detail_records[ranked.id]
		if r.distance>float(detail_catalog.enter_distance_m) and r.fine==null:continue
		if active>=int(detail_catalog.max_active_instances):_release_detail(r);continue
		if r.fine==null:
			if not detail_cache.has(r.asset) and built>=int(detail_catalog.max_builds_per_update):detail_deferred+=1;continue
			var was_cached:=detail_cache.has(r.asset);var item:=_cache_asset(r.asset)
			if item.is_empty():continue
			if not was_cached:built+=1
			var fine: Node3D=item.prefab.duplicate();fine.transform=r.pose
			for node in fine.get_children():
				if not node.has_meta("material_slot"):continue
				var slot:=str(node.get_meta("material_slot"));var color: Variant=r.palette.get(slot,item.materials[slot]);var material_key:=JSON.stringify(color)
				if not detail_materials.has(material_key):
					var mat:=StandardMaterial3D.new();mat.albedo_color=RD.color_value(color);mat.roughness=1;mat.metallic_specular=0;detail_materials[material_key]=mat
				node.material_override=detail_materials[material_key]
			r.owner.get_ref().add_child(fine);r.fine=weakref(fine);r.coarse.get_ref().visible=false;detail_revision+=1
		active+=1;retained[r.asset]=true;detail_cache[r.asset].last=detail_clock
	# Real bounded residency: no more than 3 unused cached assets after leaving an area.
	var unused: Array=[]
	for key in detail_cache:
		if not retained.has(key):unused.append(key)
	unused.sort_custom(func(a,b):return detail_cache[a].last<detail_cache[b].last)
	while unused.size()>3:_evict(str(unused.pop_front()))
	while detail_events.size()>200:detail_events.pop_front()

func debug_state() -> Dictionary:
	var d:=super.debug_state();var active:=0
	for r in detail_records.values():
		if r.fine!=null and is_instance_valid(r.fine.get_ref()):active+=1
	d.near_detail={"registered_instances":detail_records.size(),"active_instances":active,"cached_assets":detail_cache.size(),"estimated_geometry_bytes":detail_cached_bytes,"budget_bytes":detail_catalog.get("cache_budget_vertex_normal_bytes",0),"builds":detail_builds,"evictions":detail_evictions,"deferred":detail_deferred,"events":detail_events,"not_full_city_coverage":true}
	return d

func _exit_tree() -> void:
	for item in detail_cache.values():
		if is_instance_valid(item.prefab):item.prefab.free()
