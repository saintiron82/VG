extends SceneTree
const Visual=preload("res://runtime/CharacterVisual.gd")
const CACHE="res://revisions/original_lily_r01/generated/residents_r03/resident_01_female_blouse_skirt"
const OUTPUT="res://revisions/original_lily_r01/evidence/resident_01_hem_diagnostic_r03.json"
func _initialize() -> void:call_deferred("run")
func xyz(p:Vector3)->Array:return [p.x,p.y,p.z]
func run()->void:
	if FileAccess.file_exists(OUTPUT):quit(2);return
	root.size=Vector2i(1600,1000)
	var stage:=Node3D.new();root.add_child(stage)
	var visual:=Visual.new();stage.add_child(visual)
	var problem:String=visual.load_character(CACHE)
	if not problem.is_empty():push_error(problem);quit(2);return
	visual.set_locomotion(1.65);visual.seek_motion(0.0);visual.seek_blink(0.0)
	var nodes:Dictionary=visual.parts()
	var camera:=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=2.25;camera.near=.02;camera.current=true
	stage.add_child(camera);camera.position=Vector3(5,1.3,.2);camera.look_at(Vector3(0,.85,0))
	await process_frame
	var render:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(CACHE+"/lily.render.json"))
	var pivots:={}
	for part in render.rigid_parts:pivots[part.selector.part]=Visual.CommonRender.vector(part.pivot_world)
	var result:Dictionary={"cache":CACHE,"master_hash":render.master_hash,"phase_seconds":0.0,"image":"evidence/visual_r04/resident_01_contact_side.png","method":"Exact camera rays against runtime-transformed render triangles, followed by conversion to both skirt parts' source space.","pixels":[]}
	for pixel in [Vector2(932,710),Vector2(930,723),Vector2(927,705),Vector2(939,716),Vector2(925,727),Vector2(931,698),Vector2(935,735)]:
		var origin:=camera.project_ray_origin(pixel);var direction:=camera.project_ray_normal(pixel)
		var hits:Array=[]
		for part in render.rigid_parts:
			var id:String=part.selector.part
			for group in part.groups:
				for quad in group.quads:
					var q:Array=[]
					for v in quad:q.append(nodes[id].global_transform*(Visual.CommonRender.vector(v)-pivots[id]))
					for triangle in [[0,2,1],[0,3,2]]:
						var hit:Variant=Geometry3D.ray_intersects_triangle(origin,direction,q[triangle[0]],q[triangle[1]],q[triangle[2]])
						if hit==null:continue
						var source:Vector3=nodes[id].global_transform.affine_inverse()*hit+pivots[id]
						var skirts:={}
						for skirt in ["skirt_left","skirt_right"]:
							var point:Vector3=nodes[skirt].global_transform.affine_inverse()*hit+pivots[skirt]
							skirts[skirt]=xyz(point)
						hits.append({"distance":origin.distance_to(hit),"part":id,"material":group.material,"world_m":xyz(hit),"own_source_m":xyz(source),"skirt_source_m":skirts})
			hits.sort_custom(func(a:Dictionary,b:Dictionary)->bool:return a.distance<b.distance)
		result.pixels.append({"pixel":[pixel.x,pixel.y],"hits":hits.slice(0,8)})
	var file:=FileAccess.open(OUTPUT,FileAccess.WRITE);file.store_string(JSON.stringify(result,"  ")+"\n");file.close()
	print(JSON.stringify(result))
	stage.queue_free();await process_frame;quit(0)
