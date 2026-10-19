extends RefCounted
## Generic, fixed-capacity cell animation. Only configure() allocates render objects.
## Rest data is copied into private packed arrays; seek() always evaluates it directly.
## The _apply/seek/advance tick path creates no Array, Dictionary, Node or Resource.

const VoxelData = preload("res://RenderData.gd")

class Pool extends RefCounted:
	var id: String
	var capacity: int
	var cell_size: float
	var node: MultiMeshInstance3D
	var multimesh: MultiMesh
	var mesh: BoxMesh
	var material: StandardMaterial3D
	var rest_x := PackedFloat64Array()
	var rest_y := PackedFloat64Array()
	var rest_z := PackedFloat64Array()
	var palette := PackedColorArray()
	var colors := PackedInt32Array()
	var visible_members := PackedInt32Array()
	var current_positions := PackedVector3Array()
	var current_colors := PackedInt32Array()
	var visible_count: int
	var banded: bool = false
	var band_projection := PackedFloat64Array()
	var band_size: float
	var band_speed: float
	var step_rate: float
	var cycle: int
	var bright_bands: int
	var base_index: int
	var highlight_index: int
	var threshold: bool = false
	var threshold_projection := PackedFloat64Array()
	var key_times := PackedFloat64Array()
	var key_values := PackedFloat64Array()
	var smooth: bool = false
	var ballistic: bool = false
	var period: float
	var acceleration_x: float
	var acceleration_y: float
	var acceleration_z: float
	var up_x: float
	var up_y: float
	var up_z: float
	var minimum_up_offset: float
	var velocity_x := PackedFloat64Array()
	var velocity_y := PackedFloat64Array()
	var velocity_z := PackedFloat64Array()
	var phases := PackedFloat64Array()
	var lifetimes := PackedFloat64Array()
	var quantized: bool = false
	var quantize_pitch: float
	var origin_x: float
	var origin_y: float
	var origin_z: float

var _pools: Array[Pool] = []
var duration: float = 0.0
var update_hz: float = 0.0
var loop: bool = false
var playhead: float = 0.0
var evaluation_time: float = 0.0
var playing: bool = true
var source_id: String = ""
var master_hash: String = ""
var clip_hash: String = ""
var _configured: bool = false
var _bounds: AABB

static func _integer(value: Variant) -> bool:
	return VoxelData.finite_number(value) and float(value) == floor(float(value))

static func _axis_ok(value: Variant) -> bool:
	return VoxelData.vector_ok(value) and (float(value[0]) != 0.0 or float(value[1]) != 0.0 or float(value[2]) != 0.0)

static func _dot(a: Array, b: Array) -> float:
	return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1]) + float(a[2]) * float(b[2])

