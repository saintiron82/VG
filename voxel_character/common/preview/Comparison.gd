extends Node
## Two isolated worlds, identical cameras, no model scaling or asset-name dispatch.

const VoxelRenderData = preload("res://RenderData.gd")
const TransformTracks = preload("res://AnimationTracks.gd")
const VIEWS := ["orbit", "front", "detail"]
const TEXT_COLOR := Color("29343b")
const MUTED_COLOR := Color("53616a")
const AMBIENT_ENERGY := 0.28
const KEY_ENERGY := 0.65
const FILL_ENERGY := 0.10

var options: Dictionary = {"view": "orbit", "frames": "0", "yaw": "-32", "elevation": "22"}
var inputs: Array[Dictionary] = []
var input_sha256s: Array[String] = []
var cameras: Array[Camera3D] = []
var assets: Array[Node3D] = []
var mesh_ids_at_load: Array = []
var animation_players: Array = []
var animation_clip: Dictionary = {}
var animation_sha256 := ""
var animation_status: Label
var initialization_error := false
var viewports: Array[SubViewport] = []
var union_bounds: AABB
var footer: Label
var view_name := "orbit"
var yaw := -32.0
var elevation := 22.0
var zoom := 1.0
var detail_target := Vector3.ZERO
var detail_size := 1.0
var frame_count := 0
var frame_limit := 0
var ready_for_frames := false
var closing := false
var screenshot_saved := false
var screenshot_dimensions := Vector2i.ZERO

func _ready() -> void:
	set_process(false)
	var problem := parse_options()
	if options.has("help"):
		print(help_text())
		get_tree().quit()
		return
	if not problem.is_empty():
		fail(problem)
		return
	for side in ["left", "right"]:
		var result: Dictionary = VoxelRenderData.read(options[side])
		if result.has("error"):
			fail(result.error)
			return
		inputs.append(result.data)
		input_sha256s.append(result.sha256)
	problem = load_animation()
	if not problem.is_empty():
		fail(problem)
		return
	union_bounds = VoxelRenderData.bounds_of(inputs[0]).merge(VoxelRenderData.bounds_of(inputs[1]))
	view_name = options.view
	yaw = float(options.yaw)
	elevation = float(options.elevation)
	detail_target = union_bounds.get_center()
	detail_target.y = union_bounds.position.y + union_bounds.size.y * 0.35
	detail_target.z = union_bounds.end.z
	detail_size = union_bounds.get_longest_axis_size() * 0.42
	if options.has("detail-target"):
		var coordinates: PackedStringArray = options["detail-target"].split(",")
		detail_target = Vector3(float(coordinates[0]), float(coordinates[1]), float(coordinates[2]))
	if options.has("detail-size"):
		detail_size = float(options["detail-size"])
	frame_limit = int(options.frames)
	if options.has("output") and frame_limit == 0:
		frame_limit = 12
	build_ui()
	if initialization_error: return
	update_animation_label()
	# Let containers establish equal pixel dimensions before computing the fit.
	await get_tree().process_frame
	await get_tree().process_frame
	update_cameras()
	if options.has("validate-only"):
		finish()
		return
	ready_for_frames = true
	set_process(true)

