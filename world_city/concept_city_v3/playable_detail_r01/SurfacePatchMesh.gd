extends RefCounted
## Shared near-surface geometry adapter. Input is common-compiler render data.
## It neither resamples voxels nor changes collision/authoritative source meshes.
const RD=preload("res://RenderData.gd")

static func module_mesh(data: Dictionary) -> ArrayMesh:
	var vertices:=PackedVector3Array();var normals:=PackedVector3Array();var colors:=PackedColorArray()
	var average:=Color(0,0,0,1);var samples:=0
	# Declared palette is identical in full and trimmed modules, even if a trim
	# contains no geometry for one tone. Never normalize from surviving groups.
	for material in data.materials:
		if str(material).ends_with("joint"):continue
		average+=RD.color_value(data.materials[material]);samples+=1
	average/=float(maxi(samples,1))
	for group in data.groups:
		var color: Color=RD.color_value(data.materials[group.material])
		var relative:=Color(clampf(color.r/maxf(average.r,0.01),.45,1.4)/1.4,clampf(color.g/maxf(average.g,0.01),.45,1.4)/1.4,clampf(color.b/maxf(average.b,0.01),.45,1.4)/1.4,1)
		for quad in group.quads:
			var n: Vector3=(RD.vector(quad[1])-RD.vector(quad[0])).cross(RD.vector(quad[2])-RD.vector(quad[0])).normalized()
			# Backing against the original support is hidden. Its coplanar rear is omitted.
			if n.z<-.999:continue
			for i in RD.TRIANGLE_ORDER:
				vertices.append(RD.vector(quad[i]));normals.append(n);colors.append(relative)
	var arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_COLOR]=colors
	var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var material:=StandardMaterial3D.new();material.vertex_color_use_as_albedo=true;material.roughness=1;material.metallic_specular=0
	mesh.surface_set_material(0,material)
	return mesh

static func rectangular_face(quad: Array,minimum_extent: float=1.0) -> Dictionary:
	var p:=RD.vector(quad[0]);var n: Vector3=(RD.vector(quad[1])-p).cross(RD.vector(quad[2])-p).normalized()
	if maxf(absf(n.x),maxf(absf(n.y),absf(n.z)))<.99999:return {}
	var v:=Vector3.UP;var u: Vector3=v.cross(n)
	if absf(n.y)>.999:u=Vector3.RIGHT;v=n.cross(u)
	var low:=Vector2(INF,INF);var high:=Vector2(-INF,-INF)
	for point in quad:
		var q:=RD.vector(point);var uv:=Vector2(u.dot(q),v.dot(q));low=low.min(uv);high=high.max(uv)
	if high.x-low.x<minimum_extent-.00001 or high.y-low.y<minimum_extent-.00001:return {}
	return {"u":u,"v":v,"n":n,"low":low,"high":high,"plane":p.dot(n),"area":(high.x-low.x)*(high.y-low.y)}

static func subtract_feature_regions(face: Dictionary,regions: Array) -> Array:
	# Compile ROI is deliberately larger than a window. Here we subtract only the
	# source-derived feature envelope, rounded OUT to the existing 0.25m trim grid.
	# This changes transport placement only, never the compiled voxel module.
	var fragments: Array=[face.duplicate(true)]
	var u: Vector3=face.u;var v: Vector3=face.v;var n: Vector3=face.n
	for region in regions:
		var a:=RD.vector(region.min);var b:=RD.vector(region.max)
		var normal_low:=INF;var normal_high:=-INF
		var low:=Vector2(INF,INF);var high:=Vector2(-INF,-INF)
		for x in [a.x,b.x]:
			for y in [a.y,b.y]:
				for z in [a.z,b.z]:
					var p:=Vector3(x,y,z);normal_low=minf(normal_low,n.dot(p));normal_high=maxf(normal_high,n.dot(p));var uv:=Vector2(u.dot(p),v.dot(p));low=low.min(uv);high=high.max(uv)
		if float(face.plane)+.0375<normal_low-.00001 or float(face.plane)>normal_high+.00001:continue
		low=Vector2(floorf(low.x*4+.00001),floorf(low.y*4+.00001))*.25
		high=Vector2(ceilf(high.x*4-.00001),ceilf(high.y*4-.00001))*.25
		var next: Array=[]
		for fragment in fragments:
			var fl: Vector2=fragment.low;var fh: Vector2=fragment.high
			var cut_low:=fl.max(low);var cut_high:=fh.min(high)
			if cut_high.x-cut_low.x<=.00001 or cut_high.y-cut_low.y<=.00001:next.append(fragment);continue
			var pieces: Array=[[fl,Vector2(cut_low.x,fh.y)],[Vector2(cut_high.x,fl.y),fh],[Vector2(cut_low.x,fl.y),Vector2(cut_high.x,cut_low.y)],[Vector2(cut_low.x,cut_high.y),Vector2(cut_high.x,fh.y)]]
			for piece in pieces:
				var size: Vector2=piece[1]-piece[0]
				if size.x<=.00001 or size.y<=.00001:continue
				var kept: Dictionary=fragment.duplicate(true);kept.low=piece[0];kept.high=piece[1];kept.area=size.x*size.y;next.append(kept)
		fragments=next
	return fragments

