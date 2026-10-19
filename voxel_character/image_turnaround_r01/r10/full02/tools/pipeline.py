"""Preset-driven measured closed lofts and regularized multi-view hair envelope.
Source data are mandatory. Hidden depth/closure and side correspondence are priors.
No handwritten hair lock curves, image plane character or output-island repair.
"""
from pathlib import Path
import sys,os,time,resource,json,hashlib,math,copy
os.environ['OPENBLAS_NUM_THREADS']='1'
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;REPO=ROOT.parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import build_full_measured as volume
from measured_panels import *
from measure_semantic_views import classify
from measure_surface_branches import polygons_mask,boxes_mask
sys.path.insert(0,str(ROOT/'whole_source03/tools'))
from verify_hole_aware import depth_image
from scipy.spatial import cKDTree
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
P=BASE/'data/violet.json';A=read(P);C=read(ROOT/A['alignment_contract']);SCALE=C['alignment']['character_height_m_for_test']/C['views']['front']['scale_px_per_unit']

def rawsha(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def disk():
 used=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file());assert used<65*1048576;return used

def measure(source):
 ann=read(ROOT/A['semantic_annotation']);ba=read(ROOT/A['branch_annotation']);_,fg=extract(ROOT/A['alignment_contract']);masks={};classes=[]
 for name,v in C['views'].items():
  x0,y0,x1,y1=v['crop'];rgb=source[y0:y1,x0:x1];foreground=fg[name+'_foreground'];masks[name+'_foreground']=foreground
  for cl in ann['classes']:
   roi=boxes_mask(foreground.shape,v['crop'],cl['boxes'].get(name,[]));ex=boxes_mask(foreground.shape,v['crop'],cl.get('exclude_boxes',{}).get(name,[]));mask=foreground&roi&~ex&classify(rgb,cl['color']);masks[name+'_'+cl['id']]=mask
  halo=polygons_mask(foreground.shape,v['crop'],ba['views'][name]['halo_exclusion_polygons']);guide=boxes_mask(foreground.shape,v['crop'],ba['views'][name]['guide_search_boxes'])&((rgb[:,:,2]>=245)&(rgb[:,:,2].astype(int)-rgb[:,:,0]>25)&(rgb[:,:,2].astype(int)-rgb[:,:,1]>15))
  masks[name+'_hair_eligible']=masks[name+'_hair_visible']&~halo&~guide;masks[name+'_halo_eligible']=halo&foreground&(rgb.max(2)-rgb.min(2)>18)&(rgb[:,:,2].astype(int)-rgb[:,:,1]>10)&(rgb.min(2)<240);masks[name+'_guide']=guide
  classes.append({'view':name,'hair_visible_pixels':int(masks[name+'_hair_visible'].sum()),'hair_eligible_pixels':int(masks[name+'_hair_eligible'].sum()),'halo_pixels':int(masks[name+'_halo_eligible'].sum()),'guide_pixels':int(guide.sum()),'internal_gaps_preserved':True})
 lm=[]
 for q in ann['landmark_searches']:
  x0,y0,x1,y1=q['box'];mask=classify(source[y0:y1,x0:x1],q['color']);ys,xs=np.where(mask);lm.append({'id':q['id'],'view':q['view'],'centroid_xy_px':[float(xs.mean()+x0),float(ys.mean()+y0)] if len(xs) else None,'pixel_count':len(xs),'manual_search_box':q['box']})
 va=read(ROOT/A['volume_annotation']);branches={v+'__eligible__hair_visible':masks[v+'_hair_eligible'] for v in C['views']};unused,mats,profiles,sockets=volume.volume_parts(C,{'landmarks':lm},va,masks,source,branches)
 ac=read(ROOT/'full01/data/accessory_annotations.json');va2=copy.deepcopy(va);va2['parts']=[ac['bouquet']];unused,unused2,bp,bs=volume.volume_parts(C,{'landmarks':lm},va2,masks,source);profiles+=bp
 m={'schema':'riverstone.full02.independent_measurement.v1','approved_image_sha256':A['source_sha256'],'actual_pixel_sha256':rawsha(source),'source_path':A['source'],'preset_sha256':sha(P),'extractor_sha256':sha(__file__),'dependencies':[{'path':str((ROOT/A[k]).relative_to(REPO)),'sha256':sha(ROOT/A[k])} for k in ['alignment_contract','semantic_annotation','branch_annotation','volume_annotation']],'classes':classes,'landmarks':lm,'profiles':profiles,'rest_anchors':sockets,'semantic_boundary':'Search boxes, color rules, view identities are explicit human-readable annotation. Native pixel extrema and centroids computed. Hidden sections interpolate missing observations with minimum-bending support prior.','array_digest':digest({k:rawsha(v) for k,v in masks.items()})};return m,masks

