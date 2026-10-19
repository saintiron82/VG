#!/usr/bin/env python3
"""Copy-only observation run. Original strict replay remains the certificate."""
import pathlib,json,hashlib,difflib,os,subprocess,time,argparse
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):
 with pathlib.Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prepared',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--route',action='append',required=True);a=ap.parse_args();src=a.prepared.resolve();out=a.output.resolve();assert src.is_relative_to(H)and out.is_relative_to(H);out.mkdir();(out/'evidence').mkdir()
 for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot']:(out/n).write_bytes((src.parent/n).read_bytes())
 original=(out/'Traversal.gd').read_text();(out/'Traversal.original.gd').write_text(original)
 needle='\tif floor_hit.is_empty():result.ground_ray_miss_frames+=1\n'
 replacement='''\tif floor_hit.is_empty():
\t\tresult.ground_ray_miss_frames+=1
\t\tvar ray_miss_observation: Dictionary={"frame":route_frames,"capsule_center":vec(body.position),"ray_from":vec(ray.from),"ray_to":vec(ray.to),"body_floor_normal":vec(body.get_floor_normal()),"slide_collision_normals":[],"waypoint_index":waypoint_index}
\t\tfor observation_index in body.get_slide_collision_count():
\t\t\tray_miss_observation.slide_collision_normals.append(vec(body.get_slide_collision(observation_index).get_normal()))
\t\tif not result.has("ray_miss_diagnostics"):result.ray_miss_diagnostics=[]
\t\tresult.ray_miss_diagnostics.append(ray_miss_observation)
'''
 assert original.count(needle)==1;changed=original.replace(needle,replacement);assert changed.replace(replacement,needle)==original;(out/'Traversal.gd').write_text(changed);(out/'controller_observation_only.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='original_Traversal.gd',tofile='observation_only_Traversal.gd')))
 d=json.loads(src.read_bytes());d['routes']=[r for r in d['routes']if r['id']in a.route];assert len(d['routes'])==len(a.route)
 d['diagnostic_provenance']={'original_prepared':str(src),'original_prepared_sha256':sha(src),'original_controller_sha256':sha(out/'Traversal.original.gd'),'diagnostic_controller_sha256':sha(out/'Traversal.gd'),'only_change':'Log already-computed empty-ray frame, capsule position, ray endpoints and collision normals. No new query, movement, geometry, acceptance or tolerance change.','not_a_replacement_certificate':True};p=out/'prepared.json';p.write_text(json.dumps(d,indent=2)+'\n')
 refs={v['path']:v['sha256']for v in d['sources'].values()};refs.update({str(ROOT/k):v for k,v in d['implementation_hashes'].items()});refs.update({str(ROOT/v['render_path']):v['render_sha256']for v in d['assets'].values()});refs.update({str(p):sha(p),str(out/'Traversal.gd'):sha(out/'Traversal.gd'),str(out/'Traversal.original.gd'):sha(out/'Traversal.original.gd'),str(out/'RenderData.gd'):sha(out/'RenderData.gd')})
 for q,h in refs.items():assert sha(q)==h,q
 env=dict(os.environ,GODOT_SILENCE_ROOT_WARNING='1')
 for k,n in [('XDG_CACHE_HOME','cache'),('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config')]:q=out/'.runtime'/n;q.mkdir(parents=True,exist_ok=True);env[k]=str(q)
 target=out/'evidence/capsule.json';cmd=['godot','--headless','--disable-render-loop','--fixed-fps','60','--path',str(out),'res://Traversal.tscn','--','--prepared='+str(p),'--report='+str(target)];t=time.monotonic()
 with(out/'evidence/capsule.log').open('x')as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 drift=[q for q,h in refs.items()if sha(q)!=h];m={'command':cmd,'exit_code':r.returncode,'elapsed_s':time.monotonic()-t,'verified_sources':refs,'changed_sources':drift,'observation_only':True,'not_replacement_certificate':True,'report_sha256':sha(target)if target.exists()else None};(out/'evidence/run_manifest.json').write_text(json.dumps(m,indent=2)+'\n');assert not drift
 print(json.dumps({'exit_code':r.returncode,'changed_sources':drift,'report':str(target)}))
if __name__=='__main__':main()
