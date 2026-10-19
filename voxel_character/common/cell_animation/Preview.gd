extends Node3D
## Standalone render.v1 preview. Asset identity never controls rendering or animation.
const VoxelData = preload("res://RenderData.gd")
const CellPools = preload("res://CellPools.gd")

var options: Dictionary = {"time": "0", "frames": "0", "yaw": "-32", "elevation": "22"}
var data: Dictionary = {}
var input_sha256: String = ""
var player = CellPools.new()
var asset: Node3D
var camera: Camera3D
var status: Label
var union_bounds: AABB
var frame_count: int = 0
var frame_limit: int = 0
var closing: bool = false
var ready_for_frames: bool = false
var screenshot_saved: bool = false
var screenshot_size := Vector2i.ZERO
var movie_mode: bool = false
var movie_time: float = 0.0
var movie_start_time: float = 0.0
var movie_frame_count: int = 0
var movie_fps: float = 30.0
var movie_step: float = 1.0 / 30.0
var static_signature_at_load: Array = []

func _ready() -> void:
	set_process(false)
	var problem: String = parse_options()
	if options.has("help"):
		print(help_text())
		get_tree().quit()
		return
	if not problem.is_empty(): fail(problem); return
	var result: Dictionary = VoxelData.read(options.input)
	if result.has("error"): fail(result.error); return
	data = result.data
	input_sha256 = result.sha256
	problem = CellPools.validate(data)
	if not problem.is_empty(): fail(problem); return
	union_bounds = VoxelData.bounds_of(data)
	if data.has("cell_animation"):
		var bounds: Dictionary = data.cell_animation.bounds
		union_bounds = union_bounds.merge(AABB(VoxelData.vector(bounds.min), VoxelData.vector(bounds.max) - VoxelData.vector(bounds.min)))
	build_world()
	problem = player.configure(data, asset)
	if not problem.is_empty(): fail(problem); return
	static_signature_at_load = static_signatures(asset)
	player.seek(float(options.time))
	if options.has("paused"): player.pause()
	movie_start_time = float(options.time)
	movie_time = movie_start_time
	movie_frame_count = 0
	configure_movie_clock()
	frame_limit = int(options.frames)
	if options.has("output") and frame_limit == 0: frame_limit = 12
	update_camera()
	get_viewport().size_changed.connect(update_camera)
	update_status()
	if options.has("validate-only"):
		finish()
		return
	ready_for_frames = true
	set_process(true)

func parse_options() -> String:
	var allowed: Array = ["input", "time", "frames", "output", "report", "yaw", "elevation", "target", "size", "title", "capture-fps"]
	var flags: Array = ["help", "paused", "validate-only"]
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var index: int = 0
	while index < args.size():
		var argument: String = args[index]
		if not argument.begins_with("--"): return "Expected --option, got " + argument
		var separator: int = argument.find("=")
		var key: String = argument.substr(2, separator - 2) if separator >= 0 else argument.substr(2)
		if key in flags:
			if separator >= 0: return "Flag --%s does not take a value" % key
			options[key] = true
		elif key in allowed:
			if separator >= 0: options[key] = argument.substr(separator + 1)
			elif index + 1 < args.size() and not args[index + 1].begins_with("--"):
				index += 1
				options[key] = args[index]
			else: return "Missing value for --" + key
		else: return "Unknown option --" + key
		index += 1
	if options.has("help"): return ""
	if not options.has("input") or String(options.input).is_empty(): return "--input render.v1 JSON path required"
	if not String(options.frames).is_valid_int() or int(options.frames) < 0: return "--frames must be a nonnegative integer"
	for key in ["time", "yaw", "elevation", "size", "capture-fps"]:
		if options.has(key) and (not String(options[key]).is_valid_float() or not is_finite(float(options[key]))): return "--%s must be finite" % key
	if absf(float(options.elevation)) >= 89.0: return "--elevation must be between -89 and 89"
	if options.has("size") and float(options.size) <= 0.0: return "--size must be positive"
	if options.has("capture-fps") and float(options["capture-fps"]) <= 0.0: return "--capture-fps must be positive"
	if options.has("target"):
		var target: PackedStringArray = String(options.target).split(",")
		if target.size() != 3: return "--target requires x,y,z"
		for coordinate in target:
			if not coordinate.is_valid_float() or not is_finite(float(coordinate)): return "--target requires finite coordinates"
	if DisplayServer.get_name() == "headless" and not options.has("validate-only"): return "Headless preview is only for --validate-only; use graphical Godot for captures"
	if options.has("output"):
		if options.has("validate-only") or DisplayServer.get_name() == "headless": return "PNG evidence requires a graphical renderer"
		if not String(options.output).to_lower().ends_with(".png"): return "--output must be a PNG path"
	for key in ["output", "report"]:
		if options.has(key) and FileAccess.file_exists(options[key]): return "Refusing to overwrite evidence: " + str(options[key])
	return ""

