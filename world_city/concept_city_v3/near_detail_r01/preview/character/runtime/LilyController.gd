extends CharacterBody3D
## Feet-root, metre-space controller. Shared scene owns the real collision world.
## No auto-jump, point snapping, hidden floor, step teleport or route correction.
const VisualScript = preload("LilyVisual.gd")
@export var player_input_enabled := true
@export var camera_enabled := true
@export var cache_dir := ""
@export var walk_speed_mps := 1.65
@export var run_speed_mps := 3.2
@export var acceleration_mps2 := 10.0
@export var gravity_mps2 := 18.0
var visual: Node3D
var camera_pivot: Node3D
var camera: Camera3D
var camera_yaw := PI
var camera_pitch := -0.15
var requested_world_direction := Vector3.ZERO
var requested_speed := 0.0
var replay_enabled := false
var replay_frames: Array = []
var replay_index := 0
var replay_tick := 0
var simulation_tick := 0
var ground_loss_frames := 0
var blocked_frames := 0
var distance_walked_m := 0.0
var initialized := false
var load_error := ""
var _shape: CollisionShape3D

func _ready() -> void:
	name = "LilyPlayer"
	collision_layer = 2
	collision_mask = 1
	floor_snap_length = 0.20
	floor_max_angle = deg_to_rad(45.0)
	floor_stop_on_slope = true
	floor_constant_speed = true
	safe_margin = 0.001
	up_direction = Vector3.UP
	visual = VisualScript.new()
	add_child(visual)
	load_error = visual.load_character(cache_dir)
	if not load_error.is_empty():
		push_error(load_error)
		set_physics_process(false)
		return
	var capsule := CapsuleShape3D.new()
	capsule.radius = float(visual.rig.capsule.radius_m)
	capsule.height = float(visual.rig.capsule.height_m)
	_shape = CollisionShape3D.new()
	_shape.name = "GameplayCapsule"
	_shape.shape = capsule
	_shape.position = VisualScript.CommonRender.vector(visual.rig.capsule.center_m)
	add_child(_shape)
	if camera_enabled: _build_camera()
	initialized = true

func _build_camera() -> void:
	camera_pivot = Node3D.new()
	camera_pivot.name = "CameraPivot"
	camera_pivot.position = Vector3(0, float(visual.rig.capsule.height_m) * 0.756, 0)
	add_child(camera_pivot)
	var arm := SpringArm3D.new()
	arm.spring_length = 3.8
	arm.margin = 0.12
	arm.collision_mask = 1
	arm.add_excluded_object(get_rid())
	var sphere := SphereShape3D.new()
	sphere.radius = 0.12
	arm.shape = sphere
	camera_pivot.add_child(arm)
	camera = Camera3D.new()
	camera.fov = 46
	camera.near = 0.06
	camera.current = true
	arm.add_child(camera)
	_update_camera()

func _update_camera() -> void:
	if camera_pivot != null: camera_pivot.rotation = Vector3(camera_pitch, camera_yaw, 0)

func _unhandled_input(event: InputEvent) -> void:
	if not player_input_enabled or not camera_enabled: return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if event.pressed else Input.MOUSE_MODE_VISIBLE
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		camera_yaw -= event.relative.x * 0.004
		camera_pitch = clampf(camera_pitch - event.relative.y * 0.003, -0.65, 0.25)
		_update_camera()
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_ESCAPE: Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		if event.physical_keycode == KEY_1: visual.set_expression("neutral")
		if event.physical_keycode == KEY_2: visual.set_expression("happy")
		if event.physical_keycode == KEY_3: visual.set_expression("focused")

func set_control(world_direction: Vector3, speed_mps: float) -> bool:
	if not world_direction.is_finite() or not is_finite(speed_mps): return false
	world_direction.y = 0
	requested_world_direction = world_direction.normalized() if world_direction.length_squared() > 0.0001 else Vector3.ZERO
	requested_speed = clampf(speed_mps, 0.0, run_speed_mps)
	return true

