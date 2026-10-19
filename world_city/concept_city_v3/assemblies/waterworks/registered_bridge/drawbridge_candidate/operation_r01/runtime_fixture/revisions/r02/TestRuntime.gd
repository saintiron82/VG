extends SceneTree
const World=preload("RuntimeWorld.gd")
var world
var now=0
var failures=[]
var trace=[]
var assertions=0
var last={}
func _initialize(): call_deferred("run")
func check(ok: bool,label: String):
	assertions+=1
	if not ok: failures.append(label); print("FAIL ",label)
func fresh_world():
	if is_instance_valid(world): world.queue_free(); await process_frame; await physics_frame
	world=World.new(); root.add_child(world); check(world.configure("res://runtime_fixture/revisions/r02/contract.json",ProjectSettings.globalize_path("res://../resolved_placements.json")),"configuration"); now=0
	await physics_frame; await physics_frame
func tick(commands: Array=[]) -> Dictionary:
	await physics_frame
	now+=100; last=world.tick(now,commands); trace.append({"now_ms":now,"state":last.operation.controller.state,"halt_reason":last.operation.controller.halt_reason,"road_enabled":last.operation.controller.road_enabled,"navigation_enabled":last.operation.controller.navigation_enabled,"pose":last.operation.pose_parameters,"coverage_issues":last.coverage_issues,"observations":last.snapshot.observations,"exit_permission_ids":last.exit_permission_ids}); return last
func until_state(wanted: String,limit=400) -> bool:
	for i in range(limit):
		var out=await tick()
		if out.operation.controller.state=="SAFE_HALT": print("UNEXPECTED_HALT ",out.operation.controller.halt_reason," ",out.coverage_issues); return false
		if wanted=="ROAD_GRANTED" and out.operation.controller.road_enabled: return true
		if wanted=="NAV_GRANTED" and out.operation.controller.navigation_enabled: return true
		if out.operation.controller.state==wanted: return true
	return false
