"""Generic, seed-guided visible-surface measurements; never generates geometry.

Input semantics are frozen masks. Manual seeds/ROIs are separate from boundaries
computed using source RGB/luminance gradients on a four-neighbour graph. Pixels
outside the mask are never bridged; unseeded components remain unknown. A branch
is a view-local candidate patch, not a recovered sewn panel or physical hair lock.
"""
from __future__ import annotations
import argparse, gzip, hashlib, heapq, io, json, math, time, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
SCHEMA = 'riverstone.measured_surface_branches.v1'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def read(path):
    return json.loads(Path(path).read_text())

def runs(row):
    d = np.diff(np.r_[False, row, False].astype(np.int8))
    return np.column_stack((np.where(d == 1)[0], np.where(d == -1)[0])).tolist()

def row_intervals(mask, crop):
    x0, y0, _, _ = crop
    return [{'y_px': int(y + y0), 'intervals_px': [[int(a + x0), int(b + x0)] for a, b in runs(mask[y])]} for y in np.where(mask.any(axis=1))[0]]

def boxes_mask(shape, crop, boxes):
    m = np.zeros(shape, bool)
    x0, y0, x1, y1 = crop
    for a, b, c, d in boxes:
        if max(a, x0) < min(c, x1) and max(b, y0) < min(d, y1):
            m[max(0,b-y0):min(y1-y0,d-y0), max(0,a-x0):min(x1-x0,c-x0)] = True
    return m

def polygons_mask(shape, crop, polygons):
    im = Image.new('1', (shape[1], shape[0]))
    draw = ImageDraw.Draw(im)
    for p in polygons:
        draw.polygon([(int(x-crop[0]), int(y-crop[1])) for x, y in p], fill=1)
    return np.asarray(im, dtype=bool)

def classify(rgb, rule):
    a = rgb.astype(np.int16)
    r,g,b = a[:,:,0],a[:,:,1],a[:,:,2]
    channels = {'r':r, 'g':g, 'b':b, 'r_minus_g':r-g, 'g_minus_r':g-r, 'r_minus_b':r-b, 'b_minus_r':b-r, 'b_minus_g':b-g, 'g_minus_b':g-b, 'mean':a.mean(2), 'chroma':a.max(2)-a.min(2)}
    out = np.ones(a.shape[:2], bool)
    for key,value in rule.items():
        name,op = key.rsplit('_',1)
        if name not in channels or op not in ('min','max'):
            raise ValueError('Unrecognized color rule: '+key)
        out &= channels[name] >= value if op == 'min' else channels[name] <= value
    return out

def gradients(rgb, config):
    """Only the edge-cost image is smoothed; the input class mask is untouched."""
    a = rgb.astype(np.float32)
    lum = a @ np.array([.2126,.7152,.0722], np.float32)
    lum = ndi.gaussian_filter(lum, float(config['luminance_sigma_px']))
    gx = ndi.sobel(lum, axis=1, mode='nearest')/8.
    gy = ndi.sobel(lum, axis=0, mode='nearest')/8.
    magnitude = np.hypot(gx,gy)
    wrgb,wlum = float(config['rgb_edge_weight']),float(config['luminance_edge_weight'])
    eh = wrgb*np.abs(a[:,1:]-a[:,:-1]).mean(2)+wlum*np.maximum(magnitude[:,1:],magnitude[:,:-1])
    ev = wrgb*np.abs(a[1:]-a[:-1]).mean(2)+wlum*np.maximum(magnitude[1:],magnitude[:-1])
    # Quantization bounds sensitivity to insignificant floating-point noise.
    quant = float(config['edge_quantization'])
    return np.rint(eh*quant).astype(np.int32),np.rint(ev*quant).astype(np.int32)

def select_seeds(mask, crop, branches):
    seeds=[]; records=[];occupied=set()
    for label,branch in enumerate(branches,1):
        target=branch['seed_xy_px']; window=branch['seed_search_box']
        eligible=mask & boxes_mask(mask.shape,crop,[window])
        ys,xs=np.where(eligible)
        candidates=sorted(((int((x+crop[0]-target[0])**2+(y+crop[1]-target[1])**2),int(y),int(x)) for y,x in zip(ys,xs)))
        chosen=next(((y,x) for _,y,x in candidates if (y,x) not in occupied),None)
        record={'requested_xy_px':target,'search_box':window,'accepted_xy_px':None,'status':'no eligible unclaimed source pixel in annotated search box'}
        if chosen is not None:
            y,x=chosen;occupied.add((y,x));seeds.append((label,y,x))
            record['accepted_xy_px']=[x+crop[0],y+crop[1]];record['status']='nearest eligible source pixel inside explicit manual search box'
        records.append(record)
    return seeds,records

