extends SceneTree
## Source illustrations are UI comparison images only. Actors are common exported 3D cell meshes.
const Adapter = preload("res://runtime/common/RenderData.gd")
var stage: Node3D
var viewport: SubViewport
var camera: Camera3D
var actor: Node3D
var reference: TextureRect
var title: Label
var footer: Label
var info: Label
var report := {"schema":"riverstone.reference_character.godot_review.v1","engine":Engine.get_version_info(),"captures":[],"renderer":"Actual Godot 3D meshes from unchanged common RenderData.gd; reference image is a separate 2D comparison panel only.","visual_acceptance":"pending image inspection; not final art approval"}
var output := "res://evidence/visual_r05_next"
var keep_open := false
var check_only := false
var export_glb := false

func _initialize() -> void:
	keep_open = "--keep-open" in OS.get_cmdline_user_args()
	check_only = "--check-only" in OS.get_cmdline_user_args()
	export_glb = "--export-glb" in OS.get_cmdline_user_args()
	call_deferred("run")

func label(parent: Node, position: Vector2, size: int, color: String) -> Label:
	var node := Label.new()
	node.position = position
	node.add_theme_font_size_override("font_size", size)
	node.add_theme_color_override("font_color",Color(color))
	parent.add_child(node)
	return node

func setup() -> void:
	root.size=Vector2i(1440,1000)
	var background := ColorRect.new();background.color=Color("eff0f4");background.size=Vector2(1440,1000);root.add_child(background)
	var reference_bg := ColorRect.new();reference_bg.color=Color.WHITE;reference_bg.position=Vector2(20,105);reference_bg.size=Vector2(535,810);root.add_child(reference_bg)
	reference=TextureRect.new();reference.position=Vector2(20,105);reference.size=Vector2(535,810);reference.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;reference.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED;root.add_child(reference)
	var container:=SubViewportContainer.new();container.position=Vector2(575,105);container.size=Vector2(845,810);root.add_child(container)
	viewport=SubViewport.new();viewport.size=Vector2i(845,810);viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;viewport.own_world_3d=true;container.add_child(viewport)
	stage=Node3D.new();viewport.add_child(stage)
	var world:=WorldEnvironment.new();var env:=Environment.new();env.background_mode=Environment.BG_COLOR;env.background_color=Color("e9ebf2");env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("e2e6f5");env.ambient_light_energy=.18;world.environment=env;stage.add_child(world)
	var sun:=DirectionalLight3D.new();sun.rotation_degrees=Vector3(-33,-32,0);sun.light_energy=.40;sun.shadow_enabled=true;stage.add_child(sun)
	var fill:=DirectionalLight3D.new();fill.rotation_degrees=Vector3(-18,140,0);fill.light_energy=.10;stage.add_child(fill)
	var floor:=MeshInstance3D.new();var box:=BoxMesh.new();box.size=Vector3(8,.04,8);floor.mesh=box;floor.position.y=-.035
	var mat:=StandardMaterial3D.new();mat.albedo_color=Color("d2d5df");mat.roughness=1;floor.material_override=mat;stage.add_child(floor)
	camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=2.30;camera.near=.02;camera.current=true;stage.add_child(camera)
	title=label(root,Vector2(25,18),27,"31384c")
	info=label(root,Vector2(27,58),17,"596273")
	var left:=label(root,Vector2(32,925),19,"41475a");left.text="SOURCE ILLUSTRATION"
	var right:=label(root,Vector2(585,925),19,"41475a");right.text="ACTUAL 3D VOXEL MESH"
	footer=label(root,Vector2(27,967),14,"60697b")

