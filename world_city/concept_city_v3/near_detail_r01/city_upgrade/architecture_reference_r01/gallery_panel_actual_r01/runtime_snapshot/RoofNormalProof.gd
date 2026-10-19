extends Node3D
const RD=preload("res://RenderData.gd")
var args: Dictionary={}
var camera: Camera3D
var subject: Node3D
var label: Label
var normal_patches: Array=[]
var normal_report: Dictionary={}

func prepare_normal_sidecar(data: Dictionary, source_sha: String) -> String:
 var side_path:=str(args.get("normal_sidecar",""))
 if side_path.is_empty():return "normal_sidecar is required"
 var side_raw:=FileAccess.get_file_as_string(side_path)
 var parsed: Variant=JSON.parse_string(side_raw)
 if not parsed is Dictionary:return "invalid sidecar JSON"
 var side: Dictionary=parsed
 if side.get("schema")!="riverstone.roof.normal_sidecar.v1":return "unsupported sidecar schema"
 if side.get("render_sha256")!=source_sha:return "sidecar/source hash mismatch"
 if not side.get("patches") is Array or side.patches.is_empty():return "empty patches"
 if data.has("rigid_parts"):return "this diagnostic supports static groups only"
 var nodes: Dictionary={};var mesh_child:=0
 for group_index in data.groups.size():
  if data.groups[group_index].quads.is_empty():continue
  nodes[group_index]=subject.get_child(mesh_child);mesh_child+=1
 var seen: Dictionary={};var grouped: Dictionary={};var array_cache: Dictionary={}
 for row in side.patches:
  if not row is Dictionary:return "patch is not object"
  var gi: Variant=row.get("group_index");var qi: Variant=row.get("quad_index")
  if not (gi is int or gi is float) or not (qi is int or qi is float):return "indices missing"
  if float(gi)!=float(int(gi)) or float(qi)!=float(int(qi)):return "non-integral indices"
  gi=int(gi);qi=int(qi)
  if not nodes.has(gi) or qi<0 or qi>=data.groups[gi].quads.size():return "patch outside render groups"
  var key:=str(gi)+":"+str(qi)
  if seen.has(key):return "duplicate normal patch"
  seen[key]=true
  if str(row.get("source_tile_id","")).is_empty() or str(row.get("classification","")).is_empty():return "missing semantic provenance"
  if not row.get("normals") is Array or row.normals.size()!=4:return "need four corner normals"
  var node: MeshInstance3D=nodes[gi]
  if not array_cache.has(gi):array_cache[gi]=node.mesh.surface_get_arrays(0)
  var original: PackedVector3Array=array_cache[gi][Mesh.ARRAY_NORMAL]
  for value in row.normals:
   if not RD.vector_ok(value):return "invalid normal"
   var n:=RD.vector(value)
   if absf(n.length()-1.0)>.0001:return "nonunit normal"
   if n.dot(original[qi*6])<=.01:return "normal reverses original exterior hemisphere"
  if not grouped.has(gi):grouped[gi]=[]
  grouped[gi].append(row)
 var metrics:Array=[]
 for gi in grouped:
  var node: MeshInstance3D=nodes[gi]
  var raw: Array=array_cache[gi]
  var changed: Array=raw.duplicate(true)
  var normals: PackedVector3Array=raw[Mesh.ARRAY_NORMAL].duplicate()
  var touched: Dictionary={}
  for row in grouped[gi]:
   for i in RD.TRIANGLE_ORDER.size():
    var at:int=int(row.quad_index)*6+i
    normals[at]=RD.vector(row.normals[RD.TRIANGLE_ORDER[i]])
    touched[at]=true
  var old_normals: PackedVector3Array=raw[Mesh.ARRAY_NORMAL]
  var untouched_mismatch:=0
  for at in old_normals.size():
   if not touched.has(at) and normals[at]!=old_normals[at]:untouched_mismatch+=1
  if untouched_mismatch:return "untargeted normals changed"
  changed[Mesh.ARRAY_NORMAL]=normals
  var before_positions: PackedByteArray=(raw[Mesh.ARRAY_VERTEX] as PackedVector3Array).to_byte_array()
  var after_positions: PackedByteArray=(changed[Mesh.ARRAY_VERTEX] as PackedVector3Array).to_byte_array()
  if before_positions!=after_positions:return "vertex geometry changed"
  var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,changed)
  mesh.surface_set_material(0,node.mesh.surface_get_material(0))
  normal_patches.append({"node":node,"original":node.mesh,"changed":mesh})
  var hasher:=HashingContext.new();hasher.start(HashingContext.HASH_SHA256);hasher.update(before_positions)
  metrics.append({"group_index":gi,"patch_quads":grouped[gi].size(),"vertices_sha256_unchanged":hasher.finish().hex_encode(),"untouched_normal_mismatch":untouched_mismatch,"material_same_object":mesh.surface_get_material(0)==node.mesh.surface_get_material(0)})
 normal_report={"sidecar_path":side_path,"sidecar_sha256":FileAccess.get_sha256(side_path),"patch_quads":side.patches.size(),"group_proofs":metrics,"source_geometry_and_colors_unchanged":true,"scope":"12-tile analytic-normal diagnostic only; source voxel geometry stays intact"}
 return ""