func configure_movie_clock() -> void:
	movie_fps = float(ProjectSettings.get_setting("editor/movie_writer/fps", 30))
	var args: PackedStringArray = OS.get_cmdline_args()
	var index: int = 0
	while index < args.size():
		if args[index] == "--write-movie" or args[index].begins_with("--write-movie="): movie_mode = true
		if args[index] == "--fixed-fps" and index + 1 < args.size(): movie_fps = float(args[index + 1])
		elif args[index].begins_with("--fixed-fps="): movie_fps = float(args[index].get_slice("=", 1))
		index += 1
	# Engine startup may consume --write-movie/--fixed-fps before script access.
	# The explicit user option is therefore the authoritative capture clock.
	if options.has("capture-fps"):
		movie_mode = true
		movie_fps = float(options["capture-fps"])
	if movie_fps <= 0.0: movie_fps = 30.0
	movie_step = 1.0 / movie_fps

func build_world() -> void:
	var world_environment := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("e2e6e8")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color.WHITE
	environment.ambient_light_energy = 0.28
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world_environment.environment = environment
	add_child(world_environment)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-48.0, -35.0, 0.0)
	key.light_energy = 0.65
	key.shadow_enabled = true
	key.directional_shadow_max_distance = maxf(20.0, union_bounds.get_longest_axis_size() * 8.0)
	key.shadow_bias = 0.035
	add_child(key)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-24.0, 140.0, 0.0)
	fill.light_energy = 0.10
	add_child(fill)
	asset = VoxelData.build(data)
	add_child(asset)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2.ONE * union_bounds.get_longest_axis_size() * 6.0
	ground.mesh = plane
	ground.position = Vector3(union_bounds.get_center().x, union_bounds.position.y - 0.01, union_bounds.get_center().z)
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("d0d7da")
	material.roughness = 1.0
	ground.material_override = material
	add_child(ground)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.keep_aspect = Camera3D.KEEP_HEIGHT
	camera.current = true
	add_child(camera)
	var canvas := CanvasLayer.new()
	add_child(canvas)
	var title := Label.new()
	title.position = Vector2(22.0, 15.0)
	title.add_theme_color_override("font_color", Color("29343b"))
	title.add_theme_font_size_override("font_size", 25)
	title.text = str(options.get("title", "COMMON VOXEL / FIXED CELL POOLS"))
	canvas.add_child(title)
	status = Label.new()
	status.position = Vector2(22.0, 51.0)
	status.add_theme_color_override("font_color", Color("29343b"))
	status.add_theme_font_size_override("font_size", 17)
	canvas.add_child(status)
	var controls := Label.new()
	controls.text = "P pause/play · Left/Right seek · Home reset · Esc exit"
	controls.add_theme_color_override("font_color", Color("53616a"))
	controls.add_theme_font_size_override("font_size", 16)
	controls.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	controls.position = Vector2(22.0, get_viewport().get_visible_rect().size.y - 34.0)
	canvas.add_child(controls)

func update_camera() -> void:
	if camera == null: return
	var target: Vector3 = union_bounds.get_center()
	if options.has("target"):
		var values: PackedStringArray = String(options.target).split(",")
		target = Vector3(float(values[0]), float(values[1]), float(values[2]))
	var yaw: float = deg_to_rad(float(options.yaw))
	var elevation: float = deg_to_rad(float(options.elevation))
	var direction := Vector3(sin(yaw) * cos(elevation), sin(elevation), cos(yaw) * cos(elevation))
	var distance: float = maxf(1.0, union_bounds.get_longest_axis_size() * 3.0)
	camera.position = target + direction * distance
	camera.look_at(target, Vector3.UP)
	camera.near = maxf(0.001, distance * 0.0001)
	camera.far = distance * 10.0
	var inverse: Transform3D = camera.global_transform.affine_inverse()
	var low := Vector2(INF, INF)
	var high := Vector2(-INF, -INF)
	for index in range(8):
		var point: Vector3 = inverse * union_bounds.get_endpoint(index)
		low = low.min(Vector2(point.x, point.y))
		high = high.max(Vector2(point.x, point.y))
	var extent: Vector2 = high - low
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	var aspect: float = viewport_size.x / maxf(viewport_size.y, 1.0)
	camera.size = float(options.size) if options.has("size") else maxf(extent.y, extent.x / aspect) * 1.24

func update_status() -> void:
	status.text = "%s  /  pitch %.3f m  /  t %.2f s  /  evaluation %.2f s at %.1f Hz  /  %s" % [str(data.get("source_id", "render.v1")), float(data.pitch), player.playhead, player.evaluation_time, player.update_hz, "PLAYING" if player.playing else "PAUSED"]

func _process(delta: float) -> void:
	if closing or not ready_for_frames: return
	if movie_mode:
		# Use an explicit fixed-fps absolute clock; never wall-clock delta for capture.
		if player.playing and frame_count > 0:
			movie_frame_count += 1
			movie_time = movie_start_time + float(movie_frame_count) / movie_fps
			player.seek(movie_time)
	else:
		player.advance(delta)
	update_status()
	frame_count += 1
	if frame_limit > 0 and frame_count >= frame_limit: finish()

