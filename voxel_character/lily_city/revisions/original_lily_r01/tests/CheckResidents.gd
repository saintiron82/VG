extends SceneTree
## New revision only. Headless gait/rig checks and source-panel crossing diagnostics.
const Visual = preload("res://runtime/CharacterVisual.gd")
const Player = preload("res://runtime/LilyController.gd")
const Tracks = preload("res://generated/r5/common/TransformTracks.gd")
var base := "res://revisions/original_lily_r01/generated"
var output := "res://revisions/original_lily_r01/evidence/resident_runtime_r01.json"
var report := {"schema":"riverstone.character.resident_gait_check.v1","residents":[],"failures":[],"provenance":"New authored modular character variants. No B7 recovery claim.","visual_review":"Not performed; no GUI or city physics verification."}
var stage: Node3D

func _initialize() -> void:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--base="): base=argument.trim_prefix("--base=").simplify_path()
		elif argument.begins_with("--output="): output=argument.trim_prefix("--output=").simplify_path()
	call_deferred("run")

func read_json(path: String) -> Dictionary:
	var file:=FileAccess.open(path,FileAccess.READ)
	if file==null:return {}
	var value:Variant=JSON.parse_string(file.get_as_text())
	return value if value is Dictionary else {}

func check(entry: Dictionary, value: bool, label: String) -> void:
	entry.checks.append({"id":label,"pass":value})
	if not value:
		entry.failures.append(label)
		report.failures.append(entry.id+":"+label)

func snapshot(node: Node) -> Array:
	var result:Array=[node.get_instance_id()]
	if node is MeshInstance3D:result.append(node.mesh.get_rid().get_id())
	for child in node.get_children():result.append_array(snapshot(child))
	return result

func part_vertices(part: Node3D) -> PackedVector3Array:
	var result:=PackedVector3Array()
	for child in part.get_children():
		if child is MeshInstance3D:
			for surface in range(child.mesh.get_surface_count()):
				var arrays:Array=child.mesh.surface_get_arrays(surface)
				for vertex in arrays[Mesh.ARRAY_VERTEX]:result.append(child.transform*vertex)
	return result

func sole_y(nodes: Dictionary, vertices: Dictionary) -> float:
	var lowest:=INF
	for id in vertices:
		if id.begins_with("foot_") or id.begins_with("costume_foot_"):
			for vertex in vertices[id]:lowest=minf(lowest,(nodes[id].global_transform*vertex).y)
	return lowest

func source_panels(master: Dictionary) -> Array:
	var result:Array=[]
	for component in master.components:
		for operation in component.operations:
			var id:String=operation.id
			if not operation.part.begins_with("skirt_") or operation.action!="paint" or operation.shape.kind!="extrusion":continue
			if not (id.ends_with("front_left") or id.ends_with("front_right") or id.ends_with("rear_left") or id.ends_with("rear_right") or "front_left_band_" in id or "front_right_band_" in id or "rear_left_band_" in id or "rear_right_band_" in id):continue
			var shape:Dictionary=operation.shape
			if float(shape.z_max)-float(shape.z_min)>.09:continue
			var polygon:=PackedVector2Array()
			var low:=INF;var high:=-INF
			for point in shape.polygon:
				polygon.append(Vector2(point[0],point[1]));low=minf(low,point[1]);high=maxf(high,point[1])
			var front:bool=float(shape.z_min)>0
			result.append({"id":id,"part":operation.part,"polygon":polygon,"z":float(shape.z_max) if front else float(shape.z_min),"sign":1.0 if front else -1.0,"low_y":low,"high_y":high})
	# Flare-band seams are internal boundaries, not hems/waists to exclude.
	var extents:={}
	for panel in result:
		if not extents.has(panel.part):extents[panel.part]=[panel.low_y,panel.high_y]
		else:extents[panel.part]=[minf(extents[panel.part][0],panel.low_y),maxf(extents[panel.part][1],panel.high_y)]
	for panel in result:
		panel.low_y=extents[panel.part][0];panel.high_y=extents[panel.part][1]
	return result

func panel_interior(point: Vector3, panel: Dictionary, margin: float) -> bool:
	if point.y<=float(panel.low_y)+margin*2.0 or point.y>=float(panel.high_y)-margin*2.0:return false
	for offset in [Vector2.ZERO,Vector2(margin,0),Vector2(-margin,0)]:
		if not Geometry2D.is_point_in_polygon(Vector2(point.x,point.y)+offset,panel.polygon):return false
	return true