static func validate(data: Dictionary) -> String:
	var problem: String = VoxelData.validate(data)
	if not problem.is_empty(): return problem
	if not data.has("cell_animation"): return ""
	var clip: Variant = data.cell_animation
	if not clip is Dictionary: return "cell_animation must be an object"
	if not VoxelData.finite_number(clip.get("duration")) or float(clip.duration) <= 0.0: return "positive finite duration required"
	if not VoxelData.finite_number(clip.get("update_hz")) or float(clip.update_hz) <= 0.0: return "positive finite update_hz required"
	var ticks: float = float(clip.duration) * float(clip.update_hz)
	if not is_finite(ticks) or absf(ticks - round(ticks)) > 0.00000001: return "duration * update_hz must be integral"
	if not clip.get("loop") is bool: return "explicit loop boolean required"
	if not _integer(clip.get("seed")) or int(clip.seed) != 0: return "only explicit seed 0 is supported"
	if clip.has("source_id") and clip.source_id != data.get("source_id"): return "animation source_id mismatch"
	if clip.has("master_hash") and clip.master_hash != data.get("master_hash"): return "animation master_hash mismatch"
	var bounds: Variant = clip.get("bounds")
	if not bounds is Dictionary or not VoxelData.vector_ok(bounds.get("min")) or not VoxelData.vector_ok(bounds.get("max")): return "animation bounds require finite min/max"
	for axis in range(3):
		if float(bounds.min[axis]) >= float(bounds.max[axis]): return "animation bounds require positive extents"
	if not clip.get("pools") is Array or clip.pools.is_empty(): return "nonempty animation pools required"
	var ids: Dictionary = {}
	for pool in clip.pools:
		if not pool is Dictionary: return "each pool must be an object"
		if not pool.get("id") is String or pool.id.is_empty() or ids.has(pool.id): return "unique nonempty pool id required"
		ids[pool.id] = true
		if not VoxelData.finite_number(pool.get("cell_size")) or float(pool.cell_size) <= 0.0: return "positive finite cell_size required"
		if not pool.get("positions") is Array or pool.positions.is_empty(): return "nonempty positions required"
		var capacity: int = pool.positions.size()
		for position in pool.positions:
			if not VoxelData.vector_ok(position): return "finite rest positions required"
			for axis in range(3):
				if float(position[axis]) - float(pool.cell_size) * 0.5 < float(bounds.min[axis]) - 0.000001 or float(position[axis]) + float(pool.cell_size) * 0.5 > float(bounds.max[axis]) + 0.000001: return "rest cell extends beyond animation bounds"
		if not pool.get("palette") is Array or pool.palette.is_empty(): return "nonempty palette required"
		for color in pool.palette:
			if VoxelData.color_value(color) == null: return "invalid pool palette color"
		if not pool.get("color_indices") is Array or pool.color_indices.size() != capacity: return "color_indices must match capacity"
		for color_index in pool.color_indices:
			if not _integer(color_index) or int(color_index) < 0 or int(color_index) >= pool.palette.size(): return "palette index out of range"
		if pool.has("banded_color"):
			var band: Variant = pool.banded_color
			if not band is Dictionary or not _axis_ok(band.get("axis")): return "banded_color requires a nonzero finite axis"
			if not VoxelData.finite_number(band.get("band_size")) or float(band.band_size) <= 0.0: return "positive band_size required"
			if not VoxelData.finite_number(band.get("speed")) or not VoxelData.finite_number(band.get("step_rate")): return "finite band speed/step_rate required"
			if not _integer(band.get("cycle")) or int(band.cycle) <= 0: return "positive integral band cycle required"
			if not _integer(band.get("bright_bands")) or int(band.bright_bands) < 0 or int(band.bright_bands) > int(band.cycle): return "bright_bands must be within cycle"
			for field in ["base_index", "highlight_index"]:
				if not _integer(band.get(field)) or int(band[field]) < 0 or int(band[field]) >= pool.palette.size(): return "band palette index out of range"
		if pool.has("threshold_visibility") and pool.has("ballistic"): return "threshold_visibility and ballistic are mutually exclusive"
		if pool.has("threshold_visibility"):
			var threshold: Variant = pool.threshold_visibility
			if not threshold is Dictionary or not _axis_ok(threshold.get("axis")): return "threshold requires nonzero finite axis"
			if not threshold.get("interpolation") in ["linear", "smoothstep"]: return "threshold interpolation must be linear or smoothstep"
			if not threshold.get("keys") is Array or threshold.keys.size() < 2: return "threshold requires at least two keys"
			var previous: float = -INF
			for key in threshold.keys:
				if not key is Array or key.size() != 2 or not VoxelData.finite_number(key[0]) or not VoxelData.finite_number(key[1]): return "threshold key must contain finite time/value"
				if float(key[0]) <= previous or float(key[0]) < 0.0 or float(key[0]) > float(clip.duration): return "threshold key times must strictly increase within duration"
				previous = float(key[0])
			if absf(float(threshold.keys[0][0])) > 0.00000001 or absf(float(threshold.keys[-1][0]) - float(clip.duration)) > 0.00000001: return "threshold keys must cover duration"
			previous = -INF
			for position in pool.positions:
				var projection: float = _dot(position, threshold.axis)
				if projection < previous: return "threshold positions must be sorted by axis projection"
				previous = projection
		if pool.has("ballistic"):
			var ballistic: Variant = pool.ballistic
			if not ballistic is Dictionary: return "ballistic must be an object"
			if not VoxelData.finite_number(ballistic.get("period")) or float(ballistic.period) <= 0.0: return "positive finite ballistic period required"
			if not VoxelData.vector_ok(ballistic.get("acceleration")) or not _axis_ok(ballistic.get("up_axis")) or not VoxelData.finite_number(ballistic.get("minimum_up_offset")): return "finite ballistic acceleration/up axis/minimum offset required"
			for field in ["velocities", "phases", "lifetimes"]:
				if not ballistic.get(field) is Array or ballistic[field].size() != capacity: return "ballistic arrays must match capacity"
			for index in range(capacity):
				if not VoxelData.vector_ok(ballistic.velocities[index]) or not VoxelData.finite_number(ballistic.phases[index]) or not VoxelData.finite_number(ballistic.lifetimes[index]): return "finite ballistic members required"
				if float(ballistic.lifetimes[index]) < 0.0 or float(ballistic.lifetimes[index]) > float(ballistic.period): return "lifetime must be within ballistic period"
			if ballistic.has("quantize"):
				var quantize: Variant = ballistic.quantize
				if not quantize is Dictionary or not VoxelData.finite_number(quantize.get("pitch")) or float(quantize.pitch) <= 0.0 or not VoxelData.vector_ok(quantize.get("origin")): return "quantize requires positive pitch and finite origin"
	return ""

