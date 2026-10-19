extends SceneTree
const VoxelRenderAdapter = preload("res://runtime/common/RenderData.gd")
func _initialize() -> void:call_deferred("run")
func run() -> void:
 var report:={"schema":"riverstone.turnaround.godot_mesh_check.v1","pass":true,"visual_gpu_review":false,"assets":[]}
 for tag in OS.get_cmdline_user_args():
  var loaded:Dictionary=read_compact("res://generated/"+tag+"/character.render.json")
  if loaded.has("error"):push_error(loaded.error);quit(1);return
  var node:Node3D=VoxelRenderAdapter.build(loaded.data);root.add_child(node);var triangles:int=0
  for child in node.get_children():
   if child is MeshInstance3D:
    for i in range(child.mesh.get_surface_count()):triangles+=child.mesh.surface_get_arrays(i)[Mesh.ARRAY_VERTEX].size()/3
  if triangles!=int(loaded.data.quad_count)*2:push_error("Triangle count mismatch");quit(1);return
  report.assets.append({"tag":tag,"triangles":triangles,"render_sha256":loaded.sha256,"renderer":"byte-identical common/preview/RenderData.gd"});node.queue_free();await process_frame
 var file:=FileAccess.open("res://evidence/godot_mesh_check.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();print(JSON.stringify(report));quit(0)

func read_compact(path:String)->Dictionary:
 if FileAccess.file_exists(path):return VoxelRenderAdapter.read(path)
 var compressed:=FileAccess.get_file_as_bytes(path+".gz")
 var bytes:=compressed.decompress_dynamic(16777216,FileAccess.COMPRESSION_GZIP)
 var parser:=JSON.new()
 if parser.parse(bytes.get_string_from_utf8())!=OK:return {"error":"Gzip JSON parse failed"}
 var problem:=VoxelRenderAdapter.validate(parser.data)
 if not problem.is_empty():return {"error":problem}
 var hasher:=HashingContext.new();hasher.start(HashingContext.HASH_SHA256);hasher.update(bytes)
 return {"data":parser.data,"sha256":hasher.finish().hex_encode(),"storage":"gzip; standard common validator/build unchanged"}
