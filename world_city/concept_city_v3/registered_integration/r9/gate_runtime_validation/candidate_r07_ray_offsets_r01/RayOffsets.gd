extends "res://Traversal.gd"
var observed: Dictionary
func _ready() -> void:
	super._ready()
	if report.status == "error": return
	body.collision_layer = 0
	body.collision_mask = 0
	observed = JSON.parse_string(FileAccess.get_file_as_string(prepared.sources.ray_observations.path))
	report = {"schema":"riverstone.r9.exact_ray_offset_diagnostic.v1", "status":"loading", "prepared_sha256":FileAccess.get_sha256(str(options.prepared)), "observation_source":prepared.sources.ray_observations, "routes":[], "errors":[], "limits":["Static read-only native ray queries at recorded miss origins plus bounded transverse offsets. Not a controller replay, support certificate, tolerance change or replacement for original failed routes."]}
func next_route() -> void:
	stage = "loading"
	route_index += 1
	if route_index >= routes.size():
		report.status = "diagnostic_complete"
		write_report()
		get_tree().quit(0)
		return
	route = routes[route_index]
	result = {"id":route.id,"rays":[]}
	build_route_collision()
	stage = "diagnostic_settle"
	settle_frames = 0
func _physics_process(_delta: float) -> void:
	if stage != "diagnostic_settle": return
	settle_frames += 1
	if settle_frames < 3: return
	var data: Dictionary
	for r in observed.routes:
		if r.id == route.id: data = r
	var lateral := RD.vector(prepared.probe_transverse_xyz[route.id])
	for observation in data.ray_miss_diagnostics:
		var row := {"recorded_frame":observation.frame,"original_observation":observation,"probes":[]}
		for offset in [0.0,-0.001,0.001]:
			var from: Vector3 = RD.vector(observation.ray_from) + lateral * float(offset)
			var to: Vector3 = RD.vector(observation.ray_to) + lateral * float(offset)
			var query := PhysicsRayQueryParameters3D.create(from,to,1)
			var hit := get_world_3d().direct_space_state.intersect_ray(query)
			var probe := {"transverse_offset_m":offset,"from":vec(from),"to":vec(to),"hit":not hit.is_empty()}
			if not hit.is_empty():
				probe.source_id = str(hit.collider.get_meta("source_id","unknown"))
				probe.position = vec(hit.position)
				probe.normal = vec(hit.normal)
			row.probes.append(probe)
		result.rays.append(row)
	report.routes.append(result)
	write_report()
	stage = "loading"
	call_deferred("next_route")
