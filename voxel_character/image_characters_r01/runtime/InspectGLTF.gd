extends SceneTree
func _initialize() -> void:
 for method in ClassDB.class_get_method_list("GLTFDocument"):
  if "write" in str(method.name) or "generate" in str(method.name) or "append" in str(method.name):print(method)
 quit()
