extends RefCounted
## Authoritative live scheduler. One shared state machine; residents are records, not Nodes.
## Integer ticks are logical seconds. Rendering and collision controllers are separate consumers.
const SCHEMA := "riverstone.residents.state.v1"
var s: Dictionary = {}

func initialize(config: Dictionary) -> void:
	s = {"schema":SCHEMA,"tick":0,"seed":int(config.get("seed",1)),"config":config.duplicate(true),
		"facilities":{},"households":{},"residents":{},"jobs":{},"job_sequence":0,
		"reservations":{"workers":{},"goods":{},"destinations":{}},"events":[],
		"metrics":{"produced":{},"consumed":{},"transferred":{},"failed_attempts":0,"completed_jobs":0},
		"unmet":{},"population_requested":int(config.get("population",0)),"population_created":0}
	for f in config.get("facilities",[]):
		register_facility(f, false)
	_generate_population()
	_house_and_employ()
	_refresh_unmet()

func _keys(d: Dictionary) -> Array:
	var keys := d.keys()
	keys.sort()
	return keys

func _choice(key: String, count: int) -> int:
	return int((str(s.seed)+":"+key).sha256_text().substr(0,7).hex_to_int()) % count

func register_facility(spec: Dictionary, reconcile: bool = true) -> void:
	assert(not s.facilities.has(str(spec.id)), "Facility IDs are immutable and unique")
	var f := spec.duplicate(true)
	f["inventory"] = f.get("inventory", {}).duplicate(true)
	f["job_slots"] = f.get("job_slots", {}).duplicate(true)
	f["storage_capacity"] = int(f.get("storage_capacity",100))
	f["activity_slots"] = int(f.get("activity_slots",1))
	f["beds"] = int(f.get("beds",0))
	f["household_slots"] = int(f.get("household_slots",0))
	f["last_recipe_tick"] = -1000000
	s.facilities[str(f.id)] = f
	if reconcile:
		_house_and_employ()
		_refresh_unmet()

func _generate_population() -> void:
	var index := 0
	while int(s.population_created) < int(s.population_requested):
		var hid := "HH_%05d" % index
		var size := mini(2 + _choice(hid+":size",3), int(s.population_requested)-int(s.population_created))
		var family := ["Miller","Reed","Stone","Baker","Wood","Brook","Carter","Ash"][_choice(hid+":surname",8)]
		var h := {"id":hid,"members":[],"home_id":"","next_meal_tick":int(s.config.get("first_meal_tick",20)),"meals_completed":0,"unmet_food":0}
		for member in range(size):
			var rid := "%s:R%d" % [hid,member]
			var age := 23 + _choice(rid+":age",30) if member < 2 else 4 + _choice(rid+":age",13)
			var given := ["Ada","Bryn","Cora","Darin","Elin","Finn","Gwen","Hugh","Ira","Joss","Kira","Leon"][_choice(rid+":name",12)]
			var r := {"id":rid,"name":given+" "+family,"age":age,"household_id":hid,"family_role":"adult" if member<2 else "child",
				"parents":[] if member<2 else [hid+":R0",hid+":R1"],"partner_id":hid+":R"+str(1-member) if member<2 and size>1 else "",
				"home_id":"","workplace_id":"","occupation":"unassigned","location":"","position_m":[],
				"available":true,"activity":"unhoused","current_job":"","hunger":0,"appearance_seed":_choice(rid+":appearance",2147483647)}
			s.residents[rid]=r
			h.members.append(rid)
			s.population_created += 1
		s.households[hid]=h
		index += 1

