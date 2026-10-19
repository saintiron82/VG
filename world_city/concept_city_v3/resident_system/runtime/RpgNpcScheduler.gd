extends RefCounted
## Live, data-driven RPG NPCs. Economy/production simulation is deliberately absent.
## State changes occur at schedule/route/interaction events; frame rendering only samples motion.
const SCHEMA := "riverstone.rpg_npcs.state.v1"
var s: Dictionary = {}
var edge_index: Dictionary = {}
var outgoing: Dictionary = {}

func initialize(config: Dictionary) -> void:
	s={"schema":SCHEMA,"tick":int(config.get("start_tick",0)),"seed":int(config.get("seed",1)),"config":config.duplicate(true),
		"npcs":{},"facilities":{},"agenda":[],"quest_states":{},"events":[],"metrics":{"events_processed":0,"route_searches":0,"arrivals":0}}
	_index_routes()
	for spec in config.get("facilities",[]): register_facility(spec,false)
	for id in _keys(s.npcs): _schedule(s.npcs[id],int(s.tick))
	advance_to(int(s.tick))

func _keys(d: Dictionary) -> Array:
	var result := d.keys(); result.sort(); return result

func _choice(key: String, count: int) -> int:
	return int((str(s.seed)+":"+key).sha256_text().substr(0,7).hex_to_int()) % count

func register_facility(spec: Dictionary, activate: bool = true) -> void:
	assert(not s.facilities.has(str(spec.id)),"Duplicate facility ID")
	s.facilities[spec.id]=spec.duplicate(true)
	for role in _keys(spec.get("npc_slots",{})):
		assert(s.config.roles.has(role),"Unknown role template")
		var template: Dictionary = s.config.roles[role]
		for slot in range(int(spec.npc_slots[role])):
			var id: String = str(spec.id)+":"+role+":%03d" % slot
			var given: Array = s.config.names.given
			var family: Array = s.config.names.family
			var work: String = str(spec.get("work_anchor",""))
			var home: String = str(spec.get("home_anchor",""))
			var initial: String = str(spec.get("spawn_anchor",home))
			var npc := {"id":id,"name":str(given[_choice(id+":given",given.size())])+" "+str(family[_choice(id+":family",family.size())]),
				"role":role,"facility_id":spec.id,"home_anchor":home,"work_anchor":work,"rest_anchor":str(spec.get("rest_anchor",home)),
				"patrol_anchors":spec.get("patrol_anchors",[]).duplicate(),"appearance_seed":_choice(id+":appearance",2147483647),
				"personality":spec.get("personality",template.get("personality","reserved")),"shop_id":str(spec.get("shop_id","")),
				"quest_ids":spec.get("quest_ids",[]).duplicate(),"family_label":spec.get("family_label",""),
				"anchor":initial,"position_m":_anchor_position(initial),"activity":"initializing","desired_activity":"","desired_anchor":"",
				"journey":{},"reason":"","interaction_until":0,"next_due":-1,"agenda_version":0,"last_change_tick":int(s.tick)}
			s.npcs[id]=npc
			if activate: _schedule(npc,int(s.tick))
	if activate: advance_to(int(s.tick))

func _index_routes() -> void:
	edge_index={}; outgoing={}
	for edge in s.config.get("routes",[]):
		assert(not edge_index.has(str(edge.id)),"Duplicate route ID")
		edge_index[edge.id]=edge
		if not outgoing.has(edge.from): outgoing[edge.from]=[]
		outgoing[edge.from].append(edge.id)
	for ids in outgoing.values(): ids.sort()

func _anchor_position(anchor: String) -> Array:
	return s.config.get("anchors",{}).get(anchor,{}).get("position_m",[]).duplicate()

func _allowed(edge: Dictionary) -> bool:
	if edge.get("blocked",false): return false
	if str(s.config.get("mode",""))=="logical_fixture" and edge.get("evidence","")=="synthetic_fixture": return true
	return edge.get("evidence","")=="runtime_verified" and edge.get("pedestrian",false) and str(edge.get("profile_sha256","")).length()==64 and edge.get("source_hashes",{})==s.config.get("active_source_hashes",{})

