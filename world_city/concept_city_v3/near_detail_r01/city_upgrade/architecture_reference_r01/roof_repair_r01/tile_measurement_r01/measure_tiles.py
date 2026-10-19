#!/usr/bin/env python3
"""Bounded source-raster appearance extraction. No geometry, warp, or height inference."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'voxel_character/common/core.py').exists())
Q=HERE.parent.parent/'reconstruction_proof_r01/roof_measurement_r01'
SOURCE=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
EXCLUDED=[{'bbox_px':[756,772,783,982],'reason':'Entire ambiguous ridge-cap ROI, including frozen uncertain axis 766..772'}, {'bbox_px':[865,795,925,879],'reason':'Expanded chimney, rim, apparent face and shadow ROI; frozen held-out chimney failure retained'}]
PLANES=[('left',[616,791,756,974]),('right',[783,791,919,974])]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x): return hashlib.sha256(canonical(x).encode()).hexdigest()
def overlap(a,b): return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def crop(im,b): return im[b[1]:b[3],b[0]:b[2]]
def peaks(profile,distance,prominence):
    """Actual strict/plateau troughs; deterministic prominence and nonmax suppression."""
    v=-np.asarray(profile); candidates=[]; i=1
    while i<len(v)-1:
        if v[i]>v[i-1]:
            j=i
            while j+1<len(v) and v[j+1]==v[i]: j+=1
            if j+1<len(v) and v[j]>v[j+1]: candidates.append((i+j)//2)
            i=j+1
        else: i+=1
    accepted=[]
    for i in sorted(candidates,key=lambda i:(-v[i],i)):
        if any(abs(i-j)<distance for j in accepted): continue
        lo=hi=float(v[i])
        for j in range(i-1,-1,-1):
            if v[j]>v[i]: break
            lo=min(lo,float(v[j]))
        for j in range(i+1,len(v)):
            if v[j]>v[i]: break
            hi=min(hi,float(v[j]))
        p=float(v[i])-max(lo,hi)
        if p>=prominence: accepted.append(i)
    result=[]
    for i in sorted(accepted):
        # Local contrast is a reproducible strength score, not a statistical CI.
        window=np.asarray(profile)[max(0,i-3):min(len(v),i+4)]
        result.append((i,float(window.max()-profile[i])))
    return result

def sample_color(im,b):
    x0,y0,x1,y1=b
    ib=[x0+2,y0+1,x1-2,y1-1]
    if ib[2]<=ib[0] or ib[3]<=ib[1]: raise ValueError('No interior')
    a=crop(im,ib); f=a.reshape(-1,3).astype(float)
    good=(f[:,0]>f[:,1]*1.45)&(f[:,1]>f[:,2]*1.15)&(f[:,0]>90)
    ids=np.flatnonzero(good)
    if len(ids)<3: return None
    med=np.median(f[ids],axis=0); k=int(ids[np.argmin(((f[ids]-med)**2).sum(1))]); w=ib[2]-ib[0]
    return {'interior_bbox_px':ib,'support_pixels':int(len(ids)), 'median_rgb':[round(float(v),3) for v in med], 'source_sample_px':[int(ib[0]+k%w),int(ib[1]+k//w)],'source_sample_rgb':f[k].astype(int).tolist()}

def extract(im,coef):
    strips=[]; regions=[]; rejected=[]
    for side,box in PLANES:
        # Shared U seams are derived only from a clear depth interval below chimney shadow.
        ub=[box[0],884,box[2],963]; up=crop(im,ub).mean(axis=(0,2))
        us=peaks(up,7,18); edges=[(box[0],0,True)]+[(box[0]+i,p,False) for i,p in us]+[(box[2],0,True)]
        for ci,((u0,p0,partial0),(u1,p1,partial1)) in enumerate(zip(edges,edges[1:])):
            if not 7<=u1-u0<=16: continue
            center=(u0+u1)//2; vb=[center-1,box[1],center+2,box[3]]
            vp=crop(im,vb).mean(axis=(1,2)); vs=peaks(vp,6,10)
            ve=[(box[1],0,True)]+[(box[1]+i,p,False) for i,p in vs]+[(box[3],0,True)]
            strip_id=f'{side}_{ci:02d}'
            strips.append({'id':strip_id,'side':side,'u_interval_px':[u0,u1],'u_profile_roi_px':ub,'u_edge_strength':[round(p0,3),round(p1,3)],'u_partial_endpoints':[partial0,partial1],'local_v_profile_roi_px':vb,'local_v_troughs_px':[v for v,p,t in ve if not t],'local_v_strength':[round(p,3) for v,p,t in ve if not t]})
            for ri,((v0,q0,pv0),(v1,q1,pv1)) in enumerate(zip(ve,ve[1:])):
                b=[u0,v0,u1,v1]; reason=None
                if not 5<=v1-v0<=21: reason='Local interval outside bounded 5..21px support; no invented row subdivision'
                if any(overlap(b,e['bbox_px']) for e in EXCLUDED): reason='Intersects excluded ridge/chimney/shadow ROI'
                if reason: rejected.append({'strip':strip_id,'bbox_px':b,'reason':reason}); continue
                color=sample_color(im,b)
                if color is None: rejected.append({'strip':strip_id,'bbox_px':b,'reason':'Insufficient terracotta interior pixel support'});continue
                partial=[partial0,pv0,partial1,pv1]
                strength=min(p for p in [p0,q0,p1,q1] if p>0)
                confidence=min(1.,strength/40.)*(.55 if any(partial) else 1.)
                regions.append({'id':f'{strip_id}_r{ri:02d}','strip_id':strip_id,'side':side,'bbox_px':b,'diagnostic_xz_bbox':[round(coef['sx']*u0+coef['tx'],8),round(coef['sz']*v0+coef['tz'],8),round(coef['sx']*u1+coef['tx'],8),round(coef['sz']*v1+coef['tz'],8)],'partial_endpoints_left_top_right_bottom':partial,'appearance_separator_width_px_left_top_right_bottom':[0 if endpoint else 1 for endpoint in partial],'confidence_strength_score':round(confidence,4),'boundary_source_px':[[u0,884],[center,v0],[u1,884],[center,v1]],'local_v_profile_sha256':hashlib.sha256(crop(im,vb).tobytes()).hexdigest(),'color':color})
    # Six actual RGB samples, selected deterministically as medoids of brightness-ordered
    # groups of measured per-region colors. Brightness is used only for palette grouping.
    order=sorted(range(len(regions)),key=lambda i:(sum(regions[i]['color']['source_sample_rgb']),regions[i]['id']))
    palette=[]
    for pi,group in enumerate(np.array_split(order,6)):
        vals=np.array([regions[int(i)]['color']['source_sample_rgb'] for i in group],dtype=float)
        med=np.median(vals,axis=0); j=int(group[int(np.argmin(((vals-med)**2).sum(1)))]); c=regions[j]['color']
        palette.append({'id':pi,'rgb':c['source_sample_rgb'],'source_px':c['source_sample_px'],'source_region_id':regions[j]['id']})
    pal=np.array([p['rgb'] for p in palette],dtype=float)
    for r in regions:
        r['color']['palette_id']=int(np.argmin(((pal-np.array(r['color']['median_rgb']))**2).sum(1)))
    return {'strips':strips,'regions':regions,'palette':palette,'rejected_regions':rejected}

def main():
    contract=json.loads((Q/'measurement_contract.json').read_text()); measurements=json.loads((Q/'measurements.json').read_text())
    deps={str(p.relative_to(ROOT)):sha(p) for p in [SOURCE,Q/'measurement_contract.json',Q/'measurements.json']}
    assert sha(SOURCE)==contract['source_image']['sha256']
    assert sha(Q/'measurements.json')==contract['measurements']['sha256']
    im=np.asarray(Image.open(SOURCE).convert('RGB')); assert im.shape==(1024,1536,3)
    coef=contract['conditional_local_registration']['coefficients']; data=extract(im,coef)
    regions=data['regions']; assert len(regions)>200
    for i,a in enumerate(regions):
        assert all(not overlap(a['bbox_px'],b['bbox_px']) for b in regions[i+1:])
        assert all(not overlap(a['bbox_px'],e['bbox_px']) for e in EXCLUDED)
    assert all(im[p['source_px'][1],p['source_px'][0]].tolist()==p['rgb'] for p in data['palette'])
    deterministic=digest(data)==digest(extract(im,coef))
    # In-memory source-pixel perturbations are tests only, never written as images.
    chosen=next(r for r in regions if not any(r['partial_endpoints_left_top_right_bottom']) and r['bbox_px'][1]>890)
    mutated=im.copy(); ib=chosen['color']['interior_bbox_px']; pal=data['palette']; old=chosen['color']['palette_id']; new=max(range(6),key=lambda j:sum((pal[j]['rgb'][c]-pal[old]['rgb'][c])**2 for c in range(3)))
    mutated[ib[1]:ib[3],ib[0]:ib[2]]=pal[new]['rgb']; after=sample_color(mutated,chosen['bbox_px']); after_id=int(np.argmin(((np.array([p['rgb'] for p in pal])-np.array(after['median_rgb']))**2).sum(1)))
    color_changed=after['source_sample_rgb']!=chosen['color']['source_sample_rgb'] and after_id!=old
    # Erase one actual local V seam band from its narrow source strip, then add a
    # shifted dark terracotta seam. Re-extract: local endpoints must respond.
    strip=next(s for s in data['strips'] if s['id']==chosen['strip_id']); vb=strip['local_v_profile_roi_px']; seam=chosen['bbox_px'][3]
    mutated=im.copy(); mutated[seam-2:seam+4,vb[0]:vb[2]]=[220,95,42]; mutated[seam+2,vb[0]:vb[2]]=[70,24,12]
    newdata=extract(mutated,coef); newstrip=next(s for s in newdata['strips'] if s['id']==strip['id']); boundary_changed=strip['local_v_troughs_px']!=newstrip['local_v_troughs_px']
    tests={'deterministic_data_repeat':deterministic,'finite_nonoverlapping_regions':True,'excluded_roi_intersections':0,'palette_actual_source_pixels':True,'source_dependencies_unchanged':all(sha(ROOT/p)==h for p,h in deps.items()),'color_mutation':{'passed':color_changed,'region_id':chosen['id'],'mutated_source_bbox_px':ib,'before_rgb':chosen['color']['source_sample_rgb'],'after_rgb':after['source_sample_rgb'],'before_palette_id':old,'after_palette_id':after_id,'palette_held_fixed_to_isolate_color_assignment':True},'boundary_mutation':{'passed':boundary_changed,'strip_id':strip['id'],'mutated_source_bbox_px':[vb[0],seam-2,vb[2],seam+4],'before_v_troughs_px':strip['local_v_troughs_px'],'after_v_troughs_px':newstrip['local_v_troughs_px']},'resource_limits':{'address_space_mib':256,'cpu_seconds':30}}
    assert deterministic and color_changed and boundary_changed and tests['source_dependencies_unchanged']
    report={'schema':'riverstone.top_local_tile_appearance.v1','source_dependencies':deps,'script_sha256':sha(Path(__file__)),'original_global_registration_accepted':False,'real_world_scale_measured':False,'conditional_mapping':contract['conditional_local_registration'],'excluded_regions':EXCLUDED,'appearance_separator_policy':{'width_px':1,'origin':'Declared conservative appearance separator, not a measured dark-band width or depth','interpretation':'Total width centered on each measured trough boundary; each adjacent tile inset by 0.5px. Partial ROI endpoints get width 0. Geometry thickness and grid quantization must be declared separately.','brightness_to_depth':False},'safe_plane_rois':PLANES,'interpretation':'Rectangles bound local appearance intervals between observed profile troughs. They are finite nonoverlapping proxies, not proven closed tile outlines. Shared U boundaries use unoccluded depth-profile evidence; each strip has independently observed local V seams. Source brightness only measures appearance, never height. Any later thickness is an explicit thin-tile prior.','confidence_definition':'Minimum nonzero local contrast / 40, clamped to 1; multiplied by 0.55 for ROI-clipped partial endpoints. Heuristic strength, not probability or geometric accuracy.','coordinate_convention':'All boxes [u0,v0,u1,v1) in original raster. Diagnostic X/Z mapping is conditional planned-template units, not a global inverse or physical survey.','seam_graph_definition':'Each strip stores shared ordered U edges and ordered local V seam nodes. Each region references its strip and four endpoint pixels; T-junctions across strips are allowed because row phases differ. U boundary_source_px gives the beginning of the profile ROI rather than asserting a trough at every endpoint.','geometry_created':False,'image_written_or_warped':False,'compiler_invoked':False,'counts':{'strips':len(data['strips']),'regions':len(regions),'partial_regions':sum(any(r['partial_endpoints_left_top_right_bottom']) for r in regions),'palette':len(data['palette']),'rejected_regions':len(data['rejected_regions'])},**data}
    (HERE/'tile_regions.json').write_text(canonical(report)+'\n');(HERE/'validation.json').write_text(json.dumps(tests,indent=2,sort_keys=True)+'\n')
    assert sum(p.stat().st_size for p in HERE.iterdir() if p.is_file())<2*1024*1024
    print(json.dumps({'counts':report['counts'],'validation':tests,'data_sha256':sha(HERE/'tile_regions.json')}))
if __name__=='__main__':main()
