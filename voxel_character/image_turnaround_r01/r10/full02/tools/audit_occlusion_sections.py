"""Small XZ-section counterfactual, not new geometry or output repair."""
from pipeline import *

def depth(v,f,view):
 x0,y0,x1,y1=view['crop'];zbuf=np.full((y1-y0,x1-x0),-np.inf);theta=math.radians(view['yaw_degrees']);s=SCALE
 for t in v[f]:
  u=t[:,0]*math.cos(theta)-t[:,2]*math.sin(theta);zz=t[:,0]*math.sin(theta)+t[:,2]*math.cos(theta);p=np.c_[view['axis_u']+u/s-x0,view['sole_y']-t[:,1]/s-y0];lo=np.maximum(np.floor(p.min(0)).astype(int),0);hi=np.minimum(np.ceil(p.max(0)).astype(int),[x1-x0,y1-y0])
  if np.any(hi<=lo):continue
  xx,yy=np.meshgrid(np.arange(lo[0],hi[0])+.5,np.arange(lo[1],hi[1])+.5);aa,bb,cc=p;den=(bb[1]-cc[1])*(aa[0]-cc[0])+(cc[0]-bb[0])*(aa[1]-cc[1])
  if abs(den)<1e-12:continue
  wa=((bb[1]-cc[1])*(xx-cc[0])+(cc[0]-bb[0])*(yy-cc[1]))/den;wb=((cc[1]-aa[1])*(xx-cc[0])+(aa[0]-cc[0])*(yy-cc[1]))/den;wc=1-wa-wb;inside=(wa>=-1e-8)&(wb>=-1e-8)&(wc>=-1e-8);z=wa*zz[0]+wb*zz[1]+wc*zz[2];cut=zbuf[lo[1]:hi[1],lo[0]:hi[0]];cut[inside]=np.maximum(cut[inside],z[inside])
 return zbuf

def run():
 start=time.monotonic();m,a,src=load();q=np.load(BASE/'generated/full_source.npz');b=read(BASE/'evidence/build.json');v=[];f=[];off=0
 for p in b['parts'][:6]:
  i=p['index'];vv=q[f'v{i}'];ff=q[f'f{i}'];v.extend(vv);f.extend(ff+off);off+=len(vv)
 v=np.array(v);f=np.array(f);dz={name:depth(v,f,C['views'][name]) for name in ['front','side']};hair=np.load(BASE/'generated/hair_implicit.npz');X,Z=np.meshgrid(hair['x'],hair['z'],indexing='ij');costume=np.load(ROOT/'whole_source07/evidence/measurement.npz');overlaps={};sections=[];sheet=Image.new('RGB',(1200,900),'white');draw=ImageDraw.Draw(sheet);draw.text((10,10),'XZ section diagnosis | purple existing / yellow additionally allowed behind closed body | not new geometry',fill='black')
 for name in ['front','side','back']:
  ha=a[name+'_hair_eligible'];cl=costume[name+'_support'];ov=ha&cl;overlaps[name]={'observed_hair_and_costume07_overlap_pixels':int(ov.sum()),'ownership':'Unknown/conflicting semantic labels, must resolve from pixels before shape. Existing output untouched.'}
 for j,py in enumerate([175,205,240,280,340,400]):
  Y=(C['views']['front']['sole_y']-py-.5)*SCALE;current=hair['field'][:,np.argmin(abs(hair['y']-Y)),:]>0;allowed=[];coloronly=[];details={}
  for name in ['front','side']:
   vw=C['views'][name];theta=math.radians(vw['yaw_degrees']);uu=vw['axis_u']+(math.cos(theta)*X-math.sin(theta)*Z)/SCALE-vw['crop'][0]-.5;vv=np.full_like(uu,vw['sole_y']-Y/SCALE-.5);co=np.array([vv.ravel(),uu.ravel()]);hm=ndi.map_coordinates(a[name+'_hair_eligible'].astype(float),co,order=0,mode='constant',cval=0).reshape(X.shape)>0;dm=ndi.map_coordinates(np.where(np.isfinite(dz[name]),dz[name],-10),co,order=0,mode='constant',cval=-10).reshape(X.shape);camera_depth=math.sin(theta)*X+math.cos(theta)*Z;behind=camera_depth<=dm-.005;occ=(a[name+'_face_skin']|a[name+'_body_exposed_skin']|a[name+'_bodice_gloves']);cm=ndi.map_coordinates(occ.astype(float),co,order=0,mode='constant',cval=0).reshape(X.shape)>0;closed=hm|behind;colored=hm|(behind&cm);allowed.append(closed);coloronly.append(colored);details[name]={'color_only_occlusion_rejected_but_closed_body_occluded_nodes':int((closed&~colored).sum())}
  changed=allowed[0]&allowed[1];oldbinary=coloronly[0]&coloronly[1];newallowed=changed&~oldbinary;rgb=np.full((*X.shape,3),245,np.uint8);rgb[current]=[105,65,140];rgb[newallowed]=[225,180,40];im=Image.fromarray(rgb.transpose(1,0,2)).resize((370,370),Image.Resampling.NEAREST);sheet.paste(im,((j%3)*400+10,(j//3)*430+50));draw.text(((j%3)*400+10,(j//3)*430+30),'front y=%d; new hidden nodes=%d'%(py,newallowed.sum()),fill='black');sections.append({'front_source_pixel_y':py,'world_y_m':Y,'existing_smoothed_positive_nodes':int(current.sum()),'original_color_occlusion_binary_nodes':int(oldbinary.sum()),'closed_body_occlusion_binary_nodes':int(changed.sum()),'additional_behind_occluder_nodes':int(newallowed.sum()),'views':details})
 sheet.save(BASE/'generated/occlusion_section_diagnostic.jpg',quality=88);out={'status':'DIAGNOSTIC_ONLY_EXISTING_GEOMETRY_UNCHANGED','source_geometry_sha256':sha(BASE/'generated/full_source.npz'),'script_sha256':sha(__file__),'overlap':overlaps,'sections':sections,'finding':'Skin/cloth color labels omit eyes, ornament and shading pixels. They are insufficient occluders and incorrectly carve hidden hair. A closed-head/body projected occlusion mask is a geometric prior and must be separated from observed color classes. This counterfactual is not validated topology or automatic completion.','seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024};write(BASE/'evidence/occlusion_section_audit.json',out);print(json.dumps(out))
if __name__=='__main__':run()
