extends SceneTree
const Controller=preload("OperationController.gd")
func same(a,b) -> bool:
	if (typeof(a)==TYPE_INT or typeof(a)==TYPE_FLOAT) and (typeof(b)==TYPE_INT or typeof(b)==TYPE_FLOAT): return abs(float(a)-float(b))<0.00000001
	if a is Dictionary and b is Dictionary:
		if a.size()!=b.size(): return false
		for k in a:
			if not b.has(k) or not same(a[k],b[k]): return false
		return true
	if a is Array and b is Array:
		if a.size()!=b.size(): return false
		for i in range(a.size()):
			if not same(a[i],b[i]): return false
		return true
	return a==b
func _initialize():
	var args=OS.get_cmdline_user_args(); var input=args[0] if args.size()>0 else "res://test_vectors.json"; var output=args[1] if args.size()>1 else "res://godot_test_report.json"
	var data=JSON.parse_string(FileAccess.get_file_as_string("res://contract.json")); var vectors=JSON.parse_string(FileAccess.get_file_as_string(input)); var errors=[]; var replay=[]; var count=0
	for scenario in vectors.cases:
		var c=Controller.new(data); var trace={"id":scenario.id,"outputs":[]}
		for f in scenario.frames:
			var out=c.step(f.now_ms,f.snapshot,f.commands); trace.outputs.append(out); count+=1
			if f.has("expected") and not same(f.expected,out): errors.append({"case":scenario.id,"expected":f.expected,"actual":out})
		replay.append(trace)
	var report={"valid":errors.is_empty(),"cases":vectors.cases.size(),"frames":count,"errors":errors,"replay":replay,"scope":"Reconstructed headless Godot simulation; no real city integration"}
	var file=FileAccess.open(output,FileAccess.WRITE); file.store_string(JSON.stringify(report,"\t")+"\n"); file.close()
	print(JSON.stringify({"valid":errors.is_empty(),"frames":count,"cases":vectors.cases.size(),"errors":errors.size()})); quit(0 if errors.is_empty() else 1)