def save_measure():
 src=np.array(Image.open(REPO/A['source']).convert('RGB'));assert sha(REPO/A['source'])==A['source_sha256'];m,a=measure(src);np.savez_compressed(BASE/'evidence/masks.npz',**a);m['masks_file_sha256']=sha(BASE/'evidence/masks.npz');gzwrite(BASE/'evidence/measurement.json.gz',m);print(json.dumps({'parts':len(m['profiles']),'hair':m['classes'],'measurement_sha256':sha(BASE/'evidence/measurement.json.gz'),'bytes':disk()}))

def load():
 m=gzread(BASE/'evidence/measurement.json.gz');a=dict(np.load(BASE/'evidence/masks.npz'));src=np.array(Image.open(REPO/A['source']).convert('RGB'))
 if m['actual_pixel_sha256']!=rawsha(src) or m['preset_sha256']!=sha(P) or m['array_digest']!=digest({k:rawsha(v) for k,v in a.items()}):raise ValueError('Stale or absent independent measurement')
 return m,a,src

def radial(poly,center,n):
 p=np.array(poly)-center;area=np.cross(p,np.roll(p,-1,axis=0)).sum();p=p if area>0 else p[::-1];q=np.roll(p,-1,axis=0);edge=q-p;normal=np.c_[edge[:,1],-edge[:,0]];h=(normal*p).sum(1);angle=np.arange(n)*2*np.pi/n;dirs=np.c_[np.cos(angle),np.sin(angle)];den=dirs@normal.T;rs=np.min(np.where(den>1e-10,h[None,:]/np.maximum(den,1e-10),np.inf),axis=1);return np.array(center)+dirs*rs[:,None]

def loft(profile):
 n=A['volumes']['angular_samples'];vv=[];ff=[];sections=profile['sections']
 for s in sections:
  xz=radial(s['polygon_xz_m'],s['center_xz_m'],n);y=sum(s['world_y_range'])/2;vv.extend(np.c_[xz[:,0],np.full(n,y),xz[:,1]])
 for r in range(len(sections)-1):
  for j in range(n):
   k=(j+1)%n;ff.extend([[r*n+j,(r+1)*n+j,(r+1)*n+k],[r*n+j,(r+1)*n+k,r*n+k]])
 for r,sec,sgn in [(0,sections[0],1),(len(sections)-1,sections[-1],-1)]:
  center=len(vv);vv.append([sec['center_xz_m'][0],sec['world_y_range'][1 if sgn>0 else 0],sec['center_xz_m'][1]])
  for j in range(n):ff.append([center,r*n+(j+1)%n,r*n+j] if sgn>0 else [center,r*n+j,r*n+(j+1)%n])
 vv=np.array(vv);ff=np.array(ff,int)
 # Verify outward orientation relative to local measured section center.
 centers=np.array([[s['center_xz_m'][0],sum(s['world_y_range'])/2,s['center_xz_m'][1]] for s in sections]);tri=vv[ff];c=tri.mean(1);ids=np.abs(c[:,1,None]-centers[:,1]).argmin(1);d=c-centers[ids];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);reverse=(norm*d).sum(1)<0;ff[reverse]=ff[reverse][:,[0,2,1]];return vv,ff

