extends SceneTree
## Isolated compatibility fixture. This file never writes legacy r5 evidence.
const Visual = preload("res://runtime/CharacterVisual.gd")
const Player = preload("res://runtime/LilyController.gd")
const Tracks = preload("res://generated/r5/common/TransformTracks.gd")
const CACHE := "res://revisions/original_lily_r01/generated/lily_r01"
const OUTPUT := "res://revisions/original_lily_r01/evidence/runtime_checks_r01.json"
const SOLE_TOLERANCE_M := 0.011
var cache_dir := CACHE
var output_path := OUTPUT
var report := {"schema":"riverstone.character.modular_runtime_fixture.v1", "checks":[], "failures":[], "cache":CACHE, "visual_review":"not performed; headless compatibility checks only", "provenance":"New authored modular character using the existing shared runtime. No B7 source recovery is claimed."}
var stage: Node3D

func _initialize() -> void:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--cache="): cache_dir = argument.trim_prefix("--cache=")
		elif argument.begins_with("--output="): output_path = argument.trim_prefix("--output=")
	cache_dir = cache_dir.simplify_path()
	output_path = output_path.simplify_path()
	call_deferred("run")

func check(value: bool, label: String) -> void:
	report.checks.append({"id":label,"pass":value})
	if not value: report.failures.append(label)

func read_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null: return {}
	var value: Variant = JSON.parse_string(file.get_as_text())
	return value if value is Dictionary else {}

func snapshot(node: Node) -> Dictionary:
	var result := {"node_ids":[node.get_instance_id()], "mesh_rids":[], "material_rids":[]}
	if node is MeshInstance3D:
		result.mesh_rids.append(node.mesh.get_rid().get_id())
		for index in range(node.mesh.get_surface_count()):
			var material: Material = node.mesh.surface_get_material(index)
			if material != null: result.material_rids.append(material.get_rid().get_id())
	for child in node.get_children():
		var child_snapshot := snapshot(child)
		for key in result: result[key].append_array(child_snapshot[key])
	return result

func positions(nodes: Dictionary) -> Dictionary:
	var result := {}
	for id in nodes: result[id] = nodes[id].global_transform
	return result

func same_transforms(before: Dictionary, nodes: Dictionary) -> bool:
	for id in before:
		if not before[id].is_equal_approx(nodes[id].global_transform): return false
	return true

func sole_minimum(nodes: Dictionary, ids: Array) -> float:
	var result := INF
	for id in ids:
		var part: Node3D = nodes[id]
		for child in part.get_children():
			if child is MeshInstance3D:
				var bounds: AABB = child.mesh.get_aabb()
				for corner in range(8):
					result = minf(result, (child.global_transform * bounds.get_endpoint(corner)).y)
	return result

func capsule_correct(player: CharacterBody3D) -> bool:
	var collision := player.get_node_or_null("GameplayCapsule") as CollisionShape3D
	if collision == null or not collision.shape is CapsuleShape3D: return false
	var capsule := collision.shape as CapsuleShape3D
	return is_equal_approx(capsule.radius, 0.23) and is_equal_approx(capsule.height, 1.72) and collision.position.is_equal_approx(Vector3(0,0.86,0)) and player.scale.is_equal_approx(Vector3.ONE) and player.visual.scale.is_equal_approx(Vector3.ONE)

func finish() -> void:
	report["passed"] = report.failures.is_empty()
	report["check_count"] = report.checks.size()
	var file := FileAccess.open(output_path, FileAccess.WRITE)
	if file == null:
		push_error("Cannot write new revision runtime report: " + output_path)
		quit(2)
		return
	file.store_string(JSON.stringify(report,"  ") + "\n")
	file.close()
	print(JSON.stringify({"passed":report.passed,"checks":report.check_count,"failures":report.failures,"report":output_path}))
	if stage != null: stage.queue_free()
	await process_frame
	quit(0 if report.passed else 1)

