extends SceneTree
## One GUI process: Lily views + six shared-source appearance variants.
const Visual = preload("res://runtime/CharacterVisual.gd")
const OUTPUT := "res://evidence/visual_r01"
var stage: Node3D
var actors: Array = []
var camera: Camera3D
var title: Label
var subtitle: Label
var footer: Label
var light: DirectionalLight3D
var report := {"schema":"riverstone.people.visual_capture.v1","captures":[],"renderer":"actual Godot geometry, no image billboards","visual_acceptance":"pending inspection"}
var inspect_only := false

func _initialize() -> void:
	inspect_only = "--inspect-only" in OS.get_cmdline_user_args()
	call_deferred("run")

func label_at(parent: Node, pos: Vector2, size: int) -> Label:
	var label:=Label.new();label.position=pos;label.add_theme_font_size_override("font_size",size)
	label.add_theme_color_override("font_color",Color("ecede5"));label.add_theme_color_override("font_shadow_color",Color("19282f"));label.add_theme_constant_override("shadow_offset_y",2)
	parent.add_child(label);return label

func base_scene() -> void:
	root.size=Vector2i(1600,1000)
	stage=Node3D.new();root.add_child(stage)
	var world:=WorldEnvironment.new();var env:=Environment.new()
	env.background_mode=Environment.BG_COLOR;env.background_color=Color("29373e")
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("d2e4eb");env.ambient_light_energy=.64
	world.environment=env;stage.add_child(world)
	light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-38,-25,0);light.light_energy=1.45;light.shadow_enabled=true;stage.add_child(light)
	var fill:=DirectionalLight3D.new();fill.rotation_degrees=Vector3(-15,150,0);fill.light_energy=.55;stage.add_child(fill)
	var floor:=MeshInstance3D.new();var mesh:=BoxMesh.new();mesh.size=Vector3(16,.08,12);floor.mesh=mesh;floor.position.y=-.045
	var material:=StandardMaterial3D.new();material.albedo_color=Color("667573");material.roughness=1;floor.material_override=material;stage.add_child(floor)
	camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=2.25;camera.near=.02;camera.current=true;stage.add_child(camera)
	var canvas:=CanvasLayer.new();stage.add_child(canvas)
	title=label_at(canvas,Vector2(40,28),30);subtitle=label_at(canvas,Vector2(42,72),18);footer=label_at(canvas,Vector2(42,950),17)

func add_actor(cache: String, pos:=Vector3.ZERO) -> Node3D:
	var actor:=Visual.new();stage.add_child(actor);actor.position=pos
	var problem:String=actor.load_character(cache)
	if not problem.is_empty():push_error(problem);quit(1);return null
	actors.append(actor);return actor

func clear_actors() -> void:
	for actor in actors:actor.queue_free()
	actors.clear()
	await process_frame

func configure_camera(view: String) -> void:
	camera.size=2.25;var target:=Vector3(0,.87,0)
	match view:
		"front":camera.position=Vector3(0,.95,5)
		"back":camera.position=Vector3(2.4,1.6,-5)
		"face":camera.position=Vector3(0,1.62,4);target=Vector3(0,1.60,.05);camera.size=.62
		_:camera.position=Vector3(3.0,1.9,5)
	camera.look_at(target)

