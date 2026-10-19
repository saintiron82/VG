extends SceneTree
const World=preload("res://CityWorldDetail.gd")
var checks: Array=[]
func check(name: String,value: bool,details: Variant=null) -> void:checks.append({"case":name,"pass":value,"details":details})
func _init() -> void:call_deferred("run")
func run() -> void:
	var world:=World.new();root.add_child(world)
	var key:="registered_cathedral_nave_aisles_transept"
	check("source_bound",world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),false).is_empty())
	var source: Dictionary=world._asset(key);var selected:=[];var fine_groups:=[];var preserved:=[]
	for n in source.groups.size():
		var g: Dictionary=source.groups[n]
		if str(g.material).begins_with("slate"):
			selected.append({"group_index":n,"material_id":g.material,"quad_count":g.quads.size(),"complete_source_operation_coverage":true});fine_groups.append(g)
		else:preserved.append(g)
	var entry:={"replacement_source_render_sha256":world.index.common_assets[key].render_sha256,"replace_source_groups":selected}
	var fine:=source.duplicate(false);fine.groups=fine_groups
	var combined:=world._compose_replacement(key,fine,entry)
	check("actual_two_source_roof_groups_selected",selected.size()==2,selected.size())
	check("matched_groups_compose",not combined.is_empty())
	check("all_original_nonroof_groups_exact",JSON.stringify(combined.groups.slice(fine_groups.size()))==JSON.stringify(preserved))
	check("replace_does_not_duplicate_roof",World.RD.stats(combined).quads==World.RD.stats(source).quads)
	check("source_data_unmodified",JSON.stringify(world._asset(key))==JSON.stringify(source))
	# Deliberate negative contracts must fail closed; no actual node is hidden.
	var bad:=entry.duplicate(true);bad.replace_source_groups[0].complete_source_operation_coverage=false
	check("incomplete_operation_coverage_rejected",world._compose_replacement(key,fine,bad).is_empty());world.error=""
	bad=entry.duplicate(true);bad.replace_source_groups[0].quad_count+=1
	check("changed_original_group_rejected",world._compose_replacement(key,fine,bad).is_empty());world.error=""
	bad=entry.duplicate(true);bad.replacement_source_render_sha256="wrong"
	check("changed_source_hash_rejected",world._compose_replacement(key,fine,bad).is_empty());world.error=""
	var port:="registered_port_long_loading_shed";var allowed: Dictionary={}
	var addition_entry:={"added_source_materials":[{"material":"slate_dark","source_master_sha256":world.index.common_assets[port].master_sha256,"source_operations":[{"component":"roof","operation":"range_ridge"}]}]}
	check("coarse_missing_actual_source_ridge_material_authorized",world._authorize_added_materials(port,addition_entry,allowed) and allowed.has("slate_dark"))
	var invented:=addition_entry.duplicate(true);invented.added_source_materials[0].source_operations[0].operation="invented"
	check("invented_source_operation_rejected",not world._authorize_added_materials(port,invented,{}));world.error=""
	invented=addition_entry.duplicate(true);invented.added_source_materials[0].source_master_sha256="wrong"
	check("wrong_source_master_for_new_material_rejected",not world._authorize_added_materials(port,invented,{}));world.error=""
	var contract_entry:={"sha256":"fixture","replace_source_groups":selected}
	var modified:=contract_entry.duplicate(true);modified.replace_source_groups[0].quad_count+=1
	check("native_cache_binds_partial_composition_contract",world.composition_contract_hash(contract_entry)!=world.composition_contract_hash(modified))

	var report={"all_pass":checks.all(func(c):return c.pass),"checks":checks,"scope":"Actual cathedral original-group composition contract with source groups as test replacement; no detailed cathedral resource or runtime activation claimed"}
	var f:=FileAccess.open(ProjectSettings.globalize_path("res://../near_detail_r01/city_upgrade/partial_replacement_validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 2)
