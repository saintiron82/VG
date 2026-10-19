extends "res://Traversal.gd"
## Two fixed ray regressions using the original harness's unmodified collision loader.
var regression_frames := 0
var regression_options: Dictionary = {}
func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:regression_options[pair[0]]=pair[1]
	prepared=JSON.parse_string(FileAccess.get_file_as_string(regression_options.prepared))
	for source in prepared.sources.values():
		if FileAccess.get_sha256(str(source.path))!=str(source.sha256):push_error("Source hash changed");get_tree().quit(2);return
	for item in prepared.routes:
		if item.id=="SOUTH_NATIVE_TERMINAL_TO_COUNTRY":route=item
	result={}
	build_route_collision()
func _physics_process(_delta: float) -> void:
	regression_frames+=1
	if regression_frames!=4:return
	var contract: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(str(prepared.sources.supplemental_apron_contract.path)))
	var rows: Array=[]
	var passed := true
	for point in contract.positive_point_regressions:
		var origin=RD.vector(point.previous_miss_center_xyz_m)
		var hit=get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(origin,origin-Vector3(0,HEIGHT*.5+.3,0),1))
		var row={"route_id":point.route_id,"ray_from_xyz_m":vec(origin),"hit":not hit.is_empty(),"pass":false}
		if not hit.is_empty():
			row["source_id"]=str(hit.collider.get_meta("source_id","unknown"));row["position_xyz_m"]=vec(hit.position);row["normal_xyz_m"]=vec(hit.normal)
			row["pass"]=abs(hit.position.y-1.25)<0.00001 and row.source_id=="CONTRACT:SOUTHERN_NATIVE_FLAT_TERMINAL_APRON" and hit.normal.y>0.999
		passed=passed and row["pass"];rows.append(row)
	var output={"status":"pass" if passed else "fail","prepared_sha256":FileAccess.get_sha256(regression_options.prepared),"controller_sha256":FileAccess.get_sha256("res://Traversal.gd"),"collision_loader":"Inherited build_route_collision() unchanged from original Traversal.gd","regressions":rows}
	var file=FileAccess.open(regression_options.report,FileAccess.WRITE);file.store_string(JSON.stringify(output,"\t"));file.close()
	print(JSON.stringify(output));get_tree().quit(0 if passed else 2)
