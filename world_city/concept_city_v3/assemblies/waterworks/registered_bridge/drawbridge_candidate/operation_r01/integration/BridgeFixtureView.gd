extends Node3D
## Visible CLOSED-WORLD fixture. No city-wide NPC registration is implied.
const Runtime=preload("../runtime_fixture/revisions/r02/RuntimeWorld.gd")
signal fixture_event(event_name: String,record: Dictionary)
var runtime
var mechanism
var followers={}
var floor_samples={}
var current_record={}
var recorded_states=[]
var status_text="CLOSED-WORLD BRIDGE FIXTURE: unconfigured"
var label: Label
var command_queue=[]
var pending_events=[]
var demo_enabled=false
var demo_stage="WAIT_ROAD"
var stage_time=0.0
var last_state=""
var configured=false
var cart_blocked=false
var native_vessel_asset_key="registered_port_rigged_barge_24m"

func configure(existing_mechanism,repo_root: String,options: Dictionary={}) -> bool:
	if not is_inside_tree() or not global_transform.is_equal_approx(Transform3D.IDENTITY): return false
	var base=str(options.get("operation_source_dir",repo_root+"/world_city/concept_city_v3/assemblies/waterworks/registered_bridge/drawbridge_candidate/operation_r01"))
	var cp=str(options.get("contract_path",base+"/runtime_fixture/revisions/r02/contract.json"))
	var pp=str(options.get("geometry_pack_path",base+"/../resolved_placements.json"))
	floor_samples=JSON.parse_string(FileAccess.get_file_as_string(str(options.get("floor_samples_path",base+"/integration/floor_samples.json"))))
	if not floor_samples is Dictionary or not existing_mechanism.get("meshes") is Dictionary or not existing_mechanism.meshes.get(native_vessel_asset_key) is Mesh: return false
	mechanism=existing_mechanism
	# The decorative inspection boat is not a sensed actor. Replace it explicitly.
	if is_instance_valid(mechanism.get("inspection_vessel")):
		mechanism.inspection_vessel.queue_free(); mechanism.inspection_vessel=null
	runtime=Runtime.new(); runtime.name="ClosedWorldBridgeOperationFixture"; add_child(runtime)
	if not runtime.configure(cp,pp,mechanism): runtime.queue_free(); return false
	runtime.add_actor("FIXTURE_PEDESTRIAN","pedestrian",Vector3(0,_floor(0,2),2))
	runtime.add_actor("FIXTURE_CART","cart",Vector3(-27,_floor(-27,-2),-2))
	runtime.add_actor("FIXTURE_FULL_RIG","vessel",Vector3(-2.5,_water(-65),-65))
	var cap=CapsuleMesh.new(); cap.radius=0.4; cap.height=1.8
	_follow("FIXTURE_PEDESTRIAN",cap,Vector3(0,0.9,0),Color(1,0.8,0.15))
	var cart=BoxMesh.new(); cart.size=Vector3(5,2.4,2.2)
	_follow("FIXTURE_CART",cart,Vector3(0,1.2,0),Color(0.75,0.32,0.1))
	_follow("FIXTURE_FULL_RIG",mechanism.meshes[native_vessel_asset_key],Vector3.ZERO,null)
	if options.get("show_status_label",true):
		var layer=CanvasLayer.new(); add_child(layer); label=Label.new(); label.position=Vector2(14,14); label.add_theme_color_override("font_color",Color(1,0.95,0.65)); label.add_theme_color_override("font_shadow_color",Color.BLACK); label.add_theme_constant_override("shadow_offset_x",2); label.add_theme_constant_override("shadow_offset_y",2); layer.add_child(label)
	demo_enabled=bool(options.get("demonstration",false)); configured=true; _update_visuals(); return true
func _follow(ident: String,mesh: Mesh,offset: Vector3,color):
	var node=MeshInstance3D.new(); node.name=ident+"_visible"; node.mesh=mesh
	if color!=null:
		var mat=StandardMaterial3D.new(); mat.albedo_color=color; node.material_override=mat
	add_child(node); followers[ident]={"node":node,"offset":offset}
func _floor(x: float,z: float) -> float:
	var lane=floor_samples.lanes[0] if z<0 else floor_samples.lanes[1]
	var t=clampf((x-float(floor_samples.x_start_m))/float(floor_samples.step_m),0,lane.y_m.size()-1); var lo=floori(t); var hi=mini(lo+1,lane.y_m.size()-1)
	return lerpf(lane.y_m[lo],lane.y_m[hi],t-lo)
