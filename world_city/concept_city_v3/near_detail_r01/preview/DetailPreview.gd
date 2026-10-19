extends Node3D
## Standalone, source-bound material-quality sample; not a substitute city map.
const RD = preload("res://RenderData.gd")
const Player = preload("res://character/runtime/LilyController.gd")
const PALETTE = {"slate":"a16b51","slate_dark":"80523f","slate_light":"ac775c","slate_worn":"b18a6c"}
var before: Node3D
var after: Node3D
var lane: Node3D
var stairs: Node3D
var max_entry_height := 0.0
var lane_before: MeshInstance3D
var player: CharacterBody3D
var camera: Camera3D
var label: Label
var mode := "after"
var view_name := "overview"
var options: Dictionary = {}
var metrics: Dictionary = {}
var frame_ms: Array = []
var events: Array = []
var ticks := 0
var rendered_frames := 0
var ready_ms := 0
var next_auto := 0
var settled := false
var capture_done := false
var actual_input_distance := 0.0
var settled_ground_losses := 0

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	for arg in args:
		if arg.begins_with("--") and arg.contains("="):
			var pair := arg.substr(2).split("=",true,1)
			options[pair[0]]=pair[1]
	get_tree().auto_accept_quit=false
	var env := WorldEnvironment.new()
	env.environment=Environment.new()
	env.environment.background_mode=Environment.BG_COLOR
	env.environment.background_color=Color("a8b3bd")
	env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color=Color("d7e0e8")
	env.environment.ambient_light_energy=.30
	env.environment.tonemap_mode=Environment.TONE_MAPPER_LINEAR
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees=Vector3(-40,-38,0)
	sun.light_color=Color("fff0dc")
	sun.light_energy=.68
	sun.shadow_enabled=str(options.get("shadows","on"))!="off"
	sun.directional_shadow_max_distance=65
	sun.directional_shadow_mode=DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.shadow_bias=.15
	sun.shadow_normal_bias=1.5
	add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees=Vector3(-25,145,0)
	fill.light_energy=.10
	fill.light_color=Color("cbd8e5")
	add_child(fill)
	var start := Time.get_ticks_usec()
	before=load_voxel("res://assets/house_before.render.json","before")
	after=load_voxel("res://assets/house_after.render.json","after")
	lane=load_voxel("res://assets/lane_surface.render.json","lane")
	if before==null or after==null or lane==null:return
	metrics.load_build_ms=(Time.get_ticks_usec()-start)/1000.0
	# Collision never toggles with visual LOD. Reuse the original house mesh.
	for node in before.get_children():
		if node is MeshInstance3D: node.create_trimesh_collision()
	add_ground()
	add_entry_access()
	add_roof_shadow_proxy()
	player=Player.new()
	player.cache_dir="res://character/generated/original"
	player.position=Vector3(0,.02,10.5)
	player.player_input_enabled=false
	player.camera_enabled=true
	add_child(player)
	if not player.initialized: fail(player.load_error);return
	player.visible=false
	camera=Camera3D.new()
	camera.fov=45
	camera.near=.05
	add_child(camera)
	build_ui()
	set_view(str(options.get("view","overview")))
	set_mode(str(options.get("mode","after")))
	ready_ms=Time.get_ticks_msec()
	if options.has("headless-check"):
		player.player_input_enabled=false
		player.set_control(Vector3.RIGHT,1.65)
	print("NEAR_DETAIL_READY "+JSON.stringify(metrics))

func load_voxel(path: String,key: String) -> Node3D:
	var result: Dictionary=RD.read(path)
	if result.has("error"):fail(result.error);return null
	var data: Dictionary=result.data
	if key!="lane":
		for mat in PALETTE:data.materials[mat]=PALETTE[mat]
	var node: Node3D=RD.build(data)
	if key=="after":
		for i in range(data.groups.size()):
			if str(data.groups[i].material).begins_with("slate"):
				node.get_child(i).cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if key=="lane":
		for child in node.get_children():
			if child is GeometryInstance3D:child.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(node)
	metrics[key]={"sha256":result.sha256,"stats":RD.stats(data),"bounds":data.bounds}
	return node

func add_ground() -> void:
	lane_before=MeshInstance3D.new()
	var paving := BoxMesh.new()
	paving.size=Vector3(10,.04,5)
	lane_before.mesh=paving
	lane_before.position=Vector3(0,-.02,9.5)
	var paving_material := StandardMaterial3D.new()
	paving_material.albedo_color=Color("a09c8a")
	paving_material.roughness=1
	lane_before.material_override=paving_material
	lane_before.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(lane_before)
	var ground := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size=Vector3(30,.3,36)
	ground.mesh=box
	ground.position.y=-.15
	var material := StandardMaterial3D.new()
	material.albedo_color=Color("8f9286")
	material.roughness=1
	ground.material_override=material
	ground.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# The underlay is lower than joints. Separate flat physical proxy has top0.
	ground.position.y=-.19
	add_child(ground)
	var body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size=Vector3(30,.3,36)
	shape.shape=bs
	shape.position.y=-.15
	body.add_child(shape)
	add_child(body)
	# Closed sample boundary, not an unannounced infinite walking plane.
	for side in [-1,1]:
		for axis in [0,2]:
			var border := StaticBody3D.new()
			var collision := CollisionShape3D.new()
			var block := BoxShape3D.new()
			block.size=Vector3(.3,2.5,36) if axis==0 else Vector3(30,2.5,.3)
			collision.shape=block
			collision.position=Vector3(side*14.85,1.25,0) if axis==0 else Vector3(0,1.25,side*17.85)
			border.add_child(collision)
			add_child(border)