func find_route(from: String, to: String) -> Dictionary:
	s.metrics.route_searches+=1
	if from=="" or to=="": return {"ok":false,"reason":"unbound_anchor"}
	if from==to: return {"ok":true,"edge_ids":[]}
	var distances := {from:0}; var paths := {from:[]}; var open: Array = [from]
	while not open.is_empty():
		open.sort_custom(func(a,b): return int(distances[a])<int(distances[b]) or (int(distances[a])==int(distances[b]) and str(a)<str(b)))
		var node: String = open.pop_front()
		if node==to: return {"ok":true,"edge_ids":paths[node]}
		for eid in outgoing.get(node,[]):
			var edge: Dictionary = edge_index[eid]
			if not _allowed(edge): continue
			var end: String = edge.to
			var distance := int(distances[node])+maxi(1,int(edge.travel_ticks))
			if not distances.has(end) or distance<int(distances[end]):
				distances[end]=distance; paths[end]=paths[node].duplicate(); paths[end].append(eid)
				if not open.has(end): open.append(end)
	return {"ok":false,"reason":"blocked_or_unverified_route"}

func _less(a: Array,b: Array) -> bool:
	return int(a[0])<int(b[0]) or (int(a[0])==int(b[0]) and str(a[1])<str(b[1]))

func _push(entry: Array) -> void:
	s.agenda.append(entry)
	var i: int = s.agenda.size()-1
	while i>0:
		var parent: int = (i-1)/2
		if not _less(s.agenda[i],s.agenda[parent]): break
		var temp = s.agenda[i]; s.agenda[i]=s.agenda[parent]; s.agenda[parent]=temp; i=parent

func _pop() -> Array:
	var first: Array = s.agenda[0]
	var last = s.agenda.pop_back()
	if not s.agenda.is_empty():
		s.agenda[0]=last; var i := 0
		while true:
			var left := 2*i+1; var right := left+1; var smallest := i
			if left<s.agenda.size() and _less(s.agenda[left],s.agenda[smallest]): smallest=left
			if right<s.agenda.size() and _less(s.agenda[right],s.agenda[smallest]): smallest=right
			if smallest==i: break
			var temp = s.agenda[i]; s.agenda[i]=s.agenda[smallest]; s.agenda[smallest]=temp; i=smallest
	return first

func _schedule(npc: Dictionary, tick: int) -> void:
	npc.agenda_version+=1; npc.next_due=tick
	_push([tick,npc.id,npc.agenda_version])

func advance_to(target_tick: int) -> void:
	assert(target_tick>=int(s.tick),"Time cannot run backwards")
	while not s.agenda.is_empty() and int(s.agenda[0][0])<=target_tick:
		var event := _pop(); var npc: Dictionary = s.npcs[event[1]]
		if int(event[2])!=int(npc.agenda_version): continue
		s.tick=int(event[0]); s.metrics.events_processed+=1
		_update_npc(npc)
	s.tick=target_tick

func advance_ticks(ticks: int = 1) -> void:
	advance_to(int(s.tick)+ticks)

func _desired(npc: Dictionary) -> Dictionary:
	var day := int(s.config.get("day_ticks",86400)); var time := int(s.tick)%day
	var schedule: Array = s.config.roles[npc.role].schedule
	var selected: Dictionary = schedule[-1]
	var next_tick := int(s.tick)-time+day+int(schedule[0].start_tick)
	for row in schedule:
		if int(row.start_tick)<=time: selected=row
		elif next_tick>int(s.tick)-time+int(row.start_tick): next_tick=int(s.tick)-time+int(row.start_tick)
	var target := str(npc.get(str(selected.target)+"_anchor",""))
	if selected.target=="patrol":
		var anchors: Array = npc.patrol_anchors
		if not anchors.is_empty():
			var interval := int(s.config.roles[npc.role].get("patrol_interval_ticks",60))
			target=anchors[(int(s.tick)/interval+_choice(npc.id+":patrol_offset",anchors.size()))%anchors.size()]
			next_tick=mini(next_tick,(int(s.tick)/interval+1)*interval)
	return {"activity":str(selected.activity),"target":target,"next_tick":maxi(int(s.tick)+1,next_tick)}