func configure(data: Dictionary, parent: Node3D) -> String:
	var problem: String = validate(data)
	if not problem.is_empty(): return problem
	if parent == null or not is_instance_valid(parent): return "live Node3D parent required"
	clear()
	source_id = str(data.get("source_id", ""))
	master_hash = str(data.get("master_hash", ""))
	_configured = true
	if not data.has("cell_animation"): return ""
	var clip: Dictionary = data.cell_animation
	duration = float(clip.duration)
	update_hz = float(clip.update_hz)
	loop = clip.loop
	clip_hash = str(clip.get("clip_hash", data.get("clip_hash", "")))
	_bounds = AABB(VoxelData.vector(clip.bounds.min), VoxelData.vector(clip.bounds.max) - VoxelData.vector(clip.bounds.min))
	for description in clip.pools:
		var pool := Pool.new()
		pool.id = description.id
		pool.cell_size = float(description.cell_size)
		pool.capacity = description.positions.size()
		pool.rest_x.resize(pool.capacity)
		pool.rest_y.resize(pool.capacity)
		pool.rest_z.resize(pool.capacity)
		pool.colors = PackedInt32Array(description.color_indices)
		pool.visible_members.resize(pool.capacity)
		pool.current_positions.resize(pool.capacity)
		pool.current_colors.resize(pool.capacity)
		for index in range(pool.capacity):
			pool.rest_x[index] = float(description.positions[index][0])
			pool.rest_y[index] = float(description.positions[index][1])
			pool.rest_z[index] = float(description.positions[index][2])
		for color in description.palette: pool.palette.append(VoxelData.color_value(color))
		if description.has("banded_color"):
			var band: Dictionary = description.banded_color
			pool.banded = true
			pool.band_projection.resize(pool.capacity)
			for index in range(pool.capacity): pool.band_projection[index] = _dot(description.positions[index], band.axis)
			pool.band_size = float(band.band_size)
			pool.band_speed = float(band.speed)
			pool.step_rate = float(band.step_rate)
			pool.cycle = int(band.cycle)
			pool.bright_bands = int(band.bright_bands)
			pool.base_index = int(band.base_index)
			pool.highlight_index = int(band.highlight_index)
		if description.has("threshold_visibility"):
			var threshold: Dictionary = description.threshold_visibility
			pool.threshold = true
			pool.threshold_projection.resize(pool.capacity)
			for index in range(pool.capacity): pool.threshold_projection[index] = _dot(description.positions[index], threshold.axis)
			for key in threshold.keys:
				pool.key_times.append(float(key[0]))
				pool.key_values.append(float(key[1]))
			pool.smooth = threshold.interpolation == "smoothstep"
		if description.has("ballistic"):
			var ballistic: Dictionary = description.ballistic
			pool.ballistic = true
			pool.period = float(ballistic.period)
			pool.acceleration_x = float(ballistic.acceleration[0])
			pool.acceleration_y = float(ballistic.acceleration[1])
			pool.acceleration_z = float(ballistic.acceleration[2])
			pool.up_x = float(ballistic.up_axis[0])
			pool.up_y = float(ballistic.up_axis[1])
			pool.up_z = float(ballistic.up_axis[2])
			pool.minimum_up_offset = float(ballistic.minimum_up_offset)
			pool.velocity_x.resize(pool.capacity)
			pool.velocity_y.resize(pool.capacity)
			pool.velocity_z.resize(pool.capacity)
			for index in range(pool.capacity):
				pool.velocity_x[index] = float(ballistic.velocities[index][0])
				pool.velocity_y[index] = float(ballistic.velocities[index][1])
				pool.velocity_z[index] = float(ballistic.velocities[index][2])
			pool.phases = PackedFloat64Array(ballistic.phases)
			pool.lifetimes = PackedFloat64Array(ballistic.lifetimes)
			if ballistic.has("quantize"):
				pool.quantized = true
				pool.quantize_pitch = float(ballistic.quantize.pitch)
				pool.origin_x = float(ballistic.quantize.origin[0])
				pool.origin_y = float(ballistic.quantize.origin[1])
				pool.origin_z = float(ballistic.quantize.origin[2])
		pool.material = StandardMaterial3D.new()
		pool.material.vertex_color_use_as_albedo = true
		pool.material.albedo_color = Color.WHITE
		pool.material.roughness = 1.0
		pool.material.metallic_specular = 0.0
		for color in pool.palette:
			if color.a < 1.0: pool.material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		pool.mesh = BoxMesh.new()
		pool.mesh.size = Vector3.ONE * pool.cell_size
		pool.mesh.material = pool.material
		pool.multimesh = MultiMesh.new()
		pool.multimesh.transform_format = MultiMesh.TRANSFORM_3D
		pool.multimesh.use_colors = true
		pool.multimesh.mesh = pool.mesh
		pool.multimesh.instance_count = pool.capacity
		pool.multimesh.visible_instance_count = 0
		pool.multimesh.custom_aabb = _bounds
		pool.node = MultiMeshInstance3D.new()
		pool.node.name = "CellPool" + str(_pools.size())
		pool.node.set_meta("pool_id", pool.id)
		pool.node.multimesh = pool.multimesh
		parent.add_child(pool.node)
		_pools.append(pool)
	_apply()
	return ""