func run() -> void:
	if not cache_dir.begins_with("res://revisions/original_lily_r01/generated/") or not output_path.begins_with("res://revisions/original_lily_r01/evidence/"):
		push_error("This fixture only reads and writes its owned original_lily_r01 revision")
		quit(2)
		return
	if FileAccess.file_exists(output_path):
		push_error("Refusing to overwrite existing evidence: " + output_path)
		quit(2)
		return
	stage = Node3D.new()
	root.add_child(stage)
	report["cache"] = cache_dir
	report["engine_version"] = Engine.get_version_info()
	report["test_script_sha256"] = FileAccess.get_sha256(get_script().resource_path)
	report["runtime_source_sha256"] = {}
	for path in ["res://runtime/CharacterVisual.gd","res://runtime/LilyVisual.gd","res://runtime/LilyController.gd","res://generated/r5/common/RenderData.gd","res://generated/r5/common/TransformTracks.gd"]:
		report.runtime_source_sha256[path] = FileAccess.get_sha256(path)
	var manifest := read_json(cache_dir.path_join("manifest.json"))
	var render := read_json(cache_dir.path_join("lily.render.json"))
	var bind := read_json(cache_dir.path_join("bind.json"))
	check(not manifest.is_empty() and not render.is_empty() and not bind.is_empty(), "new_cache_inputs_readable")
	if manifest.is_empty() or render.is_empty() or bind.is_empty():
		await finish()
		return
	report["source_id"] = render.source_id
	report["master_hash"] = render.master_hash
	report["render_pitch_m"] = render.pitch
	report["source_parts"] = manifest.parts
	var visual := Visual.new()
	stage.add_child(visual)
	var problem: String = visual.load_character(cache_dir)
	check(problem.is_empty(), "explicit_new_cache_loads")
	if not problem.is_empty():
		report["load_error"] = problem
		await finish()
		return
	check(visual.asset.get_meta("master_hash") == manifest.source_master_hash and visual.asset.get_meta("source_id") == manifest.source_id, "visual_uses_new_source_not_default_r5")
	check(visual.parts().size() == 44 and visual.rig.parts.size() == 44 and render.rigid_parts.size() == 44 and bind.tracks.size() == 44, "all_44_rigid_parts_present")
	check(visual.parts().size() <= int(visual.rig.limits.maximum_parts), "part_count_within_declared_limit")
	check(render.groups.is_empty(), "no_unbound_static_render_geometry")
	var nodes: Dictionary = visual.parts()
	var rig_by_id := {}
	var seen := {}
	var costumes: Array = []
	var correct_rest := true
	var correct_order := true
	var correct_basis := true
	var correct_selectors := true
	for part in visual.rig.parts:
		var id: String = part.id
		if seen.has(id) or (part.parent != null and not seen.has(part.parent)): correct_order = false
		var expected: Vector3 = Visual.CommonRender.vector(part.pivot_m)
		if part.parent != null:
			expected -= Visual.CommonRender.vector(rig_by_id[part.parent].pivot_m)
			if nodes[id].get_parent() != nodes[part.parent]: correct_rest = false
		elif nodes[id].get_parent() != visual.asset: correct_rest = false
		var rest: Transform3D = visual._rest[id]
		if not rest.origin.is_equal_approx(expected) or not rest.basis.is_equal_approx(Basis.IDENTITY): correct_rest = false
		if id.begins_with("costume_"):
			costumes.append(id)
			if part.parent != id.trim_prefix("costume_") or not rest.origin.is_zero_approx(): correct_rest = false
		seen[id] = true
		rig_by_id[id] = part
	var selector_ids := {}
	for part in render.rigid_parts:
		var id: String = part.selector.part
		if selector_ids.has(id) or not rig_by_id.has(id) or part.selector.instance != "lily": correct_selectors = false
		selector_ids[id] = true
		if not Visual.CommonRender.vector(part.pivot_world).is_equal_approx(Visual.CommonRender.vector(rig_by_id[id].pivot_m)): correct_rest = false
		if not Tracks.basis_rows(part.source_world_basis).is_equal_approx(Basis.IDENTITY): correct_basis = false
	check(correct_order, "unique_topological_rig_ids")
	check(correct_selectors and selector_ids.size() == nodes.size(), "selectors_resolve_once_and_cover_rig")
	check(correct_basis, "source_bases_remain_identity")
	check(correct_rest, "all_parent_local_rests_match_exported_world_pivots")
	check(costumes.size() == 12, "twelve_separate_zero_rest_costume_children")
	report["costume_parts"] = costumes
	check(nodes.ornament.get_parent() == nodes.head, "ornament_follows_head")
	for id in ["hair_tail_left","hair_tail_right","hair_tail_back"]:
		check(nodes[id].get_parent() == nodes.hair, id + "_follows_hair")
	for name in ["bind","idle","walk","blink","expression_neutral","expression_happy","expression_focused"]:
		var clip := read_json(cache_dir.path_join(name + ".json"))
		var player := Tracks.new()
		check(clip.get("master_hash") == render.master_hash and clip.get("source_id") == render.source_id, name + "_exact_source_binding")
		var error: String = player.configure(clip, visual.asset)
		check(error.is_empty(), name + "_all_selectors_configure")
		if not error.is_empty(): report[name + "_configure_error"] = error
		check(player.seek(float(clip.duration) * 0.25), name + "_seeks")
	# Reset every part with identity bind, then establish the public motion state.
	var rest_player := Tracks.new()
	check(rest_player.configure(bind, visual.asset).is_empty(), "bind_resets_all_rigid_nodes")
	var all_world_pivots_correct := true
	for id in nodes:
		if not nodes[id].global_position.is_equal_approx(Visual.CommonRender.vector(rig_by_id[id].pivot_m)): all_world_pivots_correct = false
	check(all_world_pivots_correct, "runtime_rest_world_pivots_match_source")
	check(not visual.load_character(cache_dir).is_empty(), "second_load_rejected")
	for method in ["load_character","set_locomotion","advance","set_expression","seek_motion","seek_blink","parts","debug_state"]:
		check(visual.has_method(method), "public_visual_api_" + method)
	visual.set_locomotion(1.65)
	check(visual.seek_motion(0.0), "walk_seek_zero")
	visual.seek_blink(0.0)
	visual.set_expression("neutral")
	var loop_start := positions(nodes)
	visual.seek_motion(8.0)
	check(same_transforms(loop_start,nodes), "all_44_nodes_no_drift_after_ten_walk_loops")
	visual.seek_motion(0.2)
	check(not nodes.thigh_left.transform.is_equal_approx(visual._rest.thigh_left) or not nodes.shin_left.transform.is_equal_approx(visual._rest.shin_left), "walk_moves_base_bone")
	check(not nodes.hair_tail_left.transform.is_equal_approx(visual._rest.hair_tail_left), "walk_moves_independent_hair_tail")
	var attached := true
	for id in costumes:
		if not nodes[id].transform.is_equal_approx(visual._rest[id]) or not nodes[id].global_transform.is_equal_approx(nodes[id].get_parent().global_transform): attached = false
	check(attached, "animated_costumes_keep_zero_local_rest_and_follow_bones")
	var immutable_before := snapshot(visual)
	for frame in range(240):
		if frame == 60: visual.set_locomotion(0.0)
		if frame == 90: visual.set_locomotion(1.65)
		if frame == 120: visual.set_expression("happy")
		if frame == 180: visual.set_expression("focused")
		visual.advance(1.0/60.0)
	check(snapshot(visual) == immutable_before, "mesh_material_resources_and_nodes_immutable_over_240_advances")
	report["immutable_resource_counts"] = {"nodes":immutable_before.node_ids.size(),"mesh_resources":immutable_before.mesh_rids.size(),"material_references":immutable_before.material_rids.size()}
	for value in ["neutral","happy","focused"]: check(visual.set_expression(value), "public_expression_" + value)
	check(not visual.set_expression("invalid"), "unknown_expression_rejected")
	visual.seek_blink(0.0)
	var open_lid: Transform3D = nodes.eyelid_left.transform
	check(visual.seek_blink(3.90), "blink_close_seek")
	check(not nodes.eyelid_left.transform.is_equal_approx(open_lid), "blink_moves_eyelid_geometry")
	visual.set_locomotion(1.65)
	var sole_range := [INF,-INF]
	var body_range := [INF,-INF]
	var shoe_range := [INF,-INF]
	var phases: Array = []
	for index in range(33):
		var time := float(index) * 0.8 / 32.0
		visual.seek_motion(time)
		var body_y := sole_minimum(nodes,["foot_left","foot_right"])
		var shoe_y := sole_minimum(nodes,["costume_foot_left","costume_foot_right"])
		var minimum := minf(body_y,shoe_y)
		body_range[0]=minf(body_range[0],body_y); body_range[1]=maxf(body_range[1],body_y)
		shoe_range[0]=minf(shoe_range[0],shoe_y); shoe_range[1]=maxf(shoe_range[1],shoe_y)
		sole_range[0]=minf(sole_range[0],minimum); sole_range[1]=maxf(sole_range[1],minimum)
		phases.append({"time_seconds":time,"body_foot_min_y_m":body_y,"costume_shoe_min_y_m":shoe_y,"combined_sole_min_y_m":minimum})
	report["gait_sole_sampling"] = {"phases":phases,"combined_range_m":sole_range,"body_only_range_m":body_range,"costume_shoe_range_m":shoe_range,"tolerance_m":SOLE_TOLERANCE_M,"criterion":"Same +/- 0.011 m root sole-plane tolerance as the legacy fixture; includes independently attached costume footwear. This is not foot IK or visual acceptance."}
	check(sole_range[0] > -SOLE_TOLERANCE_M and sole_range[1] < SOLE_TOLERANCE_M, "combined_shoe_body_sole_within_legacy_11mm_tolerance_at_33_phases")
	# Construct the actual controller with the new cache, never its default r5.
	var controller := Player.new()
	controller.player_input_enabled = false
	controller.camera_enabled = false
	controller.cache_dir = cache_dir
	stage.add_child(controller)
	controller.set_physics_process(false)
	check(controller.initialized and controller.load_error.is_empty(), "actual_controller_loads_new_cache")
	if controller.initialized:
		check(controller.visual.asset.get_meta("master_hash") == render.master_hash, "controller_uses_new_source_not_default_r5")
		check(capsule_correct(controller), "actual_capsule_radius_023_height_172_center_086_unit_scale")
		var collision: CollisionShape3D = controller.get_node("GameplayCapsule")
		check(is_zero_approx(collision.position.y - collision.shape.height * 0.5) and is_equal_approx(collision.position.y + collision.shape.height * 0.5,1.72), "actual_capsule_spans_y_zero_to_172")
		check(controller.collision_layer == 2 and controller.collision_mask == 1 and is_equal_approx(controller.floor_snap_length,0.20) and is_equal_approx(controller.safe_margin,0.001), "controller_collision_contract_preserved")
		for method in ["set_control","load_replay","simulate_control","set_expression","debug_state"]: check(controller.has_method(method), "public_controller_api_" + method)
		check(controller.set_control(Vector3.BACK,1.65), "controller_control_input_accepted")
		var replay := {"schema":"riverstone.character.input_replay.v1","physics_hz":60,"frames":[{"tick":0,"direction":[0,0,1],"speed_mps":1.65},{"tick":60,"direction":[0,0,0],"speed_mps":0.0}]}
		check(controller.load_replay(replay).is_empty(), "controller_serialized_input_replay_accepted")
		var bad_replay: Dictionary = replay.duplicate(true)
		bad_replay.frames[0]["position"] = [0,50,0]
		check(not controller.load_replay(bad_replay).is_empty(), "controller_output_position_replay_rejected")
		for frame in range(240):
			controller.visual.set_locomotion(1.65 if frame < 120 else 0.0)
			if frame == 80: controller.set_expression("happy")
			if frame == 160: controller.set_expression("focused")
			controller.visual.advance(1.0/60.0)
		check(capsule_correct(controller), "actual_capsule_unchanged_after_motion_expression_and_replay_setup")
		report["controller_state"] = controller.debug_state()
	report["scope_limits"] = ["No GUI or artistic acceptance", "No city collision or route qualification", "Controller constructed and input API verified; no physics movement simulation in this fixture", "No population performance claim"]
	await finish()
