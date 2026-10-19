extends "res://validation/RoofNormalProof.gd"
## Diagnostic only. Exact cardinal-plane partition allows a new shading normal on proven subfaces.
## Common source voxels, RenderData, collision and materials are never edited.
var partition_error: String=""
var partition_total_cells: int=0

func corner_normals_error(values: Variant, original: Vector3, classification: String) -> String:
 if not values is Array or values.size()!=4:return "four normals required"
 if not (classification.begins_with("analytic_top") or classification=="preserved_cardinal"):return "unknown normal classification"
 for value in values:
  if not RD.vector_ok(value):return "nonfinite normal"
  var n:=RD.vector(value)
  if absf(n.length()-1.0)>.0001:return "nonunit normal"
  if n.dot(original)<=.01:return "reversed normal"
  if classification=="preserved_cardinal" and not n.is_equal_approx(original):return "preserved normal changed"
 return ""

func partition_check(original: Array, pieces: Array, pitch: float) -> Dictionary:
 var n:Vector3=(RD.vector(original[1])-RD.vector(original[0])).cross(RD.vector(original[2])-RD.vector(original[0])).normalized()
 var axis:=n.abs().max_axis_index()
 if absf(n[axis])<.999999:return {"error":"noncardinal original plane"}
 var u: int=(axis+1)%3;var v:int=(axis+2)%3
 var base: Array=[]
 for value in original:
  var p:=RD.vector(value)/pitch;var k:=Vector3i(roundi(p.x),roundi(p.y),roundi(p.z))
  if p.distance_to(Vector3(k))>.00001:return {"error":"original off grid"}
  base.append(k)
 var low_u:int=base[0][u];var high_u:int=low_u;var low_v:int=base[0][v];var high_v:int=low_v;var fixed:int=base[0][axis]
 for k in base:
  if k[axis]!=fixed:return {"error":"original nonplanar"}
  low_u=mini(low_u,k[u]);high_u=maxi(high_u,k[u]);low_v=mini(low_v,k[v]);high_v=maxi(high_v,k[v])
 var area:int=(high_u-low_u)*(high_v-low_v)
 if area<=0 or area>65536:return {"error":"partition area budget"}
 var covered:=PackedByteArray();covered.resize(area);covered.fill(0)
 var touched:=0
 for piece in pieces:
  if not piece is Dictionary or not piece.get("corners") is Array or piece.corners.size()!=4:return {"error":"four corners required"}
  var coords:Array=[]
  for value in piece.corners:
   if not RD.vector_ok(value):return {"error":"invalid corner"}
   var p:=RD.vector(value)/pitch;var k:=Vector3i(roundi(p.x),roundi(p.y),roundi(p.z))
   if p.distance_to(Vector3(k))>.00001:return {"error":"piece off grid"}
   if k[axis]!=fixed:return {"error":"piece off original plane"}
   if k[u]<low_u or k[u]>high_u or k[v]<low_v or k[v]>high_v:return {"error":"piece outside original"}
   coords.append(k)
  var nn:Vector3=(RD.vector(piece.corners[1])-RD.vector(piece.corners[0])).cross(RD.vector(piece.corners[2])-RD.vector(piece.corners[0])).normalized()
  if nn.dot(n)<.999999:return {"error":"piece winding or degenerate"}
  var a:int=coords[0][u];var b:int=a;var c:int=coords[0][v];var d:int=c
  for k in coords:a=mini(a,k[u]);b=maxi(b,k[u]);c=mini(c,k[v]);d=maxi(d,k[v])
  if a==b or c==d:return {"error":"zero piece area"}
  var corners:Dictionary={}
  for k in coords:
   if not k[u] in [a,b] or not k[v] in [c,d]:return {"error":"nonrectangular piece"}
   corners[str(k[u])+":"+str(k[v])]=true
  if corners.size()!=4:return {"error":"duplicate piece corner"}
  for i in range(4):
   var ca:Vector3i=coords[i];var cb:Vector3i=coords[(i+1)%4]
   if (ca[u]!=cb[u])==(ca[v]!=cb[v]):return {"error":"nonperimeter piece order"}
  var e:=corner_normals_error(piece.get("normals"),n,str(piece.get("classification","")))
  if not e.is_empty():return {"error":e}
  if str(piece.get("source_tile_id","")).is_empty():return {"error":"missing source provenance"}
  for x in range(a,b):
   for y in range(c,d):
    var at:int=(x-low_u)*(high_v-low_v)+(y-low_v)
    if covered[at]!=0:return {"error":"partition overlap"}
    covered[at]=1;touched+=1
 if touched!=area:return {"error":"partition hole"}
 partition_total_cells+=area
 if partition_total_cells>200000:return {"error":"total partition budget"}
 return {"error":"","unit_faces":area,"new_quads":pieces.size()}