def surface_rgb(v,f,source,maskdict,part):
 tri=v[f];p=tri.mean(1);norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-12);names=list(C['views']);cameras=np.array([[math.sin(math.radians(C['views'][q]['yaw_degrees'])),0,math.cos(math.radians(C['views'][q]['yaw_degrees']))] for q in names]);ids=(norm@cameras.T).argmax(1);color=np.zeros((len(f),3),np.uint8);base=read(ROOT/A['volume_annotation'])['material_base_srgb'];fallback=base['hair' if part in ['hair_envelope','head_cap_closed'] else 'stocking' if part.startswith('leg') else 'bodice']
 for j,name in enumerate(names):
  ii=np.where(ids==j)[0];view=C['views'][name];theta=math.radians(view['yaw_degrees']);s=C['alignment']['character_height_m_for_test']/view['scale_px_per_unit'];x=np.floor(view['axis_u']+(p[ii,0]*math.cos(theta)-p[ii,2]*math.sin(theta))/s).astype(int);y=np.floor(view['sole_y']-p[ii,1]/s).astype(int);x=np.clip(x,view['crop'][0],view['crop'][2]-1);y=np.clip(y,view['crop'][1],view['crop'][3]-1);rgb=source[y,x].copy();localx=x-view['crop'][0];localy=y-view['crop'][1];guide=maskdict[name+'_guide'][localy,localx];bad=(rgb.min(1)>225)&(rgb.max(1)-rgb.min(1)<25)|guide
  if part=='hair_envelope':bad|=~maskdict[name+'_hair_eligible'][localy,localx]
  # Side/rear bouquet identity not observed; choose only front or side samples.
  if part=='bouquet_envelope' and name=='back':rgb[:]=[211,201,212];bad[:]=False
  rgb[bad]=fallback;color[ii]=rgb
 return np.clip(np.round(color.astype(float)/8)*8,0,255).astype(np.uint8)

def marching_tetra(field,axes):
 # Standard six tetrahedra per cube. Isosurface is of trilinear-grid samples,
 # preserving every signed component. No component repair or deletion.
 lo=np.minimum.reduce([field[x:x+field.shape[0]-1,y:y+field.shape[1]-1,z:z+field.shape[2]-1] for x,y,z in [(0,0,0),(1,0,0),(0,1,0),(1,1,0),(0,0,1),(1,0,1),(0,1,1),(1,1,1)]]);hi=np.maximum.reduce([field[x:x+field.shape[0]-1,y:y+field.shape[1]-1,z:z+field.shape[2]-1] for x,y,z in [(0,0,0),(1,0,0),(0,1,0),(1,1,0),(0,0,1),(1,0,1),(0,1,1),(1,1,1)]]);active=np.argwhere((lo<=0)&(hi>0));del lo,hi
 offsets=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]]);tets=[[0,1,2,6],[0,2,3,6],[0,3,7,6],[0,7,4,6],[0,4,5,6],[0,5,1,6]];tris=[]
 for origin in active:
  ix=origin+offsets;vals=field[ix[:,0],ix[:,1],ix[:,2]];xyz=np.stack([axes[k][ix[:,k]] for k in range(3)],1)
  for tet in tets:
   good=[k for k in tet if vals[k]>0];bad=[k for k in tet if vals[k]<=0]
   if not good or not bad:continue
   points=[]
   for g in good:
    for b in bad:points.append(xyz[g]+vals[g]/(vals[g]-vals[b])*(xyz[b]-xyz[g]))
   pp=np.array(points);center=pp.mean(0);out=xyz[bad].mean(0)-xyz[good].mean(0);out/=np.linalg.norm(out);a=pp[0]-center;a/=np.linalg.norm(a);b=np.cross(out,a);ang=np.arctan2((pp-center)@b,(pp-center)@a);pp=pp[np.argsort(ang)]
   for j in range(1,len(pp)-1):tris.append([pp[0],pp[j],pp[j+1]])
 t=np.array(tris);u,inv=np.unique(np.round(t.reshape(-1,3),10),axis=0,return_inverse=True);f=inv.reshape(-1,3);return u,f,{'active_grid_cubes':len(active),'surface_triangles':len(f),'all_components_retained':True}

