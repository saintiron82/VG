extends RefCounted
## Reconstructed deterministic interpreter; all phase rules come from contract.json.
var contract: Dictionary
var state: String
var resume_state: String
var desired_mode = "road"
var halt_reason = ""
var last_now = null
var last_sequence = null
var last_timestamp = null
var last_snapshot = null
var active_vessels = {}
var exit_ledger = []
var road_streak = 0
var nav_streak = 0
var admissions = {"road":{"enabled":false,"generation":0},"navigation":{"enabled":false,"generation":0}}
var facts = {}
var valid = false
var last_reset_rejection = ""
var transition_serial = 0
func _init(data: Dictionary):
	contract = data.duplicate(true); state = contract.initial_state; resume_state = state
static func finite(v) -> bool: return (typeof(v)==TYPE_INT or typeof(v)==TYPE_FLOAT) and is_finite(float(v))
static func integer(v) -> bool: return finite(v) and v>=0 and floor(float(v))==float(v)
static func keys_equal(a: Dictionary,b: Array) -> bool:
	if a.size()!=b.size(): return false
	for k in b:
		if not a.has(k): return false
	return true
static func box_valid(b) -> bool:
	if not b is Dictionary: return false
	for k in ["min","max"]:
		if not b.get(k) is Array or b[k].size()!=3: return false
		for v in b[k]:
			if not finite(v): return false
	for i in range(3):
		if b.min[i]>b.max[i]: return false
	return true
static func intersects(a: Dictionary,b: Dictionary) -> bool:
	for i in range(3):
		if a.min[i]>b.max[i] or a.max[i]<b.min[i]: return false
	return true
static func rigid_valid(t) -> bool:
	if not t is Dictionary or not t.get("basis") is Array or t.basis.size()!=3 or not t.get("translation") is Array or t.translation.size()!=3: return false
	var b = t.basis
	for r in b:
		if not r is Array or r.size()!=3: return false
		for x in r:
			if not finite(x): return false
	for x in t.translation:
		if not finite(x): return false
	for i in range(3):
		for j in range(3):
			var dot = 0.0
			for k in range(3): dot += b[i][k]*b[j][k]
			if abs(dot-(1.0 if i==j else 0.0))>0.000001: return false
	var det = b[0][0]*(b[1][1]*b[2][2]-b[1][2]*b[2][1])-b[0][1]*(b[1][0]*b[2][2]-b[1][2]*b[2][0])+b[0][2]*(b[1][0]*b[2][1]-b[1][1]*b[2][0])
	return abs(det-1)<0.000001
static func transformed_box(b: Dictionary,t: Dictionary) -> Dictionary:
	var result = {"min":[INF,INF,INF],"max":[-INF,-INF,-INF]}
	for n in range(8):
		var p = []
		for i in range(3): p.append(b.max[i] if n & (1<<i) else b.min[i])
		for i in range(3):
			var v = t.translation[i]
			for j in range(3): v += t.basis[i][j]*p[j]
			result.min[i]=min(result.min[i],v); result.max[i]=max(result.max[i],v)
	return result
func _halt(reason: String):
	if state!="SAFE_HALT": resume_state=state; halt_reason=reason; transition_serial+=1
	state="SAFE_HALT"; road_streak=0; nav_streak=0
func _admissions():
	for k in admissions:
		var enabled = valid and halt_reason.is_empty() and ((k=="road" and state=="ROAD_OPEN" and desired_mode=="road") or (k=="navigation" and state=="NAVIGATION_OPEN" and desired_mode=="navigation"))
		if admissions[k].enabled!=enabled: admissions[k].enabled=enabled; admissions[k].generation+=1
