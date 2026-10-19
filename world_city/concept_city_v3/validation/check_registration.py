#!/usr/bin/env python3
"""Independent camera/trace consistency preflight; not visual fidelity approval.

Do not import the trace author or its fitted transform. Reconstruct both the
declared scalar camera and the actual look-at orthographic camera separately.
Registered source correspondence checks are added only once its schema freezes.
"""
import hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parent;ROOT=CITY.parents[1]

def project_xyz(model,p):
 s=model['scale_px_per_m'];yaw=math.radians(model['yaw_degrees']);elev=math.radians(model['elevation_degrees']);cx,cy=model['offset_pixel_xy'];x,y,z=p
 return [cx+s*(math.cos(yaw)*x-math.sin(yaw)*z),cy+s*(math.sin(elev)*(math.sin(yaw)*x+math.cos(yaw)*z)-math.cos(elev)*y)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def unit(p):
 n=math.sqrt(dot(p,p));return [x/n for x in p]
def engine_project(camera,p):
 forward=unit([b-a for a,b in zip(camera['position_m'],camera['target_m'])]);right=unit(cross(forward,[0,1,0]));up=cross(right,forward)
 offset=[a-b for a,b in zip(p,camera['target_m'])];w,h=camera['render_size_px'];s=h/camera['ortho_size_m']
 return [w/2+s*dot(offset,right),h/2-s*dot(offset,up)]
def digest(data):return hashlib.sha256(data).hexdigest()

def check(data):
 issues=[];rows=[];maximum=0.;maximum_engine=0.;count=0;w,h=data['image_size_px']
 for group in ['polygons','estates','roads','water']:
  for record in data[group]:
   pixels=record['trace_pixel_xy'];world=record['world_xyz_m'];uv=record['trace_normalized_uv']
   if len(pixels)!=len(world) or len(uv)!=len(world):issues.append({'id':record['id'],'issue':'correspondence_count'});continue
   errors=[];engine_errors=[]
   for pixel,xyz,norm in zip(pixels,world,uv):
    if not all(math.isfinite(v) for v in pixel+xyz+norm):issues.append({'id':record['id'],'issue':'nonfinite_coordinate'});continue
    err=math.dist(project_xyz(data['camera_model'],xyz),pixel);eng=math.dist(engine_project(data['matched_engine_camera'],xyz),pixel)
    errors.append(err);engine_errors.append(eng);count+=1
    if abs(norm[0]-pixel[0]/w)>1e-7 or abs(norm[1]-pixel[1]/h)>1e-7:issues.append({'id':record['id'],'issue':'normalized_trace_disagrees'})
   maximum=max(maximum,*errors);maximum_engine=max(maximum_engine,*engine_errors)
   rows.append({'group':group,'id':record['id'],'points':len(world),'maximum_model_residual_px':max(errors),'maximum_engine_camera_residual_px':max(engine_errors)})
   if max(errors+engine_errors)>.001:issues.append({'id':record['id'],'issue':'roundtrip_residual','max_px':max(errors+engine_errors)})
 anchor_errors=[];inferred=[]
 for a in data['anchors']:
  error=math.dist(project_xyz(data['camera_model'],a['current_world_xyz_m']),a['image_pixel_xy']);anchor_errors.append(error)
  inferred.append(math.dist(project_xyz(data['camera_model'],a['inferred_target_world_xyz_m']),a['image_pixel_xy']))
  if abs(error-a['current_error_px'])>1e-8:issues.append({'id':a['id'],'issue':'stored_anchor_error_disagrees'})
 rms=math.sqrt(sum(e*e for e in anchor_errors)/len(anchor_errors))
 if abs(rms-data['anchor_rms_px'])>1e-8:issues.append({'issue':'stored_rms_disagrees'})
 if max(inferred)>.001:issues.append({'issue':'inferred_anchor_roundtrip'})
 return {'status':'pass' if not issues else 'fail','scope':'camera and manual trace arithmetic only; registered geometry and visual fidelity untested','counts':{'features':len(rows),'trace_points':count,'anchors':len(anchor_errors)},'maximum_trace_residual_px':maximum,'maximum_engine_camera_residual_px':maximum_engine,'old_current_anchor_rms_px':rms,'maximum_inferred_anchor_residual_px':max(inferred),'vertical_shift_px_per_m_without_xz_compensation':data['camera_model']['scale_px_per_m']*math.cos(math.radians(data['camera_model']['elevation_degrees'])),'features':rows,'issues':issues,'limitations':['Round-trip consistency is expected for authored inverse projections and does not validate manual trace accuracy.','The generated oblique image is not a calibrated survey. Heights and occluded boundaries remain design hypotheses.','No registered source placement, image adjacency, road access, collision, hydraulic or all-door approval is inferred.','Final world geometry must be checked at its actual authored Y; changing Y without compensating XZ changes projected alignment.']}

def main():
 path=CITY/'image_registration/controls.json';raw=path.read_bytes();data=json.loads(raw);result=check(data)
 image=ROOT/data['source_image'];image_hash=digest(image.read_bytes())
 if image_hash!=data['source_image_sha256']:result['issues'].append({'issue':'source_image_hash_mismatch'});result['status']='fail'
 sha=digest(raw);script_sha=digest(Path(__file__).read_bytes());snapshot=HERE/'evidence/sources'/('registration_controls_'+sha+'.json');snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(raw)
 result['provenance']={'controls_path':str(path.relative_to(ROOT)),'controls_sha256':sha,'snapshot_path':str(snapshot.relative_to(ROOT)),'source_image_path':data['source_image'],'source_image_sha256':image_hash,'checker_sha256':script_sha}
 out=HERE/'evidence'/('registration_'+sha[:12]+'_'+script_sha[:12]+'.json');out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'status':result['status'],'report':str(out),'counts':result['counts'],'maximum_trace_residual_px':result['maximum_trace_residual_px'],'maximum_engine_camera_residual_px':result['maximum_engine_camera_residual_px'],'old_current_anchor_rms_px':result['old_current_anchor_rms_px'],'issues':result['issues']},indent=2))
 if result['issues']:raise SystemExit(2)

if __name__=='__main__':main()
