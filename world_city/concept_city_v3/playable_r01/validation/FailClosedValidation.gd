extends Node3D
## Source loader safety test only. No actor movement or invented geometry.
const CityWorld = preload("res://CityWorld.gd")
func _ready() -> void:
	var out := ""
	var repo_root_override := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.substr(6)
		if arg.begins_with("--repo-root="):repo_root_override=arg.substr(12)
	if out.is_empty() or FileAccess.file_exists(out.path_join("report.json")):get_tree().quit(3);return
	var cases: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://validation/cases.json"))
	var effective_repo_root: String=repo_root_override if not repo_root_override.is_empty() else str(cases.repo_root)
	var world: Node3D=CityWorld.new();add_child(world)
	var error: String=world.configure("res://generated/tile_r01/index.json",effective_repo_root,false)
	var valid: bool=error.is_empty() and world.ensure_region(Vector3(98.41505784216918,4,48.75638652919374),1)
	var before: Dictionary=world.debug_state()
	# Deliberately request a region far outside the finite exported scene.
	var outside: bool=world.ensure_region(Vector3(1000000,0,1000000),1)
	var after: Dictionary=world.debug_state()
	var passed: bool=valid and before.ready and not outside and not after.ready and str(after.error).begins_with("Outside exported city coverage:") and before.loaded_owners==after.loaded_owners
	var report: Dictionary={"schema":"riverstone.lily_city.missing_region_safety.v1","status":"PASS" if passed else "FAIL","effective_repo_root":effective_repo_root,"known_region_loaded":valid,"unknown_region_returned_ready":outside,"known_region_state":before,"unknown_region_state":after,"unknown_request_m":[1000000,0,1000000],"actor_moved":false,"new_test_geometry":false,"world_script_sha256":FileAccess.get_sha256("res://CityWorld.gd"),"tile_index_sha256":FileAccess.get_sha256("res://generated/tile_r01/index.json"),"expected_error":"The logged Outside exported city coverage error is intentional. The world must become not-ready and must not create a substitute floor."}
	DirAccess.make_dir_recursive_absolute(out)
	var file:=FileAccess.open(out.path_join("report.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");file.close()
	print("LILY_CITY_FAIL_CLOSED "+JSON.stringify({"status":report.status,"unknown_ready":outside,"error":after.error}));get_tree().quit(0 if passed else 1)
