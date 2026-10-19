extends RefCounted
## Optional, narrow source revision. Never silently swap the canonical city master.
static func same(a: Variant,b: Variant) -> bool:
	if a is Dictionary and b is Dictionary:
		if a.size()!=b.size():return false
		for key in a:
			if not b.has(key) or not same(a[key],b[key]):return false
		return true
	if a is Array and b is Array:
		if a.size()!=b.size():return false
		for i in a.size():
			if not same(a[i],b[i]):return false
		return true
	return a==b
static func validate(revision: Dictionary,original: Dictionary,revised: Dictionary) -> String:
	if revision.get("change_kind","")!="window_bay_relocation":return "unsupported source revision"
	var allowed: Array=revision.get("allowed_operation_ids",[])
	if allowed.is_empty():return "empty allowed operations"
	var unique: Dictionary={}
	for id in allowed:
		if unique.has(id):return "duplicate allowed operation"
		unique[id]=true
	var restored:=revised.duplicate(true);var old: Dictionary={};var changed: Dictionary={}
	for component in original.get("components",[]):old[component.id]=component
	for component in restored.get("components",[]):
		if not old.has(component.id):return "new source component"
		var before: Dictionary={}
		for operation in old[component.id].operations:before[operation.id]=operation
		for operation in component.operations:
			if operation.id not in allowed:continue
			if component.id!="windows" or not before.has(operation.id):return "non-window relocation"
			var source: Dictionary=before[operation.id]
			if operation.get("action","")!="paint" or source.get("action","")!="paint" or not operation.has("transform") or not source.has("transform"):return "invalid relocated operation"
			var a: Array=source.transform.get("translation",[]);var b: Array=operation.transform.get("translation",[])
			if a.size()!=3 or b.size()!=3 or a[0]!=b[0] or a[1]!=b[1] or a[2]==b[2]:return "non-Z translation change"
			operation.transform.translation[2]=a[2]
			if not same(operation,source):return "shape/material/basis change"
			if changed.has(operation.id):return "duplicate changed operation"
			changed[operation.id]=true
	if changed.size()!=allowed.size() or not same(restored,original):return "unlisted source changes"
	if not bool(revision.get("unchanged_structure_proof",{}).get("no_fill_operations_added",false)):return "missing no-fill proof"
	return ""
