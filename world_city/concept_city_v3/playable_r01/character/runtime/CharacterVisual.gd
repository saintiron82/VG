extends Node3D
## Shared appearance hierarchy adapter; common mesher/player copies are byte-identical.
## No per-frame voxel generation, mesh construction or Resource creation.
const CommonRender = preload("../generated/r5/common/RenderData.gd")
const CommonTracks = preload("../generated/r5/common/TransformTracks.gd")

var asset: Node3D
var rig: Dictionary = {}
var clips: Dictionary = {}
var part_nodes: Dictionary = {}
var motion = CommonTracks.new()
var blink = CommonTracks.new()
var expression = CommonTracks.new()
var motion_name := "idle"
var expression_name := "neutral"
var locomotion_speed := 0.0
var initialized := false
var _rest: Dictionary = {}
var _transition_from: Dictionary = {}
var _transition_elapsed := 0.2
const TRANSITION_SECONDS := 0.18

func _read_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null: return {"error": "Cannot read " + path}
	var value: Variant = JSON.parse_string(file.get_as_text())
	if not value is Dictionary: return {"error": "Invalid object in " + path}
	return value

func load_character(data_dir: String = "") -> String:
	if data_dir.is_empty(): data_dir = get_script().resource_path.get_base_dir().path_join("../generated/r5").simplify_path()
	if initialized: return "Character is already loaded; use a new instance"
	var result: Dictionary = CommonRender.read(data_dir.path_join("lily.render.json"))
	if result.has("error"): return result.error
	rig = _read_json(data_dir.path_join("rig.json"))
	if rig.has("error"): return rig.error
	if rig.get("schema") != "riverstone.character.rig.v1" or rig.get("master_hash") != result.data.get("master_hash"): return "Rig source mismatch"
	for key in ["idle", "walk", "blink", "expression_neutral", "expression_happy", "expression_focused"]:
		clips[key] = _read_json(data_dir.path_join(key + ".json"))
		if clips[key].has("error"): return clips[key].error
		var problem: String = CommonTracks.validate(clips[key])
		if not problem.is_empty(): return problem
	asset = CommonRender.build(result.data)
	asset.name = str(result.data.source_id)
	add_child(asset)
	var bindings: Array = asset.get_meta("rigid_parts")
	var records: Dictionary = {}
	for binding in bindings:
		var id: String = binding.selector.part
		part_nodes[id] = binding.node
		binding.node.name = id
		records[id] = binding
	# Source order is topological, all authored bases are identity. The child
	# mesh retains pivot-local vertices; only the parent's local pivot is removed.
	var built: Dictionary = {}
	for part in rig.parts:
		var id: String = part.id
		if not part_nodes.has(id): return "Missing geometry: " + id
		var node: Node3D = part_nodes[id]
		if part.parent != null:
			if not built.has(part.parent): return "Rig parent order/cycle error: " + id
			var parent: Node3D = part_nodes[part.parent]
			node.reparent(parent, false)
			node.position = CommonRender.vector(part.pivot_m) - CommonRender.vector(records[part.parent].pivot_world)
		records[id].rest_transform = node.transform
		_rest[id] = node.transform
		built[id] = true
	asset.set_meta("rigid_parts", bindings)
	for binding in [[motion, clips.idle], [blink, clips.blink], [expression, clips.expression_neutral]]:
		var problem: String = binding[0].configure(binding[1], asset)
		if not problem.is_empty(): return problem
	initialized = true
	return ""

func set_locomotion(speed_mps: float) -> void:
	if not initialized or not is_finite(speed_mps): return
	locomotion_speed = maxf(0.0, speed_mps)
	var next_name := "walk" if locomotion_speed > 0.08 else "idle"
	if next_name == motion_name: return
	_transition_from.clear()
	for id in rig.motion_channels.locomotion: _transition_from[id] = part_nodes[id].transform
	_transition_elapsed = 0.0
	motion_name = next_name
	var problem: String = motion.configure(clips[motion_name], asset)
	assert(problem.is_empty(), problem)

func set_expression(value: String) -> bool:
	if not initialized or not clips.has("expression_" + value): return false
	expression_name = value
	return expression.configure(clips["expression_" + value], asset).is_empty()

func seek_motion(seconds: float) -> bool:
	if not initialized: return false
	_transition_from.clear()
	_transition_elapsed = TRANSITION_SECONDS
	return motion.seek(seconds)

func seek_blink(seconds: float) -> bool:
	return blink.seek(seconds) if initialized else false

func advance(delta: float) -> void:
	if not initialized or not is_finite(delta) or delta < 0.0: return
	var rate := clampf(locomotion_speed / float(rig.locomotion.nominal_walk_speed_mps), 0.35, 2.0) if motion_name == "walk" else 1.0
	motion.advance(delta * rate)
	blink.advance(delta)
	if _transition_elapsed < TRANSITION_SECONDS:
		_transition_elapsed = minf(TRANSITION_SECONDS, _transition_elapsed + delta)
		var weight := smoothstep(0.0, 1.0, _transition_elapsed / TRANSITION_SECONDS)
		for id in _transition_from:
			part_nodes[id].transform = _transition_from[id].interpolate_with(part_nodes[id].transform, weight)

func parts() -> Dictionary:
	return part_nodes.duplicate()

func debug_state() -> Dictionary:
	return {"ready": initialized, "motion": motion_name, "expression": expression_name,
		"speed_mps": locomotion_speed, "part_count": part_nodes.size(),
		"motion_state": motion.state(), "blink_state": blink.state(),
		"mesh_resources_immutable": true, "hierarchy_space": "parent-local transforms; source world pivots retained as metadata"}