func _fail(reason: String) -> Array: return [reason,false,{}]
func _validate(now,s) -> Array:
	if not s is Dictionary: return _fail("snapshot_not_object")
	for k in contract.sensor_contract.required_fields:
		if not s.has(k): return _fail("missing_required_field")
	if typeof(s.complete)!=TYPE_BOOL or not s.complete: return _fail("incomplete_coverage")
	if not s.coverage_ids is Array or s.coverage_ids.size()!=contract.required_coverage_ids.size(): return _fail("incomplete_coverage")
	var coverage = {}
	for k in s.coverage_ids:
		if not k is String or not contract.required_coverage_ids.has(k) or coverage.has(k): return _fail("incomplete_coverage")
		coverage[k]=true
	if s.geometry_sha256!=contract.geometry_pack.sha256: return _fail("geometry_mismatch")
	if not integer(s.sequence) or not integer(s.timestamp_ms): return _fail("invalid_sensor_time")
	if s.timestamp_ms>now: return _fail("future_sensor_time")
	if now-s.timestamp_ms>contract.sensor_max_age_ms: return _fail("stale_sensor")
	var fresh = last_sequence==null or s.sequence>last_sequence
	if last_sequence!=null:
		if s.sequence<last_sequence: return _fail("sequence_reversal")
		if s.sequence==last_sequence and s!=last_snapshot: return _fail("rewritten_sequence")
		if fresh and s.timestamp_ms<=last_timestamp: return _fail("timestamp_not_increasing")
	if typeof(s.emergency_stop)!=TYPE_BOOL: return _fail("invalid_emergency_signal")
	if not s.actuators is Dictionary or not keys_equal(s.actuators,contract.known_actuator_status.keys()): return _fail("unknown_actuator_feedback")
	for k in contract.known_actuator_status:
		if not contract.known_actuator_status[k].has(s.actuators[k]): return _fail("unknown_actuator_feedback")
	var a = s.actuators
	if (a.barriers=="open_locked" and (a.leaves!="seated_locked" or a.covers!="seated_locked")) or (a.leaves=="open_locked" and a.covers!="stowed_locked"): return _fail("contradictory_pose")
	if not s.admission_ack is Dictionary or not keys_equal(s.admission_ack,["road","navigation"]): return _fail("unknown_admission_feedback")
	for ack in s.admission_ack.values():
		if not ack is Dictionary or not keys_equal(ack,["closed","generation"]) or typeof(ack.closed)!=TYPE_BOOL or not integer(ack.generation): return _fail("unknown_admission_feedback")
	if not s.admission_ack.road.closed and not s.admission_ack.navigation.closed: return _fail("contradictory_admission_feedback")
	if not s.observations is Array or not s.pending_navigation_admissions is Array: return _fail("missing_occupancy")
	var observed = {}
	for o in s.observations:
		if not o is Dictionary or not o.get("id") is String or o.id.is_empty() or observed.has(o.id): return _fail("invalid_object_id")
		if not ["pedestrian","cart","vessel","other"].has(o.get("kind")): return _fail("unknown_object_kind")
		var b
		if o.kind=="vessel":
			if not o.get("asset_key") is String or not contract.vessel_catalog.has(o.asset_key) or not rigid_valid(o.get("transform_bridge_local")): return _fail("unknown_full_vessel_geometry")
			b=transformed_box(contract.vessel_catalog[o.asset_key],o.transform_bridge_local)
		else: b=o.get("bounds_bridge_local_m")
		if not box_valid(b): return _fail("invalid_object_bounds")
		observed[o.id]={"kind":o.kind,"bounds":b}
	var pending = {}
	for ident in s.pending_navigation_admissions:
		if not ident is String or not observed.has(ident) or observed[ident].kind!="vessel" or pending.has(ident): return _fail("unknown_pending_vessel")
		pending[ident]=true
	for ident in active_vessels:
		if not observed.has(ident) or observed[ident].kind!="vessel": return _fail("tracked_vessel_missing")
	return ["",fresh,observed]
func _hit(b: Dictionary,volume: String) -> bool:
	for q in contract.volumes[volume]:
		if intersects(b,q.bounds): return true
	return false
func _facts(s: Dictionary,observed: Dictionary) -> Dictionary:
	var a=s.actuators
	var f={"leaves_seated":a.leaves=="seated_locked","leaves_open":a.leaves=="open_locked","covers_seated":a.covers=="seated_locked","covers_stowed":a.covers=="stowed_locked","barriers_open":a.barriers=="open_locked","barriers_closed":a.barriers=="closed_locked","want_road":desired_mode=="road","want_navigation":desired_mode=="navigation","active_vessels_empty":active_vessels.is_empty(),"pending_vessels_empty":s.pending_navigation_admissions.is_empty()}
	for name in contract.required_coverage_ids:
		var clear=true
		for o in observed.values():
			if name=="road_span" and o.kind=="vessel": continue
			if _hit(o.bounds,name): clear=false
		f[{"road_span":"road_clear","barrier_sweep":"barrier_clear","mechanism_sweep":"mechanism_clear"}.get(name,name+"_clear")]=clear
	for k in admissions:
		var a2=s.admission_ack[k]; var t=admissions[k]
		f[k+"_admission_closed_ack"]=not t.enabled and a2.closed and a2.generation==t.generation
		f[k+"_admission_open_ack"]=t.enabled and not a2.closed and a2.generation==t.generation
	f.road_clear_stable=road_streak>=contract.clear_observation_frames_required
	f.navigation_clear_stable=nav_streak>=contract.clear_observation_frames_required
	return f
func _invariant_failure(phase: String,s: Dictionary,f: Dictionary) -> String:
	var r=contract.states[phase]
	for k in r.invariants:
		if not f.get(k,false): return "invariant:"+k
	for k in s.actuators:
		if ["moving","stopped"].has(s.actuators[k]) and not r.targets.has(k): return "unexpected_actuator_motion:"+k
	return ""
