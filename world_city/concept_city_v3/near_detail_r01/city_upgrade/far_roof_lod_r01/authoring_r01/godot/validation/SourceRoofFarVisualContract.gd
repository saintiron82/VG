extends RefCounted
## Exact source-roof LOD plus byte-equivalent indexed nonroof. Visual only.
const Bounds=preload("res://validation/SourceBoundsContract.gd")
static func same(a: Variant,b: Variant) -> bool:return JSON.stringify(a)==JSON.stringify(b)
static func validate(key: String,entry: Dictionary,source: Dictionary,c: Variant,data: Dictionary,original: Dictionary,actual_sha: String) -> String:
	if not c is Dictionary or c.get("schema","")!="riverstone.source_roof_far_visual.v1" or c.get("asset_key","")!=key:return "identity"
	if entry.has("source_revision") or c.get("source_revision_required",true):return "requires separate revision contract"
	if not c.get("all_pass",false) or c.get("collision_reference_changed",true) or c.get("near_render_changed",true) or c.get("source_master_changed",true):return "unverified or changed source"
	if c.get("original_source_master_sha256","")!=source.master_sha256 or c.get("original_source_render_sha256","")!=source.render_sha256:return "source binding"
	if c.get("render_sha256","")!=actual_sha or actual_sha!=entry.get("far_visual_render_sha256","") or c.get("render_path","")!=entry.get("far_visual_render_path",""):return "render binding"
	if c.get("near_render_identity_observed",{}).get("sha256","")!=entry.get("sha256",""):return "stale near counterpart"
	if not c.get("tests") is Dictionary or c.tests.is_empty() or not c.tests.values().all(func(v):return v is bool and v):return "geometry tests"
	if data.get("pitch")!=.5 or data.get("grid_origin")!=[0.0,0.0,0.0] or not same(data.materials,original.materials):return "grid or palette"
	if not data.get("source_surface_lod") is Dictionary or not data.source_surface_lod.get("source_solid_union",false) or data.source_surface_lod.get("high_resolution_voxel_source",true):return "LOD declaration"
	var roof: Dictionary={}
	for material in c.get("owned_roof_materials",[]):roof[material]=true
	if roof.is_empty():return "no owned roof materials"
	var old: Dictionary={};var now: Dictionary={}
	for group in original.groups:old[group.material]=group
	for group in data.groups:
		if now.has(group.material):return "duplicate material group"
		now[group.material]=group
	for material in now:
		if not old.has(material) and not roof.has(material):return "changed group ownership"
	var count:=0
	for material in old:
		if not now.has(material):return "missing material"
		if not roof.has(material) and not same(old[material],now[material]):return "nonroof geometry changed"
	for group in data.groups:count+=group.quads.size()
	if count!=int(c.get("output_quad_count",-1)) or count<=0 or count>50000:return "quad budget"
	var envelope: Dictionary=c.get("allowed_visual_union_bounds",{});var rb: Dictionary=c.get("exact_source_roof_bounds",{})
	if not Bounds.bounds_ok(envelope) or not Bounds.bounds_ok(rb) or not same(c.get("candidate_bounds"),data.bounds):return "malformed envelope"
	for group in data.groups:
		var bound: Dictionary=rb if roof.has(group.material) else source.bounds
		for q in group.quads:
			for v in q:
				for a in 3:
					if not is_finite(float(v[a])) or v[a]<bound.min[a]-.0000001 or v[a]>bound.max[a]+.0000001:return "vertex outside owner envelope"
					if v[a]<envelope.min[a]-.0000001 or v[a]>envelope.max[a]+.0000001:return "vertex outside union envelope"
	return ""