func parse_options() -> String:
	var allowed := ["left", "right", "left-label", "right-label", "title", "view", "frames", "yaw", "elevation", "detail-target", "detail-size", "output", "report", "animation", "animation-time"]
	var flags := ["help", "validate-only", "paused"]
	var args := OS.get_cmdline_user_args()
	var index := 0
	while index < args.size():
		var argument: String = args[index]
		if not argument.begins_with("--"):
			return "Expected --option, got: " + argument
		var separator := argument.find("=")
		var key := argument.substr(2, separator - 2) if separator >= 0 else argument.substr(2)
		if key in flags:
			if separator >= 0:
				return "Flag --%s does not take a value" % key
			options[key] = true
		elif key in allowed:
			if separator >= 0:
				options[key] = argument.substr(separator + 1)
			elif index + 1 < args.size() and not args[index + 1].begins_with("--"):
				index += 1
				options[key] = args[index]
			else:
				return "Missing value for --" + key
		else:
			return "Unknown option: --" + key
		index += 1
	if options.has("help"):
		return ""
	for side in ["left", "right"]:
		if not options.has(side) or String(options[side]).is_empty():
			return "Both --left and --right render JSON paths are required"
	if not options.view in VIEWS:
		return "--view must be orbit, front, or detail"
	if not String(options.frames).is_valid_int() or int(options.frames) < 0:
		return "--frames must be a nonnegative integer (0 means interactive)"
	for key in ["yaw", "elevation", "detail-size", "animation-time"]:
		if options.has(key) and (not String(options[key]).is_valid_float() or not is_finite(float(options[key]))):
			return "--%s must be finite" % key
	if absf(float(options.elevation)) >= 89.0:
		return "--elevation must be between -89 and 89 degrees"
	if options.has("detail-size") and float(options["detail-size"]) <= 0.0:
		return "--detail-size must be positive"
	if options.has("detail-target"):
		var coordinates: PackedStringArray = options["detail-target"].split(",")
		if coordinates.size() != 3:
			return "--detail-target requires x,y,z world coordinates"
		for coordinate in coordinates:
			if not coordinate.is_valid_float() or not is_finite(float(coordinate)):
				return "--detail-target must contain finite world coordinates"
	if options.has("output"):
		if options.has("validate-only") or DisplayServer.get_name() == "headless":
			return "PNG capture requires a graphical renderer; --validate-only/headless cannot produce viewport evidence"
		if not String(options.output).to_lower().ends_with(".png"):
			return "--output must be a .png path"
	for key in ["output", "report"]:
		if options.has(key) and FileAccess.file_exists(options[key]):
			return "Refusing to replace existing evidence: " + String(options[key])
	return ""

func load_animation() -> String:
	if not options.has("animation"):
		if options.has("animation-time") or options.has("paused"): return "animation-time/paused requires --animation"
		return ""
	var file := FileAccess.open(options.animation, FileAccess.READ)
	if file == null: return "cannot read animation sidecar"
	var bytes := file.get_buffer(file.get_length())
	var parser := JSON.new()
	if parser.parse(bytes.get_string_from_utf8()) != OK or not parser.data is Dictionary: return "invalid animation JSON"
	animation_clip = parser.data
	var problem := TransformTracks.validate(animation_clip)
	if not problem.is_empty(): return problem
	var hasher := HashingContext.new()
	hasher.start(HashingContext.HASH_SHA256)
	hasher.update(bytes)
	animation_sha256 = hasher.finish().hex_encode()
	return ""

func mesh_ids(node: Node) -> Array:
	var result: Array = []
	if node is MeshInstance3D: result.append(node.mesh.get_instance_id())
	for child in node.get_children(): result.append_array(mesh_ids(child))
	return result

func update_animation_label() -> void:
	if animation_status == null or animation_players.is_empty(): return
	var state: Dictionary = animation_players[0].state()
	var values: Array = []
	for track in state.tracks: values.append("%.1f deg" % track.rotation_degrees)
	animation_status.text = "TRANSFORM CLIP / %s · t %.2f / %.2f s · %s · P pause/play · Left/Right seek · Home rewind" % ["PLAYING" if state.playing else "PAUSED", state.playhead, state.duration, ", ".join(values)]