func run():
	await fresh_world()
	world.add_actor("PEDESTRIAN","pedestrian",Vector3(0,4,0)); world.add_actor("WAITING_CART","cart",Vector3(-27,4,0)); world.add_actor("RIGGED_BARGE","vessel",Vector3(-2.5,-0.9,-70)); world.add_actor("WAITING_BARGE","vessel",Vector3(-2.5,-0.9,-85))
	check(await until_state("ROAD_GRANTED"),"fresh road grant"); await tick(["request_navigation"]); await tick(); check(last.operation.controller.state=="ROAD_DRAIN","pedestrian holds drain")
	var hit=world.move_actor("WAITING_CART",Vector3(20,0,0)); check(hit!=null and world.pose("WAITING_CART").origin.x < -22.7,"physical gate blocks new cart")
	for i in range(4): await tick()
	check(last.operation.controller.state=="ROAD_DRAIN" and world.adapter.leaf_angle==0,"time cannot lift occupied span")
	world.move_actor("PEDESTRIAN",Vector3(32,0,0)); check(world.pose("PEDESTRIAN").origin.x>30,"incumbent pedestrian may leave")
	check(await until_state("NAV_GRANTED"),"guarded navigation grant"); check(not world.exit_permissions.road.has("PEDESTRIAN"),"pedestrian exit revokes exception")
	world.move_actor("RIGGED_BARGE",Vector3(0,0,70)); await tick(); check(world.adapter.controller.active_vessels.has("RIGGED_BARGE"),"actual full rig tracked")
	await tick(["request_road"]); await tick(); hit=world.move_actor("WAITING_BARGE",Vector3(0,0,60)); check(hit!=null and world.pose("WAITING_BARGE").origin.z < -57.2,"navigation gate blocks new rig")
	world.move_actor("RIGGED_BARGE",Vector3(0,0,36))
	for i in range(5): await tick()
	check(last.operation.controller.state=="NAVIGATION_DRAIN" and world.adapter.leaf_angle==90,"origin outside cannot hide stern")
	world.move_actor("RIGGED_BARGE",Vector3(0,0,25)); check(world.pose("RIGGED_BARGE").origin.z>60,"incumbent vessel may exit")
	check(await until_state("ROAD_GRANTED"),"complete road-nav-road cycle"); check(not world.exit_permissions.navigation.has("RIGGED_BARGE"),"full rig exit revokes exception"); check(world.adapter.controller.exit_ledger.size()==1,"geometric exit ledger")
	hit=world.move_actor("RIGGED_BARGE",Vector3(0,0,-40)); check(hit!=null and world.pose("RIGGED_BARGE").origin.z>57.2,"exited vessel cannot re-enter")
	await tick(["request_navigation"]); check(await until_state("LEAVES_RAISING"),"second guarded lift")
	world.actors.WAITING_CART.body.global_transform=world.frame*Transform3D(Basis.IDENTITY,Vector3(0,4,0)); var before=world.adapter.leaf_angle; await tick(); check(last.operation.controller.state=="SAFE_HALT" and world.adapter.leaf_angle==before,"cart intrusion freezes pose")
	await fresh_world(); check(await until_state("ROAD_GRANTED"),"empty registered world opens")
	var rogue=CharacterBody3D.new(); rogue.collision_layer=0; rogue.collision_mask=0; var cs=CollisionShape3D.new(); cs.shape=BoxShape3D.new(); rogue.add_child(cs); world.add_child(rogue); rogue.global_transform=world.frame*Transform3D(Basis.IDENTITY,Vector3(0,4,0)); await tick(); check(last.operation.controller.state=="SAFE_HALT" and not last.snapshot.complete,"unknown layer-zero actor halts")
	await fresh_world(); world.add_actor("P","pedestrian",Vector3(30,4,0)); await tick(); world.actors.erase("P"); await tick(); check(last.operation.controller.state=="SAFE_HALT","missing registry halts")
	await fresh_world(); world.add_actor("C","cart",Vector3(30,4,0)); await tick(); world.actors.C.body.collision_mask=0; await tick(); check(last.operation.controller.state=="SAFE_HALT","mask mismatch halts")
	await fresh_world(); world.add_actor("V","vessel",Vector3(-2.5,-0.9,-70)); await tick(); world.actors.V.shape.shape.size=Vector3(5.5,2,24); await tick(); check(last.operation.controller.state=="SAFE_HALT","hull-only replacement halts")
	await fresh_world(); await tick(); world.trusted_actuator_feedback=false; await tick(); check(last.operation.controller.state=="SAFE_HALT","unknown lock halts")
	await fresh_world(); check(await until_state("ROAD_GRANTED"),"opens before opposite gate test"); world.gates.navigation[0].shape.disabled=true; await tick(); check(last.operation.controller.state=="SAFE_HALT","unexpected opposite gate opening halts")
	await fresh_world(); world.add_actor("C","cart",Vector3(-30,4,0)); await tick(); world.actors.C.body.add_collision_exception_with(world.gates.road[0].body); await tick(); check(last.operation.controller.state=="SAFE_HALT","unauthorized gate collision exception halts")
	await fresh_world(); world.add_actor("P","pedestrian",Vector3(0,4,0)); world.coverage_query_limit=1; await tick(); check(last.operation.controller.state=="SAFE_HALT","query saturation cannot claim completeness")
	await fresh_world(); await tick(); world.volumes.regions.road_span[0].get_child(0).shape.size=Vector3(1,1,1); await tick(); check(last.operation.controller.state=="SAFE_HALT","changed sensor volume halts")
	await fresh_world(); await tick(); var repeated=world.tick(now+1,[]); check(repeated.operation.controller.state=="SAFE_HALT","duplicate physics frame cannot become fresh clear observation")
	await fresh_world(); await tick(); world.gates.road[0].body.collision_mask=0; await tick(); check(last.operation.controller.state=="SAFE_HALT","changed gate collision mask halts")
	await fresh_world(); world.add_actor("TAIL","vessel",Vector3(-2.5,-0.9,-70)); check(await until_state("ROAD_GRANTED"),"r02 road start"); await tick(["request_navigation"]); check(await until_state("NAV_GRANTED"),"r02 navigation start"); world.move_actor("TAIL",Vector3(0,0,70)); await tick(); await tick(["request_road"]); world.move_actor("TAIL",Vector3(0,0,38))
	for i in range(8): await tick()
	check(last.operation.controller.state=="NAVIGATION_DRAIN" and world.adapter.leaf_angle==90,"Z38 outer incumbent cannot authorize lowering")
	world.move_actor("TAIL",Vector3(0,0,-38)); await tick(); check(last.operation.controller.state=="NAVIGATION_DRAIN" and world.adapter.leaf_angle==90,"incumbent reversal remains under fully open locked leaves")
	world.move_actor("TAIL",Vector3(0,0,61)); check(await until_state("ROAD_GRANTED"),"lower only after full outer exit")
	var reversed=world.move_actor("TAIL",Vector3(0,0,-61)); check(reversed!=null,"outer-exited rig physically blocked on reversal")
	await fresh_world(); world.add_actor("UNEXPECTED_RIG","vessel",Vector3(-2.5,-0.9,0)); await tick(); check(last.operation.controller.state=="SAFE_HALT","stable road vessel intrusion stop")
	var report={"valid":failures.is_empty(),"assertions":assertions,"failures":failures,"ticks":trace.size(),"geometry_sha256":world.contract.geometry_pack.sha256,"scope":"Reconstructed closed-world physics fixture, no city population/nav integration","trace":trace}
	var file=FileAccess.open("res://runtime_fixture/revisions/r02/runtime_report.json",FileAccess.WRITE); file.store_string(JSON.stringify(report,"\t")+"\n"); file.close(); print(JSON.stringify({"valid":failures.is_empty(),"assertions":assertions,"failures":failures,"ticks":trace.size()})); quit(0 if failures.is_empty() else 1)