func step(now_ms,snapshot,commands=[]) -> Dictionary:
	last_reset_rejection=""; var fault=false
	if not integer(now_ms): valid=false; _halt("invalid_controller_clock"); _admissions(); return output()
	if last_now!=null and (now_ms<last_now or now_ms-last_now>contract.maximum_step_gap_ms): _halt("controller_clock_discontinuity"); fault=true
	last_now=now_ms
	var cv=commands is Array
	if cv:
		for c in commands:
			if not contract.commands.has(c): cv=false
	if not cv: _halt("invalid_command"); commands=[]; fault=true
	if (commands.has("request_road") and commands.has("request_navigation")) or (commands.has("reset") and commands.has("stop")): _halt("conflicting_commands"); fault=true
	if commands.has("request_road"): desired_mode="road"
	if commands.has("request_navigation"): desired_mode="navigation"
	if commands.has("stop"): _halt("manual_stop")
	var result=_validate(now_ms,snapshot); var reason=result[0]; var fresh=result[1]; var observed=result[2]
	valid=reason.is_empty()
	if not valid: _halt(reason); _admissions(); return output()
	var s=snapshot
	if fresh:
		last_sequence=s.sequence; last_timestamp=s.timestamp_ms; last_snapshot=s.duplicate(true)
		for ident in observed:
			var o=observed[ident]
			if o.kind=="vessel":
				if _hit(o.bounds,"navigation_passage"): active_vessels[ident]=true
				elif active_vessels.has(ident): active_vessels.erase(ident); exit_ledger.append({"id":ident,"sequence":s.sequence,"full_bounds_bridge_local_m":o.bounds})
	if s.emergency_stop: _halt("emergency_stop")
	var opposite={"ROAD_OPEN":"navigation","NAVIGATION_OPEN":"road"}.get(state,"")
	if not opposite.is_empty():
		var a=s.admission_ack[opposite]; var t=admissions[opposite]
		if t.enabled or not a.closed or a.generation!=t.generation: _halt("opposite_admission_not_secured")
	_admissions(); var f=_facts(s,observed)
	if fresh:
		road_streak=road_streak+1 if state=="ROAD_DRAIN" and f.road_clear and f.road_admission_closed_ack else 0
		nav_streak=nav_streak+1 if state=="NAVIGATION_DRAIN" and f.navigation_passage_clear and f.active_vessels_empty and f.pending_vessels_empty and f.navigation_admission_closed_ack else 0
	f=_facts(s,observed)
	if state=="SAFE_HALT":
		if commands.has("reset") and not commands.has("stop") and not s.emergency_stop and not fault:
			var why=_invariant_failure(resume_state,s,f)
			if why.is_empty() and f.road_admission_closed_ack and f.navigation_admission_closed_ack:
				state=resume_state; halt_reason=""; transition_serial+=1; _admissions(); facts=_facts(s,observed); return output(true)
			last_reset_rejection=why if not why.is_empty() else "admission_closure_not_acknowledged"
		facts=f; return output()
	var why=_invariant_failure(state,s,f)
	if not why.is_empty(): _halt(why); _admissions(); facts=f; return output()
	var r=contract.states[state]; var all_guards=true
	for k in r.guards:
		if not f.get(k,false): all_guards=false
	if all_guards:
		var nxt=r.next; why=_invariant_failure(nxt,s,f)
		if not why.is_empty(): _halt(why)
		else:
			state=nxt; transition_serial+=1
			if nxt=="ROAD_DRAIN": road_streak=0
			if nxt=="NAVIGATION_DRAIN": nav_streak=0
	_admissions(); facts=_facts(s,observed); return output()
func output(suppress_motion=false) -> Dictionary:
	var safe=valid and state!="SAFE_HALT"
	var road=safe and state=="ROAD_OPEN" and facts.get("road_admission_open_ack",false) and facts.get("navigation_admission_closed_ack",false)
	var nav=safe and state=="NAVIGATION_OPEN" and facts.get("navigation_admission_open_ack",false) and facts.get("road_admission_closed_ack",false)
	var active=active_vessels.keys(); active.sort()
	return {"state":state,"desired_mode":desired_mode,"halt_reason":halt_reason,"reset_rejection":last_reset_rejection,"transition_serial":transition_serial,"road_enabled":road,"navigation_enabled":nav,"road_exit_only":safe and state=="ROAD_DRAIN","navigation_exit_only":safe and state=="NAVIGATION_DRAIN","admission_commands":admissions.duplicate(true),"actuator_targets":contract.states[state].targets.duplicate(true) if safe and not suppress_motion else {},"stop_all_actuators":not safe or suppress_motion,"active_vessel_ids":active,"exit_ledger":exit_ledger.duplicate(true),"clear_frames":{"road":road_streak,"navigation":nav_streak},"sensor_valid":valid}
