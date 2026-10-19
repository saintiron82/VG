extends RefCounted
## Small source-bound scene orchestration. Authoring/clipping remains in existing Python finite-patch pipeline.
static func fail(reason:String)->Dictionary:return {"status":"fail","reason":reason}
static func vertices_ok(values:Variant)->bool:
	if not values is Array or values.size()%3!=0:return false
	for v in values:
		if not v is Array or v.size()!=3:return false
		for n in v:
			if not(n is float or n is int)or not is_finite(float(n)):return false
		if not Vector3(v[0],v[1],v[2]).is_finite():return false
	for i in range(0,values.size(),3):
		var a:=Vector3(values[i][0],values[i][1],values[i][2]);var b:=Vector3(values[i+1][0],values[i+1][1],values[i+1][2]);var c:=Vector3(values[i+2][0],values[i+2][1],values[i+2][2])
		if (b-a).cross(c-a).length_squared()==0:return false
	return true
static func exact_triangle(a:Array,b:Variant)->bool:
	if not b is Array or b.size()!=3 or not vertices_ok(b):return false
	for i in range(3):
		for j in range(3):
			if float(a[i][j])!=float(b[i][j]):return false
	return true
static func apply_to_scene(scene:Dictionary,patch:Dictionary,base_sha:String)->Dictionary:
	if patch.get("schema","") not in ["riverstone.frozen_scene_patch.v1","riverstone.frozen_scene_disjoint_patch_composition.v1"]:return fail("schema")
	if patch.get("base_scene_sha256","")!=base_sha:return fail("base_identity")
	var edits:Dictionary={};var append:Dictionary=patch.get("appended_surfaces",{});var removed:Dictionary={};var box_ids:Dictionary={};var edit_count:int=0
	for box in scene.get("boxes",[]):box_ids[str(box.id)]=true
	for id in patch.get("removed_foundation_proxy_ids",[]):
		if not box_ids.has(str(id)) or removed.has(str(id)):return fail("unknown/duplicate proxy removal")
		removed[str(id)]=true
	for row in patch.get("surface_edits",[]):
		var material:String=str(row.get("material",""));var number=row.get("triangle_index",-1)
		if not(number is float or number is int) or float(number)!=floorf(float(number))or number<0:return fail("triangle index")
		var index:int=int(number)
		if not scene.surfaces.has(material)or index*3+3>scene.surfaces[material].size():return fail("source face range")
		var source:Array=scene.surfaces[material].slice(index*3,index*3+3)
		if not exact_triangle(source,row.get("source_triangle_xyz_m")):return fail("source coordinates")
		if not edits.has(material):edits[material]={}
		if edits[material].has(index):return fail("duplicate face edit")
		var replacement:Array=[]
		for tri in row.get("replacement_triangles_xyz_m",[]):
			if not tri is Array or tri.size()!=3 or not vertices_ok(tri):return fail("replacement triangle")
			replacement.append_array(tri)
		# Reject reversed top faces; vertical source-plane/bank orientation is producer-audited.
		var a:=Vector3(source[0][0],source[0][1],source[0][2]);var b:=Vector3(source[1][0],source[1][1],source[1][2]);var c:=Vector3(source[2][0],source[2][1],source[2][2]);var normal:Vector3=(b-a).cross(c-a)
		for i in range(0,replacement.size(),3):
			var u:=Vector3(replacement[i][0],replacement[i][1],replacement[i][2]);var v:=Vector3(replacement[i+1][0],replacement[i+1][1],replacement[i+1][2]);var w:=Vector3(replacement[i+2][0],replacement[i+2][1],replacement[i+2][2])
			if normal.dot((v-u).cross(w-u))<=0:return fail("replacement winding")
		edits[material][index]=replacement;edit_count+=1
	for material in append:
		if not scene.materials.has(material)or not vertices_ok(append[material]):return fail("appended surface")
		if material!="bank":
			for i in range(0,append[material].size(),3):
				var t:Array=append[material].slice(i,i+3);var a:=Vector3(t[0][0],t[0][1],t[0][2]);var b:=Vector3(t[1][0],t[1][1],t[1][2]);var c:=Vector3(t[2][0],t[2][1],t[2][2])
				if (b-a).cross(c-a).y<=0:return fail("appended top winding")
	# All checks completed before any mutation. Base file remains unchanged.
	for material in edits:
		var rebuilt:Array=[];var original:Array=scene.surfaces[material]
		for i in range(original.size()/3):rebuilt.append_array(edits[material].get(i,original.slice(i*3,i*3+3)))
		scene.surfaces[material]=rebuilt
	for material in append:
		if not scene.surfaces.has(material):scene.surfaces[material]=[]
		scene.surfaces[material].append_array(append[material])
	if not removed.is_empty():
		var retained:Array=[]
		for box in scene.boxes:
			if not removed.has(str(box.id)):retained.append(box)
		scene.boxes=retained
	return {"status":"pass","source_base_sha256":base_sha,"source_face_edits":edit_count,"removed_proxy_count":removed.size(),"authoring":"Existing finite clipping pipeline; no runtime height resampling"}