func _house_and_employ() -> void:
	var used_beds: Dictionary = {}
	var used_homes: Dictionary = {}
	var used_jobs: Dictionary = {}
	for hid in _keys(s.households):
		var h: Dictionary = s.households[hid]
		if h.home_id != "":
			used_beds[h.home_id]=int(used_beds.get(h.home_id,0))+h.members.size()
			used_homes[h.home_id]=int(used_homes.get(h.home_id,0))+1
	for hid in _keys(s.households):
		var h: Dictionary = s.households[hid]
		if h.home_id != "": continue
		for fid in _keys(s.facilities):
			var f: Dictionary = s.facilities[fid]
			if int(f.beds)-int(used_beds.get(fid,0)) < h.members.size() or int(f.household_slots)<=int(used_homes.get(fid,0)): continue
			h.home_id=fid
			used_beds[fid]=int(used_beds.get(fid,0))+h.members.size()
			used_homes[fid]=int(used_homes.get(fid,0))+1
			for rid in h.members:
				var r: Dictionary = s.residents[rid]
				r.home_id=fid; r.location=f.anchor; r.position_m=f.get("position_m",[]).duplicate(); r.activity="at_home"
			break
	for rid in _keys(s.residents):
		var r: Dictionary = s.residents[rid]
		if r.workplace_id != "":
			var key: String = r.workplace_id+":"+r.occupation
			used_jobs[key]=int(used_jobs.get(key,0))+1
	for fid in _keys(s.facilities):
		var f: Dictionary = s.facilities[fid]
		for role in _keys(f.job_slots):
			var key: String = fid+":"+role
			for rid in _keys(s.residents):
				if int(used_jobs.get(key,0))>=int(f.job_slots[role]): break
				var r: Dictionary = s.residents[rid]
				if r.home_id=="" or int(r.age)<18 or r.workplace_id!="": continue
				r.workplace_id=fid; r.occupation=role
				used_jobs[key]=int(used_jobs.get(key,0))+1

func step(count: int = 1) -> void:
	for _i in range(count):
		s.tick += 1
		_advance_running()
		if int(s.tick) % int(s.config.get("planning_interval_ticks",5)) == 0:
			_emit_jobs()
		for jid in _keys(s.jobs):
			var j: Dictionary = s.jobs[jid]
			if j.status in ["pending","blocked"] and int(j.retry_at)<=int(s.tick): _try_start(j)
		_refresh_unmet()
		if bool(s.config.get("assert_invariants",false)): assert(invariant_errors().is_empty(),str(invariant_errors()))

func _active_key(key: String) -> String:
	for jid in _keys(s.jobs):
		var j: Dictionary = s.jobs[jid]
		if j.key==key and j.status in ["pending","blocked","running"]: return jid
	return ""

func _new_job(kind: String, key: String, data: Dictionary, deps: Array = []) -> String:
	var found := _active_key(key)
	if found!="": return found
	s.job_sequence += 1
	var jid := "J_%08d" % int(s.job_sequence)
	var j := {"id":jid,"key":key,"kind":kind,"status":"pending","created_tick":int(s.tick),"dependencies":deps.duplicate(),
		"worker_id":"","attempts":0,"retry_at":int(s.tick),"reason":"","failed_workers":[],"reservations":{},"legs":[],"route_ids":[]}
	j.merge(data,true)
	s.jobs[jid]=j
	_event("job_emitted", {"job_id":jid,"kind":kind})
	return jid

func _production_job(fid: String) -> String:
	var f: Dictionary = s.facilities[fid]
	if not f.has("recipe"): return ""
	var recipe: Dictionary = f.recipe
	return _new_job("produce","produce:"+fid,{"source":fid,"destination":fid,"inputs":recipe.get("inputs",{}).duplicate(),
		"outputs":recipe.outputs.duplicate(),"duration":int(recipe.get("duration_ticks",5)),"role":recipe.get("role","producer"),"workplace":fid})

func _supply_job(fid: String, item: String, amount: int) -> String:
	var f: Dictionary = s.facilities[fid]
	var supplier := str(f.get("suppliers",{}).get(item,""))
	if supplier=="" or not s.facilities.has(supplier): return ""
	var deps: Array = []
	if available_goods(supplier,item)<amount:
		var producer := _production_job(supplier)
		if producer!="": deps.append(producer)
	return _new_job("transport","transport:"+fid+":"+item,{"source":supplier,"destination":fid,"inputs":{item:amount},
		"outputs":{item:amount},"duration":int(f.get("unload_ticks",2)),"role":"carrier","workplace":""},deps)

