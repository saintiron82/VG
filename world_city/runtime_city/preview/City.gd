extends Node3D
## Placement/render orchestration only. All opaque geometry comes from common voxel renders.
const RD = preload("res://RenderData.gd")
var args: Dictionary = {}
var repo: String
var data: Dictionary
var camera: Camera3D
var meshes: Dictionary = {}
var chunks: Dictionary = {}
var ready_to_view := false
var hud: Label
var report: Dictionary = {"status":"loading", "source":"actual Godot runtime", "errors":[], "loaded_assets":0, "building_instances":0, "geometry_quads_unique":0, "paletted_meshes":0,"source_material_isolation":true}
var shared_material: StandardMaterial3D
var started_ms := Time.get_ticks_msec()
var frame_after_ready := 0
var mouse_look := false
var move_speed := 14.0
var capture_views: Array[String] = []
var capture_index := 0
var capture_pending := false

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair := arg.substr(2).split("=",true,1)
			args[pair[0]]=pair[1] if pair.size()>1 else "true"
	repo=str(args.get("repo-root",ProjectSettings.globalize_path("res://../../.."))).trim_suffix("/")
	var manifest := str(args.get("manifest",repo+"/world_city/runtime_city/generated/r1/scene.json"))
	var parsed=JSON.parse_string(FileAccess.get_file_as_string(manifest))
	if not parsed is Dictionary: fail("Cannot parse manifest "+manifest);return
	data=parsed
	report.scene_manifest_path=manifest;report.scene_manifest_sha256=FileAccess.get_sha256(manifest)
	if not data.get("catalog_complete",false): fail("Incomplete compiled catalog is not a city delivery");return
	shared_material=StandardMaterial3D.new()
	shared_material.vertex_color_use_as_albedo=true
	shared_material.roughness=1.0
	shared_material.metallic_specular=0.0
	setup_environment()
	setup_camera(str(args.get("view","overview")))
	if args.has("capture-views"):
		for v in str(args["capture-views"]).split(","):capture_views.append(v)
		setup_camera(capture_views[0])
	setup_hud()
	call_deferred("load_city")

func fail(message: String) -> void:
	push_error(message)
	report.errors.append(message)
	report.status="failed"
	write_report()
	get_tree().quit(1)

func setup_environment() -> void:
	var world := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode=Environment.BG_COLOR
	environment.background_color=Color("7c9399")
	environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color=Color("c1d0d0")
	environment.ambient_light_energy=.55
	environment.tonemap_mode=Environment.TONE_MAPPER_LINEAR
	world.environment=environment;add_child(world)
	var sun:=DirectionalLight3D.new()
	sun.rotation_degrees=Vector3(-52,-28,0)
	sun.light_color=Color("fff0d8")
	sun.light_energy=.85
	sun.shadow_enabled=false # llvmpipe resource bound; no final-lighting claim.
	add_child(sun)

func setup_camera(view: String) -> void:
	if camera==null:
		camera=Camera3D.new();add_child(camera)
	camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.far=4200;camera.near=.12;camera.fov=62
	var target:=Vector3(0,12,-30)
	match view:
		"overview": camera.position=Vector3(1050,1060,1320);camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=1680
		"market": camera.position=Vector3(95,75,160);target=Vector3(-6,5,48)
		"plaza": camera.position=Vector3(-4,1.7,29);target=Vector3(-20,5,76)
		"alley": camera.position=Vector3(-2,1.7,69);target=Vector3(-22,3,83)
		"castle": camera.position=Vector3(-290,145,-170);target=Vector3(-440,15,-350)
		"cathedral": camera.position=Vector3(455,100,-200);target=Vector3(350,27,-330)
		"port": camera.position=Vector3(-110,105,640);target=Vector3(-210,10,370)
		"old_town": camera.position=Vector3(-330,70,25);target=Vector3(-260,6,-85)
		"gate": camera.position=Vector3(210,1.7,451);target=Vector3(209,4,414)
		"west_gate": camera.position=Vector3(-638.60895,1.7,16.055974);target=Vector3(-616,3.7,14.2)
	if view.begins_with("estate_"):
		var selected_class:String={"estate_stone":"older_stone_manor","estate_merchant":"merchant_palazzo","estate_timber":"timber_courtyard_house"}.get(view,"")
		for instance in data.instances:
			if str(instance.get("assembly_class",""))!=selected_class:continue
			var pos:Vector3=RD.vector(instance.position_m)
			var angle:float=float(instance.yaw_rad)
			var front:=Vector3(sin(angle),0,cos(angle));var right:=Vector3(cos(angle),0,-sin(angle))
			camera.position=pos+front*53+right*35+Vector3(0,35,0);target=pos+Vector3(0,5,0);break
	if view=="woodland":camera.position=Vector3(615,95,-410);target=Vector3(640,5,-560)
	if view=="craft":camera.position=Vector3(460,52,190);target=Vector3(390,5,145)
	# Match the near plane to an inspection distance; avoid co-planar surface depth
	# artifacts in distant precinct views without moving collision geometry.
	if camera.position.y>40:camera.near=2.0
	if view=="overview":camera.near=5.0
	camera.look_at(target)