func build_ui() -> void:
	var background := ColorRect.new()
	background.color = Color("e8ecee")
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(background)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 24)
	add_child(margin)
	var layout := VBoxContainer.new()
	layout.add_theme_constant_override("separation", 12)
	margin.add_child(layout)
	layout.add_child(make_label(options.get("title", "COMMON VOXEL / MATCHED WORLD SCALE"), 26, TEXT_COLOR))
	var same_master: bool = inputs[0].get("master_hash", "") != "" and inputs[0].get("master_hash") == inputs[1].get("master_hash")
	var subtitle := "Same master hash · independently sampled pitches · identical cameras · +Y up / +Z front" if same_master else "Different or unverified master hashes · identical world-space scale and cameras · +Y up / +Z front"
	layout.add_child(make_label(subtitle, 16, MUTED_COLOR))
	var panels := HBoxContainer.new()
	panels.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panels.add_theme_constant_override("separation", 16)
	layout.add_child(panels)
	for index in range(2):
		var panel := VBoxContainer.new()
		panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		panel.add_theme_constant_override("separation", 7)
		panels.add_child(panel)
		var side := "left" if index == 0 else "right"
		var data: Dictionary = inputs[index]
		var label_text: String = options.get(side + "-label", str(data.get("source_id", side)))
		panel.add_child(make_label("%s  /  pitch %s %s" % [label_text, str(data.pitch), str(data.get("unit", "m"))], 22, TEXT_COLOR))
		var counts := VoxelRenderData.stats(data)
		var cells := str(counts.cell_count) + " cells · " if counts.cell_count != null else ""
		panel.add_child(make_label("%s%s quads · %s triangles" % [cells, counts.quads, counts.triangles], 15, MUTED_COLOR))
		var container := SubViewportContainer.new()
		container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		container.size_flags_vertical = Control.SIZE_EXPAND_FILL
		container.stretch = true
		container.mouse_filter = Control.MOUSE_FILTER_IGNORE
		panel.add_child(container)
		var viewport := SubViewport.new()
		viewport.size = Vector2i(760, 760)
		viewport.own_world_3d = true
		viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
		viewport.msaa_3d = Viewport.MSAA_2X
		container.add_child(viewport)
		viewports.append(viewport)
		build_world(viewport, data)
		container.resized.connect(update_cameras)
	if not animation_clip.is_empty():
		animation_status = make_label("", 15, TEXT_COLOR)
		layout.add_child(animation_status)
	footer = make_label("", 16, TEXT_COLOR)
	layout.add_child(footer)
	layout.add_child(make_label("O orbit · F front · D detail · SPACE cycle · drag to orbit · wheel zoom · R reset · Esc exit", 15, MUTED_COLOR))

func make_label(value: String, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = value
	label.add_theme_color_override("font_color", color)
	label.add_theme_font_size_override("font_size", font_size)
	label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return label

func build_world(viewport: SubViewport, data: Dictionary) -> void:
	var world := Node3D.new()
	viewport.add_child(world)
	var environment_node := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("e2e6e8")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("ffffff")
	environment.ambient_light_energy = AMBIENT_ENERGY
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	environment_node.environment = environment
	world.add_child(environment_node)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-48.0, -35.0, 0.0)
	light.light_energy = KEY_ENERGY
	light.shadow_enabled = true
	light.directional_shadow_max_distance = maxf(20.0, union_bounds.get_longest_axis_size() * 8.0)
	light.shadow_bias = 0.035
	world.add_child(light)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-24.0, 140.0, 0.0)
	fill.light_energy = FILL_ENERGY
	world.add_child(fill)
	var asset := VoxelRenderData.build(data)
	world.add_child(asset)
	assets.append(asset)
	mesh_ids_at_load.append(mesh_ids(asset))
	if not animation_clip.is_empty():
		var player := TransformTracks.new()
		var problem := player.configure(animation_clip, asset)
		if not problem.is_empty():
			initialization_error = true
			fail(problem)
			return
		player.seek(float(options.get("animation-time", "0")))
		if options.has("paused"): player.pause()
		animation_players.append(player)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	var span: float = union_bounds.get_longest_axis_size()
	plane.size = Vector2.ONE * span * 6.0
	ground.mesh = plane
	ground.position = Vector3(union_bounds.get_center().x, union_bounds.position.y - span * 0.002, union_bounds.get_center().z)
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("d0d7da")
	material.roughness = 1.0
	ground.material_override = material
	world.add_child(ground)
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.keep_aspect = Camera3D.KEEP_HEIGHT
	camera.current = true
	world.add_child(camera)
	cameras.append(camera)

