extends "res://Showcase.gd"
## Recorded actual renderer comparison, not a synthetic texture preview.
func _ready() -> void:
 super._ready()
 call_deferred("capture_all")

func capture_all() -> void:
 var out := ProjectSettings.globalize_path("res://evidence_actual_r01")
 DirAccess.make_dir_recursive_absolute(out)
 var results: Array = []
 for view in ["samples", "house_front", "barrel"]:
  for state in [false, true]:
   with_grain = state
   _show(view)
   for frame in range(8): await get_tree().process_frame
   await RenderingServer.frame_post_draw
   var filename: String = str(view) + ("_after" if state else "_before") + ".png"
   var error := get_viewport().get_texture().get_image().save_png(out.path_join(filename))
   results.append({"file":filename,"save_error":error,"view":view,"with_grain":state,"camera_position":[camera.position.x,camera.position.y,camera.position.z],"camera_basis":str(camera.basis),"fps_sample_cloud_software_only":Engine.get_frames_per_second(),"active_meshes":active.size(),"geometry_unchanged":true})
   print("WOOD_CAPTURE ", filename, " ", error)
 var f := FileAccess.open(out.path_join("captures.json"),FileAccess.WRITE)
 f.store_string(JSON.stringify({"engine":Engine.get_version_info(),"records":results,"renderer":"cloud OpenGL software; not user GPU measurement"},"  "))
 get_tree().quit()
