extends "res://validation/RoofNormalFullProof.gd"
func diagnostic_title() -> String:
 return "ROOF TILE OWNERSHIP + SOURCE GALLERY"
func normal_scope_text() -> String:
 return "354 observed tiles; local cut ownership repaired / whole-house art unresolved"
func view_catalog() -> Array:
 var views:Array=super.view_catalog().slice(0,6)
 views.append({"id":"oblique","eye":Vector3(23,20,28),"target":Vector3(0,7,0),"size":20.0,"normal_patch":true})
 views.append({"id":"roof_close","eye":Vector3(15,18,18),"target":Vector3(2,11.5,0),"size":9.0,"normal_patch":true})
 views.append({"id":"street","eye":Vector3(28,1.7,34),"target":Vector3(0,9,0),"perspective":true,"normal_patch":true})
 return views
