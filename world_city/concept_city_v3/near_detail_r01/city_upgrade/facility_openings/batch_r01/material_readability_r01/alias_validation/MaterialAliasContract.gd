extends RefCounted
## Independent, read-only material-only master validator. No runtime activation.
## Public entry points return {ok: bool, errors: Array[String], ...}.
## validate_files authenticates compressed file bytes before loading JSON/gzip.
## validate_documents validates already-loaded data, without trusting report flags.
## A successful result is not a voxel compilation or visual acceptance.

const MAX_DOCUMENT_BYTES := 64 * 1024 * 1024
const REQUIRED_DOCUMENTS := ["rules", "material_revision", "palette_revision", "source", "palette_source", "base_roof", "revised_roof", "base_canonical", "revised_canonical"]

static func validate_files(repo_root: String, material_revision_path: String, palette_revision_path: String, rules_path: String) -> Dictionary:
	var loaded := load_documents(repo_root, material_revision_path, palette_revision_path, rules_path)
	if not loaded.ok:
		return loaded
	var result := validate_documents(loaded.documents)
	result["verified_files"] = loaded.verified_files
	return result

## Public loader permits the exact real data to be reused in mutation tests.
static func load_documents(repo_root: String, material_revision_path: String, palette_revision_path: String, rules_path: String) -> Dictionary:
	var errors: Array[String] = []
	var docs: Dictionary = {}
	var verified: Dictionary = {}
	for pair in [["rules", rules_path], ["material_revision", material_revision_path], ["palette_revision", palette_revision_path]]:
		docs[pair[0]] = _read_document(repo_root, pair[1], errors)
	if not errors.is_empty():
		return {"ok": false, "errors": errors}
	var rev: Dictionary = docs.material_revision
	var pal: Dictionary = docs.palette_revision
	var bindings: Dictionary = {
		"source": {"path": rev.get("original_master_path"), "sha256": rev.get("original_master_sha256")},
		"palette_source": pal.get("revised_master"),
		"base_roof": rev.get("base_roof"), "revised_roof": rev.get("revised_roof"),
		"base_canonical": rev.get("base_canonical"), "revised_canonical": rev.get("revised_canonical")}
	for label in bindings:
		if _verify_reference(repo_root, bindings[label], label, verified, errors):
			docs[label] = _read_document(repo_root, bindings[label].path, errors)
	if not _equal(pal.get("original_master"), bindings.source):
		errors.append("binding: palette original_master differs from material revision source")
	var expected_rev := {"path": material_revision_path, "sha256": FileAccess.get_sha256(_path(repo_root, material_revision_path, errors))}
	if not _equal(pal.get("material_revision"), expected_rev):
		errors.append("binding: palette revision does not bind the supplied material revision")
	_verify_reference(repo_root, pal.get("material_revision"), "material_revision", verified, errors)
	var identity: Variant = pal.get("identity")
	if identity is Dictionary:
		var expected_rules := {"path": rules_path, "sha256": FileAccess.get_sha256(_path(repo_root, rules_path, errors))}
		if not _equal(identity.get("rules"), expected_rules):
			errors.append("binding: palette identity does not bind the supplied rules")
		for key in identity:
			_verify_reference(repo_root, identity[key], "palette identity/" + str(key), verified, errors)
	else:
		errors.append("binding: palette identity must be a dictionary")
	var refs: Variant = rev.get("source_references")
	if refs is Array:
		var rules_bound := false
		for ref in refs:
			_verify_reference(repo_root, ref, "source_reference", verified, errors)
			if ref is Dictionary and ref.get("path") == rules_path:
				rules_bound = true
		if not rules_bound:
			errors.append("binding: rules absent from material revision source_references")
	else:
		errors.append("binding: source_references must be an array")
	return {"ok": errors.is_empty(), "errors": errors, "documents": docs, "verified_files": verified}