func update_cameras() -> void:
	if cameras.size() != 2 or viewports.size() != 2:
		return
	var target := union_bounds.get_center()
	var direction := Vector3(sin(deg_to_rad(yaw)) * cos(deg_to_rad(elevation)), sin(deg_to_rad(elevation)), cos(deg_to_rad(yaw)) * cos(deg_to_rad(elevation)))
	if view_name == "front":
		direction = Vector3(0.0, 0.0, 1.0)
	elif view_name == "detail":
		target = detail_target
		direction = Vector3(-0.15, 0.08, 1.0).normalized()
	var distance: float = maxf(1.0, union_bounds.get_longest_axis_size() * 3.0)
	for camera in cameras:
		camera.position = target + direction * distance
		camera.look_at(target, Vector3.UP)
		camera.near = maxf(0.001, distance * 0.0001)
		camera.far = distance * 10.0
	var inverse := cameras[0].global_transform.affine_inverse()
	var low := Vector2(INF, INF)
	var high := Vector2(-INF, -INF)
	for index in range(8):
		var point: Vector3 = inverse * union_bounds.get_endpoint(index)
		low = low.min(Vector2(point.x, point.y))
		high = high.max(Vector2(point.x, point.y))
	var extent := high - low
	var aspect: float = minf(float(viewports[0].size.x) / maxf(1.0, viewports[0].size.y), float(viewports[1].size.x) / maxf(1.0, viewports[1].size.y))
	var size: float = detail_size if view_name == "detail" else maxf(extent.y, extent.x / aspect) * 1.14
	for camera in cameras:
		camera.size = size * zoom
	if footer:
		footer.text = "%s · shared vertical span %.3f m · scale 1:1 in world units · %s" % [view_name.to_upper(), cameras[0].size, "detail is an intentional crop" if view_name == "detail" else "complete union bounds framed"]

func _input(event: InputEvent) -> void:
	if not ready_for_frames or closing:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_O: view_name = "orbit"; zoom = 1.0
			KEY_F: view_name = "front"; zoom = 1.0
			KEY_D: view_name = "detail"; zoom = 1.0
			KEY_SPACE: view_name = VIEWS[(VIEWS.find(view_name) + 1) % VIEWS.size()]; zoom = 1.0
			KEY_R: yaw = float(options.yaw); elevation = float(options.elevation); zoom = 1.0
			KEY_ESCAPE: finish(); return
			KEY_P:
				for player in animation_players:
					if player.playing: player.pause()
					else: player.play()
			KEY_HOME:
				for player in animation_players: player.seek(0.0)
			KEY_LEFT:
				for player in animation_players: player.seek(player.playhead - 0.25)
			KEY_RIGHT:
				for player in animation_players: player.seek(player.playhead + 0.25)
		update_cameras()
	elif event is InputEventMouseMotion and event.button_mask & MOUSE_BUTTON_MASK_LEFT:
		view_name = "orbit"
		yaw -= event.relative.x * 0.3
		elevation = clampf(elevation + event.relative.y * 0.25, -80.0, 80.0)
		update_cameras()
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			zoom = maxf(0.1, zoom / 1.12)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			zoom = minf(10.0, zoom * 1.12)
		update_cameras()

func _process(delta: float) -> void:
	if closing:
		return
	for player in animation_players: player.advance(delta)
	update_animation_label()
	frame_count += 1
	if frame_limit > 0 and frame_count >= frame_limit:
		finish()

func finish() -> void:
	if closing:
		return
	closing = true
	set_process(false)
	if options.has("output"):
		# This is the actual composed Godot viewport, including both rendered worlds.
		await RenderingServer.frame_post_draw
		var image := get_viewport().get_texture().get_image()
		if image == null or image.is_empty():
			fail("Graphical viewport returned no image; no screenshot evidence saved")
			return
		var problem := ensure_parent(options.output)
		if not problem.is_empty():
			fail(problem)
			return
		var status := image.save_png(options.output)
		if status != OK:
			fail("Cannot save viewport PNG: " + error_string(status))
			return
		screenshot_saved = true
		screenshot_dimensions = image.get_size()
	var report := make_report()
	if options.has("report"):
		var problem := ensure_parent(options.report)
		if not problem.is_empty():
			fail(problem)
			return
		var file := FileAccess.open(options.report, FileAccess.WRITE)
		if file == null:
			fail("Cannot write report: " + error_string(FileAccess.get_open_error()))
			return
		file.store_string(JSON.stringify(report, "\t") + "\n")
	print("COMMON_VIEWER_REPORT=" + JSON.stringify(report))
	get_tree().quit(0)

func ensure_parent(path: String) -> String:
	var parent := path.get_base_dir()
	if not parent.is_empty():
		var status := DirAccess.make_dir_recursive_absolute(parent)
		if status != OK:
			return "Cannot create output folder: " + error_string(status)
	return ""

