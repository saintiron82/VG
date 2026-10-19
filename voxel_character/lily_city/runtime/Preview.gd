extends Node3D
const Player = preload("LilyController.gd")
var player: CharacterBody3D
var status: Label

func _ready() -> void:
	var world := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("58656c")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("c8d7dc")
	environment.ambient_light_energy = 0.65
	world.environment = environment
	add_child(world)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-45, -35, 0)
	light.light_energy = 1.5
	light.shadow_enabled = true
	add_child(light)
	_box("FiniteFixtureFloor", Vector3(0,-.15,0), Vector3(16,.3,16), Color("9a9b8a"))
	_box("BlockingWall", Vector3(3,1.0,0), Vector3(.4,2.0,5), Color("7d776c"))
	_box("LowObstacleMustBlock", Vector3(-2,.32,0), Vector3(1,.64,1), Color("786953"))
	player = Player.new()
	player.position = Vector3(0,.05,0)
	add_child(player)
	var layer := CanvasLayer.new()
	add_child(layer)
	status = Label.new()
	status.position = Vector2(24,20)
	status.add_theme_color_override("font_color", Color("ffffff"))
	status.add_theme_color_override("font_shadow_color", Color("1c2527"))
	status.add_theme_constant_override("shadow_offset_x",2)
	status.add_theme_constant_override("shadow_offset_y",2)
	layer.add_child(status)

func _box(id: String, pos: Vector3, size: Vector3, color: Color) -> void:
	var body := StaticBody3D.new()
	body.name = id
	body.position = pos
	body.collision_layer = 1
	body.collision_mask = 2
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collision.shape = shape
	body.add_child(collision)
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	mesh.mesh = box
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 1
	mesh.material_override = material
	body.add_child(mesh)
	add_child(body)

func _process(_delta: float) -> void:
	if player != null and status != null:
		status.text = "LILY · Silver-haired city traveller\nWASD walk · Shift brisk walk · Hold right mouse to orbit · 1/2/3 expression\nFinite collision fixture only. City integration is separate.\nFloor: %s    Feet Y: %.3f" % [str(player.is_on_floor()), player.position.y]
