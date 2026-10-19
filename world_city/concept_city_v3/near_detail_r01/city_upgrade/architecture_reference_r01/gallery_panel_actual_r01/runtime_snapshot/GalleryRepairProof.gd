extends "res://validation/RoofNormalFullProof.gd"
func diagnostic_title() -> String:
 return "IMAGE-MEASURED GALLERY PANEL REPAIR"
func normal_scope_text() -> String:
 return "One FRONT panel; roof / foundation retained; whole-house art unresolved"
func view_catalog() -> Array:
 var views:Array=super.view_catalog().slice(0,6)
 views.append({"id":"oblique","eye":Vector3(23,20,28),"target":Vector3(0,7,0),"size":20.0,"normal_patch":true})
 views.append({"id":"rail_front_close","eye":Vector3(-2.25,7,9),"target":Vector3(-2.25,7,4.9375),"size":2.1,"normal_patch":true,"unshaded":true})
 views.append({"id":"rail_oblique_close","eye":Vector3(0.5,8.4,9.5),"target":Vector3(-2.25,6.96,4.9375),"size":3.0,"normal_patch":true})
 return views
