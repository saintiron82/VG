extends Node3D
const RD=preload("res://RenderData.gd")
const BRIDGE=preload("res://BridgeMechanism.gd")
const SURFACE_ADDENDUM=preload("res://FiniteSurfaceAddendum.gd")
## A placement-review scene. Common voxel geometry is handled by the existing
## shared RenderData converter; these explicitly labelled proxies are not a new engine.
var args:Dictionary={}
var data:Dictionary={}
var camera:Camera3D
var capture_viewport:Viewport
var hud:Label
var materials:Dictionary={}
var ready_to_view:=false
var frames:=0
var capture_views:Array[String]=[]
var capture_index:=0
var pending:=false
var mouse_look:=false
var start_ms:=Time.get_ticks_msec()
var bridge_mechanism:Node3D
var bridge_fixture:Node3D
var video_pending:=false
var video_last_ms:=0
var video_frame_index:=0
var report:Dictionary={"status":"loading","renderer_stage":"actual Godot spatial blockout","limits":["Mixed common assemblies and review terrain; unfinished exterior","No character/nav/hydraulic simulation verified"]}
func v(a:Array)->Vector3:return Vector3(float(a[0]),float(a[1]),float(a[2]))
func vec(a:Vector3)->Array:return [a.x,a.y,a.z]
func _ready()->void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair:=arg.substr(2).split("=",true,1);args[pair[0]]=pair[1] if pair.size()>1 else "true"
	if args.has("canvas-width"):
		get_window().content_scale_size=Vector2i(int(args["canvas-width"]),int(args.get("canvas-height",1024)))
		get_window().content_scale_mode=Window.CONTENT_SCALE_MODE_VIEWPORT
		get_window().content_scale_aspect=Window.CONTENT_SCALE_ASPECT_KEEP
	var manifest:String=str(args.get("manifest",ProjectSettings.globalize_path("res://../generated/blockout.scene.json")))
	var source=JSON.parse_string(FileAccess.get_file_as_string(manifest))
	if not source is Dictionary:push_error("Missing source scene");get_tree().quit(1);return
	data=source;report.scene_path=manifest;report.scene_sha256=FileAccess.get_sha256(manifest)
	if args.has("terrain-addendum"):
		var addendum_path:String=str(args["terrain-addendum"])
		var addendum_sha:String=FileAccess.get_sha256(addendum_path)
		if not args.has("terrain-addendum-sha256") or addendum_sha!=str(args["terrain-addendum-sha256"]):push_error("Surface addendum identity mismatch");get_tree().quit(5);return
		var patch=JSON.parse_string(FileAccess.get_file_as_string(addendum_path))
		if not patch is Dictionary:push_error("Invalid surface addendum");get_tree().quit(5);return
		var applied:Dictionary=SURFACE_ADDENDUM.apply_to_scene(data,patch,report.scene_sha256)
		if applied.status!="pass":push_error("Rejected surface addendum: "+str(applied));get_tree().quit(5);return
		applied["path"]=addendum_path;applied["sha256"]=addendum_sha;report["surface_addendum"]=applied
	var world:=WorldEnvironment.new();var env:=Environment.new();world.environment=env
	env.background_mode=Environment.BG_COLOR;env.background_color=Color("73858a")
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("bdc5c3");env.ambient_light_energy=.45
	add_child(world)
	var sun:=DirectionalLight3D.new();sun.rotation_degrees=Vector3(-48,-35,0);sun.light_energy=.8;sun.shadow_enabled=false;add_child(sun)
	for key in data.materials:
		var m:=StandardMaterial3D.new();m.albedo_color=Color(str(data.materials[key]));m.roughness=1;m.metallic_specular=0;materials[key]=m
		if key=="bank":m.cull_mode=BaseMaterial3D.CULL_DISABLED
	camera=Camera3D.new();camera.far=3500;add_child(camera);capture_viewport=get_viewport()
	if args.has("canvas-width"):
		var fixed:=SubViewport.new();fixed.size=Vector2i(int(args["canvas-width"]),int(args.get("canvas-height",1024)));fixed.world_3d=get_viewport().world_3d;fixed.render_target_update_mode=SubViewport.UPDATE_ALWAYS;add_child(fixed)
		remove_child(camera);fixed.add_child(camera);camera.current=true;capture_viewport=fixed
		var display_layer:=CanvasLayer.new();display_layer.layer=0;add_child(display_layer)
		var display:=TextureRect.new();display.texture=fixed.get_texture();display.size=get_viewport().get_visible_rect().size;display.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;display.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED;display_layer.add_child(display)
	if args.has("capture-views"):
		for name in str(args["capture-views"]).split(","):capture_views.append(name)
	set_camera(capture_views[0] if not capture_views.is_empty() else str(args.get("view","overview")))
	var layer:=CanvasLayer.new();layer.layer=100;add_child(layer);layer.visible=not args.has("hide-hud")
	var panel:=ColorRect.new();panel.position=Vector2(14,14);panel.size=Vector2(1080,84);panel.color=Color(.025,.035,.035,.90);layer.add_child(panel)
	hud=Label.new();hud.position=Vector2(28,21);hud.size=Vector2(1050,74);hud.add_theme_font_size_override("font_size",16);layer.add_child(hud)
	hud.text="Loading whole-city spatial plan…"
	call_deferred("load_city")
