extends SceneTree
func _initialize() -> void:
 var m:=StandardMaterial3D.new()
 for p in m.get_property_list():
  if 'vertex_color' in str(p.name):print(p.name,'=',m.get(p.name))
 m=null;quit()