def hair_field(m,a,bodyv,bodyf):
 fv=C['views']['front'];sv=C['views']['side'];fh=a['front_hair_eligible'];sh=a['side_hair_eligible'];sideocc=a['side_face_skin']|a['side_body_exposed_skin']|a['side_bodice_gloves'];frontocc=a['front_face_skin']|a['front_body_exposed_skin']|a['front_bodice_gloves'];zf=depth_image(bodyv,bodyf)
 def sdf(mask):return (ndi.distance_transform_edt(mask)-ndi.distance_transform_edt(~mask)).astype(np.float32)*SCALE
 df=sdf(fh);do=sdf(frontocc);ds=sdf(sh|sideocc);ys,xs=np.where(fh);step=A['hair']['grid_pitch_m'];xa=(xs.min()+fv['crop'][0]-fv['axis_u'])*SCALE-.02;xb=(xs.max()+fv['crop'][0]-fv['axis_u'])*SCALE+.02;ya=(fv['sole_y']-A['hair']['source_y_max_px'])*SCALE-.02;yb=(fv['sole_y']-A['hair']['source_y_min_px'])*SCALE+.02;sy,sx=np.where(sh);u0=(sx.min()+sv['crop'][0]-sv['axis_u'])*SCALE;u1=(sx.max()+sv['crop'][0]-sv['axis_u'])*SCALE;theta=math.radians(sv['yaw_degrees']);zb=(max(math.cos(theta)*xa,math.cos(theta)*xb)-u0)/math.sin(theta)+.02;za=(min(math.cos(theta)*xa,math.cos(theta)*xb)-u1)/math.sin(theta)-.02;axes=[np.arange(math.floor(q/step)*step,w+step,step) for q,w in [(xa,xb),(ya,yb),(za,zb)]];X,Y,Z=np.meshgrid(*axes,indexing='ij');px=fv['axis_u']+X/SCALE-fv['crop'][0]-.5;py=fv['sole_y']-Y/SCALE-.5;coords=np.array([py.ravel(),px.ravel()]);front=ndi.map_coordinates(df,coords,order=1,mode='constant',cval=-1).reshape(X.shape);occ=ndi.map_coordinates(do,coords,order=1,mode='constant',cval=-1).reshape(X.shape);dep=ndi.map_coordinates(np.where(np.isfinite(zf),zf,-10),coords,order=1,mode='constant',cval=-10).reshape(X.shape);front=np.maximum(front,np.minimum(occ,dep-Z-.005));su=sv['axis_u']+(math.cos(theta)*X-math.sin(theta)*Z)/SCALE-sv['crop'][0]-.5;sy=sv['sole_y']-Y/SCALE-.5;side=ndi.map_coordinates(ds,np.array([sy.ravel(),su.ravel()]),order=1,mode='constant',cval=-1).reshape(X.shape);field=np.minimum(front,side).astype(np.float32);del X,Y,Z,coords,front,side,occ,dep,su,sy,px,py
 raw=field>0;field=ndi.gaussian_filter(field,A['hair']['sdf_curvature_sigma_cells'],mode='constant',cval=-.05);cc,n=ndi.label(field>0);report={'shape':list(field.shape),'grid_pitch_m':step,'raw_positive_nodes':int(raw.sum()),'curved_positive_nodes':int((field>0).sum()),'curvature_sign_changed_nodes':int((raw!=(field>0)).sum()),'six_components':int(n),'component_node_counts':sorted(np.bincount(cc.ravel())[1:].tolist(),reverse=True),'back_is_held_out':True,'occlusion_depth_prior_m':.005,'no_island_repair':True};return field,axes,report