func prepare_normal_sidecar(data: Dictionary, source_sha: String) -> String:
 var side_path:=str(args.get("normal_sidecar",""));var parsed:Variant=load_normal_sidecar(side_path)
 if not parsed is Dictionary:return "invalid sidecar JSON"
 var side:Dictionary=parsed
 if side.get("schema")!="riverstone.roof.normal_split_sidecar.v1":return "unsupported split sidecar schema"
 if side.get("render_sha256")!=source_sha:return "sidecar/source hash mismatch"
 if not RD.finite_number(side.get("grid_pitch")) or float(side.grid_pitch)<=0:return "explicit positive grid pitch required"
 var pitch:float=float(side.grid_pitch)
 if not side.get("splits") is Array or side.splits.is_empty():return "nonempty splits required"
 if not side.get("patches",[]) is Array:return "patches must be array"
 if data.has("rigid_parts"):return "static groups only"
 var nodes:Dictionary={};var mesh_child:=0
 for gi in data.groups.size():
  if data.groups[gi].quads.is_empty():continue
  nodes[gi]=subject.get_child(mesh_child);mesh_child+=1
 var replacements:Dictionary={};var seen:Dictionary={};var checked_split:=0;var checked_patch:=0
 partition_total_cells=0
 for mode in ["patches","splits"]:
  for row in side.get(mode,[]):
   if not row is Dictionary:return "row is not object"
   var gi:Variant=row.get("group_index");var qi:Variant=row.get("quad_index")
   if not RD.finite_number(gi) or not RD.finite_number(qi):return "indices required"
   if float(gi)!=float(int(gi)) or float(qi)!=float(int(qi)):return "indices must be integral"
   gi=int(gi);qi=int(qi)
   if not nodes.has(gi) or qi<0 or qi>=data.groups[gi].quads.size():return "index outside source"
   var key:=str(gi)+":"+str(qi)
   if seen.has(key):return "duplicate split/patch source quad"
   seen[key]=true
   if row.has("material") and row.material!=data.groups[gi].material:return "declared material differs from source"
   var original:Array=data.groups[gi].quads[qi];var pieces:Array=[]
   if mode=="splits":
    if not row.get("quads") is Array or row.quads.is_empty():return "split pieces required"
    pieces=row.quads
    var proof:=partition_check(original,pieces,pitch)
    if not str(proof.error).is_empty():return str(proof.error)
    checked_split+=1
   else:
    var n:Vector3=(RD.vector(original[1])-RD.vector(original[0])).cross(RD.vector(original[2])-RD.vector(original[0])).normalized()
    var error:=corner_normals_error(row.get("normals"),n,str(row.get("classification","")))
    if not error.is_empty():return error
    if str(row.get("source_tile_id","")).is_empty():return "missing patch provenance"
    pieces=[{"corners":original,"normals":row.normals}];checked_patch+=1
   if not replacements.has(gi):replacements[gi]={}
   replacements[gi][qi]=pieces
 var metrics:Array=[]
 for gi in replacements:
  var node:MeshInstance3D=nodes[gi];var group:Dictionary=data.groups[gi]
  var quads:int=group.quads.size()
  for qi in replacements[gi]:quads+=replacements[gi][qi].size()-1
  var vertices:=PackedVector3Array();vertices.resize(quads*6)
  var normals:=PackedVector3Array();normals.resize(quads*6);var at:=0
  for qi in group.quads.size():
   var original:Array=group.quads[qi]
   var normal:Vector3=(RD.vector(original[1])-RD.vector(original[0])).cross(RD.vector(original[2])-RD.vector(original[0])).normalized()
   var pieces:Array=replacements[gi].get(qi,[{"corners":original,"normals":[[normal.x,normal.y,normal.z],[normal.x,normal.y,normal.z],[normal.x,normal.y,normal.z],[normal.x,normal.y,normal.z]]}])
   for piece in pieces:
    for index in RD.TRIANGLE_ORDER:
     vertices[at]=RD.vector(piece.corners[index]);normals[at]=RD.vector(piece.normals[index]);at+=1
  var arrays:Array=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals
  var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);mesh.surface_set_material(0,node.mesh.surface_get_material(0))
  normal_patches.append({"node":node,"original":node.mesh,"changed":mesh})
  metrics.append({"group_index":gi,"old_quads":group.quads.size(),"new_quads":quads,"material_same_object":mesh.surface_get_material(0)==node.mesh.surface_get_material(0)})
 normal_report={"sidecar_path":side_path,"sidecar_sha256":FileAccess.get_sha256(side_path),"split_quads":checked_split,"whole_quad_patches":checked_patch,"partition_unit_faces":partition_total_cells,"group_proofs":metrics,"same_exterior_surface_by_exact_grid_partition":true,"vertex_array_identical":false,"source_voxel_geometry_and_colors_unchanged":true,"scope":normal_scope_text()}
 return ""

func load_normal_sidecar(path:String) -> Variant:
 return JSON.parse_string(FileAccess.get_file_as_string(path))