def seeded_geodesic(mask, edges, seeds):
    """Marker watershed/minimax geodesic, with shortest 4-connected path tie-break.

    The objective is lexicographic (maximum RGB/luminance gradient crossed,
    source-mask geodesic path length, seed label). No dilation, closing, erosion,
    hole filling, component deletion or connection across absent mask pixels.
    """
    h,w=mask.shape;eh,ev=edges
    labels=np.zeros((h,w),np.int16)
    best_barrier=np.full((h,w),np.iinfo(np.int32).max,np.int32)
    best_length=np.full((h,w),np.iinfo(np.int32).max,np.int32)
    queue=[]
    for label,y,x in seeds:
        labels[y,x]=label;best_barrier[y,x]=0;best_length[y,x]=0
        heapq.heappush(queue,(0,0,label,y,x))
    while queue:
        barrier,length,label,y,x=heapq.heappop(queue)
        if (barrier,length,label)!=(int(best_barrier[y,x]),int(best_length[y,x]),int(labels[y,x])):continue
        neighbours=[]
        if x>0:neighbours.append((y,x-1,int(eh[y,x-1])))
        if x+1<w:neighbours.append((y,x+1,int(eh[y,x])))
        if y>0:neighbours.append((y-1,x,int(ev[y-1,x])))
        if y+1<h:neighbours.append((y+1,x,int(ev[y,x])))
        for ny,nx,cost in neighbours:
            if not mask[ny,nx]:continue
            nb,nl=max(barrier,cost),length+1
            old=(int(best_barrier[ny,nx]),int(best_length[ny,nx]),int(labels[ny,nx]))
            if (nb,nl,label)<old:
                best_barrier[ny,nx]=nb;best_length[ny,nx]=nl;labels[ny,nx]=label
                heapq.heappush(queue,(nb,nl,label,ny,nx))
    return labels

def deterministic_npz(path, arrays):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,array in sorted(arrays.items()):
            stream=io.BytesIO();np.lib.format.write_array(stream,np.asanyarray(array),allow_pickle=False)
            info=zipfile.ZipInfo(name+'.npy',date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,stream.getvalue(),compresslevel=9)

def mask_record(mask,crop):
    ys,xs=np.where(mask)
    return {'pixels':int(mask.sum()),'bbox_xyxy_px':[int(xs.min()+crop[0]),int(ys.min()+crop[1]),int(xs.max()+crop[0]+1),int(ys.max()+crop[1]+1)] if len(xs) else None,'measured_row_intervals':row_intervals(mask,crop)}

