extends SceneTree

const Contract = preload("MaterialAliasContract.gd")
const R01 := "world_city/concept_city_v3/near_detail_r01/city_upgrade/facility_openings/batch_r01/material_readability_r01"
var results: Array[Dictionary] = []
var documents: Dictionary

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() < 1:
		printerr("Usage: godot --headless --path <alias_validation> --script test_material_alias_contract.gd -- <repository-root> [material-directory-relative-path] [report-path]")
		quit(2)
		return
	var root: String = args[0]
	var material_dir: String = args[1] if args.size() > 1 else R01
	var material_path := material_dir + "/generated/material_revision.json"
	var palette_path := material_dir + "/palette_source_r01/palette_source_revision.json"
	var rules_path := material_dir + "/rules.json"
	var file_result := Contract.validate_files(root, material_path, palette_path, rules_path)
	_expect("real_files_hashes_and_complete_contract", file_result, true)
	var loaded := Contract.load_documents(root, material_path, palette_path, rules_path)
	if not loaded.ok:
		_finish(args, file_result)
		return
	documents = loaded.documents
	var original_fingerprint := JSON.stringify(documents).sha256_text()
	_expect("real_documents_ignore_report_flags", _test_flags(), true)
	_alias_tests()
	_document_tests()
	var hash_errors: Array[String] = []
	var bad_reference := {"path": documents.material_revision.original_master_path, "sha256": "0".repeat(64)}
	var hash_ok := Contract._verify_reference(root, bad_reference, "deliberately_bad_hash", {}, hash_errors)
	_expect("file_sha256_mismatch_rejected", {"ok": hash_ok, "errors": hash_errors}, false, "SHA-256 mismatch")
	_expect("validation_does_not_mutate_inputs", {"ok": original_fingerprint == JSON.stringify(documents).sha256_text(), "errors": []}, true)
	_expect("missing_file_fail_closed", Contract.validate_files(root, material_path + ".missing", palette_path, rules_path), false, "document: missing")
	_expect("unsafe_relative_path_fail_closed", Contract.validate_files(root, "../outside.json", palette_path, rules_path), false, "binding: expected safe")
	_finish(args, file_result)

func _test_flags() -> Dictionary:
	var d := documents.duplicate(true)
	d.material_revision["all_pass"] = false
	d.material_revision["tests"] = {}
	d.palette_revision["all_pass"] = false
	d.palette_revision["existing_material_definitions_unchanged"] = false
	return Contract.validate_documents(d)

func _alias_tests() -> void:
	var palette: Dictionary = documents.source.materials
	var aliases: Array = documents.rules.material_role_aliases
	for pair in [["boundary_low", 0.8, true], ["boundary_high", 1.2, true], ["integer_one", 1, true], ["below_range", 0.799999, false], ["above_range", 1.200001, false], ["boolean", true, false], ["nan", NAN, false], ["positive_infinity", INF, false], ["negative_infinity", -INF, false], ["numeric_string", "1.0", false], ["null", null, false]]:
		var a: Array = aliases.duplicate(true)
		a[0].luminance_multiplier = pair[1]
		_expect("alias_multiplier_" + pair[0], Contract.validate_aliases(a, palette), pair[2], "" if pair[2] else "multiplier must be finite numeric")
	var a: Array = aliases.duplicate(true)
	a.append(a[0].duplicate(true))
	_expect("duplicate_alias", Contract.validate_aliases(a, palette), false, "duplicate alias")
	a = aliases.duplicate(true)
	a[0].base_material_id = "not_a_known_material"
	_expect("unknown_alias_base", Contract.validate_aliases(a, palette), false, "unknown base")
	a = aliases.duplicate(true)
	a[0].base_material_id = a[0].material_id
	_expect("self_alias", Contract.validate_aliases(a, palette), false, "self-reference")
	a = aliases.duplicate(true)
	a[0].base_material_id = a[1].material_id
	a[1].base_material_id = a[2].material_id
	a[2].base_material_id = a[0].material_id
	_expect("three_node_alias_cycle", Contract.validate_aliases(a, palette), false, "cyclic dependency")
	a = aliases.duplicate(true)
	a[0].base_material_id = a[1].material_id
	var chain_result := Contract.validate_aliases(a, palette)
	_expect("acyclic_alias_chain_resolves_original_base", chain_result, true)
	_expect("chain_root_is_original_palette", {"ok": chain_result.resolved_aliases[a[0].material_id].base_material_id == aliases[1].base_material_id, "errors": []}, true)
	a = aliases.duplicate(true)
	a[0].material_id = "slate"
	_expect("alias_cannot_shadow_original", Contract.validate_aliases(a, palette), false, "shadows original")
	for field in ["material_id", "base_material_id"]:
		for value in [4, true, null, ""]:
			a = aliases.duplicate(true)
			a[0][field] = value
			_expect("alias_" + field + "_rejects_" + str(value), Contract.validate_aliases(a, palette), false, "must be nonempty strings")
	a = aliases.duplicate(true)
	a[0]["unexpected"] = "field"
	_expect("alias_extra_field", Contract.validate_aliases(a, palette), false, "unexpected declaration fields")
	_expect("aliases_array_required", Contract.validate_aliases({}, palette), false, "expected array")
	_expect("source_palette_dictionary_required", Contract.validate_aliases(aliases, []), false, "source palette dictionary")
	a = aliases.duplicate(true)
	a[0] = "not a declaration"
	_expect("alias_dictionary_required", Contract.validate_aliases(a, palette), false, "declaration must be a dictionary")

