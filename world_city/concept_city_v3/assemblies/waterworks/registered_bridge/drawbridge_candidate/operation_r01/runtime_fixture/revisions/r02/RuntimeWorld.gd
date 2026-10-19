extends "../../RuntimeWorld.gd"
## Bounded correction: full outer admission ownership and stable-road intrusion stop.
var operational_stop_reason=""
func configure(contract_path: String,pack_path: String,viewer=null) -> bool:
	var data=JSON.parse_string(FileAccess.get_file_as_string(contract_path))
	if not data is Dictionary or data.get("schema","")!="riverstone.drawbridge_operation.r02.outer_admission_ownership": return false
	return super.configure(contract_path,pack_path,viewer)
func observe(now_ms: int) -> Dictionary:
	var snapshot=super.observe(now_ms)
	operational_stop_reason=""
	# Until their whole envelope leaves the outer corridor, incumbents remain pending.
	for ident in exit_permissions.navigation:
		if not snapshot.pending_navigation_admissions.has(ident): snapshot.pending_navigation_admissions.append(ident)
	if adapter.controller.state=="ROAD_OPEN":
		for o in snapshot.observations:
			if o.kind!="vessel": continue
			var full=Controller.transformed_box(contract.vessel_catalog[o.asset_key],o.transform_bridge_local)
			if adapter.controller._hit(full,"navigation_actuation"):
				snapshot.emergency_stop=true; operational_stop_reason="vessel_inside_closed_span_actuation_domain"
	return snapshot
