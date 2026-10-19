"""Measured labels and inferred opaque geometry are separate constraints.
Only a compact field changes; frozen body/costume meshes are referenced unchanged.
"""
from pathlib import Path
import sys,time,resource,threading,os
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'full02/tools'))
import pipeline as before
from pipeline import *
from audit_occlusion_sections import depth
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;P=BASE/'data/occlusion_contract.json';A=read(P)

def guard():
 while True:
  rss=int(Path('/proc/self/status').read_text().split('VmRSS:')[1].split()[0])/1024
  if rss>A['peak_rss_hard_guard_mib']:write(BASE/'evidence/memory_guard.json',{'rss_mib':rss,'stopped':True});os._exit(77)
  time.sleep(.04)

def inputs():
 m,a,src=before.load();cp=ROOT/A['fixed_body_costume_source'];assert sha(cp)==A['fixed_source_sha256'];q=np.load(cp);build=read(ROOT/'full02/evidence/build.json');return m,a,src,q,build

def field_from_inputs(m,a,src,q,build):
 masks={};stats={};cloth=np.load(ROOT/'whole_source07/evidence/measurement.npz');ann=read(ROOT/'data/violet_full_semantic_annotations_v02.json');vertices=[];faces=[];offset=0
 for part in build['parts']:
  if part['id'] in ['hair_envelope','halo_observed']:continue
  i=part['index'];v=q[f'v{i}'];f=q[f'f{i}'];vertices.extend(v);faces.extend(f+offset);offset+=len(v)
 vertices=np.array(vertices);faces=np.array(faces);depths={}
 for name in ['front','side']:
  h=a[name+'_hair_eligible'];conflict=h&(a[name+'_face_skin']|a[name+'_body_exposed_skin']|cloth[name+'_support']);feature=np.zeros_like(h)
  for lm in ann['landmark_searches']:
   if lm['view']==name:feature|=boxes_mask(h.shape,C['views'][name]['crop'],[lm['box']])
  unknown=conflict|(feature&h);confident=h&~unknown;masks[name+'_hair_confident']=confident;masks[name+'_ownership_unknown']=unknown;depths[name]=depth(vertices,faces,C['views'][name]);stats[name]={'original_hair_pixels':int(h.sum()),'confident_visible_hair_pixels':int(confident.sum()),'unknown_conflicting_pixels':int(unknown.sum()),'opaque_geometric_projection_pixels':int(np.isfinite(depths[name]).sum())}
 old=np.load(ROOT/'full02/generated/hair_implicit.npz');axes=[old[k]for k in ['x','y','z']];field=np.full(tuple(map(len,axes)),np.inf,np.float32)
 # X-slices avoid materializing several complete XYZ coordinate volumes.
 for name in ['front','side']:
  vw=C['views'][name];theta=math.radians(vw['yaw_degrees']);hm=masks[name+'_hair_confident'];dm=depths[name];opaque=np.isfinite(dm)
  def sdf(mask):return (ndi.distance_transform_edt(mask)-ndi.distance_transform_edt(~mask)).astype(np.float32)*SCALE
  hs=sdf(hm);oc=sdf(opaque);dd=np.where(opaque,dm,-10);Y,Z=np.meshgrid(axes[1],axes[2],indexing='ij')
  for i,x in enumerate(axes[0]):
   u=vw['axis_u']+(math.cos(theta)*x-math.sin(theta)*Z)/SCALE-vw['crop'][0]-.5;y=vw['sole_y']-Y/SCALE-.5;co=np.array([y.ravel(),u.ravel()]);hv=ndi.map_coordinates(hs,co,order=1,mode='constant',cval=-1).reshape(Y.shape);ov=ndi.map_coordinates(oc,co,order=1,mode='constant',cval=-1).reshape(Y.shape);dv=ndi.map_coordinates(dd,co,order=1,mode='constant',cval=-10).reshape(Y.shape);camera_depth=math.sin(theta)*x+math.cos(theta)*Z;constraint=np.maximum(hv,np.minimum(ov,dv-camera_depth-A['behind_surface_offset_m']));field[i]=np.minimum(field[i],constraint)
 raw=field>0;field=ndi.gaussian_filter(field,A['sdf_sigma_cells'],mode='constant',cval=-.05);label,n=ndi.label(field>0);stats['field']={'shape':list(field.shape),'raw_positive_nodes':int(raw.sum()),'curved_positive_nodes':int((field>0).sum()),'sign_changed_by_curvature_nodes':int((raw!=(field>0)).sum()),'six_components':int(n),'component_sizes':sorted(np.bincount(label.ravel())[1:].tolist(),reverse=True),'no_island_deletion':True};return field,axes,masks,stats

def run():
 t=time.monotonic();m,a,src,q,b=inputs();field,axes,masks,stats=field_from_inputs(m,a,src,q,b);stored=field.astype(np.float16);err=np.abs(stored.astype(np.float32)-field);stats['storage']={'all_node_max_absolute_error_m':float(err.max()),'within10mm_of_surface_max_error_m':float(err[abs(field)<.01].max()),'source_is_stored_field_not_unstored_float32':True};np.savez_compressed(BASE/'generated/hair_field.npz',field=stored,x=axes[0],y=axes[1],z=axes[2]);np.savez_compressed(BASE/'evidence/ownership_masks.npz',**masks);report={'status':'COMPACT_SOURCE_ONLY_NO_COMMON_COMPILE','approved_source_sha256':A['approved_image_sha256'],'referenced_body_costume_source_sha256':A['fixed_source_sha256'],'measurements_sha256':sha(ROOT/A['fixed_measurement']),'contract_sha256':sha(P),'generator_sha256':sha(__file__),'field_sha256':sha(BASE/'generated/hair_field.npz'),'ownership_masks_sha256':sha(BASE/'evidence/ownership_masks.npz'),'source_primitive':'zero isosurface of trilinearly interpolated stored3D signed field; existing closed loft/costume geometry referenced unchanged','stats':stats,'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024};write(BASE/'evidence/build.json',report);print(json.dumps(report));before.disk()
if __name__=='__main__':threading.Thread(target=guard,daemon=True).start();run()
