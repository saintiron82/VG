extends SceneTree
## Deterministic GUI-only visual capture. Never used as a headless visual pass.
const Visual = preload("res://runtime/CharacterVisual.gd")
var actor: Node3D
var output := ""
var view := "three_quarter"
var pose := "idle"
var phase := 0.0
var expression := "neutral"
var cache_dir := ""
var blink_phase := 0.0
var inspect_only := false

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="): output=arg.trim_prefix("--output=")
		if arg.begins_with("--view="): view=arg.trim_prefix("--view=")
		if arg.begins_with("--pose="): pose=arg.trim_prefix("--pose=")
		if arg.begins_with("--phase="): phase=float(arg.trim_prefix("--phase="))
		if arg.begins_with("--expression="): expression=arg.trim_prefix("--expression=")
		if arg.begins_with("--cache="): cache_dir=arg.trim_prefix("--cache=")
		if arg.begins_with("--blink="): blink_phase=float(arg.trim_prefix("--blink="))
		if arg=="--inspect-only":inspect_only=true
	call_deferred("run")

func run() -> void:
	root.size=Vector2i(1100,1100)
	var scene:=Node3D.new();root.add_child(scene)
	var world:=WorldEnvironment.new();var env:=Environment.new()
	env.background_mode=Environment.BG_COLOR;env.background_color=Color("29373e")
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("d2e4eb");env.ambient_light_energy=.62
	world.environment=env;scene.add_child(world)
	var light:=DirectionalLight3D.new();light.rotation_degrees=Vector3(-38,-25,0);light.light_energy=1.5;light.shadow_enabled=true;scene.add_child(light)
	var fill:=DirectionalLight3D.new();fill.rotation_degrees=Vector3(-15,150,0);fill.light_energy=.55;scene.add_child(fill)
	var floor:=MeshInstance3D.new();var mesh:=BoxMesh.new();mesh.size=Vector3(6,.08,6);floor.mesh=mesh;floor.position.y=-.045
	var material:=StandardMaterial3D.new();material.albedo_color=Color("667573");material.roughness=1;floor.material_override=material;scene.add_child(floor)
	actor=Visual.new();scene.add_child(actor)
	var problem:String=actor.load_character(cache_dir)
	if not problem.is_empty():push_error(problem);quit(1);return
	actor.set_locomotion(1.65 if pose=="walk" else 0.0);actor.seek_motion(phase);actor.seek_blink(blink_phase);actor.set_expression(expression)
	var camera:=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=2.15;camera.near=.02;scene.add_child(camera)
	var target:=Vector3(0,.88,0)
	match view:
		"front":camera.position=Vector3(0,.95,5)
		"back":camera.position=Vector3(2.2,1.5,-5)
		"side":camera.position=Vector3(5,1.1,0)
		"face":camera.position=Vector3(0,1.62,4);target=Vector3(0,1.60,.05);camera.size=.56
		_:camera.position=Vector3(3.1,2.0,5)
	camera.look_at(target);camera.current=true
	if inspect_only:
		print(JSON.stringify({"loaded":true,"view":view,"source":actor.rig.source_id,"parts":actor.parts().size(),"visual_review":false}));scene.queue_free();await process_frame;quit(0);return
	if output.is_empty():return
	if DisplayServer.get_name()=="headless":push_error("Screenshots require a real render display; no headless visual pass");quit(1);return
	if FileAccess.file_exists(output):push_error("Capture path already exists");quit(1);return
	for _frame in range(12):await process_frame
	await RenderingServer.frame_post_draw
	var image:=root.get_texture().get_image()
	var status:=image.save_png(output)
	print(JSON.stringify({"view":view,"pose":pose,"phase":phase,"expression":expression,"output":output,"status":status,"visual_review":"capture only; human review still needed"}))
	quit(0 if status==OK else 1)
