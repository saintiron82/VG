extends SceneTree
## Thin preview scene; existing public player/controller and common runtime unchanged.
const Player=preload("res://runtime/LilyController.gd")
var stage:Node3D
var player:CharacterBody3D
func _initialize()->void:call_deferred("run")
func run()->void:
	stage=Node3D.new();root.add_child(stage)
	var world:=WorldEnvironment.new();var env:=Environment.new()
	env.background_mode=Environment.BG_COLOR;env.background_color=Color("29373e")
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("d2e4eb");env.ambient_light_energy=.22
	world.environment=env;stage.add_child(world)
	var light:=DirectionalLight3D.new();light.rotation_degrees=Vector3(-38,-25,0);light.light_energy=.65;light.shadow_enabled=true;stage.add_child(light)
	var floor:=StaticBody3D.new();floor.collision_layer=1;floor.collision_mask=2;stage.add_child(floor)
	var collision:=CollisionShape3D.new();var shape:=BoxShape3D.new();shape.size=Vector3(12,.2,12);collision.shape=shape;collision.position.y=-.1;floor.add_child(collision)
	var mesh:=MeshInstance3D.new();var box:=BoxMesh.new();box.size=shape.size;mesh.mesh=box;mesh.position.y=-.1
	var mat:=StandardMaterial3D.new();mat.albedo_color=Color("667573");mat.roughness=1;mesh.material_override=mat;floor.add_child(mesh)
	player=Player.new();player.cache_dir="res://revisions/original_lily_r01/generated/lily_r03";player.position=Vector3(0,.01,0);stage.add_child(player)
	var canvas:=CanvasLayer.new();stage.add_child(canvas);var label:=Label.new();label.position=Vector2(24,24);label.add_theme_font_size_override("font_size",20)
	label.text="LILY ORIGINAL IDENTITY / PRESERVED MEDIEVAL COSTUME\nWASD: move | Shift: run | Hold right mouse: orbit | 1/2/3: expression\nFinite character fixture only. Actual city is a separate integration."
	canvas.add_child(label)
