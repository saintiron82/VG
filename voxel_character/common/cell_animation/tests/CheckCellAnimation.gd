extends SceneTree
## Tiny fixtures by default. Full input/oracle checks are explicit CLI choices.
const VoxelData = preload("res://RenderData.gd")
const CellPools = preload("res://CellPools.gd")
const Preview = preload("res://Preview.gd")
var checks: Array = []
var options: Dictionary = {"input": "res://tests/tiny.render.json"}
var player = CellPools.new()
var asset: Node3D
var data: Dictionary
var oracle_max_position_error: float = 0.0

func _initialize() -> void:
	call_deferred("run_checks")

func check(id: String, passed: bool, detail: Variant = null) -> void:
	checks.append({"id": id, "pass": passed, "detail": detail})
	if not passed: printerr("FAILED: " + id + " " + str(detail))

func parse_options() -> String:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var index: int = 0
	while index < args.size():
		var argument: String = args[index]
		if not argument.begins_with("--"): return "Expected --input/--oracle/--report"
		var separator: int = argument.find("=")
		var key: String = argument.substr(2, separator - 2) if separator >= 0 else argument.substr(2)
		if not key in ["input", "oracle", "report"]: return "Unknown test option: " + key
		if separator >= 0: options[key] = argument.substr(separator + 1)
		elif index + 1 < args.size():
			index += 1
			options[key] = args[index]
		else: return "Missing test option value"
		index += 1
	return ""

func static_signatures(node: Node) -> Array:
	var result: Array = []
	if node is MeshInstance3D:
		result.append([node.get_instance_id(), node.mesh.get_instance_id(), hash(var_to_bytes(node.mesh.surface_get_arrays(0))), node.transform])
	for child in node.get_children(): result.append_array(static_signatures(child))
	return result

func identities(state: Dictionary) -> Array:
	var result: Array = []
	for pool in state.pools: result.append([pool.id, pool.capacity, pool.node_id, pool.multimesh_id, pool.mesh_id, pool.material_id, pool.instance_count])
	return result

func node_count(node: Node) -> int:
	var total: int = 1
	for child in node.get_children(): total += node_count(child)
	return total

func valid_render_prefix(state: Dictionary) -> bool:
	for pool in state.pools:
		if pool.visible_count < 0 or pool.visible_count > pool.capacity or pool.instance_count != pool.capacity: return false
		if pool.positions.size() != pool.visible_count or pool.member_indices.size() != pool.visible_count or pool.color_indices.size() != pool.visible_count: return false
		var previous: int = -1
		for member in pool.member_indices:
			if member <= previous or member >= pool.capacity: return false
			previous = member
	return true

func geometry_state(state: Dictionary) -> Array:
	var result: Array = []
	for pool in state.pools: result.append([pool.id, pool.positions, pool.member_indices, pool.color_indices])
	return result