func make_report() -> Dictionary:
	var model_reports: Array = []
	for index in range(inputs.size()):
		var data: Dictionary = inputs[index]
		var counts := VoxelRenderData.stats(data)
		model_reports.append({"path": options["left" if index == 0 else "right"], "render_file_sha256": input_sha256s[index], "source_id": data.get("source_id"), "source_revision": data.get("source_revision"), "master_hash": data.get("master_hash"), "payload_hash": data.get("payload_hash"), "pitch": data.pitch, "grid_origin": data.grid_origin, "bounds": data.bounds, "quads": counts.quads, "triangles": counts.triangles, "cell_count": counts.cell_count, "model_scale": [1, 1, 1]})
	var camera_reports: Array = []
	for index in range(cameras.size()):
		var camera: Camera3D = cameras[index]
		camera_reports.append({"position": xyz(camera.position), "rotation_degrees": xyz(camera.rotation_degrees), "orthographic_size": camera.size, "viewport_size": [viewports[index].size.x, viewports[index].size.y]})
	var states: Array = []
	var unchanged := true
	for index in range(assets.size()):
		unchanged = unchanged and mesh_ids(assets[index]) == mesh_ids_at_load[index] and assets[index].transform.is_equal_approx(Transform3D.IDENTITY)
	for player in animation_players: states.append(player.state())
	return {"animation": {"sidecar_sha256": animation_sha256, "states": states, "same_phase": states.is_empty() or states[0] == states[1], "mesh_resources_and_asset_roots_unchanged": unchanged, "simulation": "visual_transform_only_no_physics"}, "schema": "riverstone.voxel.preview.report.v1", "mode": "headless_validation" if options.has("validate-only") else "graphical_preview", "view": view_name, "frames": frame_count, "models": model_reports, "cameras": camera_reports, "lighting": {"ambient_energy": AMBIENT_ENERGY, "key_energy": KEY_ENERGY, "fill_energy": FILL_ENERGY, "tonemap": "linear", "key_rotation_degrees": [-48, -35, 0], "fill_rotation_degrees": [-24, 140, 0]}, "same_camera_transform": cameras[0].transform.is_equal_approx(cameras[1].transform), "same_camera_scale": is_equal_approx(cameras[0].size, cameras[1].size), "same_viewport_dimensions": viewports[0].size == viewports[1].size, "same_master_hash": inputs[0].get("master_hash", "") != "" and inputs[0].get("master_hash") == inputs[1].get("master_hash"), "screenshot_saved": screenshot_saved, "screenshot_path": options.get("output", null) if screenshot_saved else null, "screenshot_dimensions": [screenshot_dimensions.x, screenshot_dimensions.y] if screenshot_saved else null, "visual_review": "NOT_PERFORMED_BY_THIS_REPORT", "godot_version": Engine.get_version_info().string}

func xyz(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

func fail(problem: String) -> void:
	printerr("COMMON_VIEWER_ERROR: " + problem)
	get_tree().quit(1)

func help_text() -> String:
	return """Generic matched-scale Godot voxel viewer
godot --path /absolute/path/common/preview -- --left=/path/a.render.json --right=/path/b.render.json
  --view=orbit|front|detail      Shared camera preset (front is +Z)
  --left-label=TEXT --right-label=TEXT --title=TEXT
  --yaw=-32 --elevation=22      Orbit camera angles in degrees
  --detail-target=x,y,z         Same world-space crop target for both models
  --detail-size=METRES          Shared vertical span for detail crop
  --output=/path/capture.png    Actual graphical viewport PNG, then exit
  --frames=12                  Frames before capture/exit; 0 is interactive
  --report=/path/report.json    Camera/lineage/count/capture evidence
  --animation=/path/clip.json   Optional data-driven rigid part transform clip
  --animation-time=SECONDS     Seek before starting (default zero)
  --paused                     Start transform playback paused
  --validate-only              Build tiny test meshes and cameras, report, exit
Use --headless with --validate-only only, never as a screenshot substitute.
Paths are absolute or res:// relative to this preview project. Existing output files are not overwritten."""
