extends SceneTree
## Recheck cached transport against all geometry-affecting binding inputs.
const World=preload("res://CityWorldDetail.gd")
func _init() -> void:call_deferred("run")
func run() -> void:
	var world:=World.new();root.add_child(world)
	var problem:=world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),true)
	if not problem.is_empty():push_error(problem);quit(2);return
	var rows: Array=[];var all_pass:=true
	var negative: Array=[]
	for key in world.detail_catalog.assets:
		var entry: Dictionary=world.detail_catalog.assets[key]
		if not entry.has("native_scene_path"):continue
		var path: String=world._path(entry.native_scene_path)
		var scene:=load(path) as PackedScene
		var node: Node3D=scene.instantiate() if scene!=null else null
		var valid: bool=node!=null and FileAccess.get_sha256(path)==entry.native_scene_sha256
		var binding: String=world.composition_contract_hash(entry)
		var actual: String=str(node.get_meta("composition_contract_sha256","")) if node!=null else ""
		valid=valid and actual==binding and node.get_meta("source_render_sha256","")==entry.sha256
		rows.append({"asset":key,"pass":valid,"expected_binding":binding,"actual_binding":actual,"native_scene_sha256":entry.native_scene_sha256})
		all_pass=all_pass and valid
		if node!=null:node.free()
	# Ordinary houses must reject stale shadow/composition contracts too.
	for key in world.detail_catalog.assets:
		var original: Dictionary=world.detail_catalog.assets[key].duplicate(true)
		if not original.has("native_scene_path") or original.has("composed_manifest_path"):continue
		for field in ["shadow_proxy_sha256","source_master_sha256","window_contract_sha256"]:
			var altered: Dictionary=original.duplicate(true);altered[field]="deliberately_invalid_regression_fixture"
			world.detail_catalog.assets[key]=altered
			var result: Dictionary=world._cache_asset(key)
			var rejected: bool=result.is_empty() and world.error.begins_with("Native cache/source binding mismatch")
			negative.append({"asset":key,"field":field,"mismatch_rejected":rejected});all_pass=all_pass and rejected
			world.error=""
		world.detail_catalog.assets[key]=original
		var good: Dictionary=world._cache_asset(key)
		all_pass=all_pass and not good.is_empty() and world.error.is_empty()
		if not good.is_empty():world._evict(key)
		break
	var output:="res://../near_detail_r01/city_upgrade/evidence/native_binding_r01.json"
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="):output=argument.trim_prefix("--output=")
	var report:={"schema":"riverstone.native_binding_check.v1","all_pass":all_pass,"assets":rows,"negative_cases":negative,"scope":"Cached common-render transport identity, not visual acceptance or gameplay traversal."}
	var file:=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if all_pass else 3)
