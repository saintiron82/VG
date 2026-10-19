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
	var actual_entry: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://near_catalog.json")).assets.registered_cathedral_nave_aisles_transept
	var actual_source: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://generated/tile_r01/index.json")).common_assets.registered_cathedral_nave_aisles_transept
	var root_path:=ProjectSettings.globalize_path("res://../../..")
	var actual_c: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(root_path.path_join(actual_entry.far_visual_contract_path)))
	var bytes:=FileAccess.get_file_as_bytes(root_path.path_join(actual_entry.far_visual_render_path))
	var actual_data: Dictionary=JSON.parse_string(bytes.decompress_dynamic(16777216,FileAccess.COMPRESSION_GZIP).get_string_from_utf8())
	var asset_key:="registered_cathedral_nave_aisles_transept"
	rows.append({"case":"actual_source_union_valid","pass":Contract.validate(asset_key,actual_entry,actual_source,actual_c,actual_data,actual_entry.far_visual_render_sha256).is_empty()})
	for field in ["geometry_mode","union_provenance_sha256","source_shadow_proxy_sha256"]:
		var altered: Dictionary=actual_c.duplicate(true);altered[field]="wrong"
		rows.append({"case":"source_union_wrong_"+field,"pass":not Contract.validate(asset_key,actual_entry,actual_source,altered,actual_data,actual_entry.far_visual_render_sha256).is_empty()})
	var altered_data: Dictionary=actual_data.duplicate(true);altered_data.source_surface_lod.high_resolution_voxel_source=true
	rows.append({"case":"false_fine_voxel_claim","pass":not Contract.validate(asset_key,actual_entry,actual_source,actual_c,altered_data,actual_entry.far_visual_render_sha256).is_empty()})
	altered_data=actual_data.duplicate(true);altered_data.bounds.max[1]+=1
	rows.append({"case":"source_union_escape","pass":not Contract.validate(asset_key,actual_entry,actual_source,actual_c,altered_data,actual_entry.far_visual_render_sha256).is_empty()})
	var report:={"all_pass":rows.all(func(v):return v["pass"]),"tests":rows,"scope":"Optional far visual identity/finite extent/grid gating; actual mesh and LOD replay are separate."}
	var f:=FileAccess.open("res://../near_detail_r01/city_upgrade/evidence/revised_far_contract_r02.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 3)