def measure(contract_path, annotation_path, masks_path):
    c=read(contract_path);ann=read(annotation_path);source_path=REPO/c['source']
    if sha(source_path)!=c['source_sha256'] or sha(source_path)!=ann['source_sha256']:
        raise ValueError('Approved source hash mismatch')
    if sha(masks_path)!=ann['semantic_masks_sha256']:
        raise ValueError('Frozen semantic mask hash mismatch')
    source=np.array(Image.open(source_path).convert('RGB'))
    raw=np.load(masks_path,allow_pickle=False)
    result={'schema':SCHEMA,'source_path':c['source'],'source_sha256':sha(source_path),'semantic_masks_path':str(Path(masks_path).resolve().relative_to(REPO)),'semantic_masks_sha256':sha(masks_path),'contract_sha256':sha(contract_path),'annotation_sha256':sha(annotation_path),'extractor_sha256':sha(__file__),'coordinates':'source-image global pixels; intervals are [x0,x1), rows at native y; no dimensions/depth recovered','method':ann['method'],'geometry_generated':False,'views':{}}
    arrays={};overlays={};checks={}
    for view,vc in c['views'].items():
        crop=vc['crop'];x0,y0,x1,y1=crop;rgb=source[y0:y1,x0:x1];shape=rgb.shape[:2]
        if raw[view+'_hair_visible'].shape!=shape:raise ValueError('Semantic mask crop shape mismatch')
        va=ann['views'][view]
        guide=classify(rgb,ann['exclusions']['blue_guides']['color_rule']) & boxes_mask(shape,crop,va['guide_search_boxes'])
        halo=polygons_mask(shape,crop,va['halo_exclusion_polygons'])
        arrays[view+'__excluded__blue_guides']=guide;arrays[view+'__excluded__halo_semantic']=halo
        overlay=rgb.astype(float);overlay[guide]=[0,220,245]
        overlay[halo]=rgb[halo]*.5+[110,65,0]
        edges=gradients(rgb,ann['method'])
        vr={'crop':crop,'branches':[],'unknown_by_class':{},'excluded_counts':{'blue_guides':int(guide.sum()),'halo_semantic_envelope':int(halo.sum())},'cross_view_correspondence':'unknown; IDs are deliberately local to each view'}
        viewcheck={}
        for group in va['groups']:
            cl=group['source_class'];original=raw[view+'_'+cl].astype(bool)
            excluded=guide | (halo if cl=='hair_visible' else False)
            roi=boxes_mask(shape,crop,group['search_boxes'])
            clean=original & ~excluded
            domain=clean & roi
            seeds,seed_records=select_seeds(domain,crop,group['branches'])
            labels=seeded_geodesic(domain,edges,seeds)
            assigned=labels>0;unknown=clean & ~assigned
            arrays[view+'__unknown__'+cl]=unknown
            arrays[view+'__eligible__'+cl]=clean
            arrays[view+'__excluded_input__'+cl]=original & excluded
            vr['unknown_by_class'][cl]=dict(mask_record(unknown,crop),reason='unseeded disconnected component or outside explicit semantic search ROI; preserved, never deleted')
            # Retain original uncertainty separately; it never becomes a hard hole.
            arrays[view+'__input_ambiguous__'+cl]=original & raw[view+'_ambiguous']
            arrays[view+'__input_occlusion__'+cl]=original & raw[view+'_semantic_occlusion_envelopes']
            roi_edge=roi & ~ndi.binary_erosion(roi,structure=ndi.generate_binary_structure(2,1),border_value=0)
            for index,branch in enumerate(group['branches'],1):
                m=labels==index;key=view+'__'+branch['id'];arrays[key]=m
                rec=mask_record(m,crop);pix=rgb[m]
                cc,n=ndi.label(m)
                boundary=m & ~ndi.binary_erosion(m,structure=ndi.generate_binary_structure(2,1),border_value=0)
                neighbours=ndi.maximum_filter(labels,size=3)>0
                rec.update({'id':branch['id'],'source_class':cl,'role':branch['role'],'apparent_rgb_median':np.median(pix,axis=0).tolist() if len(pix) else None,'seed_xy_px':seed_records[index-1]['accepted_xy_px'],'seed_annotation':seed_records[index-1],'four_connected_components':int(n),'method':'source RGB/luminance-gradient minimax geodesic from manual seed; per-view candidate patch','uncertainty':{'cross_view_correspondence':'unknown','sewn_panel_identity':'unknown','physical_lock_identity':'unknown','depth':'unknown','boundary_status':'computed image partition, may follow shadow/highlight instead of actual surface separation','roi_boundary_pixels':int((m&roi_edge).sum()),'ambiguous_input_pixels':int((m&raw[view+'_ambiguous']).sum()),'occlusion_envelope_pixels':int((m&raw[view+'_semantic_occlusion_envelopes']).sum()),'tiny_fragments':'none removed; seed-free components remain unknown'}})
                vr['branches'].append(rec)
                color=np.array(branch['display_rgb']);overlay[m]=rgb[m]*.48+color*.52;overlay[boundary]=color*.85
            overlay[unknown]=rgb[unknown]*.55+np.array([100,55,0])
            # Exact partition and no-bridging assertions on frozen masks.
            partition=np.zeros(shape,np.uint8)
            for index in range(1,len(group['branches'])+1):partition+=(labels==index).astype(np.uint8)
            assert not np.any(assigned & ~original)
            assert not np.any(assigned & excluded)
            assert np.all(partition<=1)
            assert np.array_equal(assigned|unknown,clean)
            domain_cc,n=ndi.label(domain);seeded_ids=set(int(domain_cc[y,x]) for _,y,x in seeds)
            unseeded=domain & ~np.isin(domain_cc,list(seeded_ids))
            assert not np.any(assigned & unseeded)
            viewcheck[cl]={'input_pixels':int(original.sum()),'excluded_input_pixels':int((original&excluded).sum()),'assigned_pixels':int(assigned.sum()),'unknown_pixels':int(unknown.sum()),'accepted_seeds':len(seeds),'requested_seeds':len(group['branches']),'partition_exact':True,'no_assigned_pixel_outside_source_class':True,'no_guide_or_halo_assigned':True,'unseeded_components_preserved':True}
        im=Image.fromarray(np.clip(overlay,0,255).astype(np.uint8));d=ImageDraw.Draw(im)
        for branch in vr['branches']:
            seed=branch['seed_xy_px']
            if seed:
                x,y=seed[0]-x0,seed[1]-y0;d.ellipse((x-3,y-3,x+3,y+3),fill='white',outline='black');d.text((x+5,y-5),branch['id'],fill='black',stroke_width=1,stroke_fill='white')
        overlays[view]=im;result['views'][view]=vr;checks[view]=viewcheck
    return result,arrays,overlays,checks

