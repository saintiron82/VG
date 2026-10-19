"""Copy-only observation instrumentation. Never changes original controller."""
import pathlib,json,hashlib,copy,difflib
O=pathlib.Path(__file__).resolve().parent;ROOT=O.parents[4];SRC=O/'junction_replay_r01';OUT=O/'ray_diagnostic_r01';OUT.mkdir(exist_ok=False);(OUT/'evidence').mkdir()
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:(OUT/n).write_bytes((SRC/n).read_bytes())
original=(OUT/'Traversal.gd').read_text();(OUT/'Traversal.original.gd').write_text(original)
needle='\tif floor_hit.is_empty():result.ground_ray_miss_frames+=1\n'
replacement='''\tif floor_hit.is_empty():
\t\tresult.ground_ray_miss_frames+=1
\t\tvar ray_miss_observation: Dictionary={"frame":route_frames,"capsule_center":vec(body.position),"ray_from":vec(ray.from),"ray_to":vec(ray.to),"body_floor_normal":vec(body.get_floor_normal()),"slide_collision_normals":[],"waypoint_index":waypoint_index}
\t\tfor observation_index in body.get_slide_collision_count():
\t\t\tray_miss_observation.slide_collision_normals.append(vec(body.get_slide_collision(observation_index).get_normal()))
\t\tif not result.has("ray_miss_diagnostics"):result.ray_miss_diagnostics=[]
\t\tresult.ray_miss_diagnostics.append(ray_miss_observation)
\t\tprint("RAY_MISS_DIAGNOSTIC "+JSON.stringify(ray_miss_observation))
'''
assert original.count(needle)==1;changed=original.replace(needle,replacement);assert changed.replace(replacement,needle)==original;(OUT/'Traversal.gd').write_text(changed);(OUT/'controller_observation_only.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='original_Traversal.gd',tofile='observation_only_Traversal.gd')))
d=json.load(open(SRC/'prepared.json'));case='SEAM_03:A1:B-1_REVERSE';r=next(x for x in d['routes'] if x['id']==case);d['routes']=[r];d['diagnostic_provenance']={'original_prepared':str((SRC/'prepared.json').relative_to(ROOT)),'original_prepared_sha256':sha(SRC/'prepared.json'),'original_controller_sha256':sha(OUT/'Traversal.original.gd'),'diagnostic_controller_sha256':sha(OUT/'Traversal.gd'),'only_change':'Record ray-miss frame, position, ray endpoints and already-computed collision normals. No movement, tolerance, collision query, source geometry or acceptance change.','not_a_replacement_certificate':True};(OUT/'prepared.json').write_text(json.dumps(d,indent=2)+'\n');(OUT/'identity.json').write_text(json.dumps(d['diagnostic_provenance'],indent=2)+'\n');print(str(OUT))