func load_replay(value: Dictionary) -> String:
	# Data has direction/speed input only, never output positions to snap to.
	if value.get("schema") != "riverstone.character.input_replay.v1": return "Unsupported replay schema"
	if int(value.get("physics_hz", 0)) != Engine.physics_ticks_per_second: return "Replay physics rate must match engine"
	if not value.get("frames") is Array or value.frames.is_empty(): return "Replay frames required"
	var previous := -1
	for frame in value.frames:
		if not frame is Dictionary: return "Replay frame must be an object"
		var tick: Variant = frame.get("tick")
		if not VisualScript.CommonRender.finite_number(tick) or float(tick) != floorf(float(tick)) or tick < 0 or tick <= previous: return "Replay integer ticks must strictly increase"
		if frame.size() != 3 or not frame.has("direction") or not frame.has("speed_mps"): return "Replay frames permit only tick, direction and speed inputs"
		if not VisualScript.CommonRender.vector_ok(frame.get("direction")) or not VisualScript.CommonRender.finite_number(frame.get("speed_mps")): return "Finite direction and speed required"
		previous = int(tick)
	replay_frames = value.frames.duplicate(true)
	replay_index = 0
	replay_tick = 0
	replay_enabled = true
	player_input_enabled = false
	return ""

func _read_player_input() -> void:
	var x := float(Input.is_physical_key_pressed(KEY_D)) - float(Input.is_physical_key_pressed(KEY_A))
	var y := float(Input.is_physical_key_pressed(KEY_S)) - float(Input.is_physical_key_pressed(KEY_W))
	var local := Vector3(x, 0, y)
	var direction := Basis(Vector3.UP, camera_yaw) * local
	set_control(direction, run_speed_mps if Input.is_physical_key_pressed(KEY_SHIFT) else walk_speed_mps)

func _physics_process(delta: float) -> void:
	if not initialized: return
	if replay_enabled:
		while replay_index < replay_frames.size() and int(replay_frames[replay_index].tick) <= replay_tick:
			var frame: Dictionary = replay_frames[replay_index]
			set_control(VisualScript.CommonRender.vector(frame.direction), float(frame.speed_mps))
			replay_index += 1
		replay_tick += 1
	elif player_input_enabled: _read_player_input()
	simulate_control(delta)

func simulate_control(delta: float) -> void:
	if not initialized or delta <= 0 or not is_finite(delta): return
	var target := requested_world_direction * requested_speed
	velocity.x = move_toward(velocity.x, target.x, acceleration_mps2 * delta)
	velocity.z = move_toward(velocity.z, target.z, acceleration_mps2 * delta)
	velocity.y = -0.25 if is_on_floor() else velocity.y - gravity_mps2 * delta
	var before := global_position
	move_and_slide()
	var moved := global_position - before
	var horizontal := Vector3(moved.x, 0, moved.z)
	var actual_speed := horizontal.length() / delta
	distance_walked_m += horizontal.length()
	if not is_on_floor(): ground_loss_frames += 1
	if requested_speed > 0.1 and requested_world_direction.length_squared() > 0.1 and actual_speed < 0.05: blocked_frames += 1
	if horizontal.length_squared() > 0.000001:
		visual.rotation.y = lerp_angle(visual.rotation.y, atan2(horizontal.x, horizontal.z), minf(1.0, delta * 14))
	visual.set_locomotion(actual_speed)
	visual.advance(delta)
	simulation_tick += 1

func set_expression(value: String) -> bool:
	return visual.set_expression(value) if initialized else false

func debug_state() -> Dictionary:
	return {"ready": initialized, "load_error": load_error, "tick": simulation_tick,
		"feet_position_m": [global_position.x, global_position.y, global_position.z],
		"velocity_mps": [velocity.x, velocity.y, velocity.z], "on_floor": is_on_floor(),
		"capsule_radius_m": _shape.shape.radius if _shape != null else 0.0, "capsule_height_m": _shape.shape.height if _shape != null else 0.0,
		"ground_loss_frames": ground_loss_frames, "blocked_frames": blocked_frames,
		"distance_walked_m": distance_walked_m, "replay_tick": replay_tick,
		"replay_inputs_consumed": replay_index, "hidden_jump_or_snap": false,
		"visual": visual.debug_state() if initialized else {}}