func panel_crossings(nodes: Dictionary, vertices: Dictionary, pivots: Dictionary, panels: Array, pitch: float, phase: float) -> Dictionary:
	var result:Dictionary={"crossing_edges":0,"max_outward_depth_m":0.0,"worst_outward_sample":{},"examples":[]}
	for panel in panels:
		var garment:Node3D=nodes[panel.part]
		var to_source:Transform3D=Transform3D(Basis.IDENTITY,pivots[panel.part])*garment.global_transform.affine_inverse()
		for id in vertices:
			if not (id.begins_with("thigh_") or id.begins_with("shin_") or id.begins_with("foot_") or id.begins_with("costume_thigh_") or id.begins_with("costume_shin_") or id.begins_with("costume_foot_")):continue
			var transform:Transform3D=to_source*nodes[id].global_transform
			var points:=PackedVector3Array()
			for local in vertices[id]:
				var point:Vector3=transform*local
				points.append(point)
				if panel_interior(point,panel,pitch*.5):
					var depth:float=(point.z-float(panel.z))*float(panel.sign)
					if depth>float(result.max_outward_depth_m):
						result.max_outward_depth_m=depth
						var world:Vector3=nodes[id].global_transform*local
						result.worst_outward_sample={"phase_seconds":phase,"leg_part":id,"garment_part":panel.part,"source_panel":panel.id,"outward_depth_m":depth,"world_vertex_m":[world.x,world.y,world.z],"garment_source_vertex_m":[point.x,point.y,point.z]}
			for triangle in range(0,points.size(),3):
				for edge in range(3):
					var a:Vector3=points[triangle+edge]
					var b:Vector3=points[triangle+(edge+1)%3]
					var da:=a.z-float(panel.z);var db:=b.z-float(panel.z)
					if not ((da>pitch*.5 and db < -pitch*.5) or (db>pitch*.5 and da < -pitch*.5)):continue
					var intersection:Vector3=a.lerp(b,da/(da-db))
					if not panel_interior(intersection,panel,pitch*.5):continue
					result.crossing_edges+=1
					if result.examples.size()<6:
						var world:Vector3=garment.global_transform*(intersection-pivots[panel.part])
						result.examples.append({"phase_seconds":phase,"leg_part":id,"garment_part":panel.part,"source_panel":panel.id,"world_intersection_m":[world.x,world.y,world.z]})
	return result