def write_outputs(output,result,arrays,overlays,checks,max_bytes):
    output.mkdir(parents=True,exist_ok=True)
    if (output/'branch_measurements.json.gz').exists():raise ValueError('Refusing to overwrite existing measurements; use --verify for a read-only replay')
    deterministic_npz(output/'branch_masks.npz',arrays)
    result['branch_masks_sha256']=sha(output/'branch_masks.npz')
    payload=gzip.compress(canonical(result),mtime=0)
    (output/'branch_measurements.json.gz').write_bytes(payload)
    for view,im in overlays.items():im.save(output/(view+'_branch_overlay.png'),optimize=True)
    sheet=Image.new('RGB',(1536,690),'white');d=ImageDraw.Draw(sheet)
    d.text((12,8),'Measured view-local face / hair branches. Seeds and search regions are manual; boundaries use actual pixel gradients.',fill='black')
    d.text((12,27),'Amber: unknown. Cyan: excluded blue guides. Halo envelope: explicitly excluded. No cross-view correspondence or depth claimed.',fill='black')
    for i,view in enumerate(('front','side','back')):
        im=overlays[view].copy();im.thumbnail((500,624));sheet.paste(im,(i*512+6,52));d.text((i*512+10,673),view,fill='black')
    sheet.save(output/'branch_measurement_review.jpg',quality=86)
    summary={'schema':SCHEMA,'source_sha256':result['source_sha256'],'measurement_sha256':sha(output/'branch_measurements.json.gz'),'branch_masks_sha256':result['branch_masks_sha256'],'annotation_sha256':result['annotation_sha256'],'checks':checks,'geometry_generated':False,'cross_view_correspondence':'unknown','measurement_semantics':'Visible geodesic image regions, not verified sewn panels or physical locks'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    total=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    if total>max_bytes:raise ValueError(f'Branch output exceeds budget: {total} > {max_bytes}')
    return dict(summary,output_bytes=total,output_budget_bytes=max_bytes)

def verify_existing(output,result,arrays,checks):
    saved=json.loads(gzip.decompress((output/'branch_measurements.json.gz').read_bytes()))
    result['branch_masks_sha256']=sha(output/'branch_masks.npz')
    same_measurement=canonical(result)==canonical(saved)
    existing=np.load(output/'branch_masks.npz',allow_pickle=False)
    same_masks=set(existing.files)==set(arrays) and all(np.array_equal(existing[k],arrays[k]) for k in arrays)
    report={'same_measurement_json':same_measurement,'same_every_mask_array':same_masks,'independent_process_replay':True,'checks':checks,'source_sha256':result['source_sha256'],'measurement_sha256':sha(output/'branch_measurements.json.gz')}
    if not same_measurement or not same_masks:raise ValueError('Replay differs from saved data')
    (output/'reproducibility.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract',type=Path,default=ROOT/'data/measurement_contract.json')
    p.add_argument('--annotations',type=Path,default=ROOT/'data/violet_surface_branch_annotations.json')
    p.add_argument('--semantic-masks',type=Path,default=ROOT/'full_measurement/violet_v02/semantic_masks.npz')
    p.add_argument('--output',type=Path,default=ROOT/'full_measurement/violet_branches')
    p.add_argument('--max-output-bytes',type=int,default=2*1024*1024)
    p.add_argument('--verify',action='store_true',help='Recompute and compare to existing outputs; preserve measured files')
    a=p.parse_args();t=time.perf_counter();res,arr,ims,checks=measure(a.contract,a.annotations,a.semantic_masks)
    report=verify_existing(a.output,res,arr,checks) if a.verify else write_outputs(a.output,res,arr,ims,checks,a.max_output_bytes)
    print(json.dumps({'seconds':round(time.perf_counter()-t,3),**report}))
