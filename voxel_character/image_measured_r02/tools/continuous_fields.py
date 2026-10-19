"""Measured cross-sections, explicitly annotated semantic axes, inferred depth.

Width evidence and censored/occluded samples are recorded separately. The volume
field is never described as an automatically recovered anatomy or hidden view.
"""
import numpy as np
from scipy import ndimage as ndi
from PIL import Image,ImageDraw

def fields(rules,pixels,source,mpp,out):
 mask=pixels['mask'];sem=pixels['semantic'];h,w=mask.shape
 lo=np.full((h,w),np.inf,np.float32);hi=np.full((h,w),-np.inf,np.float32);part=np.zeros((h,w),np.uint8)
 records=[];drawimage=Image.fromarray(source.copy());draw=ImageDraw.Draw(drawimage)
 for pi,section in enumerate(rules['body_sections'],1):
  pts=np.array(section['axis_pixels'],float);delta=np.diff(pts,axis=0);lens=np.linalg.norm(delta,axis=1);arc=np.r_[0,np.cumsum(lens)]
  samples=np.linspace(0,arc[-1],max(4,int(arc[-1]/9)+1));widths=[];sample_records=[]
  bx0,by0,bx1,by1=section['roi'];limit=section['search_halfwidth_pixels']
  for s in samples:
   j=min(len(lens)-1,np.searchsorted(arc,s,side='right')-1);t=(s-arc[j])/lens[j];center=pts[j]+delta[j]*t;normal=np.array([-delta[j,1],delta[j,0]])/lens[j]
   offsets=np.arange(-limit,limit+1);xy=center[None,:]+offsets[:,None]*normal;ix=np.clip(np.rint(xy[:,0]).astype(int),0,w-1);iy=np.clip(np.rint(xy[:,1]).astype(int),0,h-1)
   inside=(ix>=bx0)&(ix<bx1)&(iy>=by0)&(iy<by1)
   accepted=mask[iy,ix]&np.isin(sem[iy,ix],section['accepted_semantics'])&inside
   # Close only 1-2 source-pixel antialias/ink gaps; never a large anatomical gap.
   accepted=ndi.binary_closing(accepted,structure=np.ones(3))&inside
   left=right=limit
   if accepted[limit]:
    while left>0 and accepted[left-1]:left-=1
    while right<len(accepted)-1 and accepted[right+1]:right+=1
   valid=accepted[limit] and right-left>=section['minimum_radius_pixels']*1.4
   censored=valid and (left==0 or right==len(accepted)-1 or not inside[max(0,left-1)] or not inside[min(len(inside)-1,right+1)])
   radius=(right-left+1)/2 if valid else float(section['occluded_width_pixels'] or section['minimum_radius_pixels'])
   radius=max(section['minimum_radius_pixels'],min(radius,limit))
   widths.append(radius);sample_records.append({'arc_pixels':float(s),'axis_pixel':center.tolist(),'halfwidth_pixels':float(radius),'status':'source semantic boundary' if valid and not censored else ('ROI-censored source width' if valid else 'occluded/uncertain width prior'),'sample_endpoints':xy[[left,right]].tolist() if valid else None})
   if valid:
    aa,bb=xy[left],xy[right];draw.line((*aa,*bb),fill=(0,160,60) if not censored else (230,160,0),width=1)
  widths=ndi.gaussian_filter1d(np.array(widths,float),1.1)
  for a,b in zip(pts[:-1],pts[1:]):draw.line((*a,*b),fill=(230,70,0),width=2)
  x0=max(0,int(pts[:,0].min()-limit-2));x1=min(w,int(pts[:,0].max()+limit+3));y0=max(0,int(pts[:,1].min()-limit-2));y1=min(h,int(pts[:,1].max()+limit+3));yy,xx=np.mgrid[y0:y1,x0:x1]
  dist2=np.full(xx.shape,np.inf);nearest_arc=np.zeros(xx.shape)
  for j,(a,b) in enumerate(zip(pts[:-1],pts[1:])):
   vx,vy=b-a;t=np.clip(((xx-a[0])*vx+(yy-a[1])*vy)/(vx*vx+vy*vy),0,1);ds=(xx-a[0]-t*vx)**2+(yy-a[1]-t*vy)**2;take=ds<dist2;dist2[take]=ds[take];nearest_arc[take]=arc[j]+t[take]*lens[j]
  radius=np.interp(nearest_arc,samples,widths);valid=(dist2<radius**2)&mask[y0:y1,x0:x1]
  # Circular/elliptic cross-section; unseen depth radius is an explicit prior.
  half=mpp*radius*section['depth_radius_ratio']*np.sqrt(np.maximum(0,1-dist2/np.maximum(radius**2,1)));half=np.maximum(half,.00625)
  z=section['center_z_m'];ls=lo[y0:y1,x0:x1];hs=hi[y0:y1,x0:x1];ps=part[y0:y1,x0:x1]
  ls[valid]=np.minimum(ls[valid],z-half[valid]);replace=valid&(z+half>hs);hs[valid]=np.maximum(hs[valid],z+half[valid]);ps[replace]=pi
  records.append({'id':section['id'],'axis_status':'manual semantic annotation','samples':sample_records,'smoothed_halfwidth_pixels':widths.tolist(),'depth_radius_ratio_assumed':section['depth_radius_ratio'],'projected_width_clipped_to_source_foreground':True})
 body=np.isfinite(lo);yy,xx=np.mgrid[:h,:w]
 # Long hair is a smooth distance-field volume connected to the head volume.
 hair=(sem==2)&mask;distance=ndi.gaussian_filter(ndi.distance_transform_edt(hair),rules['hair']['distance_smooth_sigma_pixels']);radius=np.minimum(rules['hair']['maximum_radius_m'],rules['hair']['minimum_radius_m']+distance*mpp*.7)
 hair_lo=rules['hair']['center_z_m']-radius;hair_hi=rules['hair']['center_z_m']+radius
 lo[hair]=np.minimum(lo[hair],hair_lo[hair]);hi[hair]=np.maximum(hi[hair],hair_hi[hair]);part[hair&~body]=8
 # A continuous field, rather than independent color-labelled cloth fragments.
 cloth=mask&np.isin(sem,[1,8])&~body;cr=rules['cloth'];lum=source.mean(axis=2)/255
 smooth=ndi.gaussian_filter(lum*mask,cr['luminance_sigma_pixels'])/np.maximum(.001,ndi.gaussian_filter(mask.astype(float),cr['luminance_sigma_pixels']))
 center=cr['center_z_m']+cr['continuous_fold_amplitude_m']*np.sin((xx/w*1.45+yy/h*.32)*np.pi)+(smooth-.72)*.07
 waist=cr['waist_attachment_pixel'];attachment=np.exp(-((xx-waist[0])**2+(yy-waist[1])**2)/(2*cr['waist_attachment_radius_pixels']**2));center=center*(1-attachment)+cr['waist_center_z_m']*attachment
 lo[cloth]=center[cloth]-cr['half_thickness_m'];hi[cloth]=center[cloth]+cr['half_thickness_m'];part[cloth]=9
 for sid,key,pid in [(5,'halo',10),(6,'bouquet',11),(7,'ribbon',12)]:
  chosen=(sem==sid)&mask;rule=rules[key];rad=rule.get('half_thickness_m',rule.get('depth_radius_m'));center=rule['center_z_m']
  lo[chosen]=center-rad;hi[chosen]=center+rad;part[chosen]=pid
 missing=mask&~np.isfinite(lo);lo[missing]=-.07;hi[missing]=.07;part[missing]=13
 # No separate image-colour plates: colours will paint the front cells of this field.
 assert np.all(lo[mask]<hi[mask]);drawimage.save(out/'measured_cross_sections.png')
 return lo,hi,part,records