func _emit_jobs() -> void:
	for fid in _keys(s.facilities):
		var f: Dictionary = s.facilities[fid]
		if f.has("recipe") and int(s.tick)-int(f.last_recipe_tick)>=int(f.recipe.get("interval_ticks",5)):
			for item in _keys(f.recipe.outputs):
				if available_goods(fid,item)<int(f.get("target_stock",{}).get(item,int(f.recipe.outputs[item]))):
					_production_job(fid)
		for item in _keys(f.get("target_stock",{})):
			if f.has("recipe") and f.recipe.outputs.has(item): continue
			var deficit := int(f.target_stock[item])-available_goods(fid,item)
			if deficit>0: _supply_job(fid,item,mini(deficit,int(f.get("delivery_batch",4))))
	for hid in _keys(s.households):
		var h: Dictionary = s.households[hid]
		if h.home_id=="" or int(s.tick)<int(h.next_meal_tick): continue
		var home: Dictionary = s.facilities[h.home_id]
		var amount: int = h.members.size()
		var deps: Array = []
		if available_goods(h.home_id,"food")<amount:
			var market := str(home.get("suppliers",{}).get("food",""))
			if s.facilities.has(market):
				var shop_deps: Array = []
				if available_goods(market,"food")<amount:
					var delivery := _supply_job(market,"food",maxi(amount,int(s.facilities[market].get("delivery_batch",4))))
					if delivery!="": shop_deps.append(delivery)
				var shopping := _new_job("shop","shop:"+hid,{"source":market,"destination":h.home_id,"inputs":{"food":amount},"outputs":{"food":amount},
					"duration":2,"role":"household","household_id":hid,"workplace":""},shop_deps)
				deps.append(shopping)
		_new_job("consume","consume:"+hid,{"source":h.home_id,"destination":h.home_id,"inputs":{"food":amount},"outputs":{},"duration":1,
			"role":"household","household_id":hid,"workplace":""},deps)

func available_goods(fid: String, item: String) -> int:
	return int(s.facilities[fid].inventory.get(item,0))-int(s.reservations.goods.get(fid+":"+item,0))

func _sum(d: Dictionary) -> int:
	var result := 0
	for v in d.values(): result += int(v)
	return result

func _route_allowed(edge: Dictionary) -> bool:
	if edge.get("blocked",false): return false
	if s.config.get("mode","")=="logical_fixture" and edge.get("evidence","")=="synthetic_fixture": return true
	if edge.get("evidence","")!="runtime_verified" or not edge.get("profile_sha256","").length()==64: return false
	if edge.get("source_hashes",{}) != s.config.get("active_source_hashes",{}): return false
	return edge.get("pedestrian",false)

func route(from: String, to: String) -> Dictionary:
	if from==to: return {"ok":true,"legs":[],"ticks":0,"route_ids":[]}
	if from=="" or to=="": return {"ok":false,"reason":"unhoused_or_missing_anchor"}
	var distance: Dictionary = {from:0}
	var paths: Dictionary = {from:[]}
	var open: Array = [from]
	var edges: Array = s.config.get("routes",[]).duplicate()
	edges.sort_custom(func(a,b): return str(a.id)<str(b.id))
	while not open.is_empty():
		open.sort_custom(func(a,b): return int(distance[a])<int(distance[b]) or (int(distance[a])==int(distance[b]) and str(a)<str(b)))
		var node: String = open.pop_front()
		if node==to:
			var ids: Array = []
			for edge in paths[node]: ids.append(edge.id)
			return {"ok":true,"legs":paths[node],"ticks":distance[node],"route_ids":ids}
		for edge in edges:
			if edge.from!=node or not _route_allowed(edge): continue
			var cost := int(distance[node])+maxi(1,int(edge.get("travel_ticks",1)))
			var end: String = edge.to
			if not distance.has(end) or cost<int(distance[end]):
				distance[end]=cost; paths[end]=paths[node].duplicate(); paths[end].append(edge.duplicate(true))
				if not open.has(end): open.append(end)
	return {"ok":false,"reason":"blocked_or_unverified_route"}

