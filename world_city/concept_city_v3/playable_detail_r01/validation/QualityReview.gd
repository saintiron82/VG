extends Node3D
const Plain=preload("res://CityWorld.gd")
const Detailed=preload("res://CityWorldRoadDetail.gd")
const NativeAccess=preload("res://CityWorldAccessDetail.gd")
var args: Dictionary={}
func _ready() -> void:
	for token in OS.get_cmdline_user_args():
		if token.begins_with("--"):
			var pair:=token.substr(2).split("=",true,1);args[pair[0]]=pair[1] if pair.size()>1 else true
	get_viewport().msaa_3d=Viewport.MSAA_4X if int(args.get("msaa",0))==4 else Viewport.MSAA_DISABLED
	var mode:=str(args.get("mode","after"));var output:=str(args.get("output",ProjectSettings.globalize_path("res://../near_detail_r01/city_upgrade/evidence/review_r01")))
	DirAccess.make_dir_recursive_absolute(output)
	var env:=Environment.new();env.background_mode=Environment.BG_COLOR;env.background_color=Color("a7bcc5");env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("d5dce0");env.ambient_light_energy=.38;env.tonemap_mode=Environment.TONE_MAPPER_LINEAR
	var we:=WorldEnvironment.new();we.environment=env;add_child(we)
	var sun:=DirectionalLight3D.new();sun.rotation_degrees=Vector3(-48,-35,0);sun.light_color=Color("fff1d9");sun.light_energy=.78;sun.shadow_enabled=true;sun.directional_shadow_mode=DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS;sun.directional_shadow_max_distance=85;sun.shadow_bias=.12;sun.shadow_normal_bias=1.5;add_child(sun)
	var world: Node3D=Plain.new() if mode=="before" else (NativeAccess.new() if args.has("native-access") else Detailed.new());add_child(world)
	var catalog_path:=str(args.get("detail-catalog","res://near_catalog.json"))
	if mode!="before":world.detail_catalog_path=catalog_path
	var problem: String=world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),true)
	if not problem.is_empty():push_error(problem);get_tree().quit(2);return
	var position:=Vector3(62.150496917718314,2.884433624773715,109.5418129106266);var yaw:=2.6937581289867887
	if args.has("position"):position=Plain.RD.vector(JSON.parse_string(args.position))
	if args.has("yaw"):yaw=float(args.yaw)
	var pose:=Transform3D(Basis(Vector3.UP,yaw),position)
	var eye:=Vector3(11,7,20);var target:=Vector3(0,4,0)
	if str(args.get("view","oblique"))=="street":eye=Vector3(2,1.7,12);target=Vector3(0,3.5,1)
	if args.has("eye"):eye=Plain.RD.vector(JSON.parse_string(args.eye))
	if args.has("target"):target=Plain.RD.vector(JSON.parse_string(args.target))
	var observer: Vector3=pose*Vector3(0,1.7,9)
	if args.has("observer"):observer=pose*Plain.RD.vector(JSON.parse_string(args.observer))
	if not world.ensure_region(observer,2):push_error(world.error);get_tree().quit(3);return
	if mode!="before":world.update_near_detail(observer,1)
	var camera:=Camera3D.new();camera.fov=52;camera.near=.08;camera.far=145;add_child(camera);camera.position=pose*eye;camera.look_at(pose*target);camera.current=true
	var canvas:=CanvasLayer.new();add_child(canvas)
	var label:=Label.new();label.position=Vector2(14,12);label.add_theme_font_size_override("font_size",18);label.text="RIVERSTONE  |  ACTUAL CITY  |  "+mode.to_upper()+"\nShared geometry near-detail candidate · ongoing whole-city upgrade";canvas.add_child(label)
	for i in range(5):
		if mode!="before" and args.has("required-asset"):world.update_near_detail(observer,.3)
		await get_tree().process_frame
	if mode!="before" and args.has("required-asset"):
		var present:=false
		for record in world.detail_records.values():
			if record.asset==str(args["required-asset"]):
				if str(args.get("required-state","fine"))=="coarse":present=record.fine==null and is_instance_valid(record.coarse.get_ref()) and record.coarse.get_ref().visible
				elif record.fine!=null and is_instance_valid(record.fine.get_ref()):present=true
		if not present:push_error("Required reviewed LOD state not active: "+str(args["required-asset"]));get_tree().quit(5);return
	await RenderingServer.frame_post_draw
	if mode!="before" and args.has("required-access"):
		var access_present:=false
		for record in world.access_records.values():
			if record.asset==str(args["required-access"]):access_present=true
		if not access_present or int(world.access_stats.active_modules)==0:push_error("Required native access detail not active");get_tree().quit(6);return
	var path:=output.path_join(str(args.get("view","oblique"))+"_"+mode+".png")
	var result:=get_viewport().get_texture().get_image().save_png(path)
	var report={"mode":mode,"required_state":str(args.get("required-state","fine")),"image":path,"image_status":result,"source_city_index":world.index_sha256,"near_catalog_path":catalog_path,"near_catalog_sha256":FileAccess.get_sha256(catalog_path),"camera":{"position":[camera.position.x,camera.position.y,camera.position.z],"target":[(pose*target).x,(pose*target).y,(pose*target).z],"fov":camera.fov},"observer":[observer.x,observer.y,observer.z],"world":world.debug_state(),"renderer":RenderingServer.get_video_adapter_name(),"msaa_samples":4 if get_viewport().msaa_3d==Viewport.MSAA_4X else 0,"scope":"Actual source-coordinate city and collision loaded. Fixed rendering review camera, not GUI movement or whole-city quality acceptance."}
	var file:=FileAccess.open(path.trim_suffix(".png")+".json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));get_tree().quit(0 if result==OK else 4)