func clear() -> void:
	for pool in _pools:
		if is_instance_valid(pool.node):
			if pool.node.get_parent() != null: pool.node.get_parent().remove_child(pool.node)
			pool.node.free()
	_pools.clear()
	duration = 0.0
	update_hz = 0.0
	loop = false
	playhead = 0.0
	evaluation_time = 0.0
	playing = true
	clip_hash = ""
	_configured = false

func seek(seconds: float) -> bool:
	if not _configured or not is_finite(seconds): return false
	if duration == 0.0: return true
	playhead = fposmod(seconds, duration) if loop else clampf(seconds, 0.0, duration)
	evaluation_time = floor(playhead * update_hz + 0.00000001) / update_hz
	# Tick rounding near the loop seam must evaluate the canonical first frame.
	if loop and evaluation_time >= duration: evaluation_time = 0.0
	elif not loop: evaluation_time = minf(evaluation_time, duration)
	_apply()
	return true

func advance(delta: float) -> void:
	if playing and is_finite(delta) and delta >= 0.0: seek(playhead + delta)

func pause() -> void:
	playing = false

func play() -> void:
	playing = true

func stop() -> void:
	playing = false
	seek(0.0)

func _threshold_value(pool: Pool) -> float:
	var index: int = 0
	while index < pool.key_times.size() - 2 and evaluation_time > pool.key_times[index + 1]: index += 1
	var amount: float = clampf((evaluation_time - pool.key_times[index]) / (pool.key_times[index + 1] - pool.key_times[index]), 0.0, 1.0)
	if pool.smooth: amount = amount * amount * (3.0 - 2.0 * amount)
	return lerpf(pool.key_values[index], pool.key_values[index + 1], amount)

