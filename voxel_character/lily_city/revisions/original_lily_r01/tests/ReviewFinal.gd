extends SceneTree
## One GUI process: Lily views + six shared-source appearance variants.
const Visual = preload("res://runtime/CharacterVisual.gd")
const OUTPUT := "res://revisions/original_lily_r01/evidence/visual_r03"
var stage: Node3D
var actors: Array = []
var camera: Camera3D
var title: Label
var subtitle: Label
var footer: Label
var light: DirectionalLight3D
var report := {"schema":"riverstone.people.visual_capture.v1","captures":[],"renderer":"actual Godot geometry, no image billboards","visual_acceptance":"pending inspection","candidate_change":{"scope":"shared-source original-identity revision3 with connected cowlick, image-right temple ornament, flowing rear hair, real closed eyelids","character_cache":"revisions/original_lily_r01/generated/lily_r03","master_hash":"source binding recorded in each cache manifest","ambient_energy":0.22,"sun_energy":0.65,"fill_energy":0.16,"source":"tests/ReviewBatch.gd visual_r01"}}
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
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("d2e4eb");env.ambient_light_energy=.22
	world.environment=env;stage.add_child(world)
	light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-38,-25,0);light.light_energy=.65;light.shadow_enabled=true;stage.add_child(light)
	var fill:=DirectionalLight3D.new();fill.rotation_degrees=Vector3(-15,150,0);fill.light_energy=.16;stage.add_child(fill)
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
		"face":camera.position=Vector3(0,1.66,4);target=Vector3(0,1.635,.05);camera.size=.49
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
	var actor:=add_actor("res://revisions/original_lily_r01/generated/lily_r03")
	if actor==null:return
	if inspect_only:
		print(JSON.stringify({"loaded":actor.debug_state(),"master_hash":actor.asset.get_meta("master_hash")}));stage.queue_free();await process_frame;quit(0);return
	var cuts: Array = [
		{"id":"01_lily_front","view":"front","pose":"idle","phase":0.0,"expression":"neutral","blink":0.0},
		{"id":"02_lily_three_quarter","view":"three_quarter","pose":"idle","phase":0.0,"expression":"neutral","blink":0.0},
		{"id":"03_lily_back","view":"back","pose":"idle","phase":0.0,"expression":"neutral","blink":0.0},
		{"id":"04_lily_face_happy","view":"face","pose":"idle","phase":0.0,"expression":"happy","blink":0.0},
		{"id":"05_lily_face_blink","view":"face","pose":"idle","phase":0.0,"expression":"neutral","blink":3.90},
		{"id":"06_lily_walk_contact","view":"three_quarter","pose":"walk","phase":0.0,"expression":"neutral","blink":0.0},
		{"id":"07_lily_walk_swing","view":"three_quarter","pose":"walk","phase":0.2,"expression":"neutral","blink":0.0}]
	for cut in cuts:
		if false: continue
		configure_camera(cut.view);actor.set_locomotion(1.65 if cut.pose=="walk" else 0.0);actor.seek_motion(cut.phase);actor.seek_blink(cut.blink);actor.set_expression(cut.expression)
		title.text="LILY  /  "+str(cut.view).replace("_"," ").to_upper()
		subtitle.text="Current-app Lily identity · preserved r5 medieval costume · new rear interpretation"
		footer.text="44 separate rigid parts · 0.0125 m sampling · actual 3D geometry  |  %s / %.2f s / %s"%[cut.pose,cut.phase,cut.expression]
		await capture(cut.id,cut)
	await clear_actors()
	var index: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://revisions/original_lily_r01/data/resident_review_index.json"))
	for i in range(index.presets.size()):
		var record: Dictionary=index.presets[i]
		actor=add_actor("res://revisions/original_lily_r01/"+str(record.cache))
		configure_camera("three_quarter")
		actor.seek_motion(0.0);actor.seek_blink(0.0)
		title.text="MODULAR RESIDENT  /  "+str(record.outfit).replace("_"," ").to_upper()
		subtitle.text="Separate body / face / hair / clothing modules · original-world metres"
		footer.text="%s · %s · same rig and public animation API · no NPC behavior"%[record.body,record.outfit]
		await capture("resident_%02d_front"%i,record)
		if i in [0,1,5,7,8]:
			actor.set_locomotion(1.65);actor.seek_motion(0.2)
			await capture("resident_%02d_walk"%i,{"preset":record.preset,"phase":0.2,"pose":"walk","scope":"cloth silhouette and joint review"})
		if i in [0,1,5,8]:
			actor.set_locomotion(1.65);actor.seek_motion(0.0)
			await capture("resident_%02d_contact"%i,{"preset":record.preset,"phase":0.0,"pose":"walk_contact"})
			camera.position=Vector3(5,1.3,.2);camera.look_at(Vector3(0,.85,0))
			await capture("resident_%02d_contact_side"%i,{"preset":record.preset,"phase":0.0,"view":"side","pose":"walk_contact"})
		await clear_actors()
	for group in range(2):
		var start:=group*5
		var subset: Array=[]
		for j in range(5):
			var record: Dictionary=index.presets[start+j]
			actor=add_actor("res://revisions/original_lily_r01/"+str(record.cache),Vector3((float(j)-2)*.85,0,0))
			actor.seek_motion(0.0);actor.seek_blink(0.0);subset.append(record)
		camera.size=3.2;camera.position=Vector3(0,1.6,10);camera.look_at(Vector3(0,.85,0))
		title.text="MODULAR CLOTHING  /  GROUP "+str(group+1)
		subtitle.text="Actual distinct garment geometry · shared skeleton · age-specific frame fitting"
		footer.text="Same world metres · child frame is nonuniformly retargeted · palette is a separate layer"
		await capture("residents_group_%02d"%group,{"presets":subset,"same_units":true})
		await clear_actors()
	report["capture_complete"]=true
	var file:=FileAccess.open(OUTPUT.path_join("capture_manifest.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");file.close()
	stage.queue_free();await process_frame;quit(0)