func run_checks() -> void:
	var problem: String = parse_options()
	if not problem.is_empty(): printerr(problem); quit(1); return
	var result: Dictionary = VoxelData.read(options.input)
	if result.has("error"): printerr(result.error); quit(1); return
	data = result.data
	asset = VoxelData.build(data)
	root.add_child(asset)
	var initial_static: Array = static_signatures(asset)
	var static_node_count: int = node_count(asset)
	problem = player.configure(data, asset)
	check("configure", problem.is_empty(), problem)
	if not problem.is_empty(): finish(); return
	check("lineage_preserved", player.source_id == str(data.get("source_id", "")) and player.master_hash == str(data.get("master_hash", "")))
	if data.has("cell_animation"):
		check("clip_hash_preserved", player.clip_hash == str(data.cell_animation.get("clip_hash", "")))
		var initial: Dictionary = player.state()
		var initial_ids: Array = identities(initial)
		var initial_nodes: int = node_count(asset)
		var initial_resources: int = int(Performance.get_monitor(Performance.OBJECT_RESOURCE_COUNT))
		var ticks: int = int(round(player.duration * player.update_hz))
		var first_loop: Array = []
		var fixed: bool = true
		var repeated: bool = true
		var bounded: bool = true
		var prefix: bool = true
		for tick in range(ticks * 2 + 1):
			player.seek(float(tick) / player.update_hz)
			var state: Dictionary = player.state()
			fixed = fixed and identities(state) == initial_ids and node_count(asset) == initial_nodes and state.pool_resource_count == initial.pool_resource_count
			prefix = prefix and valid_render_prefix(state)
			for pool in state.pools: bounded = bounded and pool.within_bounds
			if tick < ticks: first_loop.append(geometry_state(state))
			elif data.cell_animation.loop: repeated = repeated and geometry_state(state) == first_loop[tick % ticks]
		check("fixed_pool_node_resource_ids_over_two_loops", fixed, {"nodes": initial_nodes, "pool_resources": initial.pool_resource_count, "capacity": initial.capacity, "evaluations": ticks * 2 + 1})
		check("engine_cached_resource_monitor_unchanged_over_two_loops", int(Performance.get_monitor(Performance.OBJECT_RESOURCE_COUNT)) == initial_resources, {"before": initial_resources, "after": int(Performance.get_monitor(Performance.OBJECT_RESOURCE_COUNT))})
		check("repeat_identical_geometry_over_two_loops", repeated)
		check("visible_cells_within_declared_bounds", bounded)
		check("stable_compact_prefix_and_capacity", prefix)
		player.seek(player.duration * 0.37)
		player.pause()
		var held: Dictionary = player.state()
		player.advance(player.duration)
		check("pause_holds_exact_state", player.state() == held)
		player.seek(player.duration * 0.63)
		check("seek_while_paused", not player.playing and not is_equal_approx(player.playhead, held.playhead))
		var repeated_state: Dictionary = player.state()
		player.seek(player.duration * 0.63)
		check("identical_repeated_seek", player.state() == repeated_state)
		player.seek(0.099 / player.update_hz)
		check("fixed_hz_quantization", is_zero_approx(player.evaluation_time))
		player.seek(player.duration + 1.0 / player.update_hz)
		check("loop_or_clamp_positive_seek", is_equal_approx(player.playhead, 1.0 / player.update_hz if player.loop else player.duration))
		player.seek(-1.0 / player.update_hz)
		check("negative_seek", is_equal_approx(player.playhead, player.duration - 1.0 / player.update_hz if player.loop else 0.0))
		player.play()
		player.seek(player.duration - 0.5 / player.update_hz)
		player.advance(1.0 / player.update_hz)
		check("advance_loop_or_clamp", is_equal_approx(player.playhead, 0.5 / player.update_hz if player.loop else player.duration))
		var before_bad_seek: Dictionary = player.state()
		check("reject_nonfinite_seek", not player.seek(NAN) and not player.seek(INF) and player.state() == before_bad_seek)
		player.advance(-1.0)
		player.advance(INF)
		check("ignore_invalid_delta", player.state() == before_bad_seek)
		player.stop()
		check("stop_resets_and_pauses", not player.playing and is_zero_approx(player.playhead) and geometry_state(player.state()) == geometry_state(initial))
		if player.loop:
			player.seek(player.duration - 0.000000000001)
			check("rounded_loop_endpoint_canonicalized", is_zero_approx(player.evaluation_time) and geometry_state(player.state()) == geometry_state(initial))
			player.seek(2.0 * player.duration - 0.000000000001)
			check("rounded_second_loop_endpoint_canonicalized", is_zero_approx(player.evaluation_time) and geometry_state(player.state()) == geometry_state(initial))
			var boundaries_match: bool = true
			for frame in range(ticks * 3 + 1):
				for offset in [-0.000000000001, 0.0, 0.000000000001]:
					player.seek(float(frame) / player.update_hz + offset)
					boundaries_match = boundaries_match and is_equal_approx(player.evaluation_time, float(frame % ticks) / player.update_hz) and geometry_state(player.state()) == first_loop[frame % ticks]
			check("before_exact_after_all_tick_boundaries_three_loops", boundaries_match, {"boundary_checks": (ticks * 3 + 1) * 3, "offset_seconds": 0.000000000001})
			var seam_offsets_match: bool = true
			var outside_rounding: float = 0.00000002 / player.update_hz
			for cycle in range(1, 5):
				player.seek(player.duration * cycle - outside_rounding)
				seam_offsets_match = seam_offsets_match and geometry_state(player.state()) == first_loop[ticks - 1]
				player.seek(player.duration * cycle + outside_rounding)
				seam_offsets_match = seam_offsets_match and geometry_state(player.state()) == first_loop[0]
			check("loop_seams_outside_rounding_window", seam_offsets_match)
			var large_seeks_match: bool = true
			for cycle in [-1000000.0, 1000000.0]:
				player.seek(player.duration * cycle)
				large_seeks_match = large_seeks_match and is_zero_approx(player.evaluation_time) and geometry_state(player.state()) == first_loop[0]
			check("million_loop_positive_negative_seek", large_seeks_match)
		if options.has("oracle"): compare_oracle()
		var non_loop: Dictionary = data.duplicate(true)
		non_loop.cell_animation.loop = false
		problem = player.configure(non_loop, asset)
		player.seek(1.0e6)
		check("nonloop_end_clamped", problem.is_empty() and is_equal_approx(player.playhead, player.duration) and is_equal_approx(player.evaluation_time, player.duration))
		var terminal_geometry: Array = geometry_state(player.state())
		player.seek(player.duration - 0.000000000001)
		var terminal_unchanged: bool = is_equal_approx(player.evaluation_time, player.duration) and geometry_state(player.state()) == terminal_geometry
		player.advance(player.duration * 1000000.0)
		check("nonloop_terminal_unchanged_near_boundary_and_large_advance", terminal_unchanged and is_equal_approx(player.evaluation_time, player.duration) and geometry_state(player.state()) == terminal_geometry)
		player.seek(-1.0e6)
		check("nonloop_start_clamped", is_zero_approx(player.playhead))
		player.seek(player.duration * 0.5)
		var mutable_input: Dictionary = data.duplicate(true)
		problem = player.configure(mutable_input, asset)
		var immutable_before: Array = geometry_state(player.state())
		mutable_input.cell_animation.pools[0].positions[0][0] += 500.0
		player.seek(0.0)
		check("caller_mutation_does_not_change_rest", problem.is_empty() and geometry_state(player.state()) == immutable_before)
		var old_ids: Array = identities(player.state())
		player.seek(player.duration * 0.5)
		problem = player.configure(data, asset)
		var old_nodes_gone: bool = true
		for old in old_ids: old_nodes_gone = old_nodes_gone and not is_instance_id_valid(old[2])
		check("reconfigure_releases_previous_pool_nodes", problem.is_empty() and old_nodes_gone and node_count(asset) == initial_nodes)
		check("reconfigure_uses_immutable_rest", geometry_state(player.state()) == geometry_state(initial))
		var invalid: Dictionary = data.duplicate(true)
		invalid.cell_animation.duration = 0
		var preserved: Dictionary = player.state()
		check("invalid_reconfigure_is_atomic", not player.configure(invalid, asset).is_empty() and player.state() == preserved)
	check("static_mesh_ids_and_hashes_unchanged", static_signatures(asset) == initial_static)
	var static_only: Dictionary = data.duplicate(true)
	static_only.erase("cell_animation")
	problem = player.configure(static_only, asset)
	check("static_only_noop_and_old_pools_removed", problem.is_empty() and player.state().pool_count == 0 and node_count(asset) == static_node_count and player.seek(123.0))
	check("static_mesh_hash_after_reconfiguration", static_signatures(asset) == initial_static)
	malformed_checks()
	tiny_function_checks()
	capture_clock_checks()
	finish()