func _update_npc(npc: Dictionary) -> void:
	var desired := _desired(npc)
	npc.desired_activity=desired.activity; npc.desired_anchor=desired.target
	if int(npc.interaction_until)>int(s.tick):
		npc.activity="talking"; _schedule(npc,mini(int(npc.interaction_until),int(desired.next_tick))); return
	if not npc.journey.is_empty():
		var journey: Dictionary = npc.journey
		var edge: Dictionary = edge_index.get(journey.edge_id,{})
		if edge.is_empty() or not _allowed(edge) or str(edge.get("profile_sha256",""))!=str(journey.profile_sha256):
			if not journey.has("paused_at"):
				npc.position_m=_journey_position(journey,int(s.tick)); journey.paused_at=int(s.tick)
			npc.activity="blocked"; npc.reason="route_invalidated_in_transit"
			_schedule(npc,int(s.tick)+int(s.config.get("retry_ticks",30))); return
		if journey.has("paused_at"):
			var paused := int(s.tick)-int(journey.paused_at)
			journey.start_tick+=paused; journey.end_tick+=paused; journey.erase("paused_at")
		if int(s.tick)<int(journey.end_tick):
			npc.activity="walking"; npc.reason=""
			_schedule(npc,mini(int(journey.end_tick),int(desired.next_tick))); return
		npc.anchor=edge.to; npc.position_m=_anchor_position(edge.to); npc.journey={}; s.metrics.arrivals+=1
		_event("arrived",npc,{"anchor":npc.anchor,"route_id":edge.id})
	if desired.target=="" or not s.config.anchors.has(desired.target):
		npc.activity="blocked"; npc.reason="unbound_"+str(desired.activity)+"_anchor"
		_schedule(npc,mini(int(desired.next_tick),int(s.tick)+int(s.config.get("retry_ticks",30)))); return
	if npc.anchor==desired.target:
		if npc.activity!=desired.activity:
			npc.last_change_tick=int(s.tick); _event("activity_changed",npc,{"activity":desired.activity})
		npc.activity=desired.activity; npc.reason=""
		_schedule(npc,int(desired.next_tick)); return
	var route := find_route(npc.anchor,desired.target)
	if not route.ok:
		npc.activity="blocked"; npc.reason=route.reason
		_schedule(npc,mini(int(desired.next_tick),int(s.tick)+int(s.config.get("retry_ticks",30)))); return
	var edge: Dictionary = edge_index[route.edge_ids[0]]
	npc.journey={"edge_id":edge.id,"profile_sha256":str(edge.get("profile_sha256","")),"start_tick":int(s.tick),
		"end_tick":int(s.tick)+maxi(1,int(edge.travel_ticks)),"points":edge.points.duplicate(true)}
	npc.activity="walking"; npc.reason=""; npc.last_change_tick=int(s.tick)
	_event("departed",npc,{"route_id":edge.id,"destination":desired.target})
	_schedule(npc,mini(int(npc.journey.end_tick),int(desired.next_tick)))

func _journey_position(journey: Dictionary, at_tick: int) -> Array:
	var at := mini(at_tick,int(journey.get("paused_at",at_tick)))
	var fraction := clampf(float(at-int(journey.start_tick))/float(maxi(1,int(journey.end_tick)-int(journey.start_tick))),0.0,1.0)
	return _polyline_position(journey.points,fraction)

func _polyline_position(points: Array, fraction: float) -> Array:
	if points.is_empty(): return []
	if points.size()==1: return points[0].duplicate()
	var lengths: Array = []; var total := 0.0
	for i in range(1,points.size()):
		var a := Vector3(float(points[i-1][0]),float(points[i-1][1]),float(points[i-1][2]))
		var b := Vector3(float(points[i][0]),float(points[i][1]),float(points[i][2]))
		var length := a.distance_to(b); lengths.append(length); total+=length
	var remaining := total*fraction
	for i in range(lengths.size()):
		if remaining<=float(lengths[i]):
			var t := remaining/maxf(float(lengths[i]),0.000001); var result: Array = []
			for axis in range(3): result.append(lerpf(float(points[i][axis]),float(points[i+1][axis]),t))
			return result
		remaining-=float(lengths[i])
	return points[-1].duplicate()

func sample_npc(id: String, at_tick: int = -1) -> Dictionary:
	var npc: Dictionary = s.npcs[id]
	var position: Array = npc.position_m.duplicate()
	if not npc.journey.is_empty(): position=_journey_position(npc.journey,int(s.tick) if at_tick<0 else at_tick)
	return {"id":id,"name":npc.name,"role":npc.role,"appearance_seed":npc.appearance_seed,"position_m":position,
		"activity":npc.activity,"reason":npc.reason,"shop_id":npc.shop_id,"journey":npc.journey.duplicate(true)}

func set_route_blocked(id: String, blocked: bool) -> void:
	assert(edge_index.has(id),"Unknown route")
	edge_index[id].blocked=blocked
	# Only affected travellers and blocked NPCs are woken. No teleport or implicit detour.
	for npc in s.npcs.values():
		if npc.journey.get("edge_id","")==id or npc.activity=="blocked": _schedule(npc,int(s.tick))
	advance_to(int(s.tick))