func _document_tests() -> void:
	for target in ["palette_source", "revised_roof", "revised_canonical"]:
		var d := documents.duplicate(true)
		d[target].materials["unapproved_palette_addition"] = "ffffff"
		_expect(target + "_unknown_palette_addition", Contract.validate_documents(d), false, "unauthorized addition")
		d = documents.duplicate(true)
		d[target].materials.slate = "000000"
		_expect(target + "_original_palette_value_changed", Contract.validate_documents(d), false, "changed/removed original")
		d = documents.duplicate(true)
		d[target].materials.erase("stone")
		_expect(target + "_original_palette_removed", Contract.validate_documents(d), false, "changed/removed original")
		d = documents.duplicate(true)
		d[target].materials.erase(d.rules.material_role_aliases[0].material_id)
		_expect(target + "_alias_palette_missing", Contract.validate_documents(d), false, "missing alias")
		d = documents.duplicate(true)
		d[target].materials[d.rules.material_role_aliases[0].material_id] = "ffffff"
		_expect(target + "_alias_rgb_wrong", Contract.validate_documents(d), false, "alias RGB does not match")
		d = documents.duplicate(true)
		d[target].components[0].operations[0].shape["unauthorized_shape_field"] = 1
		_expect(target + "_nonmaterial_shape_mutation", Contract.validate_documents(d), false, "nonmaterial:")
		d = documents.duplicate(true)
		d[target].instances[0]["unexpected_transform"] = [1, 2, 3]
		_expect(target + "_instance_mutation", Contract.validate_documents(d), false, "nonmaterial:")
		d = documents.duplicate(true)
		d[target].constraints.append({"kind": "bogus_constraint"})
		_expect(target + "_constraint_mutation", Contract.validate_documents(d), false, "nonmaterial:")
	var d := documents.duplicate(true)
	d.palette_source.components[0].operations[0].material = "slate_dark"
	_expect("palette_source_operation_material_forbidden", Contract.validate_documents(d), false, "nonmaterial: palette_source")
	for pair in [["roof", "revised_roof", "roof_operation_changes"], ["canonical", "revised_canonical", "canonical_operation_changes"]]:
		d = documents.duplicate(true)
		d.material_revision[pair[2]].pop_back()
		_expect(pair[0] + "_missing_change_record", Contract.validate_documents(d), false, "unlisted material mutation")
		d = documents.duplicate(true)
		d.material_revision[pair[2]].append(d.material_revision[pair[2]][0].duplicate(true))
		_expect(pair[0] + "_duplicate_change_record", Contract.validate_documents(d), false, "duplicate operation change")
		d = documents.duplicate(true)
		d.material_revision[pair[2]][0].before = "stone"
		_expect(pair[0] + "_incorrect_change_before", Contract.validate_documents(d), false, "before/after mismatch")
		d = documents.duplicate(true)
		d.material_revision[pair[2]][0].after = "stone"
		_expect(pair[0] + "_incorrect_change_after", Contract.validate_documents(d), false, "before/after mismatch")
		d = documents.duplicate(true)
		d.material_revision[pair[2]][0].operation = "unknown_operation"
		_expect(pair[0] + "_unknown_change_operation", Contract.validate_documents(d), false, "unknown operation")
		d = documents.duplicate(true)
		var unlisted := _find_unlisted_operation(d[pair[1]], d.material_revision[pair[2]])
		unlisted.material = "slate_dark"
		_expect(pair[0] + "_unauthorized_material_mutation", Contract.validate_documents(d), false, "unlisted material mutation")
		d = documents.duplicate(true)
		d[pair[1]].components[0].operations.append(d[pair[1]].components[0].operations[0].duplicate(true))
		_expect(pair[0] + "_duplicate_operation_id", Contract.validate_documents(d), false, "duplicate operation")
		d = documents.duplicate(true)
		d[pair[1]].components.reverse()
		_expect(pair[0] + "_component_order_changed", Contract.validate_documents(d), false, "nonmaterial:")
		d = documents.duplicate(true)
		d[pair[1]].components[0].operations[0]["material_selector"] = "slate"
		_expect(pair[0] + "_added_selector_field", Contract.validate_documents(d), false, "nonmaterial:")
	d = documents.duplicate(true)
	d.palette_revision.allowed_added_material_ids.append(d.palette_revision.allowed_added_material_ids[0])
	_expect("duplicate_allowed_palette_id", Contract.validate_documents(d), false, "duplicate allowed alias")
	d = documents.duplicate(true)
	d.palette_revision.material_role_aliases[0].luminance_multiplier = 0.9
	_expect("alias_declarations_disagree", Contract.validate_documents(d), false, "declarations disagree")
	d = documents.duplicate(true)
	d.material_revision.changed_operations = true
	_expect("boolean_change_count_rejected", Contract.validate_documents(d), false, "changed_operations")
	d = documents.duplicate(true)
	d.erase("base_canonical")
	_expect("missing_required_document", Contract.validate_documents(d), false, "document:")
	for label in ["source", "palette_source", "base_roof", "revised_roof", "base_canonical", "revised_canonical"]:
		d = documents.duplicate(true)
		d[label].materials = null
		_expect(label + "_malformed_palette_fails_closed", Contract.validate_documents(d), false, "materials must be a dictionary")
	d = documents.duplicate(true)
	d.revised_roof.components = null
	_expect("malformed_component_array_fails_closed", Contract.validate_documents(d), false, "components must be an array")
	d = documents.duplicate(true)
	d.material_revision.roof_operation_changes = null
	_expect("malformed_change_array_fails_closed", Contract.validate_documents(d), false, "change list must be an array")

