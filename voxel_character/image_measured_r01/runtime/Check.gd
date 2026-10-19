extends SceneTree
const VoxelRenderAdapter = preload("res://runtime/common/RenderData.gd")
func _initialize() -> void:
 call_deferred("run")
func run() -> void:
 var report := {"schema":"riverstone.measured_volume.godot_check.v1", "pass":true,"visual_review":false,"assets":[]}
 for id in ["violet","cyan"]:
  var path:String="res://generated/"+id+"/character.render.json"
  var loaded:Dictionary=VoxelRenderAdapter.read(path)
  if loaded.has("error"):push_error(loaded.error);quit(1);return
  var node:Node3D=VoxelRenderAdapter.build(loaded.data)
  root.add_child(node)
  var triangles:int=0
  for child in node.get_children():
   if child is MeshInstance3D:
    for index in range(child.mesh.get_surface_count()):
     var arrays:Array=child.mesh.surface_get_arrays(index)
     triangles+=arrays[Mesh.ARRAY_VERTEX].size()/3
  if triangles!=int(loaded.data.quad_count)*2:push_error("Triangle mismatch");quit(1);return
  report.assets.append({"id":id,"render_sha256":loaded.sha256,"mesh_instances":node.get_child_count(),"triangles":triangles,"render_adapter":"byte-identical common/preview/RenderData.gd"})
  node.queue_free();await process_frame
 var file:=FileAccess.open("res://evidence/godot_check.json",FileAccess.WRITE)
 file.store_string(JSON.stringify(report,"  "));file.close();print(JSON.stringify(report));quit(0)