func load_actor(id: String, image_path: String) -> Dictionary:
	if is_instance_valid(actor):actor.queue_free();await process_frame
	var image:=Image.load_from_file(image_path)
	if image==null:push_error("Missing source image");quit(1);return {}
	reference.texture=ImageTexture.create_from_image(image)
	var result:Dictionary=Adapter.read("res://generated/"+id+"_r05/character.render.json")
	if result.has("error"):push_error(str(result.error));quit(1);return {}
	actor=Adapter.build(result.data);stage.add_child(actor)
	for binding in actor.get_meta("rigid_parts"):
		binding.node.name = str(binding.selector.part)
	var manifest:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://generated/"+id+"_r05/manifest.json"))
	var rig:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://generated/"+id+"_r05/rig.json"))
	var bone_root:=Node3D.new();bone_root.name="SemanticRigSockets";actor.add_child(bone_root)
	for socket_name in rig.sockets:
		var socket:Dictionary=rig.sockets[socket_name]
		var bone:Dictionary={}
		for part in rig.parts:
			if part.id==socket.part:bone=part;break
		if bone.is_empty():push_error("Missing socket part "+str(socket.part));quit(1);return {}
		var marker:=Marker3D.new();marker.name=socket_name;marker.position=Adapter.vector(bone.pivot_m)+Adapter.vector(socket.offset_m);bone_root.add_child(marker)
	if export_glb:
		DirAccess.make_dir_recursive_absolute("res://exports")
		var glb_path := "res://exports/"+id+"_r05.glb"
		if FileAccess.file_exists(glb_path):push_error("Refuse overwrite export");quit(1);return {}
		var document := GLTFDocument.new();var state := GLTFState.new()
		var status := document.append_from_scene(actor,state)
		if status != OK:push_error("GLB append failed");quit(1);return {}
		status=document.write_to_filesystem(state,glb_path)
		if status != OK:push_error("GLB write failed");quit(1);return {}
		print("GLB_EXPORT_READY "+ProjectSettings.globalize_path(glb_path))
	return {"id":id,"master_hash":result.data.master_hash,"render_sha256":result.sha256,"stats":Adapter.stats(result.data),"reference_sha256":manifest.reference_sha256,"bounds":result.data.bounds,"rig_parts":rig.parts.size(),"verified_socket_count":rig.sockets.size()}

func aim(view: String) -> void:
	camera.size=2.30;var target:=Vector3(0,1.03,-.02)
	match view:
		"front":camera.position=Vector3(0,1.03,5)
		"three_quarter":camera.position=Vector3(3.9,2.25,5.3)
		"back":camera.position=Vector3(-2.8,1.75,-5.3)
		"face":camera.size=.66;camera.position=Vector3(0,1.59,4);target=Vector3(0,1.59,0)
	camera.look_at(target)

func capture(name: String, data: Dictionary) -> void:
	for _i in range(8):await process_frame
	await RenderingServer.frame_post_draw
	var img:=root.get_texture().get_image();var path:=output.path_join(name+".png")
	if FileAccess.file_exists(path):push_error("Refuse overwrite "+path);quit(1);return
	var result:=img.save_png(path)
	if result!=OK:push_error("Capture write failed "+str(result));quit(1);return
	report.captures.append({"file":name+".png","pixels":[img.get_width(),img.get_height()],"data":data})
	var file:=FileAccess.open(output.path_join("capture_manifest.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("CAPTURE_READY "+ProjectSettings.globalize_path(path))

func run() -> void:
	setup()
	if not check_only:
		if DisplayServer.get_name()=="headless":push_error("Image review requires actual graphical rendering");quit(1);return
		if DirAccess.dir_exists_absolute(output):push_error("Immutable capture directory already exists");quit(1);return
		DirAccess.make_dir_recursive_absolute(output)
	var subjects:Array=[{"id":"violet_bride","image":"res://reference/1000041593.png","label":"VIOLET HALO / GOLD EYES"},{"id":"cyan_bride","image":"res://reference/1000041592.png","label":"CYAN HALO / SWEPT FRINGE"}]
	for subject in subjects:
		var data:Dictionary=await load_actor(subject.id,subject.image)
		if data.is_empty():return
		if check_only:print(JSON.stringify(data));continue
		for view in ["front","three_quarter","back","face"]:
			aim(view);title.text=subject.label+"  ·  "+view.replace("_"," ").to_upper()
			info.text="One common 3D master per character · data presets · 0.025 / 0.0125 m cells · 0.00625 m eye details"
			footer.text="%s occupied cells  |  %s quads  |  %s semantic parts  |  Rear and hidden surfaces are new interpretations."%[data.stats.cell_count,data.stats.quads,data.rig_parts]
			await capture(subject.id+"_"+view,{"view":view,"asset":data})
	print("REFERENCE_CHARACTER_REVIEW_PASS")
	if not keep_open:quit(0)