func _find_unlisted_operation(master: Dictionary, changes: Array) -> Dictionary:
	var changed: Dictionary = {}
	for change in changes:
		changed[JSON.stringify([change.component, change.operation])] = true
	for component in master.components:
		for operation in component.operations:
			if not changed.has(JSON.stringify([component.id, operation.id])):
				return operation
	return {}

func _expect(name: String, result: Dictionary, expected_ok: bool, required_error: String = "") -> void:
	var error_text := JSON.stringify(result.get("errors", []))
	var passed: bool = result.get("ok", false) == expected_ok and (required_error.is_empty() or error_text.contains(required_error))
	results.append({"name": name, "passed": passed, "expected_ok": expected_ok, "actual_ok": result.get("ok"), "required_error": required_error, "errors": result.get("errors", [])})
	if not passed:
		printerr("FAIL " + name + " " + error_text)

func _finish(args: PackedStringArray, real_result: Dictionary) -> void:
	var failed := 0
	for result in results:
		if not result.passed:
			failed += 1
	var report := {"schema": "riverstone.material_alias_contract_tests.v1", "godot_version": Engine.get_version_info().string,
		"all_pass": failed == 0, "total": results.size(), "passed": results.size() - failed, "failed": failed,
		"real_contract": real_result, "cases": results, "voxel_compilation_performed": false, "runtime_activated": false}
	if args.size() > 2:
		var output := FileAccess.open(args[2], FileAccess.WRITE)
		if output == null:
			printerr("Could not write requested test report")
			quit(2)
			return
		output.store_string(JSON.stringify(report, "\t") + "\n")
	print(JSON.stringify({"all_pass": report.all_pass, "total": report.total, "passed": report.passed, "failed": failed, "real_contract_ok": real_result.ok}))
	quit(0 if failed == 0 else 1)
