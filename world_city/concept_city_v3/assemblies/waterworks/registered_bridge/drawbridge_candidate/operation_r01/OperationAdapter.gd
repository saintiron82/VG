extends RefCounted
## Reconstructed kinematic adapter; live observations are mandatory per tick.
const Controller=preload("OperationController.gd")
var controller
var geometry={}
var mechanism=null
var leaf_angle=0.0
var barrier_angle=90.0
var cover_progress=0.0
var last_tick_ms=null
var last_pose={}
var last_output={}
var configured=false
var adapter_fault=""
func configure_from_files(contract_path: String,pack_path: String,view=null) -> bool:
	var data=JSON.parse_string(FileAccess.get_file_as_string(contract_path)); var pack=JSON.parse_string(FileAccess.get_file_as_string(pack_path))
	if not data is Dictionary or not pack is Dictionary: return false
	return configure(data,pack,FileAccess.get_sha256(pack_path),view)
func configure(data: Dictionary,pack: Dictionary,verified_pack_sha256: String,view=null) -> bool:
	if verified_pack_sha256!=data.geometry_pack.sha256: return false
	for key in ["states","motion_samples","barrier_samples","hinge_cover_samples"]:
		if not pack.has(key): return false
	controller=Controller.new(data); geometry=pack; mechanism=view; leaf_angle=0; barrier_angle=90; cover_progress=0; last_tick_ms=null; configured=true; adapter_fault=""
	last_pose=geometry.states.ROAD_OPEN.duplicate(true); last_pose.road_enabled=false; last_pose.navigation_enabled=false; _apply_pose(); return true
func attach_mechanism(view) -> bool:
	if view==null or not view.has_method("apply_state"): return false
	mechanism=view; _apply_pose(); return true
func actual_pose_parameters() -> Dictionary: return {"leaf_angle_degrees":leaf_angle,"barrier_angle_degrees":barrier_angle,"hinge_plate_progress":cover_progress}
func _feedback_matches(s: Dictionary) -> bool:
	if not s.get("actuators") is Dictionary: return true
	for k in s.actuators:
		var st=s.actuators[k]
		if k=="leaves" and ((st=="seated_locked" and abs(leaf_angle)>0.000001) or (st=="open_locked" and abs(leaf_angle-90)>0.000001)): return false
		if k=="covers" and ((st=="seated_locked" and abs(cover_progress)>0.000001) or (st=="stowed_locked" and abs(cover_progress-1)>0.000001)): return false
		if k=="barriers" and ((st=="open_locked" and abs(barrier_angle-90)>0.000001) or (st=="closed_locked" and abs(barrier_angle)>0.000001)): return false
	return true
func tick(now_ms,snapshot,commands=[]) -> Dictionary:
	if not configured: return {"state":"UNCONFIGURED","stop_all_actuators":true,"road_enabled":false,"navigation_enabled":false}
	var s=snapshot.duplicate(true) if snapshot is Dictionary else snapshot; adapter_fault=""
	if s is Dictionary and not _feedback_matches(s): adapter_fault="lock_feedback_disagrees_with_kinematic_pose"; s.actuators={}
	last_output=controller.step(now_ms,s,commands)
	var delta_s=0.0
	if Controller.integer(now_ms) and last_tick_ms!=null: delta_s=clamp(float(now_ms-last_tick_ms)/1000.0,0.0,1.0)
	if Controller.integer(now_ms): last_tick_ms=now_ms
	if not last_output.stop_all_actuators:
		var t=last_output.actuator_targets
		if t.has("leaves"): leaf_angle=move_toward(leaf_angle,90.0 if t.leaves=="open_locked" else 0.0,9.0*delta_s)
		if t.has("covers"): cover_progress=move_toward(cover_progress,1.0 if t.covers=="stowed_locked" else 0.0,0.2*delta_s)
		if t.has("barriers"): barrier_angle=move_toward(barrier_angle,90.0 if t.barriers=="open_locked" else 0.0,45.0*delta_s)
	last_pose=_pose(); last_pose.road_enabled=last_output.road_enabled; last_pose.navigation_enabled=last_output.navigation_enabled; _apply_pose()
	return {"controller":last_output.duplicate(true),"pose_parameters":actual_pose_parameters(),"adapter_fault":adapter_fault,"scope":"Kinematic candidate requiring external complete sensing"}
static func rigid(d: Dictionary) -> Transform3D:
	var b=d.basis
	return Transform3D(Basis(Vector3(b[0][0],b[0][1],b[0][2]),Vector3(b[1][0],b[1][1],b[1][2]),Vector3(b[2][0],b[2][1],b[2][2])).transposed(),Vector3(d.translation[0],d.translation[1],d.translation[2]))
static func dict_transform(t: Transform3D) -> Dictionary:
	var b=t.basis.transposed()
	return {"basis":[[b.x.x,b.x.y,b.x.z],[b.y.x,b.y.y,b.y.z],[b.z.x,b.z.y,b.z.z]],"translation":[t.origin.x,t.origin.y,t.origin.z]}
func _sample(samples: Array,index: float) -> Dictionary:
	var lo=clampi(floori(index),0,samples.size()-1); var hi=mini(lo+1,samples.size()-1); var f=clampf(index-lo,0,1); var a=samples[lo]; var b=samples[hi]; var result=a.duplicate(true)
	for i in range(result.movable_placements.size()): result.movable_placements[i].transform_bridge_local=dict_transform(rigid(a.movable_placements[i].transform_bridge_local).interpolate_with(rigid(b.movable_placements[i].transform_bridge_local),f))
	for i in range(result.chains.size()):
		for j in range(result.chains[i].polyline_bridge_xyz_m.size()):
			for k in range(3): result.chains[i].polyline_bridge_xyz_m[j][k]=lerpf(a.chains[i].polyline_bridge_xyz_m[j][k],b.chains[i].polyline_bridge_xyz_m[j][k],f)
	result.leaf_angle_degrees=leaf_angle; result.barrier_angle_degrees=barrier_angle; result.hinge_plate_progress=cover_progress; return result
func _pose() -> Dictionary:
	if leaf_angle>0.000001: return _sample(geometry.motion_samples,leaf_angle)
	if cover_progress>0.000001: return _sample(geometry.hinge_cover_samples,cover_progress*(geometry.hinge_cover_samples.size()-1))
	return _sample(geometry.barrier_samples,barrier_angle)
func _apply_pose():
	if mechanism!=null:
		mechanism.set("cycle_enabled",false); mechanism.set("state_name",last_output.get("state","UNVERIFIED_INITIAL_POSE")); mechanism.call("apply_state",last_pose)