func inspect_cache(path: String) -> void:
	var manifest:=read_json(path.path_join("manifest.json"))
	var master:=read_json(path.path_join("derived.master.json"))
	var preset:Dictionary=master.extensions.assembly.preset
	var entry:Dictionary={"id":path.get_file(),"cache":path,"master_hash":manifest.source_master_hash,"body_frame":preset.body,"role":preset.role,"checks":[],"failures":[],"gait_phases":[]}
	report.residents.append(entry)
	var visual:=Visual.new();stage.add_child(visual)
	var error:String=visual.load_character(path)
	check(entry,error.is_empty(),"explicit_cache_loads")
	if not error.is_empty():entry["error"]=error;visual.queue_free();await process_frame;return
	var nodes:Dictionary=visual.parts()
	entry["parts"]=nodes.size()
	check(entry,nodes.size()==int(manifest.parts),"part_count_matches_manifest")
	check(entry,visual.asset.get_meta("master_hash")==manifest.source_master_hash,"new_cache_hash_used")
	for name in ["bind","idle","walk","blink","expression_neutral","expression_happy","expression_focused"]:
		var clip:=read_json(path.path_join(name+".json"));var track_player:=Tracks.new()
		check(entry,clip.get("master_hash")==manifest.source_master_hash and clip.get("source_id")==master.id,name+"_source_binding")
		check(entry,track_player.configure(clip,visual.asset).is_empty(),name+"_selectors_configure")
	var bind_player:=Tracks.new();bind_player.configure(read_json(path.path_join("bind.json")),visual.asset)
	var vertices:= {};var pivots:={}
	for part in visual.rig.parts:
		pivots[part.id]=Visual.CommonRender.vector(part.pivot_m)
		vertices[part.id]=part_vertices(nodes[part.id])
	var panels:=source_panels(master)
	entry["clearance_panel_count"]=panels.size()
	visual.set_locomotion(1.65);visual.seek_blink(0);visual.set_expression("neutral")
	var immutable:=snapshot(visual)
	var minimum:=INF;var maximum:=-INF
	var crossing_count:=0;var crossing_phases:=0;var largest_depth:=0.0;var worst_sample:={};var examples:Array=[]
	for index in range(33):
		var time:=float(index)*.8/32.0;visual.seek_motion(time)
		var low:=sole_y(nodes,vertices);minimum=minf(minimum,low);maximum=maxf(maximum,low)
		var crossing:=panel_crossings(nodes,vertices,pivots,panels,float(manifest.pitch_m),time)
		crossing_count+=int(crossing.crossing_edges)
		if crossing.crossing_edges>0:crossing_phases+=1
		if float(crossing.max_outward_depth_m)>largest_depth:
			largest_depth=float(crossing.max_outward_depth_m);worst_sample=crossing.worst_outward_sample
		if examples.size()<12:examples.append_array(crossing.examples.slice(0,12-examples.size()))
		entry.gait_phases.append({"time_seconds":time,"combined_body_shoe_sole_y_m":low,"source_panel_crossing_edges":crossing.crossing_edges,"max_panel_outward_depth_m":crossing.max_outward_depth_m,"worst_outward_sample":crossing.worst_outward_sample})
	entry["sole_range_m"]=[minimum,maximum]
	entry["sole_within_legacy_11mm_benchmark"]=minimum > -.011 and maximum < .011
	entry["skirt_clearance"]={"crossing_edge_samples":crossing_count,"phases_with_crossing":crossing_phases,"max_outward_vertex_depth_m":largest_depth,"worst_outward_sample":worst_sample,"examples":examples,"assessment":"Source-panel surface crossing candidates detected; motion-art clearance is not accepted." if crossing_count>0 else "No selected front/back source-panel crossing was detected at sampled phases. This does not prove absence of intersections."}
	var walk:=read_json(path.path_join("walk.json"));var angles:={}
	for track in walk.tracks:
		if track.selector.part.begins_with("thigh_") or track.selector.part.begins_with("skirt_"):angles[track.selector.part]=track.keys[0].rotation_degrees
	entry["contact_zero_local_rotation_degrees"]=angles
	for frame in range(240):
		if frame==80:visual.set_locomotion(0)
		if frame==120:visual.set_locomotion(1.65)
		visual.advance(1.0/60.0)
	check(entry,snapshot(visual)==immutable,"part_nodes_and_meshes_unchanged_across_phases_and_240_advances")
	var controller:=Player.new();controller.player_input_enabled=false;controller.camera_enabled=false;controller.cache_dir=path;stage.add_child(controller);controller.set_physics_process(false)
	check(entry,controller.initialized,"actual_controller_loads")
	if controller.initialized:
		var shape:CollisionShape3D=controller.get_node("GameplayCapsule")
		var child:bool=preset.body=="child"
		var radius:=.18 if child else .23;var height:=1.27 if child else 1.72;var center:=.635 if child else .86
		check(entry,shape.shape is CapsuleShape3D and is_equal_approx(shape.shape.radius,radius) and is_equal_approx(shape.shape.height,height) and shape.position.is_equal_approx(Vector3(0,center,0)),"actual_capsule_matches_explicit_age_frame_contract")
		check(entry,controller.scale.is_equal_approx(Vector3.ONE) and controller.visual.scale.is_equal_approx(Vector3.ONE),"controller_and_visual_have_unit_scale")
		entry["actual_capsule"]={"radius_m":shape.shape.radius,"height_m":shape.shape.height,"center_m":[shape.position.x,shape.position.y,shape.position.z],"child_scope":"new proportion preview only" if child else "unchanged adult contract"}
	entry["compatibility_passed"]=entry.failures.is_empty()
	print(JSON.stringify({"resident":entry.id,"compatible":entry.compatibility_passed,"sole_range_m":entry.sole_range_m,"crossing_phases":crossing_phases,"max_outward_depth_m":largest_depth}))
	controller.queue_free();visual.queue_free();await process_frame

func run() -> void:
	if not base.begins_with("res://revisions/original_lily_r01/generated") or not output.begins_with("res://revisions/original_lily_r01/evidence/") or FileAccess.file_exists(output):push_error("Unsafe or existing fixture destination");quit(2);return
	stage=Node3D.new();root.add_child(stage)
	var names:=DirAccess.get_directories_at(base);names.sort()
	for name in names:
		if name.begins_with("resident_") and FileAccess.file_exists(base.path_join(name).path_join("manifest.json")):await inspect_cache(base.path_join(name))
	report["cache_base"]=base
	report["resident_count"]=report.residents.size()
	report["compatibility_passed"]=report.failures.is_empty() and report.residents.size()==10
	report["test_script_sha256"]=FileAccess.get_sha256(get_script().resource_path)
	report["clearance_method"]="Actual leg/foot and costume-leg/foot triangle edges are transformed into each animated skirt part's source coordinates. We test crossings of selected front/back extrusion outer planes inside source polygons, excluding a one-pitch margin at whole-part hems/waist and requiring endpoints on both sides by half a voxel. Internal flare-band seams remain tested. Counts contain duplicate triangle edges. Source planes approximate sampled voxel surfaces; side panels, cuts, fully contained overlap, and unsampled phases are not certified. This is a diagnostic, never proof of cloth clearance."
	report["scope_limits"]=["No GUI, visual acceptance, city routes, or physical cloth simulation", "Sole range uses actual transformed mesh vertices including costume footwear", "Child 0.18/1.27 capsule is an explicit new proportion-preview contract", "Shared adult gait is measured on child proportions, not assumed accepted"]
	var file:=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");file.close()
	print(JSON.stringify({"compatibility_passed":report.compatibility_passed,"residents":report.resident_count,"failures":report.failures,"report":output}))
	stage.queue_free();await process_frame;quit(0 if report.compatibility_passed else 1)