func compare_oracle() -> void:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(options.oracle))
	if not parsed is Dictionary or not parsed.get("states") is Array:
		check("oracle_readable", false)
		return
	check("oracle_clip_hash_matches", str(parsed.get("clip_hash", "")) == player.clip_hash)
	var match_all: bool = true
	var mismatch: Variant = null
	for expected in parsed.states:
		player.seek(float(expected.playhead))
		var actual: Dictionary = player.state()
		if absf(actual.evaluation_time - float(expected.evaluation_time)) > 0.00000001 or actual.pools.size() != expected.pools.size(): match_all = false
		for index in range(mini(actual.pools.size(), expected.pools.size())):
			var got: Dictionary = actual.pools[index]
			var want: Dictionary = expected.pools[index]
			var members: Array = want.get("member_ids", want.get("member_indices", []))
			if got.id != want.id or got.visible_count != want.visible_count or PackedInt32Array(got.member_indices) != PackedInt32Array(members) or PackedInt32Array(got.color_indices) != PackedInt32Array(want.color_indices) or got.positions.size() != want.positions.size():
				match_all = false
				if mismatch == null: mismatch = {"time": expected.playhead, "pool": want.id, "actual_count": got.visible_count, "expected_count": want.visible_count, "actual_members": got.member_indices, "expected_members": members, "actual_colors": got.color_indices, "expected_colors": want.color_indices}
			for member in range(mini(got.positions.size(), want.positions.size())):
				for axis in range(3):
					var error: float = absf(float(got.positions[member][axis]) - float(want.positions[member][axis]))
					oracle_max_position_error = maxf(error, oracle_max_position_error)
					if error > 0.000001:
						match_all = false
						if mismatch == null: mismatch = {"time": expected.playhead, "pool": want.id, "member": member, "actual_position": got.positions[member], "expected_position": want.positions[member]}
	check("direct_functions_match_independent_oracle", match_all, {"samples": parsed.states.size(), "position_tolerance": 0.000001, "maximum_position_error": oracle_max_position_error, "first_mismatch": mismatch})

