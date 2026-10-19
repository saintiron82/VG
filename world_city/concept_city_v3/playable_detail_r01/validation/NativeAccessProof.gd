extends RefCounted
## Check immutable authoring evidence by streaming SHA, without parsing large proofs.
static func reference_error(value: Variant, repository: String, checked: Dictionary) -> String:
	if not value is Dictionary:return "Reference is not an object"
	if not value.get("path") is String or not value.get("sha256") is String:return "Invalid reference fields"
	var path: String=value.path;var digest: String=value.sha256
	if path.is_empty() or path.is_absolute_path() or path.contains("\\") or path.split("/").has("..") or path.contains(":"):return "Reference must remain repository-relative"
	if digest.length()!=64 or digest.hex_decode().size()!=32:return "Invalid SHA256"
	var token:=path+":"+digest
	if checked.has(token):return ""
	var file:=repository.path_join(path)
	if not FileAccess.file_exists(file) or FileAccess.get_sha256(file)!=digest:return "Authoring proof SHA mismatch"
	checked[token]=true
	return ""
static func asset_error(asset: Dictionary, repository: String, checked: Dictionary) -> String:
	var p: Variant=asset.get("full_source_proof")
	if not p is Dictionary or p.get("asset_key")!=asset.get("asset_key"):return "Projected asset has no matching full-source proof"
	var problem:=reference_error(p,repository,checked)
	if not problem.is_empty():return problem
	for key in ["geometry_validation","source_application_audit"]:
		if p.has(key):
			problem=reference_error(p[key],repository,checked)
			if not problem.is_empty():return problem
	return ""
