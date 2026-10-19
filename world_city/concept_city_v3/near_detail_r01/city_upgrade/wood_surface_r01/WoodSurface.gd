extends RefCounted
## Reusable, opt-in appearance adapter. Source geometry is copied verbatim.
## Call validate_binding() with bytes hashes before build_mesh().
const SCHEMA := "riverstone.directional_wood_surface.v1"
const TRIANGLE_ORDER := [0, 2, 1, 0, 3, 2]
static var _textures: Dictionary = {}
static var _shaders: Dictionary = {}

static func vector(v: Array) -> Vector3:
 return Vector3(float(v[0]), float(v[1]), float(v[2]))

static func read_json(path: String) -> Dictionary:
 var bytes := FileAccess.get_file_as_bytes(path)
 if path.ends_with(".gz"):
  bytes = bytes.decompress_dynamic(64 * 1024 * 1024, FileAccess.COMPRESSION_GZIP)
 var value: Variant = JSON.parse_string(bytes.get_string_from_utf8())
 return value if value is Dictionary else {}

static func validate_binding(data: Dictionary, sidecar: Dictionary, render_sha256: String, master_sha256: String = "") -> String:
 if sidecar.get("schema", "") != SCHEMA: return "Wrong wood sidecar schema"
 if sidecar.get("render", {}).get("sha256", "") != render_sha256: return "Wood sidecar render hash mismatch"
 if not master_sha256.is_empty() and sidecar.get("source_master", {}).get("sha256", "") != master_sha256: return "Wood source master hash mismatch"
 if sidecar.render.get("source_id", "") != data.get("source_id", ""): return "Wood source identity mismatch"
 if int(sidecar.render.get("quad_count", -1)) != int(data.get("quad_count", -2)): return "Wood quad count mismatch"
 var seen: Dictionary = {}
 for item in sidecar.get("quads", []):
  var gi := int(item.get("group", -1)); var qi := int(item.get("quad", -1))
  if gi < 0 or gi >= data.groups.size(): return "Invalid wood group"
  if qi < 0 or qi >= data.groups[gi].quads.size(): return "Invalid wood quad"
  if seen.has(str(gi) + "/" + str(qi)): return "Duplicate wood quad"
  seen[str(gi) + "/" + str(qi)] = true
  if not item.get("uv") is Array or item.uv.size() != 4: return "Wood quad needs four UVs"
  if int(item.get("mode", 0)) not in [1, 2]: return "Invalid wood mode"
  if not sidecar.get("parts", {}).has(str(item.get("part", ""))): return "Missing wood source owner"
  if sidecar.parts[str(item.part)].get("material", "") != data.groups[gi].material: return "Wood part material mismatch"
  for uv in item.uv:
   if not uv is Array or uv.size() != 2 or not is_finite(float(uv[0])) or not is_finite(float(uv[1])): return "Non-finite wood UV"
 return ""

static func _texture(path: String) -> Texture2D:
 if _textures.has(path): return _textures[path]
 var image := Image.load_from_file(path)
 if image == null or image.is_empty(): return null
 image.generate_mipmaps()
 var texture := ImageTexture.create_from_image(image)
 _textures[path] = texture
 return texture

static func _color(value: Variant) -> Color:
 if value is String:
  return Color.html(value if value.begins_with("#") else "#" + value)
 if value is Dictionary: return _color(value.get("rgba", value.get("color", value.get("hex", "ffffff"))))
 if value is Array: return Color(float(value[0]), float(value[1]), float(value[2]), float(value[3]) if value.size() == 4 else 1.0)
 return Color.WHITE

static func material_for(base: Color, root: String, textured: bool = true) -> Material:
 if not textured:
  var plain := StandardMaterial3D.new()
  plain.albedo_color = base; plain.roughness = 1.0; plain.metallic_specular = 0.0
  if base.a < 1.0: plain.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
  return plain
 var path := root.path_join("directional_wood.gdshader")
 if not _shaders.has(path):
  var shader := Shader.new()
  shader.code = FileAccess.get_file_as_string(path)
  _shaders[path] = shader
 var material := ShaderMaterial.new()
 material.shader = _shaders[path]
 material.set_shader_parameter("base_color", base)
 material.set_shader_parameter("wood_fibers", _texture(root.path_join("wood_fibers.png")))
 material.set_shader_parameter("wood_endgrain", _texture(root.path_join("wood_endgrain.png")))
 return material

static func build_mesh(data: Dictionary, sidecar: Dictionary, palette: Dictionary, material_root: String) -> ArrayMesh:
 var by_group: Dictionary = {}
 for item in sidecar.get("quads", []):
  var gi := int(item.group)
  if not by_group.has(gi): by_group[gi] = {}
  by_group[gi][int(item.quad)] = item
 var mesh := ArrayMesh.new()
 for gi in range(data.groups.size()):
  var group: Dictionary = data.groups[gi]
  if group.quads.is_empty(): continue
  var vertices := PackedVector3Array(); var normals := PackedVector3Array()
  var uvs := PackedVector2Array(); var modes := PackedVector2Array()
  var mappings: Dictionary = by_group.get(gi, {})
  for qi in range(group.quads.size()):
   var quad: Array = group.quads[qi]
   var n := (vector(quad[1]) - vector(quad[0])).cross(vector(quad[2]) - vector(quad[0])).normalized()
   var mapping: Dictionary = mappings.get(qi, {})
   for corner in TRIANGLE_ORDER:
    vertices.append(vector(quad[corner])); normals.append(n)
    uvs.append(Vector2(float(mapping.uv[corner][0]), float(mapping.uv[corner][1])) if not mapping.is_empty() else Vector2.ZERO)
    modes.append(Vector2(float(mapping.get("mode", 0)), float(mapping.get("wear", 0))))
  var arrays: Array = []; arrays.resize(Mesh.ARRAY_MAX)
  arrays[Mesh.ARRAY_VERTEX] = vertices; arrays[Mesh.ARRAY_NORMAL] = normals
  if not mappings.is_empty():
   arrays[Mesh.ARRAY_TEX_UV] = uvs; arrays[Mesh.ARRAY_TEX_UV2] = modes
  mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
  var color := _color(palette.get(group.material, data.materials[group.material]))
  mesh.surface_set_material(mesh.get_surface_count()-1, material_for(color, material_root, not mappings.is_empty()))
 return mesh
