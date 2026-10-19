extends SceneTree
const Bounds=preload("res://validation/SourceBoundsContract.gd")
func _init() -> void:call_deferred("run")
func run() -> void:
	var base:="res://../near_detail_r01/city_upgrade/evidence/"
	var fixtures: Array=JSON.parse_string(FileAccess.get_file_as_string(base+"source_bounds_fixtures_r01.json"))
	var report:={"all_pass":true,"tests":[]}
	for fixture in fixtures:
		var reason: String=Bounds.validate(fixture.contract,fixture.fine,fixture.coarse,fixture.source_sha,fixture.proof)
		var accepted:=reason.is_empty();var valid: bool=accepted==fixture.expected
		report.tests.append({"name":fixture.name,"accepted":accepted,"expected":fixture.expected,"reason":reason,"pass":valid});report.all_pass=report.all_pass and valid
	var file:=FileAccess.open(base+"source_bounds_godot_r01.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 3)