func set_camera(name:String)->void:
	var c:Dictionary=data.inspection_cameras.get(name,data.inspection_cameras.values()[0])
	camera.position=v(c.position_m);camera.projection=Camera3D.PROJECTION_ORTHOGONAL if c.has("ortho_size_m") else Camera3D.PROJECTION_PERSPECTIVE
	if c.has("ortho_size_m"):camera.size=float(c.ortho_size_m)
	camera.fov=62;camera.near=2 if camera.position.y>40 else .12;camera.look_at(v(c.target_m));report.camera={"view":name,"position_m":vec(camera.position)}
	if bridge_mechanism and bridge_fixture==null and c.has("bridge_state"):bridge_mechanism.set_named_state(str(c.bridge_state))
func load_city()->void:
	var tri_count:=0
	for key in data.surfaces:
		var raw:Array=data.surfaces[key];var vertices:=PackedVector3Array();var normals:=PackedVector3Array()
		for i in range(0,raw.size(),3):
			var a:=v(raw[i]);var b:=v(raw[i+1]);var c:=v(raw[i+2]);var n:Vector3=(b-a).cross(c-a).normalized()
			vertices.append_array(PackedVector3Array([a,c,b]));normals.append_array(PackedVector3Array([n,n,n])) # Godot clockwise front faces; retain authored upward normal.
		var ar:Array=[];ar.resize(Mesh.ARRAY_MAX);ar[Mesh.ARRAY_VERTEX]=vertices;ar[Mesh.ARRAY_NORMAL]=normals
		var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,ar);mesh.surface_set_material(0,materials[key])
		var node:=MeshInstance3D.new();node.mesh=mesh;node.name="Surface_"+key;add_child(node);tri_count+=raw.size()/3
		await get_tree().process_frame
	var batches:Dictionary={}
	for b in data.boxes:
		if not batches.has(b.material):batches[b.material]=[]
		batches[b.material].append(b)
	for key in batches:
		var mesh:=BoxMesh.new();mesh.size=Vector3.ONE;mesh.material=materials[key]
		var mm:=MultiMesh.new();mm.transform_format=MultiMesh.TRANSFORM_3D;mm.mesh=mesh;mm.instance_count=batches[key].size()
		for i in batches[key].size():
			var b:Dictionary=batches[key][i];var basis:=Basis(Vector3.UP,float(b.get("yaw_rad",0))).scaled_local(v(b.size_m));mm.set_instance_transform(i,Transform3D(basis,v(b.position_m)))
		var node:=MultiMeshInstance3D.new();node.multimesh=mm;node.name="Massing_"+key;add_child(node)
	if data.has("common_instances"):await load_common()
	if data.has("bridge_mechanism"):
		bridge_mechanism=BRIDGE.new();add_child(bridge_mechanism)
		var repo:String=str(args.get("repo-root",ProjectSettings.globalize_path("res://../../.."))).trim_suffix("/")
		if not bridge_mechanism.configure(data.bridge_mechanism,data.common_assets,repo,common_mesh):report.status="bridge_asset_failed";write_report();get_tree().quit(3);return
		set_camera(str(report.camera.view));bridge_mechanism.cycle_enabled=args.has("bridge-cycle")
		if args.has("bridge-operation-fixture"):
			if args.has("bridge-cycle"):push_error("Choose only one bridge mode");get_tree().quit(4);return
			# Source-bound helper is attached separately; absent fixture bytes fail closed.
			var script=load("res://generated/bridge_operation_r02/integration/BridgeFixtureView.gd")
			if script==null:push_error("Missing sealed operational fixture");get_tree().quit(4);return
			bridge_fixture=script.new();add_child(bridge_fixture)
			report.bridge_operation_scope="Closed-world registered actor fixture; city-wide NPC/navigation absent"
			bridge_fixture.fixture_event.connect(_on_fixture_event)
			var options={"contract_path":"res://generated/bridge_operation_r02/runtime_fixture/revisions/r02/contract.json","floor_samples_path":"res://generated/bridge_operation_r02/integration/floor_samples.json","geometry_pack_path":repo+"/world_city/concept_city_v3/assemblies/waterworks/registered_bridge/drawbridge_candidate/resolved_placements.json","demonstration":args.has("operation-demo"),"show_status_label":not args.has("hide-hud")}
			if not bridge_fixture.configure(bridge_mechanism,repo,options):push_error("Operational fixture configuration failed");get_tree().quit(4);return
			capture_views.clear()
	report.status="runtime_loaded";report.counts=data.counts;report.surface_triangles=tri_count;report.box_proxies=data.boxes.size();report.load_ms=Time.get_ticks_msec()-start_ms;report.renderer=RenderingServer.get_video_adapter_name()
	hud.text="CONCEPT CITY V3 · WHOLE-CITY SPATIAL BLOCKOUT · %d building masses\nNoble estates / clergy / merchant courts / poorer housing / crafts / working port\nTerrain, streets and water heads are authored planning data · common voxel replacement follows"%int(data.counts.building_masses)
	if data.has("common_instances"):
		hud.text="CONCEPT CITY V3 · COMMON ASSEMBLY EXTERIOR CANDIDATE\n%d shared common components placed (buildings, trees, facilities) · terrain/remaining masses still staged\nSocial parcels, roads, courts and water network preserved · actual visual and passage review ongoing"%data.common_instances.size()
	ready_to_view=true;write_report()