func malformed_checks() -> void:
	var tiny: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tests/tiny.render.json"))
	var bad: Dictionary = tiny.duplicate(true)
	bad.cell_animation.duration = 0
	check("reject_zero_duration", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.duration = 2.03
	check("reject_fractional_tick_count", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.update_hz = 0
	check("reject_zero_update_hz", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.seed = 5
	check("reject_unsupported_seed", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.master_hash = "wrong"
	check("reject_master_mismatch", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.source_id = "wrong"
	check("reject_source_mismatch", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[1].id = bad.cell_animation.pools[0].id
	check("reject_duplicate_pool_id", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[0].positions[0][0] = NAN
	check("reject_nonfinite_position", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[0].positions[0][0] = 100
	check("reject_out_of_bounds_rest_cell", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[0].color_indices = [0]
	check("reject_wrong_color_capacity", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[0].color_indices[0] = 99
	check("reject_invalid_palette_index", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[0].banded_color.cycle = 0
	check("reject_zero_band_cycle", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[1].positions.reverse()
	check("reject_unsorted_threshold_members", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[1].threshold_visibility.keys[1][0] = 0
	check("reject_duplicate_threshold_key", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[1].threshold_visibility.keys[-1][0] = 1.5
	check("reject_incomplete_threshold_keys", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[1].ballistic = bad.cell_animation.pools[2].ballistic
	check("reject_mutually_exclusive_motion", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[2].ballistic.velocities.pop_back()
	check("reject_wrong_velocity_capacity", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[2].ballistic.lifetimes[0] = 5
	check("reject_lifetime_past_period", not CellPools.validate(bad).is_empty())
	bad = tiny.duplicate(true); bad.cell_animation.pools[2].ballistic.quantize.pitch = 0
	check("reject_zero_quantize_pitch", not CellPools.validate(bad).is_empty())

func tiny_function_checks() -> void:
	var tiny: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tests/tiny.render.json"))
	var parent := Node3D.new()
	root.add_child(parent)
	var sample_player = CellPools.new()
	var problem: String = sample_player.configure(tiny, parent)
	check("tiny_functions_configure", problem.is_empty())
	sample_player.seek(0.2)
	var state: Dictionary = sample_player.state()
	check("band_color_from_rest_position_and_time", state.pools[0].color_indices == [1, 0])
	check("threshold_uses_sorted_prefix", state.pools[1].member_indices == [0])
	check("ballistic_compacts_noncontiguous_members", state.pools[2].member_indices == [0, 2])
	check("ballistic_keeps_member_colors", state.pools[2].color_indices == [0, 2])
	var got: Vector3 = VoxelData.vector(state.pools[2].positions[0])
	var expected := Vector3(0.25, 0.45, 0.05)
	check("ballistic_quantized_cell_centers", got.distance_to(expected) < 0.000001, state.pools[2].positions[0])
	sample_player.seek(0.5)
	state = sample_player.state()
	check("threshold_exact_boundary_visible", state.pools[1].member_indices == [0, 1])
	check("ballistic_phase_and_lifetime", state.pools[2].member_indices == [1] and state.pools[2].color_indices == [1])
	tiny.cell_animation.pools[1].threshold_visibility.interpolation = "smoothstep"
	sample_player.configure(tiny, parent)
	sample_player.seek(0.4)
	check("smoothstep_threshold_interpolation", sample_player.state().pools[1].visible_count == 1)
	var ballistic: Dictionary = tiny.cell_animation.pools[2].ballistic
	ballistic.lifetimes = [0.54, 0.54, 0.54]
	ballistic.phases = [-(0.54 - 0.00000002), -0.54, -(0.54 + 0.00000002)]
	sample_player.configure(tiny, parent)
	check("expiry_before_exact_after_boundary", sample_player.state().pools[2].member_indices == [0])
	ballistic.lifetimes = [0.000000000001, 0.000000000001, 0.000000000001]
	ballistic.phases = [0.0, -0.0000000000005, -0.000000000001]
	sample_player.configure(tiny, parent)
	check("tiny_lifetime_preserves_zero_and_half_age", sample_player.state().pools[2].member_indices == [0, 1])
	ballistic.lifetimes = [0.0, 0.0, 0.0]
	ballistic.phases = [0.0, 0.0, 0.0]
	sample_player.configure(tiny, parent)
	check("zero_lifetime_never_visible", sample_player.state().pools[2].visible_count == 0)
	sample_player.clear()
	check("clear_removes_owned_nodes", parent.get_child_count() == 0)
	parent.free()


func capture_clock_checks() -> void:
	# Do not depend on OS engine arguments: Godot may consume them at startup.
	var preview = Preview.new()
	preview.options["capture-fps"] = "30"
	preview.configure_movie_clock()
	check("explicit_capture_fps_activates_movie_clock", preview.movie_mode and is_equal_approx(preview.movie_fps, 30.0) and is_equal_approx(preview.movie_step, 1.0 / 30.0))
	var tiny: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tests/tiny.render.json"))
	var pool_parent := Node3D.new()
	preview.data = tiny
	preview.player.configure(tiny, pool_parent)
	preview.status = Label.new()
	preview.ready_for_frames = true
	var all_clock_frames_exact: bool = true
	for frame in range(7):
		preview._process(0.71)
		all_clock_frames_exact = all_clock_frames_exact and preview.movie_time == float(frame) / 30.0
	check("movie_clock_ignores_wall_clock_delta", is_equal_approx(preview.movie_time, 6.0 / 30.0) and is_equal_approx(preview.player.playhead, 6.0 / 30.0) and preview.frame_count == 7)
	preview.player.pause()
	preview._process(123.0)
	check("movie_clock_respects_pause", is_equal_approx(preview.movie_time, 6.0 / 30.0))
	preview.player.play()
	for frame in range(138):
		preview._process(0.007)
		all_clock_frames_exact = all_clock_frames_exact and preview.movie_time == float(frame + 7) / 30.0
	check("absolute_movie_clock_all_145_frame_times", all_clock_frames_exact)
	check("absolute_movie_frame_144_is_exactly_4_8", preview.movie_frame_count == 144 and preview.movie_time == 144.0 / 30.0 and preview.movie_time == 4.8)
	check("pause_does_not_skip_movie_time_on_resume", preview.frame_count == 146 and preview.movie_frame_count == 144)
	preview.player.clear()
	preview.status.free()
	pool_parent.free()
	preview.free()

func finish() -> void:
	var passed: bool = true
	for item in checks: passed = passed and item["pass"]
	var report: Dictionary = {"schema": "riverstone.voxel.cell_animation.test_report.v1", "passed": passed,
		"checks": checks, "input": options.input, "oracle": options.get("oracle"),
		"source_id": data.get("source_id"), "master_hash": data.get("master_hash"),
		"clip_hash": data.get("cell_animation", {}).get("clip_hash"), "godot": Engine.get_version_info().string,
		"mode": "headless_numerical_validation_no_visual_evidence", "threshold_boundary_tolerance": 0.00000001, "minimum_offset_tolerance": 0.00000001, "expiry_tolerance": "min(1e-8, lifetime * 1e-6)", "headless_renderer_limit": "Numerical buffers and resource identities verified; dummy renderer does not provide transform/color readback. Graphical evidence required separately."}
	if options.has("report"):
		var parent: String = String(options.report).get_base_dir()
		if not parent.is_empty(): DirAccess.make_dir_recursive_absolute(parent)
		var file: FileAccess = FileAccess.open(options.report, FileAccess.WRITE)
		if file == null:
			printerr("Cannot write test report: " + error_string(FileAccess.get_open_error()))
			passed = false
		else: file.store_string(JSON.stringify(report, "  ") + "\n")
	print("CELL_ANIMATION_CHECKS=" + JSON.stringify(report))
	player.clear()
	if asset != null: asset.free()
	quit(0 if passed else 1)