func setup_hud() -> void:
	var layer:=CanvasLayer.new();add_child(layer)
	var panel:=ColorRect.new();panel.color=Color(0.025,.04,.045,.88);panel.position=Vector2(14,14);panel.size=Vector2(1030,93);layer.add_child(panel)
	hud=Label.new();hud.position=Vector2(27,21);hud.size=Vector2(1002,80);hud.add_theme_font_size_override("font_size",16);layer.add_child(hud)
	hud.text="Loading common voxel city assemblies…"

func chunk_node(id: String) -> Node3D:
	if not chunks.has(id):
		var node:=Node3D.new();node.name="Chunk_"+id.replace("-","n");add_child(node);chunks[id]=node
	return chunks[id]

func merged_mesh(render: Dictionary, overrides: Dictionary) -> ArrayMesh:
	# RenderData remains the sole quad-to-mesh converter; this stage batches its immutable surfaces.
	var original_materials:Dictionary=render.materials.duplicate(true)
	var original_quad_count:int=int(render.quad_count)
	var overlay:Dictionary=render.duplicate(false)
	overlay.materials=render.materials.duplicate(true)
	for key in overrides:
		if overlay.materials.has(key):overlay.materials[key]=overrides[key]
	var source:=RD.build(overlay)
	var vertices:=PackedVector3Array();var normals:=PackedVector3Array();var colors:=PackedColorArray()
	for child in source.get_children():
		if not child is MeshInstance3D:continue
		var ar:Array=child.mesh.surface_get_arrays(0)
		var count:int=ar[Mesh.ARRAY_VERTEX].size()
		vertices.append_array(ar[Mesh.ARRAY_VERTEX]);normals.append_array(ar[Mesh.ARRAY_NORMAL])
		var color:Color=child.mesh.surface_get_material(0).albedo_color
		for i in range(count):colors.append(color)
	source.free()
	if render.materials!=original_materials or int(render.quad_count)!=original_quad_count:
		report.source_material_isolation=false;fail("Palette override changed canonical render data")
	var arrays:Array=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_COLOR]=colors
	var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);mesh.surface_set_material(0,shared_material)
	return mesh

func load_city() -> void:
	var by_asset:Dictionary={}
	for instance in data.instances:
		var key:String=instance.asset_key
		if not by_asset.has(key):by_asset[key]=[]
		by_asset[key].append(instance)
	var use_fine:bool=str(args.get("view","overview"))!="overview" or args.has("capture-views")
	for key in by_asset:
		var asset:Dictionary=data.assets[key]
		var lod:String="fine" if use_fine and asset.has("fine") else "coarse"
		var read:Dictionary=RD.read(repo+"/"+str(asset[lod].render_path))
		if read.has("error"):fail(read.error);return
		if read.sha256!=asset[lod].render_sha256:fail("Asset hash differs "+key);return
		var render:Dictionary=read.data
		report.geometry_quads_unique+=int(render.quad_count)
		var palettes:Dictionary={}
		for instance in by_asset[key]:
			var palette_id:String=instance.palette_id
			if not palettes.has(palette_id):
				palettes[palette_id]=merged_mesh(render,instance.palette_override)
				report.paletted_meshes+=1
			var mesh_instance:=MeshInstance3D.new();mesh_instance.mesh=palettes[palette_id]
			mesh_instance.name=instance.id
			mesh_instance.position=RD.vector(instance.position_m);mesh_instance.rotation.y=float(instance.yaw_rad)
			chunk_node(str(instance.chunk_id)).add_child(mesh_instance)
			report.building_instances+=1
		report.loaded_assets+=1
		hud.text="Common voxel assemblies: %d / %d buildings\nOne continuous master per design · shared geometry cache · 64 m placement chunks\nReconstructed checkpoint · exterior milestone · source terrain grades still pending"%[report.building_instances,data.instances.size()]
		if int(report.loaded_assets)%8==0:await get_tree().process_frame
	await load_infrastructure()
	report.status="runtime_loaded";report.load_ms=Time.get_ticks_msec()-started_ms
	report.renderer=RenderingServer.get_video_adapter_name();report.chunks=chunks.size();report.scene_revision=data.revision
	report.scope=str(data.get("camera_scope","Whole-city exterior assemblies; no interiors or NPC simulation; source terrain grades unresolved"))
	report.camera={"position":vec(camera.position),"view":args.get("view","overview")}
	ready_to_view=true
	hud.text="CITY EXTERIOR · %d buildings / %d cached masters / %d chunks\n11 historical districts · actual common voxel assemblies · reconstructed source checkpoint\nWASD + mouse: free inspection · exterior milestone · terrain-grade and play tests pending"%[report.building_instances,report.loaded_assets,chunks.size()]
	if str(data.revision).begins_with("recovered_r2"):
		hud.text="PROPERTY + HISTORY REVISION · %d buildings / %d shared masters\nDistinct estates, attached rows, working courts, orchards and outside woodland\nRed clay · brown wood · gray slate · staged exterior review; terrain/player checks separate"%[report.building_instances,report.loaded_assets]
	write_report()