func _input(event: InputEvent) -> void:
	if closing or not ready_for_frames: return
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_ESCAPE: finish(); return
			KEY_P:
				if player.playing: player.pause()
				else: player.play()
			KEY_HOME: player.seek(0.0); movie_time = 0.0; movie_start_time = 0.0; movie_frame_count = 0
			KEY_LEFT: player.seek(player.playhead - 0.1); movie_time = player.playhead; movie_start_time = movie_time; movie_frame_count = 0
			KEY_RIGHT: player.seek(player.playhead + 0.1); movie_time = player.playhead; movie_start_time = movie_time; movie_frame_count = 0
		update_status()

func static_signatures(node: Node) -> Array:
	var result: Array = []
	if node is MeshInstance3D:
		result.append([node.mesh.get_instance_id(), hash(var_to_bytes(node.mesh.surface_get_arrays(0)))])
	for child in node.get_children(): result.append_array(static_signatures(child))
	return result

func ensure_parent(path: String) -> String:
	var directory: String = path.get_base_dir()
	if directory.is_empty(): return ""
	var result: Error = DirAccess.make_dir_recursive_absolute(directory)
	return "" if result == OK else "Cannot create output directory: " + error_string(result)

func finish() -> void:
	if closing: return
	closing = true
	set_process(false)
	if options.has("output"):
		await RenderingServer.frame_post_draw
		var screenshot: Image = get_viewport().get_texture().get_image()
		if screenshot == null or screenshot.is_empty(): fail("Graphical viewport returned no image"); return
		var problem: String = ensure_parent(options.output)
		if not problem.is_empty(): fail(problem); return
		var result: Error = screenshot.save_png(options.output)
		if result != OK: fail("Cannot save PNG: " + error_string(result)); return
		screenshot_saved = true
		screenshot_size = screenshot.get_size()
	var report: Dictionary = make_report()
	if options.has("report"):
		var problem: String = ensure_parent(options.report)
		if not problem.is_empty(): fail(problem); return
		var file: FileAccess = FileAccess.open(options.report, FileAccess.WRITE)
		if file == null: fail("Cannot write report: " + error_string(FileAccess.get_open_error())); return
		file.store_string(JSON.stringify(report, "  ") + "\n")
	print("CELL_PREVIEW_REPORT=" + JSON.stringify(report))
	get_tree().quit(0)

func make_report() -> Dictionary:
	return {"schema": "riverstone.voxel.cell_animation.preview_report.v1", "input": options.input,
		"render_file_sha256": input_sha256, "source_id": data.get("source_id"), "master_hash": data.get("master_hash"),
		"clip_hash": player.clip_hash, "state": player.state(), "frames": frame_count,
		"mode": "headless_validation" if DisplayServer.get_name() == "headless" else "graphical_preview",
		"movie_mode": movie_mode, "movie_fps": movie_fps if movie_mode else null, "movie_time": movie_time if movie_mode else null,
		"movie_clock_frame": movie_frame_count if movie_mode else null,
		"movie_clock_source": "explicit_capture_fps" if options.has("capture-fps") else ("engine_arguments" if movie_mode else "realtime_delta"),
		"static_mesh_resources_and_arrays_unchanged": static_signatures(asset) == static_signature_at_load,
		"camera": {"position": xyz(camera.position), "rotation_degrees": xyz(camera.rotation_degrees), "size": camera.size},
		"bounds": {"min": xyz(union_bounds.position), "max": xyz(union_bounds.end)},
		"screenshot_saved": screenshot_saved, "screenshot_path": options.get("output") if screenshot_saved else null,
		"screenshot_dimensions": [screenshot_size.x, screenshot_size.y] if screenshot_saved else null,
		"visual_review": "NOT_PERFORMED_BY_THIS_REPORT", "godot": Engine.get_version_info().string}

func xyz(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

func fail(problem: String) -> void:
	printerr("CELL_PREVIEW_ERROR: " + problem)
	get_tree().quit(1)

func help_text() -> String:
	return """Generic fixed-pool voxel preview
  --input=FILE       Any riverstone.voxel.render.v1 JSON, optional cell_animation
  --time=SECONDS     Initial direct seek, default 0
  --paused           Freeze animation at requested time
  --frames=N         Exit after N rendered frames; 0 is interactive
  --output=FILE.png  Save actual graphical viewport; default 12 frames
  --report=FILE.json Save lineage, state, resource and camera report
  --capture-fps=30   Explicit capture clock; match engine --fixed-fps value
  --yaw=-32 --elevation=22 --target=x,y,z --size=METRES
  --validate-only    Headless tiny-fixture validation, no image evidence
MovieMaker: godot4 --path PATH --write-movie FILE.avi --fixed-fps 30 -- --input=FILE --capture-fps=30 --frames=144
Existing evidence files are never overwritten. Headless rendering is not capture evidence."""
