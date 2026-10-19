extends SceneTree
const Wood := preload("res://WoodSurface.gd")
var failed := false
var report: Dictionary = {"schema":"riverstone.wood_native_validation.v1","assets":{},"gpu_benchmark":"not measured"}
func _initialize() -> void:
 call_deferred("_run")
func check(value: bool, message: String) -> void:
 if not value: failed = true; push_error(message)
func _run() -> void:
 var root := ProjectSettings.globalize_path("res://../../../../../")
 for name in ["house_r04","barrel_r01","showcase_samples"]:
  var side := Wood.read_json("res://" + name + ".wood.json")
  var path: String = root.path_join(side.render.path)
  var data := Wood.read_json(path)
  var binding := Wood.validate_binding(data,side,FileAccess.get_sha256(path),FileAccess.get_sha256(root.path_join(side.source_master.path)))
  check(binding.is_empty(),binding)
  check(not Wood.validate_binding(data,side,"wrong").is_empty(),"Wrong hash accepted")
  var mesh := Wood.build_mesh(data,side,{},ProjectSettings.globalize_path("res://"))
  var baseline := Wood.build_mesh(data,{}, {},ProjectSettings.globalize_path("res://"))
  var legacy_adapter: Script = load(root.path_join("world_city/concept_city_v3/playable_detail_r01/RenderData.gd"))
  var legacy: Node3D = legacy_adapter.build(data)
  check(mesh.get_surface_count()==baseline.get_surface_count(),"Surface count changed")
  check(mesh.get_aabb()==baseline.get_aabb(),"AABB changed")
  var quads := 0; var textured := 0
  for i in range(mesh.get_surface_count()):
   var actual := mesh.surface_get_arrays(i); var original := baseline.surface_get_arrays(i)
   check(actual[Mesh.ARRAY_VERTEX]==original[Mesh.ARRAY_VERTEX],"Vertex/winding mismatch")
   check(actual[Mesh.ARRAY_NORMAL]==original[Mesh.ARRAY_NORMAL],"Normal mismatch")
   var legacy_mesh: ArrayMesh = legacy.get_child(i).mesh
   var legacy_arrays: Array = legacy_mesh.surface_get_arrays(0)
   check(actual[Mesh.ARRAY_VERTEX]==legacy_arrays[Mesh.ARRAY_VERTEX],"Original RenderData vertex/winding mismatch")
   check(actual[Mesh.ARRAY_NORMAL]==legacy_arrays[Mesh.ARRAY_NORMAL],"Original RenderData normal mismatch")
   var legacy_material: StandardMaterial3D = legacy_mesh.surface_get_material(0)
   var candidate_material: Material = mesh.surface_get_material(i)
   var actual_color: Color = candidate_material.get_shader_parameter("base_color") if candidate_material is ShaderMaterial else candidate_material.albedo_color
   check(actual_color==legacy_material.albedo_color,"Source base palette changed")
   quads += actual[Mesh.ARRAY_VERTEX].size()/6
   if mesh.surface_get_material(i) is ShaderMaterial:
    textured += 1
    var mat: ShaderMaterial = mesh.surface_get_material(i)
    check(mat.get_shader_parameter("wood_fibers").get_image().has_mipmaps(),"Fiber mipmaps missing")
    check(mat.get_shader_parameter("wood_endgrain").get_image().has_mipmaps(),"End-grain mipmaps missing")
  check(quads==int(data.quad_count),"Quad count changed")
  var original_collision := baseline.create_trimesh_shape()
  var wood_collision := mesh.create_trimesh_shape()
  check(original_collision.get_faces()==wood_collision.get_faces(),"Derived collision triangles changed")
  legacy.free()
  report.assets[name]={"original_RenderData_geometry_palette_equal":true,"quads":quads,"textured_material_groups":textured,"vertices_normals_winding_bounds_identical":true,"derived_trimesh_collision_faces_identical":true,"mipmaps_present":true,"render_binding_checked":true}
 report["all_passed"] = not failed
 var file := FileAccess.open("res://validation_godot.json",FileAccess.WRITE)
 file.store_string(JSON.stringify(report,"  ")+"\n")
 print(JSON.stringify(report))
 quit(1 if failed else 0)