func _block(j: Dictionary, reason: String) -> void:
	j.status="blocked"; j.reason=reason; j.retry_at=int(s.tick)+int(s.config.get("retry_ticks",5))

func _eligible(r: Dictionary, j: Dictionary) -> bool:
	if not r.available or int(r.age)<18 or r.home_id=="" or s.reservations.workers.has(r.id) or j.failed_workers.has(r.id): return false
	if j.role=="household": return r.household_id==j.household_id
	return r.occupation==j.role and (j.workplace=="" or r.workplace_id==j.workplace)

func _try_start(j: Dictionary) -> void:
	for dep_id in j.dependencies:
		var dep: Dictionary = s.jobs[dep_id]
		if dep.status=="failed": _block(j,"dependency_failed:"+dep_id); return
		if dep.status!="completed": _block(j,"awaiting_dependency:"+dep_id); return
	for item in _keys(j.inputs):
		if available_goods(j.source,item)<int(j.inputs[item]): _block(j,"shortage:"+item); return
	var destination: Dictionary = s.facilities[j.destination]
	var reserved: Dictionary = s.reservations.destinations.get(j.destination,{"slots":0,"units":0})
	if int(reserved.slots)>=int(destination.activity_slots): _block(j,"destination_busy"); return
	var net_units := maxi(0,_sum(j.outputs)-(_sum(j.inputs) if j.source==j.destination else 0))
	if _sum(destination.inventory)+int(reserved.units)+net_units>int(destination.storage_capacity): _block(j,"destination_full"); return
	var selected: Dictionary = {}
	var itinerary: Array = []
	var travel_ticks := 0
	var had_candidate := false
	for rid in _keys(s.residents):
		var r: Dictionary = s.residents[rid]
		if not _eligible(r,j): continue
		had_candidate=true
		var commute := route(r.location,s.facilities[j.source].anchor)
		if not commute.ok: continue
		var delivery := route(s.facilities[j.source].anchor,destination.anchor)
		if not delivery.ok: continue
		selected=r; itinerary=commute.legs+delivery.legs; travel_ticks=int(commute.ticks)+int(delivery.ticks)
		break
	if selected.is_empty(): _block(j,"blocked_or_unverified_route" if had_candidate else "no_available_worker"); return
	# Commit all reservations only after every precondition succeeds.
	j.reservations={"goods":{},"destination_units":net_units}
	for item in _keys(j.inputs):
		var key: String = j.source+":"+item
		s.reservations.goods[key]=int(s.reservations.goods.get(key,0))+int(j.inputs[item])
		j.reservations.goods[key]=int(j.inputs[item])
	s.reservations.destinations[j.destination]={"slots":int(reserved.slots)+1,"units":int(reserved.units)+net_units}
	s.reservations.workers[selected.id]=j.id
	j.worker_id=selected.id; j.status="running"; j.reason=""; j.attempts+=1; j.start_tick=int(s.tick)
	j.end_tick=int(s.tick)+maxi(1,travel_ticks+int(j.duration)); j.travel_ticks=travel_ticks; j.legs=itinerary; j.route_ids=[]
	for leg in itinerary: j.route_ids.append(leg.id)
	selected.current_job=j.id; selected.activity="travel" if not itinerary.is_empty() else j.kind
	_event("job_started",{"job_id":j.id,"worker_id":selected.id,"route_ids":j.route_ids.duplicate()})

func _advance_running() -> void:
	for jid in _keys(s.jobs):
		var j: Dictionary = s.jobs[jid]
		if j.status!="running": continue
		var r: Dictionary = s.residents[j.worker_id]
		if not r.available:
			_fail_attempt(j,"worker_unavailable",true); continue
		var invalid := false
		for route_id in j.route_ids:
			var found := false
			for edge in s.config.routes:
				if edge.id==route_id:
					found=true
					if not _route_allowed(edge): invalid=true
			if not found: invalid=true
		if invalid: _fail_attempt(j,"route_invalidated",false); continue
		_update_logical_location(j,r)
		if int(s.tick)>=int(j.end_tick): _complete(j)

