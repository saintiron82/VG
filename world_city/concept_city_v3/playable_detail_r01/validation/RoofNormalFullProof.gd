extends "res://validation/RoofNormalSplitProof.gd"
## Optional source-bound diagnostic. Same common voxel render and exact surface partition.
const MAX_COMPRESSED:int=8*1024*1024
const MAX_RAW:int=32*1024*1024
func decode_sidecar(bytes:PackedByteArray,gzip:bool) -> Variant:
 if bytes.is_empty() or bytes.size()>MAX_COMPRESSED:return null
 var raw:PackedByteArray=bytes.decompress_dynamic(MAX_RAW,FileAccess.COMPRESSION_GZIP) if gzip else bytes
 if raw.is_empty() or raw.size()>MAX_RAW:return null
 return JSON.parse_string(raw.get_string_from_utf8())
func load_normal_sidecar(path:String) -> Variant:
 var f:=FileAccess.open(path,FileAccess.READ)
 if f==null or f.get_length()>MAX_COMPRESSED:return null
 return decode_sidecar(f.get_buffer(f.get_length()),path.ends_with(".gz"))
func normal_scope_text() -> String:
 return "Same geometry and colors; source-validated tile normals / diagnostic only"
func required_view_names() -> Array:
 return ["front","right","back","left","top","bottom"]
func view_catalog() -> Array:
 var views:Array=[]
 var positions:Dictionary={"front":Vector3(0,7,30),"right":Vector3(30,7,0),"back":Vector3(0,7,-30),"left":Vector3(-30,7,0),"top":Vector3(0,30,0),"bottom":Vector3(0,-23,0)}
 for id in required_view_names():
  views.append({"id":id,"eye":positions[id],"target":Vector3(0,7,0),"up":Vector3(0,0,-1) if id=="top" else Vector3(0,0,1) if id=="bottom" else Vector3.UP,"size":18.0,"normal_patch":true,"unshaded":true})
 for pair in [{"id":"oblique","eye":Vector3(23,20,28),"target":Vector3(0,7,0),"size":20.0},{"id":"roof_close","eye":Vector3(15,18,18),"target":Vector3(2,11.5,0),"size":9.0},{"id":"street","eye":Vector3(28,1.7,34),"target":Vector3(0,9,0),"perspective":true}]:
  for enabled in [false,true]:
   var v:Dictionary=pair.duplicate();v.id=str(pair.id)+("_after" if enabled else "_before");v.normal_patch=enabled;views.append(v)
 return views