func begin_interaction(id: String, player_position: Array, duration_ticks: int = 10) -> Dictionary:
	if not s.npcs.has(id): return {"ok":false,"reason":"unknown_npc"}
	var npc: Dictionary = s.npcs[id]; var sample := sample_npc(id)
	if sample.position_m.size()!=3: return {"ok":false,"reason":"unbound_position"}
	var p := Vector3(float(player_position[0]),float(player_position[1]),float(player_position[2]))
	var n := Vector3(float(sample.position_m[0]),float(sample.position_m[1]),float(sample.position_m[2]))
	if p.distance_to(n)>float(s.config.get("interaction_radius_m",3.0)): return {"ok":false,"reason":"out_of_range"}
	if not npc.journey.is_empty(): return {"ok":false,"reason":"walking"}
	npc.interaction_until=int(s.tick)+clampi(duration_ticks,1,120)
	_schedule(npc,int(s.tick)); advance_to(int(s.tick))
	return {"ok":true,"dialogue":dialogue(id)}

func dialogue(id: String) -> Dictionary:
	var npc: Dictionary = s.npcs[id]; var template: Dictionary = s.config.roles[npc.role]
	var topics: Array = [{"id":"greeting","text":str(template.get("greeting","Good day.")).replace("{name}",npc.name)}]
	var shop: Dictionary = s.config.get("shops",{}).get(npc.shop_id,{})
	if not shop.is_empty():
		topics.append({"id":"specialty","text":shop.pitch,"catalog":shop.catalog.duplicate(true),"price_band":shop.price_band,"service":shop_status(npc.shop_id)})
	for quest in npc.quest_ids:
		if s.config.get("quests",{}).has(quest):
			var q: Dictionary = s.config.quests[quest]
			topics.append({"id":quest,"text":q.hook,"state":s.quest_states.get(quest,"available"),"objective":q.objective})
	return {"npc_id":id,"name":npc.name,"personality":npc.personality,"role":npc.role,"topics":topics}

func shop_status(shop_id: String) -> Dictionary:
	var owners: Array = []
	for npc in s.npcs.values():
		if npc.shop_id!=shop_id: continue
		owners.append(npc.id)
		if npc.anchor==npc.work_anchor and npc.journey.is_empty() and npc.desired_activity=="service":
			return {"open":true,"owner_id":npc.id,"reason":"owner_present_during_open_hours"}
	return {"open":false,"owner_ids":owners,"reason":"owner_absent_or_closed_hours"}

func set_quest_state(id: String, state: String) -> bool:
	if not s.config.get("quests",{}).has(id) or not state in ["available","accepted","completed","failed"]: return false
	s.quest_states[id]=state
	return true

func _event(kind: String, npc: Dictionary, detail: Dictionary) -> void:
	var event := {"tick":int(s.tick),"type":kind,"npc_id":npc.id}; event.merge(detail); s.events.append(event)
	while s.events.size()>int(s.config.get("event_history_limit",512)): s.events.pop_front()

func invariant_errors() -> Array:
	var errors: Array = []
	for npc in s.npcs.values():
		if not s.facilities.has(npc.facility_id): errors.append("unknown facility:"+npc.id)
		if int(npc.next_due)<int(s.tick): errors.append("overdue event:"+npc.id)
		if npc.anchor!="" and not s.config.anchors.has(npc.anchor): errors.append("unknown anchor:"+npc.id)
		if not npc.journey.is_empty() and not edge_index.has(npc.journey.edge_id): errors.append("unknown route:"+npc.id)
	for i in range(1,s.agenda.size()):
		if _less(s.agenda[i],s.agenda[(i-1)/2]): errors.append("agenda heap invalid")
	return errors

func save_json() -> String:
	var payload := JSON.stringify(s,"",true,true)
	return JSON.stringify({"schema":"riverstone.rpg_npcs.save.v1","payload":payload,"sha256":payload.sha256_text()})

func restore_json(serialized: String) -> bool:
	var envelope = JSON.parse_string(serialized)
	if not envelope is Dictionary or envelope.get("schema","")!="riverstone.rpg_npcs.save.v1": return false
	var payload: String = envelope.get("payload","")
	if payload.sha256_text()!=envelope.get("sha256",""): return false
	var restored = JSON.parse_string(payload)
	if not restored is Dictionary or restored.get("schema","")!=SCHEMA: return false
	var old := s
	s=restored; _index_routes()
	if not invariant_errors().is_empty(): s=old; _index_routes(); return false
	return true
