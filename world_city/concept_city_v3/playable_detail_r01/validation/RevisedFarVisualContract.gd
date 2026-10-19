extends RefCounted
const RD=preload("res://RenderData.gd")
static func validate(key: String,entry: Dictionary,source: Dictionary,c: Variant,data: Dictionary,actual_sha: String) -> String:
	if not c is Dictionary:return "missing contract"
	var schema: String=str(c.get("schema",""))
	if schema not in ["riverstone.revised_far_visual.v1","riverstone.revised_far_visual.v2"] or c.get("asset_key","")!=key:return "wrong contract identity"
	if not bool(c.get("all_pass",false)) or bool(c.get("collision_reference_changed",true)):return "unverified or collision-changing contract"
	if not entry.get("source_revision") is Dictionary:return "missing source revision"
	if c.get("original_master_sha256","")!=source.master_sha256 or c.get("original_render_sha256","")!=source.render_sha256 or c.get("revised_master_sha256","")!=entry.source_revision.revised_master_sha256:return "source binding mismatch"
	if c.get("render_path","")!=entry.get("far_visual_render_path","") or c.get("render_sha256","")!=entry.get("far_visual_render_sha256","") or actual_sha!=c.get("render_sha256",""):return "render identity mismatch"
	if float(c.get("pitch",-1))!=.5 or float(data.get("pitch",-1))!=.5 or c.get("grid_origin",[])!=[0.0,0.0,0.0] or data.get("grid_origin",[])!=[0.0,0.0,0.0]:return "grid mismatch"
	if not c.get("tests") is Dictionary or c.tests.is_empty() or not c.tests.values().all(func(v):return v is bool and v):return "missing passed tests"
	var count:=0
	for g in data.groups:count+=g.quads.size()
	if count!=int(c.get("output_quad_count",-1)) or count<=0 or count>50000:return "quad budget mismatch"
	if not source.bounds is Dictionary:return "missing source bounds"
	if schema=="riverstone.revised_far_visual.v2":
		if c.get("geometry_mode","")!="source_roof_union_lod" or not data.get("source_surface_lod") is Dictionary or not data.source_surface_lod.get("source_solid_union",false) or data.source_surface_lod.get("high_resolution_voxel_source",true):return "invalid source surface LOD declaration"
		if c.get("union_provenance_sha256","")!=entry.get("far_union_provenance_sha256","") or c.get("source_shadow_proxy_sha256","")!=entry.get("shadow_proxy_sha256",""):return "unbound source roof proof"
		var proof: Dictionary=c.get("source_bounds_contract",{})
		var bounds=preload("res://validation/SourceBoundsContract.gd")
		if not bounds.same(proof,entry.get("bounds_contract",{})):return "unbound source envelope"
		var problem: String=bounds.validate(proof,data.bounds,source.bounds,source.master_sha256)
		if not problem.is_empty():return "source envelope: "+problem
	else:
		for a in range(3):
			if float(data.bounds.min[a])<float(source.bounds.min[a]) or float(data.bounds.max[a])>float(source.bounds.max[a]):return "far bounds escape unchanged source envelope"
	return ""
