extends Node3D
## Data-driven rigid poses of existing common geometry. This viewer does not
## simulate loads, sense occupancy, or claim controller/nav collision approval.
const RD=preload("res://RenderData.gd")
var contract:Dictionary={}
var meshes:Dictionary={}
var moving:Dictionary={}
var chains:Dictionary={}
var world_frame:=Transform3D.IDENTITY
var state_name:="ROAD_OPEN"
var road_enabled:=false
var navigation_enabled:=false
var elapsed:=0.0
var cycle_enabled:=false
var inspection_vessel:MeshInstance3D
var audit:Dictionary={"status":"not_loaded","collision":"kinematic visualization only; no runtime occupancy sensing"}
func v(a:Array)->Vector3:return Vector3(float(a[0]),float(a[1]),float(a[2]))
func rigid(d:Dictionary)->Transform3D:
	var rows:Array=d.basis
	return Transform3D(Basis(v(rows[0]),v(rows[1]),v(rows[2])).transposed(),v(d.translation))
func configure(d:Dictionary,assets:Dictionary,repo:String,mesh_builder:Callable)->bool:
	contract=d;world_frame=rigid(d.bridge_to_world)
	for key in d.asset_keys:
		var a:Dictionary=assets[key];var read:Dictionary=RD.read(repo+"/"+str(a.render_path))
		if read.has("error") or read.get("sha256","")!=a.render_sha256:
			audit.status="asset_hash_failed";return false
		meshes[key]=mesh_builder.call(read.data,{})
	var closed:Dictionary=d.states.ROAD_OPEN
	for p in closed.movable_placements:
		var node:=MeshInstance3D.new();node.mesh=meshes[p.asset_key];node.name=str(p.id).replace("-","minus");add_child(node);moving[p.id]=node
	for chain in closed.chains:
		var node:=MultiMeshInstance3D.new();var mm:=MultiMesh.new();mm.transform_format=MultiMesh.TRANSFORM_3D;mm.mesh=meshes[chain.native_link_key];node.multimesh=mm;add_child(node);chains[chain.id]=node
	if d.has("inspection_vessel"):
		var p:Dictionary=d.inspection_vessel;inspection_vessel=MeshInstance3D.new();inspection_vessel.mesh=meshes[p.asset_key];inspection_vessel.transform=rigid(p.transform_world);inspection_vessel.name="FullRigClearanceInspectionVessel";add_child(inspection_vessel)
	audit.status="native_assets_loaded";audit.movable_nodes=moving.size();audit.chain_runs=chains.size();audit.motion_interpolation="Adjacent one-degree source poses, render only; analytical sweep proof is separate."
	set_named_state("ROAD_OPEN");return true
func apply_state(s:Dictionary)->void:
	road_enabled=bool(s.get("road_enabled",false));navigation_enabled=bool(s.get("navigation_enabled",false))
	assert(not (road_enabled and navigation_enabled))
	for p in s.movable_placements:moving[p.id].transform=world_frame*rigid(p.transform_bridge_local)
	for chain in s.chains:
		var poses:Array[Transform3D]=[];var pts:Array=chain.polyline_bridge_xyz_m
		for i in range(pts.size()-1):
			var a:=v(pts[i]);var b:=v(pts[i+1]);var distance:=a.distance_to(b)
			if distance<.00001:continue
			var direction:Vector3=(b-a)/distance;var count:=maxi(1,ceili(distance/float(chain.link_spacing_m)))
			var orientation:=Basis(Quaternion(Vector3.UP,direction))
			for j in count:
				var twist:=Basis(Vector3.UP,PI*.5 if j%2 else 0.0)
				poses.append(world_frame*Transform3D(orientation*twist,a+direction*(distance*float(j)/count)))
		var mm:MultiMesh=chains[chain.id].multimesh;mm.instance_count=poses.size()
		for j in poses.size():mm.set_instance_transform(j,poses[j])
	if inspection_vessel:inspection_vessel.visible=navigation_enabled
	audit.state=state_name;audit.road_enabled=road_enabled;audit.navigation_enabled=navigation_enabled
	audit.leaf_angle_degrees=s.leaf_angle_degrees;audit.barrier_angle_degrees=s.barrier_angle_degrees
func set_named_state(name:String)->void:
	if not contract.states.has(name):return
	state_name=name;cycle_enabled=false;apply_state(contract.states[name])
func sampled_pose(samples:Array,angle:float)->Dictionary:
	var low:=clampi(floori(angle),0,samples.size()-1);var high:=mini(low+1,samples.size()-1);var t:=clampf(angle-low,0,1)
	var a:Dictionary=samples[low];var b:Dictionary=samples[high];var result:Dictionary=a.duplicate(true)
	for i in result.movable_placements.size():
		var tr:=rigid(a.movable_placements[i].transform_bridge_local).interpolate_with(rigid(b.movable_placements[i].transform_bridge_local),t)
		var rows:Basis=tr.basis.transposed()
		result.movable_placements[i].transform_bridge_local={"basis":[[rows.x.x,rows.x.y,rows.x.z],[rows.y.x,rows.y.y,rows.y.z],[rows.z.x,rows.z.y,rows.z.z]],"translation":[tr.origin.x,tr.origin.y,tr.origin.z]}
	for i in result.chains.size():
		for j in result.chains[i].polyline_bridge_xyz_m.size():
			var p:=v(a.chains[i].polyline_bridge_xyz_m[j]).lerp(v(b.chains[i].polyline_bridge_xyz_m[j]),t)
			result.chains[i].polyline_bridge_xyz_m[j]=[p.x,p.y,p.z]
	result.road_enabled=false;result.navigation_enabled=false
	result.leaf_angle_degrees=lerpf(float(a.leaf_angle_degrees),float(b.leaf_angle_degrees),t)
	result.barrier_angle_degrees=lerpf(float(a.barrier_angle_degrees),float(b.barrier_angle_degrees),t)
	return result
func smooth(t:float)->float:return t*t*(3-2*t)
func _process(delta:float)->void:
	if not cycle_enabled or not contract.has("cycle_stages"):return
	var total:=0.0
	for stage in contract.cycle_stages:total+=float(stage.duration_s)
	if total<=0:return
	elapsed=fmod(elapsed+delta,total);var start:=0.0
	for stage in contract.cycle_stages:
		var duration:=float(stage.duration_s)
		if elapsed<start+duration:
			state_name=str(stage.id)
			if stage.has("pose_state"):apply_state(contract.states[stage.pose_state])
			else:
				var t:=smooth(clampf((elapsed-start)/duration,0,1));var value:=lerpf(float(stage.start_angle),float(stage.end_angle),t)
				apply_state(sampled_pose(contract[stage.sample_array],value))
			break
		start+=duration