func _update_logical_location(j: Dictionary, r: Dictionary) -> void:
	var elapsed := int(s.tick)-int(j.start_tick)
	for leg in j.legs:
		var duration := maxi(1,int(leg.travel_ticks))
		if elapsed<duration:
			r.activity="travel"
			# No inferred coordinates: only the exact bound polyline can drive the view.
			r.position_m=_point_on_polyline(leg.get("points",[]),float(elapsed)/float(duration))
			return
		elapsed-=duration; r.location=leg.to
		if not leg.get("points",[]).is_empty(): r.position_m=leg.points[-1].duplicate()
	r.location=s.facilities[j.destination].anchor; r.activity=j.kind

func _point_on_polyline(points: Array, fraction: float) -> Array:
	if points.is_empty(): return []
	if points.size()==1: return points[0].duplicate()
	var lengths: Array = []; var total := 0.0
	for i in range(1,points.size()):
		var a := Vector3(float(points[i-1][0]),float(points[i-1][1]),float(points[i-1][2]))
		var b := Vector3(float(points[i][0]),float(points[i][1]),float(points[i][2]))
		var length := a.distance_to(b); lengths.append(length); total+=length
	var target := total*clampf(fraction,0.0,1.0)
	for i in range(lengths.size()):
		if target<=float(lengths[i]):
			var t := target/maxf(float(lengths[i]),0.000001)
			var result: Array = []
			for axis in range(3): result.append(lerpf(float(points[i][axis]),float(points[i+1][axis]),t))
			return result
		target-=float(lengths[i])
	return points[-1].duplicate()

func _release(j: Dictionary) -> void:
	if j.reservations.is_empty(): return
	for key in j.reservations.goods:
		s.reservations.goods[key]=int(s.reservations.goods[key])-int(j.reservations.goods[key])
		if int(s.reservations.goods[key])==0: s.reservations.goods.erase(key)
	var reserved: Dictionary = s.reservations.destinations[j.destination]
	reserved.slots-=1; reserved.units-=int(j.reservations.destination_units)
	if int(reserved.slots)==0: s.reservations.destinations.erase(j.destination)
	s.reservations.workers.erase(j.worker_id)
	var r: Dictionary = s.residents[j.worker_id]
	r.current_job=""; r.activity="idle"
	j.reservations={}

func _fail_attempt(j: Dictionary, reason: String, exclude_worker: bool) -> void:
	var worker: String = j.worker_id
	_release(j)
	if exclude_worker and not j.failed_workers.has(worker): j.failed_workers.append(worker)
	j.worker_id=""; j.legs=[]; j.route_ids=[]
	s.metrics.failed_attempts+=1
	_block(j,reason)
	_event("attempt_failed",{"job_id":j.id,"worker_id":worker,"reason":reason})

func _complete(j: Dictionary) -> void:
	for item in j.inputs: s.facilities[j.source].inventory[item]=int(s.facilities[j.source].inventory.get(item,0))-int(j.inputs[item])
	for item in j.outputs: s.facilities[j.destination].inventory[item]=int(s.facilities[j.destination].inventory.get(item,0))+int(j.outputs[item])
	if j.kind=="produce":
		s.facilities[j.source].last_recipe_tick=int(s.tick)
		for item in j.outputs: s.metrics.produced[item]=int(s.metrics.produced.get(item,0))+int(j.outputs[item])
	if j.kind in ["transport","shop"]:
		for item in j.outputs: s.metrics.transferred[item]=int(s.metrics.transferred.get(item,0))+int(j.outputs[item])
	if j.kind=="consume":
		var h: Dictionary = s.households[j.household_id]
		h.meals_completed+=1; h.next_meal_tick=int(s.tick)+int(s.config.get("meal_interval_ticks",120))
		for rid in h.members: s.residents[rid].hunger=0
		for item in j.inputs: s.metrics.consumed[item]=int(s.metrics.consumed.get(item,0))+int(j.inputs[item])
	s.residents[j.worker_id].location=s.facilities[j.destination].anchor
	_release(j)
	j.status="completed"; j.completed_tick=int(s.tick); j.reason=""; s.metrics.completed_jobs+=1
	_event("job_completed",{"job_id":j.id,"kind":j.kind})

