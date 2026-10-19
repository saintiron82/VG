#!/usr/bin/env python3
"""Read-only independent source/provenance gates and adversarial tests.

No common compiler or mesher is invoked. Raster reads verify recorded evidence,
not continuous-shape sampling. Mutated test data stays exclusively in memory.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(60,)*2)
import argparse,copy,hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent;R=HERE.parent;ARCH=R.parent
ROOT=next(p for p in HERE.parents if (p/'voxel_character/common/core.py').exists())
sys.path.insert(0,str(ROOT))
from voxel_character.common import core
from validate_exterior import ref,sha,read,save
Q=ARCH/'reconstruction_proof_r01/roof_measurement_r01'
T=R/'tile_measurement_r01'
SOURCE=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
FROZEN_SOURCE_SHA='552b0bd61eba3c3f5bee98a6b3a5fac085362dc8804e049e325db55fb902ec93'
FROZEN_CONTRACT_SHA='ba6bc11b5e37e28b42a25d0f55b73b045f317f7f29d8bcf696bbe140c6b1dac3'
FROZEN_MEASUREMENTS_SHA='307f3e8c148dd04a19fab4dbb1eb5163daefba0a6c2c1066f407f9d26e239c06'

def require(test,message):
    if not test:raise ValueError(message)
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def finite_nums(a,n):return isinstance(a,list) and len(a)==n and all(type(x) in (int,float) and math.isfinite(x) for x in a)
def bbox(a):return finite_nums(a,4) and all(type(x)is int for x in a) and a[0]<a[2] and a[1]<a[3]
def contained(a,b):return b[0]<=a[0]<a[2]<=b[2] and b[1]<=a[1]<a[3]<=b[3]
def valid_px(p,im):return isinstance(p,list) and len(p)==2 and all(type(x)is int for x in p) and 0<=p[0]<im.shape[1] and 0<=p[1]<im.shape[0]

def validate_tiles(data,contract,im,dependencies):
    require(data.get('schema')=='riverstone.top_local_tile_appearance.v1','Tile schema')
    require(data.get('source_dependencies')==dependencies,'Tile source dependency mismatch')
    require(data.get('script_sha256')==sha(T/'measure_tiles.py'),'Tile measurement script mismatch')
    require(data.get('conditional_mapping')==contract['conditional_local_registration'],'Conditional mapping differs from frozen contract')
    require(data.get('original_global_registration_accepted') is False and data.get('real_world_scale_measured') is False,'Unsupported metric acceptance')
    require(data.get('compiler_invoked') is False and data.get('image_written_or_warped') is False,'Image-only measurement flags')
    expected_rois=[['left',[616,791,756,974]],['right',[783,791,919,974]]]
    expected_excluded=[[756,772,783,982],[865,795,925,879]]
    require(data['safe_plane_rois']==expected_rois,'Plane ROI change')
    require([e['bbox_px'] for e in data['excluded_regions']]==expected_excluded,'Excluded ridge or chimney ROI change')
    rois=dict(expected_rois);strips={};palette={};regions={};coef=contract['conditional_local_registration']['coefficients']
    for s in data['strips']:
        require(s['id'] not in strips and s['side'] in rois,'Duplicate/unknown strip')
        strips[s['id']]=s;u0,u1=s['u_interval_px'];box=rois[s['side']]
        require(type(u0)is int and type(u1)is int and box[0]<=u0<u1<=box[2],'Invalid strip extent')
        nodes=s['local_v_troughs_px']
        require(nodes==sorted(set(nodes)) and all(type(v)is int and box[1]<v<box[3] for v in nodes),'Invalid local seam nodes')
        vb=s['local_v_profile_roi_px'];require(bbox(vb) and contained(vb,box),'Invalid local profile ROI')
    for p in data['palette']:
        require(type(p['id'])is int and p['id'] not in palette,'Duplicate/invalid palette ID')
        require(valid_px(p['source_px'],im),'Invalid palette source pixel')
        require(im[p['source_px'][1],p['source_px'][0]].tolist()==p['rgb'],'Palette RGB not at recorded source pixel')
        palette[p['id']]=p
    require(sorted(palette)==list(range(6)),'Six source palette IDs required')
    palette_colors=np.array([palette[i]['rgb'] for i in range(6)])
    occupied=np.zeros(im.shape[:2],np.bool_)
    for r in data['regions']:
        require(r['id'] not in regions and r['strip_id'] in strips,'Duplicate/unknown tile region provenance')
        regions[r['id']]=r;s=strips[r['strip_id']];box=rois[s['side']];b=r['bbox_px']
        require(bbox(b) and contained(b,box),'Invalid/outside tile box')
        require(r['side']==s['side'],'Tile side differs from source strip')
        require(all(not overlap(b,e) for e in expected_excluded),'Tile enters excluded ridge/chimney/shadow')
        require(not occupied[b[1]:b[3],b[0]:b[2]].any(),'Overlapping tile evidence')
        occupied[b[1]:b[3],b[0]:b[2]]=True
        require([b[0],b[2]]==s['u_interval_px'],'Tile U endpoints not from strip')
        nodes=[box[1]]+s['local_v_troughs_px']+[box[3]]
        require(any(b[1:4:2]==[v0,v1] for v0,v1 in zip(nodes,nodes[1:])),'Tile V endpoints not adjacent measured seams')
        center=(b[0]+b[2])//2
        require(r['boundary_source_px']==[[b[0],884],[center,b[1]],[b[2],884],[center,b[3]]],'Tile boundary source references changed')
        vb=s['local_v_profile_roi_px'];profile=im[vb[1]:vb[3],vb[0]:vb[2]]
        require(hashlib.sha256(profile.tobytes()).hexdigest()==r['local_v_profile_sha256'],'Tile local profile hash mismatch')
        wanted=[round(coef['sx']*b[0]+coef['tx'],8),round(coef['sz']*b[1]+coef['tz'],8),round(coef['sx']*b[2]+coef['tx'],8),round(coef['sz']*b[3]+coef['tz'],8)]
        require(r['diagnostic_xz_bbox']==wanted,'Tile mapped extent mismatch')
        c=r['color'];ib=[b[0]+2,b[1]+1,b[2]-2,b[3]-1]
        require(c['interior_bbox_px']==ib and bbox(ib),'Tile interior provenance mismatch')
        require(valid_px(c['source_sample_px'],im),'Tile source pixel invalid')
        u,v=c['source_sample_px'];require(ib[0]<=u<ib[2] and ib[1]<=v<ib[3],'Tile source color outside its interior')
        require(im[v,u].tolist()==c['source_sample_rgb'],'Tile RGB not at recorded source pixel')
        pixels=im[ib[1]:ib[3],ib[0]:ib[2]].reshape(-1,3).astype(float)
        good=(pixels[:,0]>pixels[:,1]*1.45)&(pixels[:,1]>pixels[:,2]*1.15)&(pixels[:,0]>90)
        require(int(good.sum())==c['support_pixels'],'Tile source support count mismatch')
        median=np.median(pixels[good],axis=0)
        require([round(float(v),3) for v in median]==c['median_rgb'],'Tile source median mismatch')
        require(c['palette_id'] in palette and c['palette_id']==int(np.argmin(((palette_colors-median)**2).sum(1))),'Tile palette assignment mismatch')
        require(type(r['confidence_strength_score'])in(int,float) and math.isfinite(r['confidence_strength_score']) and 0<r['confidence_strength_score']<=1,'Invalid tile confidence')
    for p in palette.values():
        require(p['source_region_id'] in regions,'Palette source region unknown')
        c=regions[p['source_region_id']]['color'];require(p['rgb']==c['source_sample_rgb'] and p['source_px']==c['source_sample_px'],'Palette source region disagrees')
    require(data['counts']['regions']==len(regions) and data['counts']['strips']==len(strips) and data['counts']['palette']==len(palette),'Tile counts mismatch')
    return {'regions':len(regions),'strips':len(strips),'palette_source_colors':len(palette),'every_region_source_profile_and_interior_verified':True}

def run():
    started=time.monotonic();contract=read(Q/'measurement_contract.json')
    require(sha(SOURCE)==FROZEN_SOURCE_SHA,'Original image changed')
    require(sha(Q/'measurement_contract.json')==FROZEN_CONTRACT_SHA,'Frozen contract changed')
    require(sha(Q/'measurements.json')==FROZEN_MEASUREMENTS_SHA,'Frozen measurements changed')
    handoff=read(Q/'handoff.json')
    for r in handoff['files']:require(sha(ROOT/r['path'])==r['sha256'],'Frozen handoff dependency changed')
    dependencies={str(SOURCE.relative_to(ROOT)):FROZEN_SOURCE_SHA,str((Q/'measurement_contract.json').relative_to(ROOT)):FROZEN_CONTRACT_SHA,str((Q/'measurements.json').relative_to(ROOT)):FROZEN_MEASUREMENTS_SHA}
    im=np.asarray(Image.open(SOURCE).convert('RGB'));data=read(T/'tile_regions.json')
    accepted=validate_tiles(data,contract,im,dependencies);tests={}
    def rejected(label,mutate):
        candidate=copy.deepcopy(data);mutate(candidate)
        try:validate_tiles(candidate,contract,im,dependencies)
        except (ValueError,KeyError,TypeError,IndexError) as e:tests[label]={'rejected':True,'reason':str(e)}
        else:raise AssertionError('Malformed tile provenance accepted: '+label)
    rejected('wrong_schema',lambda d:d.__setitem__('schema','legacy'))
    rejected('wrong_source_hash',lambda d:d['source_dependencies'].__setitem__(str(SOURCE.relative_to(ROOT)),'0'*64))
    rejected('wrong_measurement_script',lambda d:d.__setitem__('script_sha256','0'*64))
    rejected('wrong_mapping',lambda d:d['conditional_mapping']['coefficients'].__setitem__('sx',1.0))
    rejected('duplicate_region',lambda d:d['regions'].append(copy.deepcopy(d['regions'][0])))
    rejected('unknown_strip',lambda d:d['regions'][0].__setitem__('strip_id','not_measured'))
    rejected('modified_endpoint',lambda d:d['regions'][0]['bbox_px'].__setitem__(3,d['regions'][0]['bbox_px'][3]-1))
    rejected('ridge_fill',lambda d:d['regions'][0].__setitem__('bbox_px',[756,800,783,820]))
    rejected('invalid_profile_hash',lambda d:d['regions'][0].__setitem__('local_v_profile_sha256','0'*64))
    rejected('invented_color',lambda d:d['regions'][0]['color'].__setitem__('source_sample_rgb',[255,0,255]))
    rejected('unknown_palette',lambda d:d['regions'][0]['color'].__setitem__('palette_id',99))
    rejected('invented_palette_color',lambda d:d['palette'][0].__setitem__('rgb',[255,0,255]))
    rejected('unknown_palette_source_region',lambda d:d['palette'][0].__setitem__('source_region_id','unmeasured'))
    rejected('nonfinite_mapping_extent',lambda d:d['regions'][0]['diagnostic_xz_bbox'].__setitem__(0,float('nan')))
    # Actual shared-source grammar is tested without any compile/evaluation call.
    source={'schema':core.SCHEMA,'id':'malformed_rejection_fixture','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'materials':{'test':'ffffff'},'components':[{'id':'fixture','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':[{'id':'box','action':'paint','part':'solid','material':'test','shape':{'kind':'box','min':[0,0,0],'max':[1,1,1]}}]}],'instances':[{'id':'fixture','component':'fixture'}]}
    core.validate_master(source,.0625);source_tests={}
    for name,mutate in [
        ('wrong_master_schema',lambda d:d.__setitem__('schema','wrong')),
        ('unknown_material',lambda d:d['components'][0]['operations'][0].__setitem__('material','unknown')),
        ('nonfinite_box',lambda d:d['components'][0]['operations'][0]['shape']['max'].__setitem__(1,float('nan'))),
        ('reversed_box',lambda d:d['components'][0]['operations'][0]['shape']['max'].__setitem__(0,-1)),
        ('unsupported_shape',lambda d:d['components'][0]['operations'][0]['shape'].__setitem__('kind','brightness_depth')),
        ('duplicate_operation',lambda d:d['components'][0]['operations'].append(copy.deepcopy(d['components'][0]['operations'][0]))),
        ('unknown_part',lambda d:d['components'][0]['operations'][0].__setitem__('part','unknown'))]:
        bad=copy.deepcopy(source);mutate(bad)
        try:core.validate_master(bad,.0625)
        except (ValueError,KeyError,TypeError) as e:source_tests[name]={'rejected':True,'reason':str(e)}
        else:raise AssertionError('Malformed master accepted: '+name)
    report={'schema':'riverstone.roof_repair.independent_source_validation.v1','status':'PASS','tile_data':ref(T/'tile_regions.json'),'frozen_contract':ref(Q/'measurement_contract.json'),'original_raster':ref(SOURCE),'validator':ref(Path(__file__)),'positive_tile_validation':accepted,'tile_provenance_negative_tests':tests,'common_master_negative_tests':source_tests,'all_frozen_handoff_files_unchanged':True,'geometry_sampling_calls':0,'compiler_calls':0,'mesher_calls':0,'mutated_sources_written':False,'address_space_limit_mib':256,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-started}
    save(HERE/'source_validation.json',report)
    print(json.dumps({'status':report['status'],'positive_tile_validation':accepted,'tile_negative_tests':len(tests),'source_negative_tests':len(source_tests),'peak_rss_kib':report['peak_rss_kib'],'elapsed_seconds':report['elapsed_seconds']}))
if __name__=='__main__':run()