static func validate_documents(documents: Dictionary) -> Dictionary:
	var errors: Array[String] = []
	for key in REQUIRED_DOCUMENTS:
		if not documents.get(key) is Dictionary:
			errors.append("document: missing or non-dictionary " + key)
	if not errors.is_empty():
		return {"ok": false, "errors": errors}
	var rules: Dictionary = documents.rules
	var rev: Dictionary = documents.material_revision
	var pal: Dictionary = documents.palette_revision
	if rules.get("schema") != "riverstone.roof.material_tone_rules.v1" or rev.get("schema") != "riverstone.roof.material_revision.v1" or pal.get("schema") != "riverstone.palette_source_revision.v1":
		errors.append("schema: unsupported rules/revision schema")
	if not _string_id(rules.get("asset_key")) or rules.get("asset_key") != rev.get("asset_key") or rules.get("asset_key") != pal.get("asset_key"):
		errors.append("binding: asset keys are missing or inconsistent")
	var source_palette: Variant = documents.source.get("materials")
	if not source_palette is Dictionary:
		return {"ok": false, "errors": ["palette: source materials must be a dictionary"]}
	for label in ["palette_source", "base_roof", "revised_roof", "base_canonical", "revised_canonical"]:
		if not documents[label].get("materials") is Dictionary:
			errors.append("palette: " + label + " materials must be a dictionary")
	if not errors.is_empty():
		return {"ok": false, "errors": errors}
	var alias_result := validate_aliases(rules.get("material_role_aliases"), source_palette)
	errors.append_array(alias_result.errors)
	if not _equal(rules.get("material_role_aliases"), rev.get("material_role_aliases")) or not _equal(rules.get("material_role_aliases"), pal.get("material_role_aliases")):
		errors.append("aliases: declarations disagree between rules and revisions")
	if not alias_result.ok:
		return {"ok": false, "errors": errors}
	var aliases: Dictionary = alias_result.aliases
	var allowed: Variant = pal.get("allowed_added_material_ids")
	if not allowed is Array:
		errors.append("palette: allowed_added_material_ids must be an array")
	else:
		var actual_ids: Dictionary = {}
		for id in allowed:
			if not _string_id(id) or actual_ids.has(id):
				errors.append("palette: invalid or duplicate allowed alias ID")
			actual_ids[id] = true
		if not _same_keys(actual_ids, aliases):
			errors.append("palette: allowed_added_material_ids differs from alias declarations")
	for label in ["source", "base_roof", "base_canonical"]:
		if not _equal(documents[label].get("materials"), source_palette):
			errors.append("palette: " + label + " differs from original source palette")
	for label in ["palette_source", "revised_roof", "revised_canonical"]:
		_validate_palette(documents[label].get("materials"), source_palette, alias_result.resolved_aliases, label, errors)
	var restored_source: Dictionary = documents.palette_source.duplicate(true)
	restored_source["materials"] = source_palette.duplicate(true)
	var difference := _first_difference(documents.source, restored_source)
	if not difference.is_empty():
		errors.append("nonmaterial: palette_source differs at " + difference)
	var roof_count := _validate_revision_pair(documents.base_roof, documents.revised_roof, rev.get("roof_operation_changes"), aliases, "roof", errors)
	var canonical_count := _validate_revision_pair(documents.base_canonical, documents.revised_canonical, rev.get("canonical_operation_changes"), aliases, "canonical", errors)
	var count: Variant = rev.get("changed_operations")
	if not _number(count) or count != roof_count or count != canonical_count:
		errors.append("changes: changed_operations must equal both complete change-list lengths")
	return {"ok": errors.is_empty(), "errors": errors, "aliases": aliases, "resolved_aliases": alias_result.resolved_aliases,
		"checks": {"roof_changes": roof_count, "canonical_changes": canonical_count, "alias_count": aliases.size(),
		"exact_nonmaterial_comparison_performed": true, "original_palette_comparison_performed": true}}

## Direct-original contract: every base must exist in the original source palette.
## Alias chains are forbidden; no compounded multiplier is returned. The graph
## is also inspected for self/cyclic declarations to provide explicit diagnostics.
## IDs are strings, never coerced with str(); multipliers are numeric [0.8, 1.2].
static func validate_aliases(alias_list: Variant, source_palette: Variant) -> Dictionary:
	var errors: Array[String] = []
	var aliases: Dictionary = {}
	var resolved: Dictionary = {}
	if not alias_list is Array or not source_palette is Dictionary:
		return {"ok": false, "errors": ["aliases: expected array and source palette dictionary"], "aliases": {}, "resolved_aliases": {}}
	for entry in alias_list:
		if not entry is Dictionary:
			errors.append("aliases: declaration must be a dictionary")
			continue
		var id: Variant = entry.get("material_id")
		var base: Variant = entry.get("base_material_id")
		var multiplier: Variant = entry.get("luminance_multiplier")
		if not _string_id(id) or not _string_id(base):
			errors.append("aliases: material_id and base_material_id must be nonempty strings")
			continue
		if not _number(multiplier) or not is_finite(float(multiplier)) or float(multiplier) < 0.8 or float(multiplier) > 1.2:
			errors.append("aliases: " + id + " multiplier must be finite numeric within [0.8, 1.2]")
		if aliases.has(id):
			errors.append("aliases: duplicate alias " + id)
		if source_palette.has(id):
			errors.append("aliases: alias shadows original palette material " + id)
		if id == base:
			errors.append("aliases: self-reference " + id)
		if not source_palette.has(base):
			errors.append("aliases: unknown base in original source palette " + base + " for " + id)
		if entry.size() != 3:
			errors.append("aliases: unexpected declaration fields for " + id)
		aliases[id] = entry.duplicate(true)
	for id in aliases:
		var cursor: String = id
		var seen: Dictionary = {}
		while aliases.has(cursor):
			if seen.has(cursor):
				errors.append("aliases: cyclic dependency from " + id)
				break
			seen[cursor] = true
			var item: Dictionary = aliases[cursor]
			cursor = item.base_material_id
		var direct: Dictionary = aliases[id]
		if source_palette.has(direct.base_material_id) and _number(direct.get("luminance_multiplier")):
			resolved[id] = {"base_material_id": direct.base_material_id, "luminance_multiplier": direct.luminance_multiplier}
	if not errors.is_empty():
		resolved.clear()
	return {"ok": errors.is_empty(), "errors": errors, "aliases": aliases, "resolved_aliases": resolved}