func switch_normals(enabled: bool) -> void:
 for patch in normal_patches:patch.node.mesh=patch.changed if enabled else patch.original

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
 var normal_error:=prepare_normal_sidecar(data.data,data.sha256)
 if not normal_error.is_empty():push_error(normal_error);get_tree().quit(3);return
 var env:=Environment.new();env.background_mode=Environment.BG_COLOR;env.background_color=Color("f7f4ee");env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("fff9ed");env.ambient_light_energy=.65;env.tonemap_mode=Environment.TONE_MAPPER_LINEAR
 var world:=WorldEnvironment.new();world.environment=env;add_child(world)
 var sun:=DirectionalLight3D.new();sun.rotation_degrees=Vector3(-45,-35,0);sun.light_energy=.8;sun.shadow_enabled=true;add_child(sun)
 camera=Camera3D.new();camera.near=.05;camera.far=100;camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=16;add_child(camera)
 var canvas:=CanvasLayer.new();add_child(canvas)
 var panel:=ColorRect.new();panel.color=Color(.05,.07,.09,.85);panel.position=Vector2(10,10);panel.size=Vector2(840,57);canvas.add_child(panel)
 label=Label.new();label.position=Vector2(20,15);label.add_theme_font_size_override("font_size",18);canvas.add_child(label)
 var rows:Array=[]
 var views:Array=view_catalog()

 for view in views:
  switch_normals(bool(view.normal_patch))
  sun.shadow_enabled=bool(view.get("shadows",true))
  var ortho:bool=bool(view.get("unshaded",false))
  set_unshaded(subject,ortho)
  camera.position=view.eye;camera.look_at(view.target,view.get("up",Vector3.UP));camera.size=float(view.get("size",20.0));camera.fov=60.0;camera.projection=Camera3D.PROJECTION_PERSPECTIVE if bool(view.get("perspective",false)) else Camera3D.PROJECTION_ORTHOGONAL
  label.text=diagnostic_title()+"  |  "+str(view.id)+"\n"+normal_scope_text()
  for frame in range(7):await get_tree().process_frame
  await RenderingServer.frame_post_draw
  var target:=out.path_join(str(view.id)+".png")
  var code:=get_viewport().get_texture().get_image().save_png(target)
  var anchors:Array=[]
  for anchor in [Vector3(-6,14,5),Vector3(6,0,5),Vector3(6,14,5),Vector3(6,0,-5),Vector3(6,14,-5),Vector3(-6,0,-5),Vector3(-6,14,-5),Vector3(-6,0,5)]:
   var pixel:Vector2=camera.unproject_position(anchor)
   anchors.append({"world":[anchor.x,anchor.y,anchor.z],"pixel":[pixel.x,pixel.y]})
  rows.append({"view":view.id,"image":target,"save_error":code,"eye":[camera.position.x,camera.position.y,camera.position.z],"target":[view.target.x,view.target.y,view.target.z],"projection":"perspective" if camera.projection==Camera3D.PROJECTION_PERSPECTIVE else "orthographic","fov":camera.fov,"size_m":camera.size,"viewport_size":[get_viewport().size.x,get_viewport().size.y],"unshaded":ortho,"normal_patch":view.normal_patch,"shadows_enabled":sun.shadow_enabled,"up":[camera.global_basis.y.x,camera.global_basis.y.y,camera.global_basis.y.z],"world_to_pixel_anchors":anchors})
  print("PROOF_CAPTURE ",view.id," ",code)
 var f:=FileAccess.open(out.path_join("capture_report.json"),FileAccess.WRITE)
 f.store_string(JSON.stringify({"source_render_path":file,"source_render_sha256":data.sha256,"engine":Engine.get_version_info(),"renderer":RenderingServer.get_video_adapter_name(),"actual_common_render_schema":RD.SCHEMA,"required_views":required_view_names(),"six_view_gate_substitute":false,"diagnostic_only":true,"normal_validation":normal_report,"script_path":get_script().resource_path,"script_sha256":FileAccess.get_sha256(get_script().resource_path),"base_script_sha256":FileAccess.get_sha256("res://validation/RoofNormalProof.gd"),"records":rows,"production_approved":false},"  "))
 get_tree().quit()

func normal_scope_text() -> String:
 return "Same geometry and colors; 12 measured tiles / diagnostic only"

func required_view_names() -> Array:
 return []

func view_catalog() -> Array:
 return [
 {"id":"oblique_before","eye":Vector3(23,20,28),"target":Vector3(0,7,0),"size":20.0,"normal_patch":false},
 {"id":"oblique_after","eye":Vector3(23,20,28),"target":Vector3(0,7,0),"size":20.0,"normal_patch":true},
 {"id":"roof_close_before","eye":Vector3(15,18,18),"target":Vector3(2,11.5,0),"size":9.0,"normal_patch":false},
 {"id":"roof_close_after","eye":Vector3(15,18,18),"target":Vector3(2,11.5,0),"size":9.0,"normal_patch":true},
 {"id":"oblique_before_noshadow","eye":Vector3(23,20,28),"target":Vector3(0,7,0),"size":20.0,"normal_patch":false,"shadows":false},
 {"id":"oblique_after_noshadow","eye":Vector3(23,20,28),"target":Vector3(0,7,0),"size":20.0,"normal_patch":true,"shadows":false},
 {"id":"roof_close_before_noshadow","eye":Vector3(15,18,18),"target":Vector3(2,11.5,0),"size":9.0,"normal_patch":false,"shadows":false},
 {"id":"roof_close_after_noshadow","eye":Vector3(15,18,18),"target":Vector3(2,11.5,0),"size":9.0,"normal_patch":true,"shadows":false}]

func diagnostic_title() -> String:
 return "ROOF NORMAL DIAGNOSTIC"
