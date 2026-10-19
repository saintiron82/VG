extends Node3D
const World=preload("res://CityWorldDetail.gd")
func _ready() -> void:
	var w:=World.new();add_child(w)
	var err:=w.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),false)
	if not err.is_empty():get_tree().quit(2);return
	var origin:=Vector3(62.150496917718314,2.884433624773715,109.5418129106266)
	var pose:=Transform3D(Basis(Vector3.UP,2.6937581289867887),origin)
	if not w.ensure_region(origin,1):get_tree().quit(2);return
	await get_tree().physics_frame;await get_tree().physics_frame
	var samples: Array=[]
	for z in [7.5,8.0,9.0,10.0,12.0]:
		var point:=pose*Vector3(0,0,z)
		var query:=PhysicsRayQueryParameters3D.create(point+Vector3(0,1.0,0),point-Vector3(0,2,0),1)
		var hit:=get_world_3d().direct_space_state.intersect_ray(query)
		samples.append({"local_z":z,"query_world":[point.x,point.y,point.z],"hit":not hit.is_empty(),"position":str(hit.get("position",Vector3.ZERO)),"normal":str(hit.get("normal",Vector3.ZERO)),"source":str(hit.collider.get_meta("source_id","unknown")) if not hit.is_empty() else ""})
	var f:=FileAccess.open("res://../near_detail_r01/city_upgrade/site_probe.json",FileAccess.WRITE);f.store_string(JSON.stringify({"samples":samples,"world":w.debug_state()},"\t"));print(JSON.stringify(samples));get_tree().quit()
