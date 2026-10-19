extends SceneTree
const A=preload("res://VisualAddendum.gd")
var checks:int=0
var failures:int=0
func check(value:bool,label:String)->void:
	checks+=1
	if not value:failures+=1;push_error(label)
func base()->Dictionary:return {"common_assets":{"existing":{"render_path":"existing.json","render_sha256":"a"}},"common_instances":[{"id":"base","asset_key":"existing","position_m":[1,2,3],"yaw_rad":0,"palette_id":"base"}],"inspection_cameras":{}}
func write_pack(pack:Dictionary)->Dictionary:
	var root:String=ProjectSettings.globalize_path("user://r9_addendum_test")
	DirAccess.make_dir_recursive_absolute(root)
	var f:=FileAccess.open(root+"/pack.json",FileAccess.WRITE);f.store_string(JSON.stringify(pack));f.close()
	return {"root":root,"index":{"schema":"riverstone.city.visual_pack_index.v1","base_scene_sha256":"base_sha","packs":[{"path":"pack.json","sha256":FileAccess.get_sha256(root+"/pack.json")}]}}
func pack()->Dictionary:return {"schema":"riverstone.city.visual_addendum.v1","base_scene_sha256":"base_sha","common_assets":{},"add_instances":[{"id":"new","asset_key":"existing","position_m":[1,6,3],"yaw_rad":0,"palette_id":"base","scale":[1,1,1]}],"remove_instance_ids":[]}
func _initialize()->void:
	check(A.finite_vector([1,2,3],3),"finite vector")
	check(not A.finite_vector([1,NAN,3],3),"reject NaN")
	check(not A.finite_vector([1,"2",3],3),"reject numeric string")
	var d:Dictionary=base();check(A.apply_to_scene(d,{},"base_sha","").status=="fail","reject identity")
	check(d.common_instances.size()==1,"invalid no mutation")
	var p:Dictionary=pack();var w:Dictionary=write_pack(p);d=base()
	var result:Dictionary=A.apply_to_scene(d,w.index,"base_sha",w.root)
	check(result.status=="pass" and d.common_instances.size()==2,"valid common append")
	p=pack();p.add_instances[0].id="base";w=write_pack(p);d=base();check(A.apply_to_scene(d,w.index,"base_sha",w.root).status=="fail" and d.common_instances.size()==1,"reject duplicate atomic")
	p=pack();p.add_instances[0].scale=[2,1,1];w=write_pack(p);d=base();check(A.apply_to_scene(d,w.index,"base_sha",w.root).status=="fail","no mesh scaling")
	p=pack();p.common_assets={"existing":{"render_path":"different.json","render_sha256":"bad"}};w=write_pack(p);d=base();check(A.apply_to_scene(d,w.index,"base_sha",w.root).status=="fail","asset conflict")
	p=pack();p.remove_instance_ids=["missing"];w=write_pack(p);d=base();check(A.apply_to_scene(d,w.index,"base_sha",w.root).status=="fail","unknown removal")
	p=pack();p.add_instances[0].asset_key="missing";w=write_pack(p);d=base();check(A.apply_to_scene(d,w.index,"base_sha",w.root).status=="fail" and d.common_instances.size()==1,"unresolved asset atomic")
	p=pack();w=write_pack(p);w.index.packs[0].sha256="bad";d=base();check(A.apply_to_scene(d,w.index,"base_sha",w.root).status=="fail","pack hash mismatch")
	# A roof replacement must retain identity/pose and bind its voxel parity proof.
	p=pack();p.add_instances=[];p.common_assets={"revised":{"render_path":"revised.json","render_sha256":"b"}};w=write_pack(p)
	var proof:=FileAccess.open(w.root+"/proof.json",FileAccess.WRITE);proof.store_string("{\"parity\":true}");proof.close()
	var replacement:Dictionary={"id":"base","expected_asset_key":"existing","expected_position_m":[1,2,3],"expected_yaw_rad":0,"asset_key":"revised","palette_id":"roof","proof_path":"proof.json","proof_sha256":FileAccess.get_sha256(w.root+"/proof.json")}
	p.replace_instances=[replacement];w=write_pack(p);d=base();result=A.apply_to_scene(d,w.index,"base_sha",w.root)
	check(result.status=="pass" and d.common_instances.size()==1 and d.common_instances[0].id=="base" and d.common_instances[0].asset_key=="revised" and d.common_instances[0].position_m==[1,2,3],"replacement retains ID/pose/count")
	p.replace_instances[0].expected_position_m=[1,2,4];w=write_pack(p);d=base();result=A.apply_to_scene(d,w.index,"base_sha",w.root);check(result.status=="fail" and d.common_instances[0].asset_key=="existing","replacement pose mismatch atomic")
	p.replace_instances[0].expected_position_m=[1,2,3];p.replace_instances[0].proof_sha256="bad";w=write_pack(p);d=base();check(A.apply_to_scene(d,w.index,"base_sha",w.root).status=="fail","replacement proof mismatch")
	p.replace_instances[0].proof_sha256=FileAccess.get_sha256(w.root+"/proof.json");p.remove_instance_ids=["base"];w=write_pack(p);d=base();check(A.apply_to_scene(d,w.index,"base_sha",w.root).status=="fail","replacement removal conflict")
	# A later pack may retire an earlier addendum's merlon when a true gate replaces its curtain.
	p=pack();w=write_pack(p)
	var first:=FileAccess.open(w.root+"/first.json",FileAccess.WRITE);first.store_string(FileAccess.get_file_as_string(w.root+"/pack.json"));first.close()
	var first_sha:String=FileAccess.get_sha256(w.root+"/first.json")
	p=pack();p.add_instances=[];p.remove_instance_ids=["new"];w=write_pack(p);w.index.packs.push_front({"path":"first.json","sha256":first_sha});d=base()
	result=A.apply_to_scene(d,w.index,"base_sha",w.root)
	check(result.status=="pass" and d.common_instances.size()==1 and d.common_instances[0].id=="base","later pack retires earlier addition atomically")

	print("PASS " if failures==0 else "FAIL ",checks," visual addendum checks; failures=",failures);quit(0 if failures==0 else 1)
