extends SceneTree
var report := {"schema":"riverstone.reference_character.glb_roundtrip.v1","pass":true,"assets":[]}
func _initialize() -> void:call_deferred("run")
func inspect(node: Node, stats: Dictionary) -> void:
 if node is MeshInstance3D:
  stats.meshes+=1
  for i in range(node.mesh.get_surface_count()):
   var arrays:Array=node.mesh.surface_get_arrays(i)
   stats.vertices+=arrays[Mesh.ARRAY_VERTEX].size()
   stats.triangles+=(arrays[Mesh.ARRAY_INDEX].size()/3 if arrays[Mesh.ARRAY_INDEX]!=null and arrays[Mesh.ARRAY_INDEX].size()>0 else arrays[Mesh.ARRAY_VERTEX].size()/3)
 for child in node.get_children():inspect(child,stats)
func run() -> void:
 for id in ["violet_bride","cyan_bride"]:
  var doc:=GLTFDocument.new();var state:=GLTFState.new()
  var path:String="res://exports/"+id+"_r05.glb"
  var error:=doc.append_from_file(path,state)
  if error!=OK:push_error("GLB read failed "+path);quit(1);return
  var scene:=doc.generate_scene(state)
  if scene==null:push_error("GLB scene missing");quit(1);return
  root.add_child(scene)
  var stats:={"id":id,"meshes":0,"vertices":0,"triangles":0}
  inspect(scene,stats)
  var manifest:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://generated/"+id+"_r05/manifest.json"))
  if stats.triangles!=int(manifest.quad_count)*2:push_error("GLB triangle count mismatch");quit(1);return
  report.assets.append(stats);scene.queue_free();await process_frame
 var file:=FileAccess.open("res://evidence/glb_roundtrip_r05.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
 print(JSON.stringify(report));quit(0)