func _apply() -> void:
	var pool_index: int = 0
	while pool_index < _pools.size():
		var pool: Pool = _pools[pool_index]
		var threshold_value: float = _threshold_value(pool) if pool.threshold else INF
		var member: int = 0
		var visible: int = 0
		while member < pool.capacity:
			if pool.threshold and pool.threshold_projection[member] > threshold_value + 0.00000001: break
			var x: float = pool.rest_x[member]
			var y: float = pool.rest_y[member]
			var z: float = pool.rest_z[member]
			if pool.ballistic:
				var age: float = fposmod(evaluation_time - pool.phases[member], pool.period)
				var dx: float = pool.velocity_x[member] * age + 0.5 * pool.acceleration_x * age * age
				var dy: float = pool.velocity_y[member] * age + 0.5 * pool.acceleration_y * age * age
				var dz: float = pool.velocity_z[member] * age + 0.5 * pool.acceleration_z * age * age
				if age >= pool.lifetimes[member] - minf(0.00000001, pool.lifetimes[member] * 0.000001) or dx * pool.up_x + dy * pool.up_y + dz * pool.up_z < pool.minimum_up_offset - 0.00000001:
					member += 1
					continue
				x += dx
				y += dy
				z += dz
				if pool.quantized:
					x = pool.origin_x + (floor((x - pool.origin_x) / pool.quantize_pitch) + 0.5) * pool.quantize_pitch
					y = pool.origin_y + (floor((y - pool.origin_y) / pool.quantize_pitch) + 0.5) * pool.quantize_pitch
					z = pool.origin_z + (floor((z - pool.origin_z) / pool.quantize_pitch) + 0.5) * pool.quantize_pitch
			var color_index: int = pool.colors[member]
			if pool.banded:
				var band: int = int(floor((pool.band_projection[member] + evaluation_time * pool.band_speed) / pool.band_size)) + int(floor(evaluation_time * pool.step_rate))
				color_index = pool.highlight_index if posmod(band, pool.cycle) < pool.bright_bands else pool.base_index
			var position := Vector3(x, y, z)
			pool.multimesh.set_instance_transform(visible, Transform3D(Basis.IDENTITY, position))
			pool.multimesh.set_instance_color(visible, pool.palette[color_index])
			pool.visible_members[visible] = member
			pool.current_positions[visible] = position
			pool.current_colors[visible] = color_index
			visible += 1
			member += 1
		pool.visible_count = visible
		pool.multimesh.visible_instance_count = visible
		pool_index += 1

func state() -> Dictionary:
	# Debug/report only. These allocations are deliberately outside the tick path.
	var pools: Array = []
	var total_capacity: int = 0
	var total_visible: int = 0
	for pool in _pools:
		var positions: Array = []
		var members: Array = []
		var color_indices: Array = []
		var within_bounds: bool = true
		for slot in range(pool.visible_count):
			var position: Vector3 = pool.current_positions[slot]
			positions.append([position.x, position.y, position.z])
			members.append(pool.visible_members[slot])
			color_indices.append(pool.current_colors[slot])
			var half_size := Vector3.ONE * pool.cell_size * 0.5
			within_bounds = within_bounds and _bounds.grow(0.000001).encloses(AABB(position - half_size, half_size * 2.0))
		pools.append({"id": pool.id, "capacity": pool.capacity, "visible_count": pool.visible_count,
			"positions": positions, "member_indices": members, "color_indices": color_indices,
			"cell_size": pool.cell_size, "within_bounds": within_bounds,
			"node_id": pool.node.get_instance_id(), "multimesh_id": pool.multimesh.get_instance_id(),
			"mesh_id": pool.mesh.get_instance_id(), "material_id": pool.material.get_instance_id(),
			"instance_count": pool.multimesh.instance_count})
		total_capacity += pool.capacity
		total_visible += pool.visible_count
	return {"source_id": source_id, "master_hash": master_hash, "clip_hash": clip_hash,
		"duration": duration, "loop": loop, "update_hz": update_hz, "seed": 0,
		"playhead": playhead, "evaluation_time": evaluation_time, "playing": playing,
		"pool_count": _pools.size(), "pool_node_count": _pools.size(), "pool_resource_count": _pools.size() * 3,
		"capacity": total_capacity, "visible_count": total_visible, "pools": pools}
