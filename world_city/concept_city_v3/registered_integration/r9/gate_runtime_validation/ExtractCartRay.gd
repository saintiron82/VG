extends SceneTree
func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var output: Array = []
	for r in data.routes:
		if not str(r.id) in ["WEST_GATE_THROAT_TURNS","WEST_GATE_THROAT_TURNS_REVERSE"]: continue
		var reverse := str(r.id).ends_with("_REVERSE")
		var n: int = r.points.size()
		var aa: Array = r.points[n-2] if reverse else r.points[0]
		var bb: Array = r.points[n-1] if reverse else r.points[1]
		var a := Vector3(aa[0],aa[1],aa[2])
		var b := Vector3(bb[0],bb[1],bb[2])
		var d := b-a
		var yaw := atan2(d.x,d.z)
		var basis := Basis(Vector3.UP,yaw)
		var point: Vector3 = b if reverse else a
		var i := 1 if reverse else 2
		var track := float(data.cart_fixture.support_track_m)*0.5
		var wheelbase := float(data.cart_fixture.support_wheelbase_m)*0.5
		var local := Vector3(track,0,-wheelbase) if reverse else Vector3(-track,0,wheelbase)
		var foot := point+basis*local
		var ray_from := foot+Vector3.UP*0.75
		var ray_to := foot-Vector3.UP*1.5
		output.append({"route":r.id,"missing_support_index":i,"pose_point":[point.x,point.y,point.z],"yaw_rad":yaw,"ray_from":[ray_from.x,ray_from.y,ray_from.z],"ray_to":[ray_to.x,ray_to.y,ray_to.z]})
	var report := {"status":"ENGINE_MATH_RECONSTRUCTION_ONLY","prepared_path":args[0],"prepared_sha256":FileAccess.get_sha256(args[0]),"engine_version":Engine.get_version_info(),"formula":"Same Vector3/Basis/atan2/local support offsets as immutable CartClearance.gd; no collision queries or controller replay performed.","rays":output}
	var f := FileAccess.open(args[1],FileAccess.WRITE)
	f.store_string(JSON.stringify(report,"  ")+"\n")
	print(JSON.stringify(report))
	quit()
