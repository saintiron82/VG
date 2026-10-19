#!/usr/bin/env python3
import pathlib,json,hashlib,os,subprocess,time
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());SRC=H/'candidate_r07_replay_r01';OUT=H/'candidate_r07_ray_offsets_r01';OUT.mkdir();(OUT/'evidence').mkdir()
def sha(p):
 with pathlib.Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
for n in ['Traversal.gd','RenderData.gd','project.godot']:(OUT/n).write_bytes((SRC/n).read_bytes())
(OUT/'RayOffsets.gd').write_bytes((H/'RayOffsets.gd').read_bytes());(OUT/'RayOffsets.tscn').write_text('[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://RayOffsets.gd" id="1"]\n[node name="RayOffsets" type="Node3D"]\nscript = ExtResource("1")\n')
d=json.loads((SRC/'prepared.json').read_bytes());obs=H/'candidate_r07_ray_observation_r01/evidence/capsule.json';o=json.loads(obs.read_bytes());ids=[r['id']for r in o['routes']];d['routes']=[r for r in d['routes']if r['id']in ids];d['sources']['ray_observations']={'path':str(obs),'sha256':sha(obs)};gates=d['coverage']['new_gate_routes'];d['probe_transverse_xyz']={r['id']:[-g['travel_unit_xz'][1],0,g['travel_unit_xz'][0]]for r in d['routes']for g in gates if g['id'].startswith(r['group'])};d['diagnostic_only']=True;p=OUT/'prepared.json';p.write_text(json.dumps(d,indent=2)+'\n')
refs={v['path']:v['sha256']for v in d['sources'].values()};refs.update({str(ROOT/k):v for k,v in d['implementation_hashes'].items()});refs.update({str(ROOT/v['render_path']):v['render_sha256']for v in d['assets'].values()});refs.update({str(q):sha(q)for q in [p,OUT/'RayOffsets.gd',OUT/'RayOffsets.tscn',OUT/'Traversal.gd',OUT/'RenderData.gd']})
for q,h in refs.items():assert sha(q)==h,q
assert sha(OUT/'Traversal.gd')==sha(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd')
env=dict(os.environ,GODOT_SILENCE_ROOT_WARNING='1')
for k,n in [('XDG_CACHE_HOME','cache'),('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config')]:q=OUT/'.runtime'/n;q.mkdir(parents=True,exist_ok=True);env[k]=str(q)
report=OUT/'evidence/rays.json';cmd=['godot','--headless','--disable-render-loop','--fixed-fps','60','--path',str(OUT),'res://RayOffsets.tscn','--','--prepared='+str(p),'--report='+str(report)];t=time.monotonic()
with(OUT/'evidence/rays.log').open('x')as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
drift=[q for q,h in refs.items()if sha(q)!=h];m={'command':cmd,'exit_code':r.returncode,'elapsed_s':time.monotonic()-t,'verified_sources':refs,'changed_sources':drift,'not_replacement_certificate':True,'report_sha256':sha(report)if report.exists()else None};(OUT/'evidence/run_manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m|{'verified_sources':'see manifest'}));assert not drift
