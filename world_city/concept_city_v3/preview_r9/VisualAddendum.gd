extends RefCounted
## Placement orchestration only: render geometry remains common RenderData.
static func reject(reason:String)->Dictionary:return {"status":"fail","reason":reason}
static func finite_vector(value:Variant,size:int)->bool:
	if not value is Array or value.size()!=size:return false
	for n in value:
		if not (n is float or n is int) or not is_finite(float(n)):return false
	return true
static func apply_to_scene(data:Dictionary,index:Dictionary,base_sha:String,repo:String)->Dictionary:
	if index.get("schema","")!="riverstone.city.visual_pack_index.v1" or index.get("base_scene_sha256","")!=base_sha:return reject("index/base identity")
	var additions:Array=[];var replacements:Dictionary={};var base_instances:Dictionary={};var removed:Dictionary={};var assets:Dictionary={};var cameras:Dictionary={};var records:Array=[];var ids:Dictionary={}
	for p in data.common_instances:ids[str(p.id)]=true;base_instances[str(p.id)]=p
	for entry in index.get("packs",[]):
		var path:String=repo+"/"+str(entry.path)
		if FileAccess.get_sha256(path)!=str(entry.sha256):return reject("pack hash "+path)
		var value=JSON.parse_string(FileAccess.get_file_as_string(path))
		if not value is Dictionary:return reject("pack object")
		var pack:Dictionary=value
		if pack.get("schema","")!="riverstone.city.visual_addendum.v1" or pack.get("base_scene_sha256","")!=base_sha:return reject("pack/base identity")
		for key in pack.get("common_assets",{}):
			var a:Dictionary=pack.common_assets[key]
			if not a.has("render_path") or not a.has("render_sha256"):return reject("asset identity")
			if data.common_assets.has(key) and data.common_assets[key].render_sha256!=a.render_sha256:return reject("asset key conflict")
			if assets.has(key) and assets[key].render_sha256!=a.render_sha256:return reject("pack asset conflict")
			assets[key]=a
		for id in pack.get("remove_instance_ids",[]):
			if not ids.has(str(id)) or removed.has(str(id)) or replacements.has(str(id)):return reject("unknown/duplicate removal")
			removed[str(id)]=true
		for p in pack.get("add_instances",[]):
			if not p is Dictionary or not p.has("id") or ids.has(str(p.id)):return reject("duplicate/addition ID")
			if not finite_vector(p.get("position_m"),3) or not is_finite(float(p.get("yaw_rad",0))):return reject("nonfinite pose")
			var scale_value:Variant=p.get("scale",[1,1,1])
			if not finite_vector(scale_value,3):return reject("invalid scale")
			for axis in scale_value:
				if float(axis)!=1.0:return reject("unsupported scaling")
			if not p.has("asset_key") or not p.has("palette_id"):return reject("missing asset/palette")
			ids[str(p.id)]=true;additions.append(p)
		for replacement in pack.get("replace_instances",[]):
			var id:String=str(replacement.get("id",""))
			if not base_instances.has(id) or replacements.has(id) or removed.has(id):return reject("unknown/duplicate replacement")
			var original:Dictionary=base_instances[id]
			if original.asset_key!=replacement.get("expected_asset_key"):return reject("replacement source asset")
			if not finite_vector(replacement.get("expected_position_m"),3):return reject("replacement expected pose")
			for axis in range(3):
				if float(original.position_m[axis])!=float(replacement.expected_position_m[axis]):return reject("replacement position changed")
			if float(original.get("yaw_rad",0))!=float(replacement.get("expected_yaw_rad",0)):return reject("replacement rotation changed")
			if not replacement.has("proof_path") or not replacement.has("proof_sha256"):return reject("replacement proof missing")
			if FileAccess.get_sha256(repo+"/"+str(replacement.proof_path))!=str(replacement.proof_sha256):return reject("replacement proof hash")
			var revised:Dictionary=original.duplicate(true)
			revised.asset_key=replacement.asset_key;revised.palette_id=replacement.palette_id;revised.palette_override=replacement.get("palette_override",{})
			replacements[id]=revised
		for key in pack.get("inspection_cameras",{}):
			var c:Dictionary=pack.inspection_cameras[key]
			if not finite_vector(c.get("position_m"),3) or not finite_vector(c.get("target_m"),3):return reject("invalid camera")
			cameras[key]=c
		records.append({"path":entry.path,"sha256":entry.sha256,"added":pack.get("add_instances",[]).size(),"removed":pack.get("remove_instance_ids",[]).size()})
	for p in additions+replacements.values():
		if not assets.has(p.asset_key) and not data.common_assets.has(p.asset_key):return reject("unresolved asset "+str(p.asset_key))
	# All checks precede mutation. Original base dictionary came from a preserved file.
	var retained:Array=[]
	for p in data.common_instances:
		if not removed.has(str(p.id)):retained.append(replacements.get(str(p.id),p))
	for p in additions:
		if not removed.has(str(p.id)):retained.append(p)
	data.common_instances=retained
	for key in assets:data.common_assets[key]=assets[key]
	for key in cameras:data.inspection_cameras[key]=cameras[key]
	return {"status":"pass","packs":records,"added_instances":additions.size(),"removed_instances":removed.size(),"same_pose_geometry_replacement_instances":replacements.size(),"base_scene_sha256":base_sha,"terrain_geometry_unchanged":true}
