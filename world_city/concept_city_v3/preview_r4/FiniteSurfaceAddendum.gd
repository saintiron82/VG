extends RefCounted
## A source-bound, append-only top-surface addendum. It never edits cached parts.
static func apply_to_scene(scene:Dictionary, patch:Dictionary, scene_sha:String)->Dictionary:
	if patch.get("schema","")!="riverstone.frozen_scene_patch.v1":return {"status":"fail","reason":"schema"}
	if str(patch.get("base_scene_sha256",""))!=scene_sha:return {"status":"fail","reason":"base_scene_identity"}
	for key in ["surface_edits","removed_foundation_proxy_ids"]:
		var edits=patch.get(key,[])
		if not edits is Array or not edits.is_empty():return {"status":"fail","reason":"append_only_required"}
	var hashes=patch.get("source_surface_hashes",{})
	if not hashes is Dictionary or not hashes.is_empty():return {"status":"fail","reason":"source_edits_not_supported"}
	var surfaces=patch.get("appended_surfaces",{})
	if not surfaces is Dictionary or surfaces.is_empty():return {"status":"fail","reason":"empty_addendum"}
	var triangles:=0
	for material in surfaces:
		if not scene.get("materials",{}).has(material):return {"status":"fail","reason":"unknown_material"}
		var vertices=surfaces[material]
		if not vertices is Array or vertices.is_empty() or vertices.size()%3!=0:return {"status":"fail","reason":"triangle_rows"}
		for row in vertices:
			if not row is Array or row.size()!=3:return {"status":"fail","reason":"vertex_shape"}
			for value in row:
				if not(value is int or value is float)or not is_finite(float(value)):return {"status":"fail","reason":"nonfinite_coordinate"}
		for i in range(0,vertices.size(),3):
			var a:=Vector3(float(vertices[i][0]),float(vertices[i][1]),float(vertices[i][2]))
			var b:=Vector3(float(vertices[i+1][0]),float(vertices[i+1][1]),float(vertices[i+1][2]))
			var c:=Vector3(float(vertices[i+2][0]),float(vertices[i+2][1]),float(vertices[i+2][2]))
			if not a.is_finite() or not b.is_finite() or not c.is_finite():return {"status":"fail","reason":"float32_overflow"}
			if (b-a).cross(c-a).y<=0.0:return {"status":"fail","reason":"top_surface_winding_or_degenerate"}
		triangles+=vertices.size()/3
	# Commit only after every row passed. Original scene remains unchanged on failure.
	for material in surfaces:
		if not scene.surfaces.has(material):scene.surfaces[material]=[]
		scene.surfaces[material].append_array(surfaces[material])
	return {"status":"pass","id":str(patch.get("id","")),"appended_triangles":triangles,"base_scene_sha256":scene_sha,"source_edits":0}