func _water(z: float) -> float:
	var world=runtime.frame*Vector3(-2.5,0,z)
	return 1.2-0.0035*(world.x+470.0)
func request_navigation(): command_queue.append("request_navigation")
func request_road(): command_queue.append("request_road")
func stop(): command_queue.append("stop")
func reset_fault(): command_queue.append("reset")
func _event(name: String):
	var record={"event":name,"time_ms":Time.get_ticks_msec(),"state":current_record.get("state","UNCONFIGURED"),"demo_stage":demo_stage,"scope":"closed-world fixture; city NPC/nav system unregistered"}
	recorded_states.append(record); fixture_event.emit(name,record)
func _stage(name: String): demo_stage=name; stage_time=0; pending_events.append(name.to_lower())
func _demo(delta: float):
	if not demo_enabled or current_record.is_empty() or current_record.state=="SAFE_HALT": return
	stage_time+=delta
	if demo_stage=="WAIT_ROAD" and current_record.road_enabled:
		request_navigation(); _stage("OCCUPIED_WAIT")
	elif demo_stage=="OCCUPIED_WAIT":
		if not cart_blocked:
			cart_blocked=runtime.move_actor("FIXTURE_CART",Vector3(3*delta,0,0))!=null
		if stage_time>=2.0: _stage("PEDESTRIAN_EXIT")
	elif demo_stage=="PEDESTRIAN_EXIT":
		var p=runtime.pose("FIXTURE_PEDESTRIAN").origin; var nx=minf(23,p.x+4*delta)
		runtime.move_actor("FIXTURE_PEDESTRIAN",Vector3(nx-p.x,_floor(nx,p.z)-p.y,0))
		if runtime.pose("FIXTURE_PEDESTRIAN").origin.x>=22.9: _stage("WAIT_NAVIGATION")
	elif demo_stage=="WAIT_NAVIGATION" and current_record.navigation_enabled: _stage("VESSEL_ENTER")
	elif demo_stage=="VESSEL_ENTER":
		_move_vessel_toward(0,delta)
		if runtime.pose("FIXTURE_FULL_RIG").origin.z>=-0.01: request_road(); _stage("VESSEL_TO_TAIL_HOLD")
	elif demo_stage=="VESSEL_TO_TAIL_HOLD":
		_move_vessel_toward(38,delta)
		if runtime.pose("FIXTURE_FULL_RIG").origin.z>=37.99: _stage("FULL_RIG_TAIL_WAIT")
	elif demo_stage=="FULL_RIG_TAIL_WAIT":
		if stage_time>=2.0: _stage("VESSEL_EXIT")
	elif demo_stage=="VESSEL_EXIT":
		_move_vessel_toward(61,delta)
		if runtime.pose("FIXTURE_FULL_RIG").origin.z>=60.99: _stage("WAIT_ROAD_RESTORED")
	elif demo_stage=="WAIT_ROAD_RESTORED" and current_record.road_enabled: _stage("ROAD_RESTORED"); demo_enabled=false
func _move_vessel_toward(target: float,delta: float):
	var p=runtime.pose("FIXTURE_FULL_RIG").origin; var nz=move_toward(p.z,target,8*delta)
	runtime.move_actor("FIXTURE_FULL_RIG",Vector3(0,_water(nz)-p.y,nz-p.z))
func _physics_process(delta: float):
	if not configured: return
	_demo(delta)
	var result=runtime.tick_live(command_queue); command_queue=[]
	current_record=result.operation.controller.duplicate(true)
	current_record.coverage_issues=result.coverage_issues; current_record.pose=result.operation.pose_parameters; current_record.complete=result.snapshot.complete
	if current_record.state!=last_state:
		last_state=current_record.state; recorded_states.append({"time_ms":Time.get_ticks_msec(),"controller":current_record.duplicate(true)}); fixture_event.emit("state_changed",current_record.duplicate(true))
	status_text="CLOSED-WORLD GUARDED FIXTURE | "+current_record.state+" | "+demo_stage+"\nRegistered: one capsule, one cart, one full-rig vessel. City-wide NPC/nav coverage absent."
	if current_record.state=="SAFE_HALT": status_text+="\nSTOP: "+str(current_record.halt_reason)+" "+str(current_record.coverage_issues)
	if label: label.text=status_text
	_update_visuals()
	var emitted=pending_events.duplicate(); pending_events.clear()
	for event_name in emitted: _event(event_name)
func _update_visuals():
	for ident in followers:
		var f=followers[ident]; f.node.global_transform=runtime.actors[ident].body.global_transform*Transform3D(Basis.IDENTITY,f.offset)
