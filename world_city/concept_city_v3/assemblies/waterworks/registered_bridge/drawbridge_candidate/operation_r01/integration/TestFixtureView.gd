extends SceneTree
const View=preload("BridgeFixtureView.gd")
class ProbeMechanism extends Node3D:
	var meshes={}
	var inspection_vessel: MeshInstance3D
	var cycle_enabled=true
	var state_name=""
	var pose={}
	func apply_state(s: Dictionary): pose=s.duplicate(true)
var helper
var events=[]
var start_ms=0
var done=false
var source_hash=""
func _initialize(): call_deferred("run")
func native_mesh(path: String,expected: String) -> ArrayMesh:
	assert(FileAccess.get_sha256(path)==expected)
	var d=JSON.parse_string(FileAccess.get_file_as_string(path)); var vertices=PackedVector3Array(); var normals=PackedVector3Array()
	for group in d.groups:
		for q in group.quads:
			var p=[]
			for v in q: p.append(Vector3(v[0],v[1],v[2]))
			var n=(p[1]-p[0]).cross(p[2]-p[0]).normalized()
			for i in [0,2,1,0,3,2]: vertices.append(p[i]); normals.append(n)
	var a=[]; a.resize(Mesh.ARRAY_MAX); a[Mesh.ARRAY_VERTEX]=vertices; a[Mesh.ARRAY_NORMAL]=normals
	var mesh=ArrayMesh.new(); mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,a); return mesh
func run():
	var repo=OS.get_environment("RIVERSTONE_REPO_ROOT"); assert(not repo.is_empty())
	var base=repo+"/world_city/concept_city_v3/assemblies/waterworks/registered_bridge/drawbridge_candidate"
	var pack=JSON.parse_string(FileAccess.get_file_as_string(base+"/resolved_placements.json")); var asset=pack.assets.registered_port_rigged_barge_24m; source_hash=asset.render_sha256
	var bridge=ProbeMechanism.new(); root.add_child(bridge); bridge.meshes.registered_port_rigged_barge_24m=native_mesh(repo+"/"+asset.render_path,asset.render_sha256); bridge.inspection_vessel=MeshInstance3D.new(); bridge.add_child(bridge.inspection_vessel)
	helper=View.new(); root.add_child(helper); helper.fixture_event.connect(on_event)
	assert(helper.configure(bridge,repo,{"demonstration":true,"show_status_label":false})); start_ms=Time.get_ticks_msec()
func on_event(name: String,record: Dictionary):
	events.append({"name":name,"record":record})
	if name=="road_restored": finish(true,"")
func _process(_delta):
	if done or not is_instance_valid(helper) or not helper.configured: return
	if helper.current_record.get("state","")=="SAFE_HALT": finish(false,"unexpected halt: "+str(helper.current_record))
	elif Time.get_ticks_msec()-start_ms>100000: finish(false,"bounded 100 second demo timeout")
func finish(valid: bool,reason: String):
	if done: return
	done=true
	var report={"valid":valid,"reason":reason,"elapsed_ms":Time.get_ticks_msec()-start_ms,"events":events,"controller_states":helper.recorded_states,"native_vessel_render_sha256":source_hash,"native_vessel_vertices":helper.followers.FIXTURE_FULL_RIG.node.mesh.surface_get_array_len(0),"cart_physically_blocked":helper.cart_blocked,"final_state":helper.current_record,"scope":"Live engine-clock closed-world fixture and actual native rig mesh; ProbeMechanism captures source poses, no city NPC/nav registration"}
	var file=FileAccess.open("res://integration/view_test_report.json",FileAccess.WRITE); file.store_string(JSON.stringify(report,"\t")+"\n"); file.close(); print(JSON.stringify({"valid":valid,"reason":reason,"elapsed_ms":report.elapsed_ms,"events":events.size(),"cart_blocked":helper.cart_blocked})); quit(0 if valid else 1)