def build():
 start=time.monotonic();m,a,source=load();items=[];bodyv=[];bodyf=[];off=0
 for p in m['profiles']:
  v,f=loft(p);rgb=surface_rgb(v,f,source,a,p['id']);items.append((p['id'],v,f,rgb))
  if p['id']!='bouquet_envelope':bodyv.extend(v);bodyf.extend(f+off);off+=len(v)
 field,axes,hreport=hair_field(m,a,np.array(bodyv),np.array(bodyf));v,f,mr=marching_tetra(field,axes);rgb=surface_rgb(v,f,source,a,'hair_envelope');items.append(('hair_envelope',v,f,rgb));np.savez_compressed(BASE/'generated/hair_implicit.npz',field=field,x=axes[0],y=axes[1],z=axes[2]);hreport.update(mr);write(BASE/'evidence/hair_representation.json',hreport);del field
 # Approved measured costume source07 is immutable; full source includes it unchanged.
 cp=ROOT/A['costume_source'];assert sha(cp)==A['costume_sha256'];q=np.load(cp);v=q['vertices'];f=q['triangles'];rgb=surface_rgb(v,f,source,a,'costume')
 # Both sides of cloth remain actual source sheets; normals are not body enclosure.
 items.append(('costume07',v,np.r_[f,f[:,[0,2,1]]],np.r_[rgb,rgb]))
 # Actual observed halo pixels lowered by existing common extrusion adapter.
 old=gzread(ROOT/'full01/generated/accessory_operations.json.gz');ops=[o for o in old['operations'] if o['part']=='halo_observed'];hv=[];hf=[]
 for op in ops:
  for quad in volume.primitive_quads(op):
   off=len(hv);hv.extend(quad);hf.append([off,off+1,off+2]);
   if quad[2]!=quad[3]:hf.append([off,off+2,off+3])
 hv=np.array(hv);hf=np.array(hf,int);items.append(('halo_observed',hv,hf,np.tile([184,92,190],(len(hf),1)).astype(np.uint8)))
 arrays={};parts=[]
 for i,(name,v,f,rgb) in enumerate(items):
  arrays[f'v{i}']=v;arrays[f'f{i}']=f;arrays[f'c{i}']=rgb;parts.append({'index':i,'id':name,'vertices':len(v),'triangles':len(f),'source_bounds_m':[v.min(0).tolist(),v.max(0).tolist()],'closed_topology_expected':name not in ['costume07'],'geometry_digest':rawsha(v[f])})
 np.savez_compressed(BASE/'generated/full_source.npz',**arrays);out={'schema':'riverstone.measured_full_source.v1','status':'FULL_LOW_COST_SOURCE_CANDIDATE_NOT_ART_APPROVED','approved_image_sha256':A['source_sha256'],'measurement_sha256':sha(BASE/'evidence/measurement.json.gz'),'source_sha256':sha(BASE/'generated/full_source.npz'),'preset_sha256':sha(P),'generator_sha256':sha(__file__),'costume_source07_sha256':A['costume_sha256'],'parts':parts,'hair':hreport,'seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'GPU_rig_socket_approved':False,'limits':['Source appearance contains illustration lighting; not recovered albedo','Headcap convex section is a hidden-volume hypothesis, not bare skull measurement','Hair envelope is multiview/occlusion/curvature constrained; no strand identity recovery','Hair back held out due pose mismatch; compare residuals','Bouquet aggregate envelope; individual flowers and ribbon depth unresolved','Costume07 failures retained, no repair']};write(BASE/'evidence/build.json',out);print(json.dumps(out));disk()

if __name__=='__main__':
 if sys.argv[1]=='measure':save_measure()
 elif sys.argv[1]=='build':build()
