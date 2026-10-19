extends Node3D
const RD=preload("res://RenderData.gd")
var args: Dictionary={}
var camera: Camera3D
var subject: Node3D
var label: Label

func set_unshaded(node: Node, enabled: bool) -> void:
 if node is MeshInstance3D:
  for i in node.mesh.get_surface_count():
   var mat: Material=node.mesh.surface_get_material(i)
   if mat is StandardMaterial3D:
    mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED if enabled else BaseMaterial3D.SHADING_MODE_PER_PIXEL
 for child in node.get_children():set_unshaded(child,enabled)

func _ready() -> void:
 for token in OS.get_cmdline_user_args():
  if token.begins_with("--"):
   var pair:=token.substr(2).split("=",true,1);args[pair[0]]=pair[1] if pair.size()>1 else true
 var file:=str(args.get("render",""))
 var data:=RD.read(file)
 if data.has("error"):push_error(data.error);get_tree().quit(2);return
 var out:=str(args.get("output",file.get_base_dir().path_join("actual_godot_r01")))
 DirAccess.make_dir_recursive_absolute(out)
 subject=RD.build(data.data);add_child(subject)
 var env:=Environment.new();env.background_mode=Environment.BG_COLOR;env.background_color=Color("f7f4ee");env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("fff9ed");env.ambient_light_energy=.65;env.tonemap_mode=Environment.TONE_MAPPER_LINEAR
 var world:=WorldEnvironment.new();world.environment=env;add_child(world)
 var sun:=DirectionalLight3D.new();sun.rotation_degrees=Vector3(-45,-35,0);sun.light_energy=.8;sun.shadow_enabled=true;add_child(sun)
 camera=Camera3D.new();camera.near=.05;camera.far=100;camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=16;add_child(camera)
 var canvas:=CanvasLayer.new();add_child(canvas)
 var panel:=ColorRect.new();panel.color=Color(.05,.07,.09,.85);panel.position=Vector2(10,10);panel.size=Vector2(840,57);canvas.add_child(panel)
 label=Label.new();label.position=Vector2(20,15);label.add_theme_font_size_override("font_size",18);canvas.add_child(label)
 var rows:Array=[]
 var views:=[
 {"id":"oblique_lit","eye":Vector3(23,20,28),"target":Vector3(0,7,0),"size":20.0,"unshaded":false},
 {"id":"oblique_unshaded","eye":Vector3(23,20,28),"target":Vector3(0,7,0),"size":20.0,"unshaded":true},
 {"id":"street_lit","eye":Vector3(13,1.7,20),"target":Vector3(0,7,0),"perspective":true,"unshaded":false},
 {"id":"street_unshaded","eye":Vector3(13,1.7,20),"target":Vector3(0,7,0),"perspective":true,"unshaded":true},
 {"id":"roof_close_lit","eye":Vector3(15,18,18),"target":Vector3(2,11.5,0),"size":9.0,"unshaded":false}]

 for view in views:
  var ortho:bool=bool(view.get("unshaded",false))
  set_unshaded(subject,ortho)
  camera.position=view.eye;camera.look_at(view.target,Vector3.UP);camera.size=float(view.get("size",20.0));camera.fov=60.0;camera.projection=Camera3D.PROJECTION_PERSPECTIVE if bool(view.get("perspective",false)) else Camera3D.PROJECTION_ORTHOGONAL
  label.text="ROOF READABILITY DIAGNOSTIC  |  "+str(view.id)+"\nSame source geometry; lighting isolation / 1.7m eye-level / close view"
  for frame in range(7):await get_tree().process_frame
  await RenderingServer.frame_post_draw
  var target:=out.path_join(str(view.id)+".png")
  var code:=get_viewport().get_texture().get_image().save_png(target)
  var anchors:Array=[]
  for anchor in [Vector3(-6,14,5),Vector3(6,0,5),Vector3(6,14,5),Vector3(6,0,-5),Vector3(6,14,-5),Vector3(-6,0,-5),Vector3(-6,14,-5),Vector3(-6,0,5)]:
   var pixel:Vector2=camera.unproject_position(anchor)
   anchors.append({"world":[anchor.x,anchor.y,anchor.z],"pixel":[pixel.x,pixel.y]})
  rows.append({"view":view.id,"image":target,"save_error":code,"eye":[camera.position.x,camera.position.y,camera.position.z],"target":[view.target.x,view.target.y,view.target.z],"projection":"perspective" if camera.projection==Camera3D.PROJECTION_PERSPECTIVE else "orthographic","fov":camera.fov,"size_m":camera.size,"viewport_size":[get_viewport().size.x,get_viewport().size.y],"unshaded":ortho,"up":[camera.global_basis.y.x,camera.global_basis.y.y,camera.global_basis.y.z],"world_to_pixel_anchors":anchors})
  print("PROOF_CAPTURE ",view.id," ",code)
 var f:=FileAccess.open(out.path_join("capture_report.json"),FileAccess.WRITE)
 f.store_string(JSON.stringify({"source_render_path":file,"source_render_sha256":data.sha256,"engine":Engine.get_version_info(),"renderer":RenderingServer.get_video_adapter_name(),"actual_common_render_schema":RD.SCHEMA,"required_views":[],"six_view_gate_substitute":false,"diagnostic_only":true,"script_sha256":FileAccess.get_sha256("res://validation/RoofReadabilityProof.gd"),"records":rows,"production_approved":false},"  "))
 get_tree().quit()
