extends Node3D
## Gameplay integration, not the placement review camera. Source city is streamed.
const World = preload("res://CityWorld.gd")
const Lily = preload("res://character/runtime/LilyController.gd")
var world: Node3D
var player: CharacterBody3D
var args: Dictionary = {}
var hud: Label
var state := "loading"
var session: Dictionary = {"schema":"riverstone.playable.session.v1","input_mode":"physical_gui_keys","events":[],"samples":[],"captures":[],"wall_frame_ms":[],"scope":"Source-coordinate r04 city tiles + unchanged Lily r5 controller; NPC behavior paused"}
var start_usec := 0
var ready_usec := 0
var previous_usec := 0
var last_sample_usec := 0
var last_report_usec := 0
var last_record_usec := 0
var recording := false
var pending_capture := false
var frame_number := 0
var pause_streaming := false
var interest_radius_cells := 2
var portable_runtime := false

func _ready() -> void:
	process_physics_priority = -100
	start_usec=Time.get_ticks_usec()
	portable_runtime=bool(ProjectSettings.get_setting("application/riverstone/portable_runtime",false))
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair:=arg.substr(2).split("=",true,1);args[pair[0]]=pair[1] if pair.size()>1 else "true"
	interest_radius_cells=clampi(int(args.get("radius-cells",2)),1,3)
	var layer:=CanvasLayer.new();add_child(layer)
	var panel:=ColorRect.new();panel.position=Vector2(18,18);panel.size=Vector2(640,72);panel.color=Color(.025,.035,.04,.84);layer.add_child(panel)
	hud=Label.new();hud.position=Vector2(32,27);hud.add_theme_font_size_override("font_size",18);layer.add_child(hud)
	hud.text="RIVERSTONE\nLoading the city…"
	var env_node:=WorldEnvironment.new();var env:=Environment.new();env_node.environment=env;add_child(env_node)
	env.background_mode=Environment.BG_COLOR;env.background_color=Color("a0b4bd")
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("d3dce5");env.ambient_light_energy=.38
	var sun:=DirectionalLight3D.new();sun.rotation_degrees=Vector3(-48,-35,0);sun.light_color=Color("fff1d9");sun.light_energy=1.05
	sun.shadow_enabled=not args.has("no-shadows");sun.directional_shadow_mode=DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS;sun.directional_shadow_max_distance=85;sun.shadow_bias=.12;sun.shadow_normal_bias=.85;add_child(sun)
	world=World.new();world.name="SourceCity";add_child(world)
	var default_root: String="res://runtime_data" if portable_runtime else ProjectSettings.globalize_path("res://../../..")
	var default_index: String="res://runtime_data/world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json" if portable_runtime else "res://generated/tile_r01/index.json"
	var repo: String=str(args.get("repo-root",default_root)).trim_suffix("/")
	var problem: String=world.configure(str(args.get("index",default_index)),repo,not args.has("no-render"))
	if not problem.is_empty():_stop(problem);return
	var spawn:=Vector3(98.41505784216918,4,48.75638652919374)
	if args.has("spawn"):
		var parsed:Variant=JSON.parse_string(args.spawn)
		if not World.RD.vector_ok(parsed):_stop("Invalid authored spawn");return
		spawn=World.RD.vector(parsed)
	if not world.ensure_region(spawn,interest_radius_cells):_stop(world.error);return
	await get_tree().physics_frame
	await get_tree().physics_frame
	var ray:=PhysicsRayQueryParameters3D.create(spawn+Vector3(0,.45,0),spawn-Vector3(0,2,0),1)
	var hit:=get_world_3d().direct_space_state.intersect_ray(ray)
	if hit.is_empty() or hit.normal.y < .60 or absf(hit.position.y-spawn.y)>.35:
		_stop("Authored spawn has no matching upward source support; refusing underside/fallback floor")
		return
	player=Lily.new();player.camera_enabled=not args.has("no-render");player.set_physics_process(false)
	# Appearance is interchangeable; the shared controller/capsule and city stay exact.
	if portable_runtime:
		player.cache_dir=str(ProjectSettings.get_setting("application/riverstone/character_cache",""))
	if args.has("character-cache"):
		player.cache_dir=str(args["character-cache"])
	add_child(player)
	if not player.initialized:_stop(player.load_error);return
	player.global_position=Vector3(spawn.x,hit.position.y+.04,spawn.z)
	player.camera_yaw=float(args.get("camera-yaw",PI));player._update_camera()
	if player.camera:player.camera.far=interest_radius_cells*64.0-8.0
	player.set_physics_process(true)
	state="playing";ready_usec=Time.get_ticks_usec()
	session.spawn={"authored":World.RD.vector_ok([spawn.x,spawn.y,spawn.z]),"position_m":[spawn.x,spawn.y,spawn.z],"support_y":hit.position.y,"support_id":str(hit.collider.get_meta("source_id","unknown")),"initialization_only":true}
	session.renderer=RenderingServer.get_video_adapter_name();session.load_wall_ms=(ready_usec-start_usec)/1000.0
	session.character_source_binding=JSON.parse_string(FileAccess.get_file_as_string("res://character/source_binding.json"))
	session.appearance={"cache_dir":player.cache_dir,"is_default_r5":player.cache_dir.is_empty(),"rig_master_hash":player.visual.rig.get("master_hash","")}
	get_window().title="Riverstone · Lily · WASD / RMB camera"
	hud.text="RIVERSTONE  ·  Market district\nWASD move  Shift run  RMB / arrows look  F8 photo"
	print("PLAYABLE_CITY_READY "+JSON.stringify({"spawn":session.spawn,"load_ms":session.load_wall_ms,"world":world.debug_state()}))
	write_report()

