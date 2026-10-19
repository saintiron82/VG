extends SceneTree
const Contract=preload("res://validation/RevisedFarVisualContract.gd")
func _init() -> void:call_deferred("run")
func run() -> void:
	var source:={"master_sha256":"old_master","render_sha256":"old_render","bounds":{"min":[-2.0,0.0,-2.0],"max":[2.0,5.0,2.0]}}
	var entry:={"source_revision":{"revised_master_sha256":"new_master"},"far_visual_render_path":"far.render.json","far_visual_render_sha256":"new_render"}
	var c:={"schema":"riverstone.revised_far_visual.v1","asset_key":"test","all_pass":true,"collision_reference_changed":false,"original_master_sha256":"old_master","original_render_sha256":"old_render","revised_master_sha256":"new_master","render_path":"far.render.json","render_sha256":"new_render","pitch":.5,"grid_origin":[0.0,0.0,0.0],"tests":{"replayed":true},"output_quad_count":1}
	var data:={"pitch":.5,"grid_origin":[0.0,0.0,0.0],"groups":[{"quads":[[[0,0,0],[1,0,0],[1,1,0],[0,1,0]]]}],"bounds":source.bounds.duplicate(true)}
	var rows:=[{"case":"valid","pass":Contract.validate("test",entry,source,c,data,"new_render").is_empty()}]
	for field in ["schema","asset_key","original_master_sha256","original_render_sha256","revised_master_sha256","render_path","render_sha256"]:
		var bad: Dictionary=c.duplicate(true);bad[field]="wrong"
		rows.append({"case":"wrong_"+field,"pass":not Contract.validate("test",entry,source,bad,data,"new_render").is_empty()})
	for field in ["all_pass","collision_reference_changed"]:
		var bad: Dictionary=c.duplicate(true);bad[field]=not bad[field]
		rows.append({"case":"wrong_"+field,"pass":not Contract.validate("test",entry,source,bad,data,"new_render").is_empty()})
	var bad_pitch: Dictionary=data.duplicate(true);bad_pitch.pitch=.25
	rows.append({"case":"wrong_grid_pitch","pass":not Contract.validate("test",entry,source,c,bad_pitch,"new_render").is_empty()})
	var bad_origin: Dictionary=data.duplicate(true);bad_origin.grid_origin[0]=.25
	rows.append({"case":"wrong_grid_origin","pass":not Contract.validate("test",entry,source,c,bad_origin,"new_render").is_empty()})
	var escape: Dictionary=data.duplicate(true);escape.bounds.max[0]=2.01
	rows.append({"case":"out_of_envelope","pass":not Contract.validate("test",entry,source,c,escape,"new_render").is_empty()})
	var count: Dictionary=c.duplicate(true);count.output_quad_count=2
	rows.append({"case":"wrong_count","pass":not Contract.validate("test",entry,source,count,data,"new_render").is_empty()})
	var empty: Dictionary=c.duplicate(true);empty.tests={}
	rows.append({"case":"missing_tests","pass":not Contract.validate("test",entry,source,empty,data,"new_render").is_empty()})
	var fail: Dictionary=c.duplicate(true);fail.tests.replayed=false
	rows.append({"case":"failed_tests","pass":not Contract.validate("test",entry,source,fail,data,"new_render").is_empty()})
	rows.append({"case":"bytes_sha_mismatch","pass":not Contract.validate("test",entry,source,c,data,"wrong").is_empty()})
	var report:={"all_pass":rows.all(func(v):return v["pass"]),"tests":rows,"scope":"Optional far visual identity/finite extent/grid gating; actual mesh and LOD replay are separate."}
	var f:=FileAccess.open("res://../near_detail_r01/city_upgrade/evidence/revised_far_contract_r01.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 3)