func load_infrastructure() -> void:
	if not data.has("infrastructure"):return
	var inf:Dictionary=data.infrastructure
	var infrastructure_loaded:=0
	for key in inf.assets:
		var asset:Dictionary=inf.assets[key]
		var read:Dictionary=RD.read(repo+"/"+str(asset.render_path))
		if read.has("error"):fail(read.error);return
		var mesh:=merged_mesh(read.data,{})
		var transforms:Array=[]
		for placement in inf.placements:
			if placement.asset_key==key:transforms.append(placement)
		var buckets:Dictionary={}
		for placement in transforms:
			var position:Vector3=RD.vector(placement.position_m)
			var chunk_id:String=str(floori(position.x/64))+"_"+str(floori(position.z/64))
			if not buckets.has(chunk_id):buckets[chunk_id]=[]
			buckets[chunk_id].append(placement)
		for cid in buckets:
			var mm:=MultiMesh.new();mm.transform_format=MultiMesh.TRANSFORM_3D;mm.mesh=mesh;mm.instance_count=buckets[cid].size()
			for i in buckets[cid].size():
				var p:Dictionary=buckets[cid][i]
				var basis:Basis=Basis(Vector3.UP,deg_to_rad(float(p.get("yaw_deg",0))))
				if p.has("transform") and p.transform.has("basis"):
					var rows:Array=p.transform.basis;basis=Basis(RD.vector(rows[0]),RD.vector(rows[1]),RD.vector(rows[2])).transposed()
				mm.set_instance_transform(i,Transform3D(basis,RD.vector(p.position_m)+Vector3(0,float(p.get("render_offset_y_m",0)),0)))
			var node:=MultiMeshInstance3D.new();node.multimesh=mm;chunk_node(cid).add_child(node)
		infrastructure_loaded+=1
		if infrastructure_loaded%32==0:await get_tree().process_frame
	report.infrastructure_instances=inf.placements.size()

func vec(v:Vector3)->Array:return [v.x,v.y,v.z]
func write_report()->void:
	if args.has("report"):
		var file:=FileAccess.open(str(args.report),FileAccess.WRITE)
		if file:file.store_string(JSON.stringify(report,"  ")+"\n")

func _process(delta:float)->void:
	if not ready_to_view:return
	frame_after_ready+=1
	if not capture_views.is_empty() and frame_after_ready>=12 and not capture_pending and DisplayServer.get_name()!="headless":
		capture_pending=true
		await RenderingServer.frame_post_draw
		var view:String=capture_views[capture_index]
		var path:String=str(args.get("capture-dir",repo+"/world_city/runtime_city/evidence"))+"/"+view+".png"
		var result:int=get_viewport().get_texture().get_image().save_png(path)
		if not report.has("captures"):report.captures=[]
		report.captures.append({"view":view,"path":path,"error":result,"position":vec(camera.position),"width":get_viewport().size.x,"height":get_viewport().size.y})
		write_report()
		if result!=OK:fail("Capture write failed "+path);return
		capture_index+=1
		if capture_index==capture_views.size():get_tree().quit(0);return
		setup_camera(capture_views[capture_index]);frame_after_ready=0;capture_pending=false
	if args.has("capture") and frame_after_ready==12 and DisplayServer.get_name()!="headless":
		await RenderingServer.frame_post_draw
		var err:=get_viewport().get_texture().get_image().save_png(str(args.capture))
		report.capture={"path":args.capture,"error":err,"width":get_viewport().size.x,"height":get_viewport().size.y};write_report()
		get_tree().quit(0 if err==OK else 1)
	if args.has("headless-check") and frame_after_ready==3:get_tree().quit(0)
	if mouse_look:
		var direction:=Vector3.ZERO
		if Input.is_physical_key_pressed(KEY_W):direction-=camera.global_basis.z
		if Input.is_physical_key_pressed(KEY_S):direction+=camera.global_basis.z
		if Input.is_physical_key_pressed(KEY_A):direction-=camera.global_basis.x
		if Input.is_physical_key_pressed(KEY_D):direction+=camera.global_basis.x
		if Input.is_physical_key_pressed(KEY_E):direction+=Vector3.UP
		if Input.is_physical_key_pressed(KEY_Q):direction-=Vector3.UP
		camera.position+=direction.normalized()*move_speed*delta*(4 if Input.is_physical_key_pressed(KEY_SHIFT) else 1)

func _unhandled_input(event:InputEvent)->void:
	if event is InputEventKey and event.pressed and event.keycode==KEY_ESCAPE:
		mouse_look=not mouse_look;Input.mouse_mode=Input.MOUSE_MODE_CAPTURED if mouse_look else Input.MOUSE_MODE_VISIBLE
	if event is InputEventMouseMotion and mouse_look:
		camera.rotate_y(-event.relative.x*.002);camera.rotate_object_local(Vector3.RIGHT,-event.relative.y*.002)