static func full_patches(face: Dictionary,observer: Vector3,radius: float) -> Array:
	var u: Vector3=face.u;var v: Vector3=face.v;var n: Vector3=face.n
	var distance:=absf(n.dot(observer)-float(face.plane))
	if distance>radius:return []
	var uv:=Vector2(u.dot(observer),v.dot(observer))
	var low: Vector2=face.low;var high: Vector2=face.high
	var out: Array=[]
	# Integer metre modules, contained in an actual exterior quad, never over a cut/door.
	var x0:=maxi(ceili(low.x-.00001),floori(uv.x-radius));var x1:=mini(floori(high.x+.00001)-1,ceili(uv.x+radius))
	var y0:=maxi(ceili(low.y-.00001),floori(uv.y-radius));var y1:=mini(floori(high.y+.00001)-1,ceili(uv.y+radius))
	for x in range(x0,x1+1):
		for y in range(y0,y1+1):
			var centre:=u*(x+.5)+v*(y+.5)+n*float(face.plane)
			var d:=centre.distance_to(observer)
			if d<=radius:out.append({"x":x,"y":y,"distance":d,"transform":Transform3D(Basis(u,v,n),u*x+v*y+n*(float(face.plane)+.0375))})
	return out

static func trimmed_patches(face: Dictionary,observer: Vector3,radius: float) -> Array:
	var u: Vector3=face.u;var v: Vector3=face.v;var n: Vector3=face.n
	if absf(n.dot(observer)-float(face.plane))>radius:return []
	var low: Vector2=face.low;var high: Vector2=face.high
	for coordinate in [low.x,low.y,high.x,high.y]:
		if absf(coordinate*4-roundf(coordinate*4))>.0001:return [] # explicit unsupported edge
	var uv:=Vector2(u.dot(observer),v.dot(observer));var out: Array=[]
	var x0:=maxi(floori(low.x),floori(uv.x-radius));var x1:=mini(ceili(high.x)-1,ceili(uv.x+radius))
	var y0:=maxi(floori(low.y),floori(uv.y-radius));var y1:=mini(ceili(high.y)-1,ceili(uv.y+radius))
	for x in range(x0,x1+1):
		for y in range(y0,y1+1):
			var start:=Vector2(maxf(x,low.x),maxf(y,low.y));var end:=Vector2(minf(x+1,high.x),minf(y+1,high.y));var size:=end-start
			if size.x<.24999 or size.y<.24999:continue
			var centre:=u*(start.x+size.x*.5)+v*(start.y+size.y*.5)+n*float(face.plane)
			var distance:=centre.distance_to(observer)
			if distance>radius:continue
			var code:="w%d_h%d_x%d_y%d" % [roundi(size.x*4),roundi(size.y*4),roundi((start.x-x)*4),roundi((start.y-y)*4)]
			out.append({"x":x,"y":y,"distance":distance,"trim_key":code,"size":size,"offset":start-Vector2(x,y),"transform":Transform3D(Basis(u,v,n),u*start.x+v*start.y+n*(float(face.plane)+.0375))})
	return out