func add_roof_shadow_proxy() -> void:
	var data: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/roof_shadow_proxy.json"))
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for ex in data.extrusions:
		var p: Array=ex.polygon
		var faces: Array=[]
		faces.append([Vector3(p[3][0],p[3][1],ex.z_min),Vector3(p[2][0],p[2][1],ex.z_min),Vector3(p[1][0],p[1][1],ex.z_min),Vector3(p[0][0],p[0][1],ex.z_min)])
		faces.append([Vector3(p[0][0],p[0][1],ex.z_max),Vector3(p[1][0],p[1][1],ex.z_max),Vector3(p[2][0],p[2][1],ex.z_max),Vector3(p[3][0],p[3][1],ex.z_max)])
		for i in range(4):
			var j := (i+1)%4
			faces.append([Vector3(p[i][0],p[i][1],ex.z_min),Vector3(p[j][0],p[j][1],ex.z_min),Vector3(p[j][0],p[j][1],ex.z_max),Vector3(p[i][0],p[i][1],ex.z_max)])
		for f in faces:
			for idx in [0,2,1,0,3,2]:st.add_vertex(f[idx])
	st.generate_normals()
	var proxy := MeshInstance3D.new()
	proxy.mesh=st.commit()
	proxy.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
	after.add_child(proxy)
	metrics.roof_shadow={"visible_geometry_unchanged":true,"smooth_underlay_triangles":24,"fine_tile_casting":false,"fine_tile_receiving":true}

func add_entry_access() -> void:
	stairs=load_voxel("res://assets/entry_steps.render.json","entry_steps")
	var body := StaticBody3D.new()
	var collision := CollisionShape3D.new()
	var ramp := ConvexPolygonShape3D.new()
	ramp.points=PackedVector3Array([Vector3(-1.05,0,7.9),Vector3(1.05,0,7.9),Vector3(-1.05,0,7),Vector3(1.05,0,7),Vector3(-1.05,.5,7),Vector3(1.05,.5,7)])
	collision.shape=ramp
	body.add_child(collision)
	add_child(body)
	var door_body := StaticBody3D.new()
	var door_collision := CollisionShape3D.new()
	var door_shape := BoxShape3D.new()
	door_shape.size=Vector3(1.35,2.15,.52)
	door_collision.shape=door_shape
	door_collision.position=Vector3(0,.5+2.15/2.0,5.7-.52/2.0)
	door_body.add_child(door_collision)
	add_child(door_body)
	metrics.entry={"closed_door_exact_plane_z":5.7,"old_coarse_door_plane_z":5.5,"rise":.125,"tread":.3,"width":2.1,"threshold":.5,"ramp_grade_degrees":29.0546,"door_closed":true,"shared_in_both_visual_modes":true}

func build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := ColorRect.new()
	panel.color=Color(.04,.065,.08,.90)
	panel.position=Vector2(16,16)
	panel.size=Vector2(1248,96)
	layer.add_child(panel)
	label=Label.new()
	label.position=Vector2(30,26)
	label.add_theme_font_size_override("font_size",17)
	layer.add_child(label)

func set_mode(value: String) -> void:
	mode=value
	var fine := value!="before"
	before.visible=not fine
	after.visible=fine
	lane.visible=fine
	lane_before.visible=not fine
	events.append({"event":"mode","mode":mode,"ms":Time.get_ticks_msec()})
	frame_ms.clear()

func set_view(value: String) -> void:
	view_name=value
	player.player_input_enabled=value=="play"
	player.visible=value=="play"
	if value=="play":
		player.camera_yaw=0
		player.camera_pitch=-.15
		player._update_camera()
		player.camera.current=true
		return
	camera.current=true
	var at := Vector3(0,4.2,0)
	match value:
		"street":camera.position=Vector3(6.3,2.0,11.9);at=Vector3(.0,2.0,5.8)
		"roof":camera.position=Vector3(6,10.2,7.5);at=Vector3(.5,8.1,3.0)
		"stone":camera.position=Vector3(3.3,1.20,8.6);at=Vector3(1.4,.45,6.1)
		_:camera.position=Vector3(13,11.3,19)
	camera.look_at(at,Vector3.UP)
	events.append({"event":"camera","view":value,"position":[camera.position.x,camera.position.y,camera.position.z],"target":[at.x,at.y,at.z]})

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		events.append({"event":"gui_key","key":OS.get_keycode_string(event.physical_keycode),"ms":Time.get_ticks_msec(),"player":player.debug_state()})
		match event.physical_keycode:
			KEY_F1:set_mode("before")
			KEY_F2:set_mode("after")
			KEY_F3:set_mode("auto")
			KEY_1:set_view("overview")
			KEY_2:set_view("street")
			KEY_3:set_view("roof")
			KEY_4:set_view("stone")
			KEY_5:set_view("play")
			KEY_F12:save_capture("user://detail_capture.png")
			KEY_Q:finish()

