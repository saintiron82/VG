extends RefCounted
## Canonical transform-track player. Rest geometry/resources never change.
## Deploy through sync_runtime.py; never hand-edit the preview copy.
const SCHEMA := "riverstone.voxel.transform_animation.v1"
var clip: Dictionary = {}
var bindings: Array = []
var playhead := 0.0
var playing := true

static func finite(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value))

static func vector_ok(value: Variant) -> bool:
	return value is Array and value.size() == 3 and finite(value[0]) and finite(value[1]) and finite(value[2])

static func vec(value: Array) -> Vector3:
	return Vector3(float(value[0]), float(value[1]), float(value[2]))

static func basis_rows(rows: Array) -> Basis:
	return Basis(Vector3(rows[0][0], rows[1][0], rows[2][0]), Vector3(rows[0][1], rows[1][1], rows[2][1]), Vector3(rows[0][2], rows[1][2], rows[2][2]))

static func validate(value: Dictionary) -> String:
	if value.get("schema") != SCHEMA: return "unsupported transform animation schema"
	if not finite(value.get("duration")) or float(value.duration) <= 0: return "positive finite duration required"
	if not value.get("loop") is bool: return "explicit loop boolean required"
	if not value.get("tracks") is Array or value.tracks.is_empty(): return "nonempty tracks required"
	var ids: Dictionary = {}
	var selectors: Dictionary = {}
	for track in value.tracks:
		if not track is Dictionary or track.get("type") != "rigid_transform": return "only rigid_transform tracks supported"
		if not track.get("id") is String or track.id.is_empty() or ids.has(track.id): return "unique track ID required"
		ids[track.id] = true
		var selector: Variant = track.get("selector")
		if not selector is Dictionary or selector.size() != 2 or not selector.get("instance") is String or not selector.get("part") is String: return "instance+part selector required"
		var key := JSON.stringify([selector.instance, selector.part])
		if selectors.has(key): return "duplicate target track"
		selectors[key] = true
		if not vector_ok(track.get("axis")) or vec(track.axis).length_squared() < 0.00000001: return "nonzero finite axis required"
		if not track.get("space") in ["part", "world"]: return "axis/translation space must be part or world"
		if not track.get("interpolation") in ["linear", "smoothstep"]: return "linear or smoothstep interpolation required"
		if not track.get("keys") is Array or track.keys.size() < 2: return "at least two keys required"
		var previous := -INF
		for keyframe in track.keys:
			if not keyframe is Dictionary or not finite(keyframe.get("time")) or float(keyframe.time) <= previous or keyframe.time < 0 or keyframe.time > value.duration: return "key times must strictly increase within duration"
			if not finite(keyframe.get("rotation_degrees")) or not vector_ok(keyframe.get("translation")): return "finite key transform required"
			previous = float(keyframe.time)
		if not is_zero_approx(float(track.keys[0].time)) or not is_equal_approx(float(track.keys[-1].time), float(value.duration)): return "keys must cover zero through duration"
		if value.loop and (not is_equal_approx(float(track.keys[0].rotation_degrees), float(track.keys[-1].rotation_degrees)) or not vec(track.keys[0].translation).is_equal_approx(vec(track.keys[-1].translation))): return "loop endpoints must match"
	return ""

func configure(value: Dictionary, asset: Node3D) -> String:
	var problem := validate(value)
	if not problem.is_empty(): return problem
	if value.get("source_id") != asset.get_meta("source_id", null) or value.get("master_hash") != asset.get_meta("master_hash", null): return "animation source/master does not match geometry"
	var available: Array = asset.get_meta("rigid_parts", [])
	var pending: Array = []
	for track in value.tracks:
		var matched: Array = []
		for part in available:
			if part.selector == track.selector: matched.append(part)
		if matched.size() != 1: return "selector must resolve to exactly one independent rigid part: " + JSON.stringify(track.selector)
		var part: Dictionary = matched[0]
		var source_basis := basis_rows(part.source_world_basis)
		pending.append({"track": track.duplicate(true), "node": part.node, "rest": part.rest_transform,
			"axis": (source_basis * vec(track.axis) if track.space == "part" else vec(track.axis)).normalized(),
			"translation_basis": source_basis if track.space == "part" else Basis.IDENTITY,
			"pivot_world": part.pivot_world})
	clip = value.duplicate(true)
	bindings = pending
	playhead = 0.0
	playing = true
	_apply()
	return ""

func seek(seconds: float) -> bool:
	if not is_finite(seconds) or clip.is_empty(): return false
	playhead = fposmod(seconds, float(clip.duration)) if clip.loop else clampf(seconds, 0, float(clip.duration))
	_apply()
	return true

func advance(delta: float) -> void:
	if playing and is_finite(delta) and delta >= 0: seek(playhead + delta)

func pause() -> void:
	playing = false

func play() -> void:
	playing = true

func stop() -> void:
	playing = false
	seek(0.0)

func sample(track: Dictionary, seconds: float) -> Dictionary:
	var keys: Array = track.keys
	var left: Dictionary = keys[0]
	var right: Dictionary = keys[-1]
	for index in range(keys.size() - 1):
		if seconds <= float(keys[index + 1].time):
			left = keys[index]
			right = keys[index + 1]
			break
	var amount := clampf((seconds - float(left.time)) / (float(right.time) - float(left.time)), 0, 1)
	if track.interpolation == "smoothstep": amount = amount * amount * (3.0 - 2.0 * amount)
	return {"rotation_degrees": lerpf(float(left.rotation_degrees), float(right.rotation_degrees), amount), "translation": vec(left.translation).lerp(vec(right.translation), amount)}

func _apply() -> void:
	for binding in bindings:
		var value := sample(binding.track, playhead)
		var rest: Transform3D = binding.rest
		var rotation := Basis(binding.axis, deg_to_rad(value.rotation_degrees))
		binding.node.transform = Transform3D(rotation * rest.basis, rest.origin + binding.translation_basis * value.translation)

func state() -> Dictionary:
	var tracks: Array = []
	for binding in bindings:
		var value := sample(binding.track, playhead)
		tracks.append({"id": binding.track.id, "selector": binding.track.selector, "rotation_degrees": value.rotation_degrees,
			"pivot_world": binding.pivot_world, "node_origin": [binding.node.position.x, binding.node.position.y, binding.node.position.z]})
	return {"playhead": playhead, "playing": playing, "duration": clip.get("duration"), "loop": clip.get("loop"), "tracks": tracks}
