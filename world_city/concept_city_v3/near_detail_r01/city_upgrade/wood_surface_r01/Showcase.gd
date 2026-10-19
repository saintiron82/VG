extends Node3D
## Standalone visual proof. Default samples; --wood-view=house_front or barrel.
## 1 samples, 2 house front, 3 house side, 4 barrel, Space toggles identical base mesh.
const Wood := preload("res://WoodSurface.gd")
var repo_root := ProjectSettings.globalize_path("res://../../../../../")
var camera: Camera3D
var asset_root: Node3D
var label: Label
var current_view := "samples"
var with_grain := true
var active: Array = []

func _ready() -> void:
 var environment := WorldEnvironment.new()
 var settings := Environment.new()
 settings.background_mode = Environment.BG_COLOR; settings.background_color = Color("25313a")
 settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; settings.ambient_light_color = Color("e3e5e0"); settings.ambient_light_energy = 0.70
 settings.tonemap_mode = Environment.TONE_MAPPER_LINEAR
 environment.environment = settings; add_child(environment)
 var sun := DirectionalLight3D.new(); sun.light_energy = 1.15; sun.rotation_degrees = Vector3(-42,-35,0); sun.shadow_enabled = true; add_child(sun)
 camera = Camera3D.new(); camera.near = .025; camera.far = 200; camera.fov = 42; add_child(camera)
 asset_root = Node3D.new(); add_child(asset_root)
 var canvas := CanvasLayer.new(); add_child(canvas)
 label = Label.new(); label.position = Vector2(22,18); label.add_theme_font_size_override("font_size",22); canvas.add_child(label)
 for arg in OS.get_cmdline_user_args():
  if arg.begins_with("--wood-view="): current_view = arg.split("=",true,1)[1]
 _show(current_view)

func _add_asset(sidecar_name: String, offset: Vector3 = Vector3.ZERO) -> void:
 var sidecar := Wood.read_json("res://" + sidecar_name + ".wood.json")
 var render_path: String = repo_root.path_join(sidecar.render.path)
 var data := Wood.read_json(render_path)
 var problem := Wood.validate_binding(data, sidecar, FileAccess.get_sha256(render_path), FileAccess.get_sha256(repo_root.path_join(sidecar.source_master.path)))
 if not problem.is_empty(): push_error(problem); return
 var instance := MeshInstance3D.new(); instance.position = offset
 instance.mesh = Wood.build_mesh(data,sidecar if with_grain else {},{},ProjectSettings.globalize_path("res://"))
 asset_root.add_child(instance); active.append(instance)

func _show(view: String) -> void:
 current_view = view
 for instance in active: instance.queue_free()
 active.clear()
 if view == "barrel":
  _add_asset("barrel_r01");camera.position = Vector3(1.3,1.25,1.8);camera.look_at(Vector3(0,.52,0))
 elif view.begins_with("house"):
  _add_asset("house_r04")
  if view == "house_side": camera.position = Vector3(7,5.8,7);camera.look_at(Vector3(2.2,4.2,2.5))
  else: camera.position = Vector3(4.3,4.7,12.8);camera.look_at(Vector3(.0,3.8,6.0))
 else:
  _add_asset("showcase_samples");_add_asset("barrel_r01",Vector3(1.3,0,0))
  camera.position = Vector3(4.2,3.0,9);camera.look_at(Vector3(0,1.15,0))
 label.text = "Directional wood  |  %s  |  %s\n1 samples   2 house front   3 house side   4 barrel   Space before / after" % [view,"source grain + end grain" if with_grain else "original flat palette"]

func _unhandled_key_input(event: InputEvent) -> void:
 if not event is InputEventKey or not event.pressed or event.echo: return
 match event.keycode:
  KEY_1: _show("samples")
  KEY_2: _show("house_front")
  KEY_3: _show("house_side")
  KEY_4: _show("barrel")
  KEY_SPACE: with_grain = not with_grain;_show(current_view)