func set_route_blocked(route_id: String, blocked: bool) -> void:
	for edge in s.config.routes:
		if edge.id==route_id: edge.blocked=blocked

func set_worker_available(resident_id: String, available: bool) -> void:
	s.residents[resident_id].available=available
	if available:
		for j in s.jobs.values(): j.failed_workers.erase(resident_id)

func _refresh_unmet() -> void:
	var unhoused := 0; var food := 0; var blocked: Dictionary = {}; var vacant: Dictionary = {}
	for h in s.households.values():
		if h.home_id=="": unhoused+=h.members.size()
		h.unmet_food=h.members.size() if int(s.tick)>=int(h.next_meal_tick) else 0
		food+=int(h.unmet_food)
		for rid in h.members: s.residents[rid].hunger=maxi(0,int(s.tick)-int(h.next_meal_tick))
	for j in s.jobs.values():
		if j.status=="blocked": blocked[j.reason]=int(blocked.get(j.reason,0))+1
	for f in s.facilities.values():
		for role in f.job_slots:
			var count := 0
			for r in s.residents.values():
				if r.workplace_id==f.id and r.occupation==role: count+=1
			if count<int(f.job_slots[role]): vacant[f.id+":"+role]=int(f.job_slots[role])-count
	s.unmet={"housing_residents":unhoused,"food_units_due":food,"blocked_jobs":blocked,"vacant_job_slots":vacant}

func _event(kind: String, detail: Dictionary) -> void:
	var event := {"tick":int(s.tick),"type":kind}; event.merge(detail); s.events.append(event)
	while s.events.size()>int(s.config.get("event_history_limit",2048)): s.events.pop_front()

func invariant_errors() -> Array:
	var errors: Array = []; var workers: Dictionary = {}; var goods: Dictionary = {}; var slots: Dictionary = {}; var units: Dictionary = {}
	for j in s.jobs.values():
		if j.status!="running":
			if not j.reservations.is_empty(): errors.append("inactive reservation:"+j.id)
			continue
		if workers.has(j.worker_id): errors.append("double worker:"+j.worker_id)
		workers[j.worker_id]=j.id
		for key in j.reservations.goods: goods[key]=int(goods.get(key,0))+int(j.reservations.goods[key])
		slots[j.destination]=int(slots.get(j.destination,0))+1
		units[j.destination]=int(units.get(j.destination,0))+int(j.reservations.destination_units)
	if workers!=s.reservations.workers: errors.append("worker reservation mismatch")
	if goods!=s.reservations.goods: errors.append("goods reservation mismatch")
	for fid in s.facilities:
		var f: Dictionary = s.facilities[fid]
		for item in f.inventory:
			if int(f.inventory[item])<0 or available_goods(fid,item)<0: errors.append("negative goods:"+fid+":"+item)
		if _sum(f.inventory)+int(units.get(fid,0))>int(f.storage_capacity): errors.append("storage overflow:"+fid)
		if int(slots.get(fid,0))>int(f.activity_slots): errors.append("destination oversubscription:"+fid)
		var expected: Dictionary = {"slots":int(slots.get(fid,0)),"units":int(units.get(fid,0))}
		if expected!=s.reservations.destinations.get(fid,{"slots":0,"units":0}): errors.append("destination reservation mismatch:"+fid)
	return errors

func save_json() -> String:
	var payload := JSON.stringify(s,"",true,true)
	return JSON.stringify({"schema":"riverstone.residents.save.v1","payload":payload,"sha256":payload.sha256_text()})

func restore_json(serialized: String) -> bool:
	var envelope = JSON.parse_string(serialized)
	if not envelope is Dictionary or envelope.get("schema","")!="riverstone.residents.save.v1": return false
	var payload: String = envelope.get("payload","")
	if payload.sha256_text()!=envelope.get("sha256",""): return false
	var state = JSON.parse_string(payload)
	if not state is Dictionary or state.get("schema","")!=SCHEMA: return false
	var previous := s
	s=state
	if not invariant_errors().is_empty(): s=previous; return false
	return true