func write_report()->void:
	if bridge_mechanism:report.bridge_mechanism=bridge_mechanism.audit
	if bridge_fixture:
		report.bridge_operation_scope="Closed-world fixture; live city registration incomplete"
		report.bridge_fixture_record=bridge_fixture.current_record
		report.bridge_fixture_transitions=bridge_fixture.recorded_states
	if args.has("report"):
		var f:=FileAccess.open(str(args.report),FileAccess.WRITE)
		if f:f.store_string(JSON.stringify(report,"  ")+"\n")
func _process(delta:float)->void:
	if not ready_to_view:return
	frames+=1
	if args.has("video-dir") and bridge_fixture and not video_pending and Time.get_ticks_msec()-video_last_ms>=200 and DisplayServer.get_name()!="headless":
		_record_video_frame()
	if args.has("headless-check") and frames==3:get_tree().quit(0)
	if not capture_views.is_empty() and frames>=10 and not pending and DisplayServer.get_name()!="headless":
		pending=true;await RenderingServer.frame_post_draw
		var name:String=capture_views[capture_index];var path:String=str(args["capture-dir"])+"/"+name+".png";var err:int=capture_viewport.get_texture().get_image().save_png(path)
		if not report.has("captures"):report.captures=[]
		report.captures.append({"view":name,"path":path,"error":err,"width":capture_viewport.size.x,"height":capture_viewport.size.y});write_report()
		if err!=OK:get_tree().quit(2);return
		capture_index+=1
		if capture_index==capture_views.size():get_tree().quit(0);return
		set_camera(capture_views[capture_index]);frames=0;pending=false
	if mouse_look:
		var direction:=Vector3.ZERO
		if Input.is_physical_key_pressed(KEY_W):direction-=camera.global_basis.z
		if Input.is_physical_key_pressed(KEY_S):direction+=camera.global_basis.z
		if Input.is_physical_key_pressed(KEY_A):direction-=camera.global_basis.x
		if Input.is_physical_key_pressed(KEY_D):direction+=camera.global_basis.x
		if Input.is_physical_key_pressed(KEY_E):direction+=Vector3.UP
		if Input.is_physical_key_pressed(KEY_Q):direction-=Vector3.UP
		camera.position+=direction.normalized()*16*delta*(4 if Input.is_physical_key_pressed(KEY_SHIFT) else 1)
func _unhandled_input(event:InputEvent)->void:
	if event is InputEventKey and event.pressed and event.keycode==KEY_ESCAPE:
		mouse_look=not mouse_look;Input.mouse_mode=Input.MOUSE_MODE_CAPTURED if mouse_look else Input.MOUSE_MODE_VISIBLE
	if event is InputEventMouseMotion and mouse_look:
		camera.rotate_y(-event.relative.x*.002);camera.rotate_object_local(Vector3.RIGHT,-event.relative.y*.002)