func capture(name: String, metadata: Dictionary) -> void:
	for _frame in range(10):await process_frame
	await RenderingServer.frame_post_draw
	var path:=OUTPUT.path_join(name+".png")
	if FileAccess.file_exists(path):push_error("Refusing to overwrite capture "+path);quit(1);return
	var image:=root.get_texture().get_image();var status:=image.save_png(path)
	if status!=OK:push_error("Capture failed: "+str(status));quit(1);return
	report.captures.append({"file":name+".png","pixels":[image.get_width(),image.get_height()],"metadata":metadata})
	var file:=FileAccess.open(OUTPUT.path_join("capture_manifest.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");file.close()
	print("CAPTURE_READY "+ProjectSettings.globalize_path(path))

func run() -> void:
	if not inspect_only:
		if DisplayServer.get_name()=="headless":push_error("Visual batch requires actual GUI rendering");quit(1);return
		if DirAccess.dir_exists_absolute(OUTPUT):push_error("Refusing existing capture directory "+OUTPUT);quit(1);return
		DirAccess.make_dir_recursive_absolute(OUTPUT)
	base_scene()
	var actor:=add_actor("")
	if actor==null:return
	if inspect_only:
		await clear_actors()
		for i in range(6):add_actor("res://generated/people_review_r1/review_%02d"%i,Vector3(float(i)-2.5,0,0))
		print(JSON.stringify({"batch_parse":true,"variant_actors":actors.size(),"visual_review":false}));stage.queue_free();await process_frame;quit(0);return
	var cuts: Array = [
		{"id":"01_lily_front","view":"front","pose":"idle","phase":0.0,"expression":"neutral","blink":0.0},
		{"id":"02_lily_three_quarter","view":"three_quarter","pose":"idle","phase":0.0,"expression":"neutral","blink":0.0},
		{"id":"03_lily_back","view":"back","pose":"idle","phase":0.0,"expression":"neutral","blink":0.0},
		{"id":"04_lily_face_happy","view":"face","pose":"idle","phase":0.0,"expression":"happy","blink":0.0},
		{"id":"05_lily_face_blink","view":"face","pose":"idle","phase":0.0,"expression":"neutral","blink":3.90},
		{"id":"06_lily_walk_contact","view":"three_quarter","pose":"walk","phase":0.0,"expression":"neutral","blink":0.0},
		{"id":"07_lily_walk_swing","view":"three_quarter","pose":"walk","phase":0.2,"expression":"neutral","blink":0.0}]
	for cut in cuts:
		configure_camera(cut.view);actor.set_locomotion(1.65 if cut.pose=="walk" else 0.0);actor.seek_motion(cut.phase);actor.seek_blink(cut.blink);actor.set_expression(cut.expression)
		title.text="LILY  /  "+str(cut.view).replace("_"," ").to_upper()
		subtitle.text="Silver hair · teal eyes · medieval city traveller"
		footer.text="28 rigid voxel parts · 0.02 m sampling · actual 3D geometry  |  %s / %.2f s / %s"%[cut.pose,cut.phase,cut.expression]
		await capture(cut.id,cut)
	await clear_actors()
	var names: Array=[]
	for i in range(6):
		var cache: String="res://generated/people_review_r1/review_%02d"%i
		actor=add_actor(cache,Vector3((float(i)-2.5)*1.0,0,0));actor.seek_motion(0.0)
		var source: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(cache.path_join("derived.master.json")))
		var p: Dictionary=source.extensions.appearance.preset
		names.append({"id":p.id,"body":p.body_frame,"hair":p.hair_style,"outfit":p.outfit,"palette":p.palette})
	camera.size=3.80;camera.position=Vector3(0,1.65,10);camera.look_at(Vector3(0,.86,0))
	title.text="SHARED PEOPLE APPEARANCE  /  SIX PRESETS"
	subtitle.text="One source family · shared body parts, pivots, sockets and motion"
	footer.text="Body frame · face shape · hairstyle · garment · palette · accessories  |  Appearance data only; no NPC simulation"
	for i in range(6):
		var position_2d:=camera.unproject_position(Vector3((float(i)-2.5),-.10,0))
		var label:=label_at(title.get_parent(),position_2d-Vector2(65,0),15)
		label.text="%02d  %s\n%s\n%s"%[i,names[i].body,names[i].hair,names[i].outfit.replace("_"," ")]
	await capture("08_resident_six_presets",{"presets":names,"coordinates":"same metres, source-dependent shared body scale"})
	report["capture_complete"]=true
	var file:=FileAccess.open(OUTPUT.path_join("capture_manifest.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");file.close()
	stage.queue_free();await process_frame;quit(0)