static func _validate_palette(palette: Variant, original: Dictionary, resolved: Dictionary, label: String, errors: Array[String]) -> void:
	if not palette is Dictionary:
		errors.append("palette: " + label + " materials must be a dictionary")
		return
	for id in original:
		if not palette.has(id) or not _equal(palette[id], original[id]):
			errors.append("palette: " + label + " changed/removed original material " + str(id))
	for id in palette:
		if not original.has(id) and not resolved.has(id):
			errors.append("palette: " + label + " has unauthorized addition " + str(id))
	for id in resolved:
		if not palette.has(id):
			errors.append("palette: " + label + " missing alias " + id)
			continue
		var base: Variant = original[resolved[id].base_material_id]
		if not _hex_rgb(base):
			errors.append("palette: unsupported base RGB declaration for " + id)
		elif palette[id] != _scale_hex(base, resolved[id].luminance_multiplier):
			errors.append("palette: " + label + " alias RGB does not match linear multiplier: " + id)

static func _validate_revision_pair(before: Dictionary, after: Dictionary, changes: Variant, aliases: Dictionary, label: String, errors: Array[String]) -> int:
	if not changes is Array:
		errors.append("changes: " + label + " change list must be an array")
		return -1
	var old_ops := _index_operations(before, label + "/before", errors)
	var new_ops := _index_operations(after, label + "/after", errors)
	var listed: Dictionary = {}
	var restored: Dictionary = after.duplicate(true)
	var restore_ops := _index_operations(restored, label + "/restore", errors)
	for change in changes:
		if not change is Dictionary or not _string_id(change.get("component")) or not _string_id(change.get("operation")) or not _string_id(change.get("before")) or not _string_id(change.get("after")):
			errors.append("changes: " + label + " invalid change record")
			continue
		var key := JSON.stringify([change.component, change.operation])
		if listed.has(key):
			errors.append("changes: " + label + " duplicate operation change " + key)
		listed[key] = change
		if not old_ops.has(key) or not new_ops.has(key):
			errors.append("changes: " + label + " unknown operation " + key)
			continue
		if old_ops[key].get("material") != change.before or new_ops[key].get("material") != change.after:
			errors.append("changes: " + label + " before/after mismatch " + key)
		if change.before == change.after:
			errors.append("changes: " + label + " listed operation is unchanged " + key)
		if not before.get("materials", {}).has(change.before) or (not before.get("materials", {}).has(change.after) and not aliases.has(change.after)):
			errors.append("changes: " + label + " unknown material in change " + key)
		restore_ops[key]["material"] = old_ops[key].get("material")
	for key in old_ops:
		if new_ops.has(key) and old_ops[key].get("material") != new_ops[key].get("material") and not listed.has(key):
			errors.append("changes: " + label + " unlisted material mutation " + key)
	restored["materials"] = before.get("materials", {}).duplicate(true)
	var difference := _first_difference(before, restored)
	if not difference.is_empty():
		errors.append("nonmaterial: " + label + " differs after authorized material restore at " + difference)
	return changes.size()

static func _index_operations(master: Dictionary, label: String, errors: Array[String]) -> Dictionary:
	var index: Dictionary = {}
	var component_ids: Dictionary = {}
	var components: Variant = master.get("components")
	if not components is Array:
		errors.append("operations: " + label + " components must be an array")
		return index
	for component in components:
		if not component is Dictionary or not _string_id(component.get("id")) or not component.get("operations") is Array:
			errors.append("operations: " + label + " invalid component")
			continue
		if component_ids.has(component.id):
			errors.append("operations: " + label + " duplicate component " + component.id)
		component_ids[component.id] = true
		for operation in component.operations:
			if not operation is Dictionary or not _string_id(operation.get("id")):
				errors.append("operations: " + label + " invalid operation")
				continue
			var key := JSON.stringify([component.id, operation.id])
			if index.has(key):
				errors.append("operations: " + label + " duplicate operation " + key)
			index[key] = operation
	return index

