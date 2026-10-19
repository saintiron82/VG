extends Node3D
## Raw area absence is not complete coverage. Full registry/direct queries are required.
const Adapter=preload("OperationAdapter.gd")
var regions={}
func configure(contract: Dictionary,mask: int):
	for child in get_children(): child.queue_free()
	regions.clear(); transform=Adapter.rigid(contract.bridge_to_world)
	for family in contract.volumes:
		regions[family]=[]
		for q in contract.volumes[family]:
			var b=q.bounds; var a=Area3D.new(); a.collision_layer=0; a.collision_mask=mask; a.monitoring=true; a.monitorable=false
			var cs=CollisionShape3D.new(); var box=BoxShape3D.new(); box.size=Vector3(b.max[0]-b.min[0],b.max[1]-b.min[1],b.max[2]-b.min[2]); cs.shape=box
			a.position=Vector3((b.max[0]+b.min[0])*0.5,(b.max[1]+b.min[1])*0.5,(b.max[2]+b.min[2])*0.5); a.add_child(cs); add_child(a); regions[family].append(a)
func observed_body_ids() -> Dictionary:
	var result={}
	for family in regions:
		var ids={}
		for area in regions[family]:
			for body in area.get_overlapping_bodies(): ids[str(body.get_instance_id())]=true
		result[family]=ids.keys()
	return {"complete":false,"families":result,"reason":"Raw overlap lists cannot attest whole-world registry, rig tracking or fresh lock coverage."}
