extends SceneTree
const RD=preload("res://RenderData.gd")
func _init() -> void:
	var root:=ProjectSettings.globalize_path("res://../../..")
	var dir:=root.path_join("world_city/concept_city_v3/near_detail_r01/city_upgrade/evidence/render_transport_r01")
	var binding: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(dir.path_join("binding.json")))
	var plain:=RD.read(root.path_join(binding.source))
	var packed:=RD.read(dir.path_join("fixture.render.json.gz"))
	var tests: Array=[{"case":"plain_schema_pass","pass":not plain.has("error")},{"case":"python_gzip_godot_decode_pass","pass":not packed.has("error")},{"case":"compressed_identity_hash_preserved","pass":packed.get("sha256")==binding.gzip_sha256},{"case":"decompressed_common_data_exact","pass":JSON.stringify(packed.get("data"))==JSON.stringify(plain.get("data"))}]
	var report={"all_pass":tests.all(func(t):return t.pass),"checks":tests,"compressed_bytes":binding.compressed_bytes,"uncompressed_bytes":binding.decompressed_bytes,"limit_bytes":64*1024*1024,"scope":"Lossless common render transport only; not mesh simplification"}
	var f:=FileAccess.open(dir.path_join("validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 2)