static func _verify_reference(root: String, ref: Variant, label: String, verified: Dictionary, errors: Array[String]) -> bool:
	if not ref is Dictionary or not ref.get("path") is String or not ref.get("sha256") is String or ref.sha256.length() != 64:
		errors.append("binding: malformed file reference " + label)
		return false
	var full_path := _path(root, ref.path, errors)
	if full_path.is_empty() or not FileAccess.file_exists(full_path):
		errors.append("binding: missing file " + ref.path)
		return false
	var actual := FileAccess.get_sha256(full_path)
	if actual != ref.sha256:
		errors.append("binding: SHA-256 mismatch " + ref.path)
		return false
	verified[ref.path] = actual
	return true

static func _path(root: String, relative: String, errors: Array[String]) -> String:
	if relative.is_empty() or relative.is_absolute_path() or relative.contains(":") or relative.contains("\\") or relative.split("/").has(".."):
		errors.append("binding: expected safe repository-relative path")
		return ""
	return root.path_join(relative).simplify_path()

static func _read_document(root: String, relative: String, errors: Array[String]) -> Dictionary:
	var full_path := _path(root, relative, errors)
	if full_path.is_empty() or not FileAccess.file_exists(full_path):
		errors.append("document: missing " + relative)
		return {}
	var f := FileAccess.open(full_path, FileAccess.READ)
	if f == null or f.get_length() > MAX_DOCUMENT_BYTES:
		errors.append("document: unreadable or oversized " + relative)
		return {}
	var bytes := f.get_buffer(f.get_length())
	if relative.ends_with(".gz"):
		bytes = bytes.decompress_dynamic(MAX_DOCUMENT_BYTES, FileAccess.COMPRESSION_GZIP)
	if bytes.is_empty():
		errors.append("document: empty or failed decompression " + relative)
		return {}
	var parser := JSON.new()
	if parser.parse(bytes.get_string_from_utf8()) != OK or not parser.data is Dictionary:
		errors.append("document: invalid JSON dictionary " + relative)
		return {}
	return parser.data

static func _number(value: Variant) -> bool:
	return typeof(value) == TYPE_FLOAT or typeof(value) == TYPE_INT

static func _string_id(value: Variant) -> bool:
	return value is String and not value.is_empty()

static func _same_keys(a: Dictionary, b: Dictionary) -> bool:
	if a.size() != b.size():
		return false
	for key in a:
		if not b.has(key):
			return false
	return true

static func _equal(a: Variant, b: Variant) -> bool:
	return _first_difference(a, b).is_empty()

## Dictionary key order is immaterial; array order and every scalar value are
## exact. JSON's numeric representation is compared as numeric values, no epsilon.
static func _first_difference(a: Variant, b: Variant, path: String = "$", depth: int = 0) -> String:
	if depth > 128:
		return path + "/excessive_depth"
	if _number(a) and _number(b):
		return "" if a == b else path
	if typeof(a) != typeof(b):
		return path
	if a is Dictionary:
		if not _same_keys(a, b):
			return path + "/keys"
		for key in a:
			var diff := _first_difference(a[key], b[key], path + "/" + str(key), depth + 1)
			if not diff.is_empty():
				return diff
		return ""
	if a is Array:
		if a.size() != b.size():
			return path + "/length"
		for i in a.size():
			var diff := _first_difference(a[i], b[i], path + "/" + str(i), depth + 1)
			if not diff.is_empty():
				return diff
		return ""
	return "" if a == b else path

static func _hex_rgb(value: Variant) -> bool:
	if not value is String or value.length() != 6:
		return false
	for c in value.to_lower():
		if not c in "0123456789abcdef":
			return false
	return true

static func _scale_hex(rgb: String, multiplier: float) -> String:
	var output := ""
	for offset in [0, 2, 4]:
		var srgb := float(rgb.substr(offset, 2).hex_to_int()) / 255.0
		var linear := srgb / 12.92 if srgb <= 0.04045 else pow((srgb + 0.055) / 1.055, 2.4)
		linear = clampf(linear * multiplier, 0.0, 1.0)
		srgb = linear * 12.92 if linear <= 0.0031308 else 1.055 * pow(linear, 1.0 / 2.4) - 0.055
		# The source author uses Python round(): nearest integer, ties to even.
		# Godot round() uses a different tie rule, observable for dark RGB values.
		var value := srgb * 255.0
		var lower := int(floor(value))
		var fraction := value - lower
		var rounded := lower + (1 if fraction > 0.5 or (fraction == 0.5 and lower % 2 == 1) else 0)
		output += "%02x" % rounded
	return output
