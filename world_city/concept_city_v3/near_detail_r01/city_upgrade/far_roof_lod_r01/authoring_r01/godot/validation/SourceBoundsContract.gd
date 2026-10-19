extends RefCounted
## Mirrors bounds_contract.py. Occupancy is proven offline and SHA-bound.
const EPS:=0.000001
static func same(a: Variant,b: Variant) -> bool:
	return JSON.stringify(JSON.parse_string(JSON.stringify(a)))==JSON.stringify(JSON.parse_string(JSON.stringify(b)))
static func vector_ok(v: Variant) -> bool:
	if not v is Array or v.size()!=3:return false
	for n in v:
		if (not n is float and not n is int) or not is_finite(float(n)):return false
	return true
static func bounds_ok(b: Variant) -> bool:
	if not b is Dictionary or not vector_ok(b.get("min")) or not vector_ok(b.get("max")):return false
	for i in 3:
		if b.min[i]>b.max[i]:return false
	return true
static func valid_hash(value: String) -> bool:
	if value.length()!=64:return false
	for c in value:
		if c not in "0123456789abcdef":return false
	return true
static func validate(c: Dictionary,fine: Dictionary,coarse: Dictionary,source_sha: String,proof: Dictionary={}) -> String:
	if c.get("source_master_sha256","")!=source_sha or not same(c.get("composed_render_bounds"),fine) or not same(c.get("coarse_render_bounds"),coarse) or str(c.get("reason","")).is_empty():return "source binding"
	var analytic: Dictionary=c.get("analytic_source_bounds",{})
	if not bounds_ok(fine) or not bounds_ok(coarse) or not bounds_ok(analytic):return "malformed bounds"
	var outside:=int(c.get("outside_analytic_aabb_vertices",-1))
	if outside==0:
		for i in 3:
			if fine.min[i]<analytic.min[i]-EPS or fine.max[i]>analytic.max[i]+EPS:return "exceeds analytic source"
		return ""
	if outside<0 or int(c.get("outside_original_coarse_aabb_vertices",-1))!=0:return "missing coarse containment"
	var env: Dictionary=c.get("voxel_cell_envelope",{})
	if not bounds_ok(env) or not vector_ok(env.get("grid_origin_m")) or not vector_ok(env.get("max_excess_by_axis_m")):return "malformed envelope"
	var pitch:=float(env.get("pitch_m",0))
	if not is_finite(pitch) or pitch<=0 or pitch>.05 or env.get("sampling","")!="cell_center" or int(env.get("outside_envelope_vertices",-1))!=0:return "unsupported sampling"
	var largest:=0.0
	for i in 3:
		if fine.min[i]<coarse.min[i]-EPS or fine.max[i]>coarse.max[i]+EPS:return "outside coarse bounds"
		var origin: float=env.grid_origin_m[i]
		var expected_min: float=origin+ceil((analytic.min[i]-origin)/pitch-.5-1e-8)*pitch
		var expected_max: float=origin+(floor((analytic.max[i]-origin)/pitch-.5+1e-8)+1)*pitch
		if abs(env.min[i]-expected_min)>EPS or abs(env.max[i]-expected_max)>EPS:return "not exact cell envelope"
		if fine.min[i]<env.min[i]-EPS or fine.max[i]>env.max[i]+EPS:return "outside envelope"
		var excess: float=max(0.0,analytic.min[i]-fine.min[i],fine.max[i]-analytic.max[i])
		if excess>pitch/2+EPS or abs(env.max_excess_by_axis_m[i]-excess)>EPS:return "incorrect excess"
		largest=max(largest,excess)
	if abs(float(env.get("max_excess_from_analytic_m",-1))-largest)>EPS:return "incorrect maximum excess"
	if proof.get("schema","")!="riverstone.common.cell_center_envelope_proof.v1" or proof.get("source_master_sha256","")!=source_sha or not same(proof.get("analytic_source_bounds"),analytic) or not same(proof.get("voxel_cell_envelope"),env):return "unbound replay proof"
	if int(proof.get("outside_analytic_aabb_vertices",-1))!=outside or int(proof.get("outside_original_coarse_aabb_vertices",-1))!=0 or bool(proof.get("source_shapes_cropped",true)):return "invalid replay scope"
	var seen: Dictionary={}
	for replay in proof.get("source_canonical_replay",[]):
		if not replay is Dictionary or not bool(replay.get("every_witness_source_and_canonical_occupied",false)) or not bounds_ok(replay.get("cell_bounds")):return "failed replay"
		var points: Array=replay.get("witness_cells",[])
		if points.is_empty() or int(replay.get("witness_cell_count",-1))!=points.size():return "wrong witness count"
		if not valid_hash(str(replay.get("source_payload_sha256",""))) or not valid_hash(str(replay.get("canonical_payload_sha256",""))):return "missing payload binding"
		for i in 3:
			if int(replay.cell_bounds.min[i])!=replay.cell_bounds.min[i] or int(replay.cell_bounds.max[i])!=replay.cell_bounds.max[i]:return "noninteger cell bounds"
		for point in points:
			if not vector_ok(point):return "invalid witness"
			for i in 3:
				if int(point[i])!=point[i] or point[i]<replay.cell_bounds.min[i] or point[i]>=replay.cell_bounds.max[i]:return "witness outside replay"
			var token:=Vector3i(int(point[0]),int(point[1]),int(point[2]))
			if seen.has(token):return "duplicate witness"
			seen[token]=true
	if seen.is_empty() or seen.size()!=int(proof.get("source_occupied_boundary_cell_count",-1)):return "incomplete witness replay"
	return ""