func _process(delta: float) -> void:
	if after==null or player==null:return
	rendered_frames+=1
	if rendered_frames>10:frame_ms.append(delta*1000)
	if frame_ms.size()>600:frame_ms.pop_front()
	if mode=="auto":
		var previous_fine := after.visible
		var distance: float=(player.global_position if view_name=="play" else camera.global_position).distance_to(Vector3(0,4,0))
		if after.visible and distance>24:after.visible=false;before.visible=true;lane.visible=false;lane_before.visible=true
		elif not after.visible and distance<20:after.visible=true;before.visible=false;lane.visible=true;lane_before.visible=false
		if previous_fine!=after.visible:events.append({"event":"distance_lod","fine":after.visible,"distance":distance,"ms":Time.get_ticks_msec()})
	label.text="B_REG_0120  |  "+mode.to_upper()+"  |  "+view_name+"  |  %.1f FPS (this machine only)"%Engine.get_frames_per_second()+"\nF1 Current city  /  F2 Detail candidate  /  F3 Distance LOD  |  1 Whole  2 Street  3 Roof  4 Stone  5 Walk\nWASD + Shift, right mouse camera  |  Q Exit  |  One-house geometry study, not a rebuilt whole city"
	if options.has("capture") and rendered_frames==30 and not capture_done:
		capture_done=true
		save_capture(str(options.capture))
		finish()

func _physics_process(_delta: float) -> void:
	if player==null:return
	ticks+=1
	if options.has("headless-check"):
		if ticks>30 and not player.is_on_floor():settled_ground_losses+=1
		max_entry_height=maxf(max_entry_height,player.position.y)
		if ticks==90:player.set_control(Vector3.LEFT,1.65)
		if ticks==180:
			metrics.controller_positive={"state":player.debug_state(),"case":"unchanged controller walks right then left on flat sample collision"}
			player.set_control(Vector3.FORWARD,1.65)
		if ticks==230:set_mode("before")
		if ticks==290:set_mode("after")
		if ticks==420:
			metrics.entry_ascent=player.debug_state()
			player.set_control(Vector3.BACK,1.65)
		if ticks==510:
			metrics.entry_descent=player.debug_state()
			player.set_control(Vector3.FORWARD,1.65)
		if ticks==660:
			metrics.controller_negative={"state":player.debug_state(),"case":"unchanged closed door blocks after climbing added steps; no interior claim"}
			metrics.settled_ground_loss_frames=settled_ground_losses
			metrics.max_entry_height=max_entry_height
			metrics.controller_pass=settled_ground_losses==0 and player.blocked_frames>30 and max_entry_height>.49 and player.position.z>=5.92 and player.position.z<6.05
			finish()

func save_capture(path: String) -> void:
	if DisplayServer.get_name()=="headless":return
	var image := get_viewport().get_texture().get_image()
	image.save_png(path)
	metrics.capture=path

func fail(message: String) -> void:
	push_error(message)
	get_tree().quit(2)

func finish() -> void:
	metrics.mode=mode
	metrics.view=view_name
	metrics.camera_transform=str(camera.global_transform) if camera!=null else ""
	metrics.events=events
	metrics.render_frames=rendered_frames
	metrics.frame_ms=frame_ms
	metrics.renderer=RenderingServer.get_video_adapter_name()
	metrics.preview_script_sha256=FileAccess.get_sha256("res://DetailPreview.gd")
	metrics.lighting={"shadow_option":str(options.get("shadows","on")),"sun_energy":.68,"ambient_energy":.30,"fill_energy":.10,"shadow_bias":.15,"normal_bias":1.5,"ground_shadow_casting":false,"ground_shadow_receiving":true,"light_and_camera_identical_across_AB":true}
	metrics.player=player.debug_state() if player!=null else {}
	metrics.scope="A source-bound single-house quality sample in local coordinates; retained city placement in source_binding.json. Coarse reference mesh collision stays fixed across visual LOD. Added sample stairs reach the closed doorway; no interior or whole-city entrance validation."
	var file:=FileAccess.open(str(options.get("report","user://detail_session.json")),FileAccess.WRITE)
	if file!=null:file.store_string(JSON.stringify(metrics,"\t"))
	get_tree().quit()

func _notification(what: int) -> void:
	if what==NOTIFICATION_WM_CLOSE_REQUEST:finish()