func _stop(message: String) -> void:
	state="safe_stop";pause_streaming=true
	if player:player.set_physics_process(false);player.velocity=Vector3.ZERO
	if hud:hud.text="RIVERSTONE  ·  Safely paused\n"+message.substr(0,87)
	session.error=message;write_report();push_error(message)
	if DisplayServer.get_name()=="headless":get_tree().quit(3)

func _physics_process(delta: float) -> void:
	if state!="playing" or not player:return
	if not world.ensure_region(player.global_position,interest_radius_cells):_stop(world.error)
	# Keyboard camera alternative, also useful with accessibility input devices.
	# Character movement/physics remain the unchanged shared controller.
	var yaw_input:=float(Input.is_key_pressed(KEY_LEFT))-float(Input.is_key_pressed(KEY_RIGHT))
	var pitch_input:=float(Input.is_key_pressed(KEY_UP))-float(Input.is_key_pressed(KEY_DOWN))
	if yaw_input!=0 or pitch_input!=0:
		player.camera_yaw+=yaw_input*delta*.8
		player.camera_pitch=clampf(player.camera_pitch+pitch_input*delta*.5,-.65,.25)
		player._update_camera()

func _input(event: InputEvent) -> void:
	if state!="playing":return
	if event is InputEventKey and not event.echo:
		session.events.append({"kind":"physical_key","wall_ms":(Time.get_ticks_usec()-ready_usec)/1000.0,"tick":player.simulation_tick,"physical_keycode":event.physical_keycode,"keycode":event.keycode,"pressed":event.pressed})
		if event.pressed and event.physical_keycode==KEY_F8:_capture("manual")
		if event.pressed and event.physical_keycode==KEY_F10:write_report();get_tree().quit()
	if event is InputEventMouseButton:
		session.events.append({"kind":"mouse_button","wall_ms":(Time.get_ticks_usec()-ready_usec)/1000.0,"button":event.button_index,"pressed":event.pressed})
	if event is InputEventMouseMotion and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED:
		session.events.append({"kind":"mouse_relative","wall_ms":(Time.get_ticks_usec()-ready_usec)/1000.0,"relative":[event.relative.x,event.relative.y]})

func _process(_delta: float) -> void:
	if state!="playing":return
	var now:=Time.get_ticks_usec()
	if previous_usec>0:session.wall_frame_ms.append((now-previous_usec)/1000.0)
	if portable_runtime:
		# Bounded diagnostic history for long play sessions; recording builds retain full evidence.
		while session.samples.size()>1200:session.samples.pop_front()
		while session.events.size()>2000:session.events.pop_front()
		while session.wall_frame_ms.size()>600:session.wall_frame_ms.pop_front()
	previous_usec=now
	if now-last_sample_usec>=100000:
		var sample:Dictionary=player.debug_state()
		var visual:Dictionary=sample.get("visual",{})
		sample.visual={"motion":visual.get("motion"),"expression":visual.get("expression"),"ready":visual.get("ready")}
		sample.wall_ms=(now-ready_usec)/1000.0;sample.active_cell=world.debug_state().active_cell;sample.camera_yaw=player.camera_yaw;sample.camera_pitch=player.camera_pitch
		session.samples.append(sample);last_sample_usec=now
	if now-last_report_usec>=2000000:write_report();last_report_usec=now
	if args.has("record-dir") and now-last_record_usec>=200000 and not pending_capture and DisplayServer.get_name()!="headless":
		last_record_usec=now;_capture("video")
	if args.has("smoke") and player.simulation_tick>=60:write_report();get_tree().quit()
	if args.has("duration") and now-ready_usec>=float(args.duration)*1000000:write_report();get_tree().quit()

func _capture(kind: String) -> void:
	if pending_capture or DisplayServer.get_name()=="headless":return
	pending_capture=true
	await RenderingServer.frame_post_draw
	var folder:String=str(args.get("record-dir",args.get("evidence-dir",ProjectSettings.globalize_path("user://photos" if portable_runtime else "res://evidence/gui_r01"))))
	DirAccess.make_dir_recursive_absolute(folder)
	var path:=folder.path_join("%s_%06d.png"%[kind,frame_number])
	var status:=get_viewport().get_texture().get_image().save_png(path)
	session.captures.append({"kind":kind,"path":path,"error":status,"wall_ms":(Time.get_ticks_usec()-ready_usec)/1000.0,"tick":player.simulation_tick,"feet_position_m":[player.position.x,player.position.y,player.position.z]})
	frame_number+=1;pending_capture=false
	if kind=="manual":write_report()

func write_report() -> void:
	session.state=state
	if world:session.world=world.debug_state()
	if player:session.final_player=player.debug_state()
	session.elapsed_wall_ms=(Time.get_ticks_usec()-start_usec)/1000.0
	session.performance_scope="Actual cloud llvmpipe monotonic frame intervals; includes synchronous streaming and screenshot cost; not local GPU benchmark"
	var path:String=str(args.get("report",ProjectSettings.globalize_path("user://last_session.json" if portable_runtime else "res://evidence/session.json")))
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var temporary:=path+".writing"
	var f:=FileAccess.open(temporary,FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(session,"  ")+"\n")
		f.close()
		DirAccess.rename_absolute(temporary,path)

func _notification(what: int) -> void:
	if what==NOTIFICATION_WM_CLOSE_REQUEST:write_report()