func common_mesh(render:Dictionary,override:Dictionary)->ArrayMesh:
	var overlay:Dictionary=render.duplicate(false);overlay.materials=render.materials.duplicate(true)
	for key in override:
		if overlay.materials.has(key):overlay.materials[key]=override[key]
	var root:=RD.build(overlay);var vertices:=PackedVector3Array();var normals:=PackedVector3Array();var colors:=PackedColorArray()
	for child in root.get_children():
		if not child is MeshInstance3D:continue
		var ar:Array=child.mesh.surface_get_arrays(0);vertices.append_array(ar[Mesh.ARRAY_VERTEX]);normals.append_array(ar[Mesh.ARRAY_NORMAL])
		var color:Color=child.mesh.surface_get_material(0).albedo_color
		for i in ar[Mesh.ARRAY_VERTEX].size():colors.append(color)
	root.free()
	var arrays:Array=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_COLOR]=colors
	var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var material:=StandardMaterial3D.new();material.vertex_color_use_as_albedo=true;material.roughness=1;material.metallic_specular=0;mesh.surface_set_material(0,material);return mesh
func load_common()->void:
	var repo:String=str(args.get("repo-root",ProjectSettings.globalize_path("res://../../.."))).trim_suffix("/")
	var groups:Dictionary={};var render_cache:Dictionary={};var palette_mesh_cache:Dictionary={}
	var spatial_chunks:Dictionary={}
	for p in data.common_instances:
		var chunk:String="%d_%d"%[floori(float(p.position_m[0])/64.0),floori(float(p.position_m[2])/64.0)]
		spatial_chunks[chunk]=true
		var key:String=str(p.asset_key)+"/"+str(p.palette_id)+"/"+chunk
		if not groups.has(key):groups[key]=[]
		groups[key].append(p)
	var quads:=0;var n:=0
	for key in groups:
		var p:Dictionary=groups[key][0];var asset:Dictionary=data.common_assets[p.asset_key]
		if not render_cache.has(p.asset_key):
			var read:Dictionary=RD.read(repo+"/"+str(asset.render_path))
			if read.has("error") or read.get("sha256","")!=asset.render_sha256:
				push_error("Common asset source validation failed: "+str(p.asset_key));report.status="asset_failed";write_report();get_tree().quit(3);return
			render_cache[p.asset_key]=read.data;quads+=int(read.data.quad_count)
		var palette_key:String=str(p.asset_key)+"/"+str(p.palette_id)
		if not palette_mesh_cache.has(palette_key):palette_mesh_cache[palette_key]=common_mesh(render_cache[p.asset_key],p.get("palette_override",{}))
		var mesh:ArrayMesh=palette_mesh_cache[palette_key]
		var mm:=MultiMesh.new();mm.transform_format=MultiMesh.TRANSFORM_3D;mm.mesh=mesh;mm.instance_count=groups[key].size()
		for i in groups[key].size():
			var pp:Dictionary=groups[key][i];mm.set_instance_transform(i,Transform3D(Basis(Vector3.UP,float(pp.get("yaw_rad",0))),v(pp.position_m)))
		var node:=MultiMeshInstance3D.new();node.multimesh=mm;add_child(node);n+=1
		if n%8==0:await get_tree().process_frame
	report.common_assets=render_cache.size();report.common_instances=data.common_instances.size();report.common_unique_quads=quads;report.common_palette_meshes=palette_mesh_cache.size();report.common_draw_batches=groups.size();report.common_spatial_chunks=spatial_chunks.size();report.common_chunk_pitch_m=64

func _on_fixture_event(event_name:String,record:Dictionary)->void:
	if event_name not in ["occupied_wait","vessel_enter","vessel_to_tail_hold","full_rig_tail_wait","road_restored"]:return
	if not report.has("operation_events"):report.operation_events=[]
	var item={"event":event_name,"record":record.duplicate(true)}
	if DisplayServer.get_name()!="headless" and args.has("capture-dir"):
		await RenderingServer.frame_post_draw
		var path:String=str(args["capture-dir"])+"/operation_"+event_name+".png"
		item.image_path=path;item.image_error=capture_viewport.get_texture().get_image().save_png(path)
	report.operation_events.append(item);write_report()
	if event_name=="road_restored" and args.has("operation-demo"):get_tree().quit(0)

func _record_video_frame()->void:
	video_pending=true
	await RenderingServer.frame_post_draw
	var at_ms:=Time.get_ticks_msec()
	var path:String=str(args["video-dir"])+("/frame_%05d.png"%video_frame_index)
	var err:int=capture_viewport.get_texture().get_image().save_png(path)
	if not report.has("video_frames"):report.video_frames=[]
	report.video_frames.append({"path":path,"time_ms":at_ms,"state":bridge_fixture.current_record.get("state",""),"demo_stage":bridge_fixture.demo_stage,"error":err})
	video_frame_index+=1;video_last_ms=at_ms;video_pending=false
