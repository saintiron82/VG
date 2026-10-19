extends SceneTree
const RD=preload("res://RenderData.gd")
const Gate=preload("res://validation/SourceRoofFarVisualContract.gd")
func read(path: String) -> Dictionary:return JSON.parse_string(FileAccess.get_file_as_string(path))
func _initialize() -> void:
	var repo:=OS.get_environment("SOURCE_REPO")
	var manifest:=read(OS.get_environment("BATCH_MANIFEST"))
	var index:=read(repo+"/world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json")
	var catalog:=read(repo+"/world_city/concept_city_v3/playable_detail_r01/near_catalog.json")
	var rows: Array=[]
	for c in manifest.entries:
		var key: String=c.asset_key;var e: Dictionary=catalog.assets[key].duplicate(true);var source: Dictionary=index.common_assets[key]
		var inp:=read(repo.path_join(c.source_roof_input_contract.path))
		c.schema="riverstone.source_roof_far_visual.v1";c.owned_roof_materials=inp.materials
		e.far_visual_render_sha256=c.render_sha256;e.far_visual_render_path=c.render_path
		var result:=RD.read(repo.path_join(c.render_path));var original:=RD.read(repo.path_join(source.render_path))
		var problem:=Gate.validate(key,e,source,c,result.data,original.data,result.sha256)
		rows.append({"asset_key":key,"all_pass":problem.is_empty(),"problem":problem,"render_sha256":result.sha256})
	var report: Dictionary={"all_pass":rows.all(func(r):return r.all_pass),"scope":"Current shared source-roof far gate positive cases, contract and entry augmentation in memory only; no runtime or catalog writes.","cases":rows}
	var f:=FileAccess.open("res://gate_validation.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");f.close()
	print(JSON.stringify(report));quit(0 if report.all_pass else 1)
