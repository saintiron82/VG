extends SceneTree
const VoxelData = preload("res://RenderData.gd")
const Tracks = preload("res://AnimationTracks.gd")
var checks: Array = []
var assets: Array = []
var players: Array = []

func _initialize() -> void:
	call_deferred("run_checks")

func check(id: String, passed: bool, detail: Variant = null) -> void:
	checks.append({"id": id, "pass": passed, "detail": detail})

func signatures(node: Node) -> Array:
	var result: Array = []
	if node is MeshInstance3D: result.append([node.mesh.get_instance_id(), hash(var_to_bytes(node.mesh.surface_get_arrays(0)))])
	for child in node.get_children(): result.append_array(signatures(child))
	return result

func angle(player) -> float:
	return float(player.state().tracks[0].rotation_degrees)

func run_checks() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 4:
		printerr("Expected left render, right render, clip, output report")
		quit(1)
		return
	var clip: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[2]))
	var initial_signatures: Array = []
	for path in [args[0], args[1]]:
		var result := VoxelData.read(path)
		if result.has("error"):
			printerr(result.error); quit(1); return
		var asset := VoxelData.build(result.data)
		root.add_child(asset)
		assets.append(asset)
		initial_signatures.append(signatures(asset))
		var player := Tracks.new()
		var problem := player.configure(clip, asset)
		check("bind_part_" + str(result.data.pitch), problem.is_empty(), problem)
		if not problem.is_empty(): quit(1); return
		players.append(player)
	var player = players[0]
	check("initial_closed", is_zero_approx(angle(player)))
	player.seek(2.4)
	check("exact_open_key_105", is_equal_approx(angle(player), 105.0), angle(player))
	player.seek(5.2)
	check("return_closed_key", is_zero_approx(angle(player)), angle(player))
	player.seek(1.5)
	check("smoothstep_midpoint", is_equal_approx(angle(player), 52.5), angle(player))
	player.pause()
	var held: Dictionary = player.state()
	player.advance(2.0)
	check("pause_does_not_advance", player.state() == held)
	player.seek(2.4)
	check("seek_while_paused", not player.playing and is_equal_approx(angle(player), 105.0))
	player.seek(6.6)
	check("loop_wrap", is_equal_approx(player.playhead, 0.6) and is_zero_approx(angle(player)))
	player.seek(-0.1)
	check("negative_loop_seek", is_equal_approx(player.playhead, 5.9) and is_zero_approx(angle(player)))
	player.play()
	player.seek(5.9)
	player.advance(0.2)
	check("advance_crosses_loop", is_equal_approx(player.playhead, 0.1))
	player.seek(2.4)
	player.configure(clip, assets[0])
	check("rebind_uses_immutable_rest", is_zero_approx(angle(player)) and players[0].bindings[0].node.basis.is_equal_approx(Basis.IDENTITY))
	var max_pivot_error := 0.0
	var max_phase_error := 0.0
	for frame in range(721):
		var seconds := frame / 60.0
		for p in players: p.seek(seconds)
		max_phase_error = maxf(max_phase_error, absf(angle(players[0])-angle(players[1])))
		for p in players:
			for binding in p.bindings:
				max_pivot_error = maxf(max_pivot_error, binding.node.position.distance_to(Tracks.vec(binding.pivot_world)))
	check("same_angle_across_pitches", max_phase_error < 0.000001, max_phase_error)
	check("master_pivot_fixed_for_two_loops", max_pivot_error < 0.000001, max_pivot_error)
	check("same_master_pivot_across_pitches", players[0].bindings[0].pivot_world == players[1].bindings[0].pivot_world, players[0].bindings[0].pivot_world)
	var unchanged := true
	for index in range(assets.size()):
		unchanged = unchanged and signatures(assets[index]) == initial_signatures[index] and assets[index].transform == Transform3D.IDENTITY
	check("immutable_meshes_and_asset_origins", unchanged)
	player.stop()
	check("stop_resets_rest", not player.playing and is_zero_approx(player.playhead) and is_zero_approx(angle(player)))
	var invalid := clip.duplicate(true)
	invalid.duration = 0
	check("reject_zero_duration", not Tracks.validate(invalid).is_empty())
	invalid = clip.duplicate(true)
	invalid.tracks[0].keys[1].time = invalid.tracks[0].keys[0].time
	check("reject_duplicate_key_times", not Tracks.validate(invalid).is_empty())
	invalid = clip.duplicate(true)
	invalid.tracks[0].keys[-1].rotation_degrees = 5
	check("reject_loop_seam_jump", not Tracks.validate(invalid).is_empty())
	invalid = clip.duplicate(true)
	invalid.tracks[0].selector.instance = "nonexistent_binding"
	check("reject_unknown_selector", not player.configure(invalid, assets[0]).is_empty())
	invalid = clip.duplicate(true)
	invalid.master_hash = "different_master"
	check("reject_mismatched_geometry", not player.configure(invalid, assets[0]).is_empty())
	var non_loop := clip.duplicate(true)
	non_loop.loop = false
	player.configure(non_loop, assets[0])
	player.seek(100)
	check("nonloop_seek_clamps", is_equal_approx(player.playhead, 6.0) and is_zero_approx(angle(player)))
	var passed := true
	for item in checks:
		if not item["pass"]: passed = false
	var report := {"schema":"riverstone.voxel.animation.test_report.v1", "passed":passed, "checks":checks, "godot":Engine.get_version_info().string, "master_hash":clip.master_hash, "render_inputs":[args[0],args[1]], "mode":"headless_transform_evaluation_no_physics_or_render_capture"}
	FileAccess.open(args[3], FileAccess.WRITE).store_string(JSON.stringify(report, "  ")+"\n")
	print("ANIMATION_CHECKS="+JSON.stringify(report))
	for asset in assets: asset.free()
	quit(0 if passed else 1)
