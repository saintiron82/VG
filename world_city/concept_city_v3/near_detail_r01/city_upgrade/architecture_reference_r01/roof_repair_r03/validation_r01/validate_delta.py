#!/usr/bin/env python3
"""Independent source-owned r03 delta audit; no compiler, sampler, mesher or GUI.
Compares every upper cell to an independently reconstructed row oracle. Mutations
are in RAM only. R02 validators and all original inputs stay read-only.
"""
from validate_exterior import *
import copy,gc,sys
sys.dont_write_bytecode=True
from PIL import Image
sys.path.insert(0,str(ROOT))
from voxel_character.common import core
OLD=ARCH/'roof_repair_r02';FOUND=ARCH/'foundation_repair_r01'
SOURCE=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
FROZEN_SOURCE='552b0bd61eba3c3f5bee98a6b3a5fac085362dc8804e049e325db55fb902ec93'
FROZEN_R02='d71a5987debe5e3e22a3663f8ee4b604bd7d880a0fa7d8188e4d9247c26edb17'

def require(test,reason):
 if not test:raise ValueError(reason)
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def fg(rgb):
 r,g,b=np.moveaxis(np.asarray(rgb,dtype=float),-1,0);lum=(r+g+b)/3
 return ((r-b>12)&(r>=.95*g)&(lum<248))|(lum<110)|((g-r>12)&(g-b>12)&(lum<205))
def pins():
 p=read(R/'plan.json');wanted=dict(p['source_dependencies'])
 wanted.update({str(R/n).replace(str(ROOT)+'/',''):sha(R/n) for n in ['plan.json','compile.json','roof_patch.master.json.gz','upper_union_arrays.npz','delta_ownership_arrays.npz']})
 require(sha(SOURCE)==FROZEN_SOURCE,'Frozen source changed');require(sha(OLD/'roof_repaired.render.json.gz')==FROZEN_R02,'Frozen r02 changed')
 for path,h in wanted.items():require(sha(ROOT/path)==h,'Source pin mismatch: '+path)
 for path,h in read(OLD/'plan.json')['source_dependencies'].items():require(sha(ROOT/path)==h,'R02 source pin mismatch: '+path)
 return wanted

def source_proof(plan=None,master=None):
 plan=read(R/'plan.json') if plan is None else plan;master=read(R/'roof_patch.master.json.gz') if master is None else master
 legacy=read(OLD/'roof_patch.master.json.gz');palette=read(FOUND/'foundation_revised.master.json.gz')['materials']|legacy['materials']
 require(master['materials']==palette,'Palette changed');names=list(palette);ids={n:i for i,n in enumerate(names)}
 require(master['metadata']['brightness_to_height'] is False and master['metadata']['true_occluder_auto_filled'] is False,'Unsupported depth or occluder policy')
 ops={o['id']:o for c in master['components'] for o in c['operations']};require(len(ops)==sum(len(c['operations']) for c in master['components']),'Duplicate operation')
 slope=legacy['metadata']['measured_gable_slope'];ridge=legacy['metadata']['original_max_y'];require(plan['backing_bottom_offset_m']==-.1875,'Restoration plane altered')
 require(legacy['metadata']['thin_tile_normal_thickness_prior_m']==legacy['metadata']['barrel_normal_crest_prior_m']==.0625,'R02 geometry priors changed')
 require(legacy['metadata']['continuous_support_vertical_thickness_prior_m']==.125,'R02 backing thickness changed')
 im=np.asarray(Image.open(SOURCE).convert('RGB'));a=np.load(FOUND/'foundation_arrays.npz');occ=a['occupancy'];mats=a['materials'];kept=np.load(OLD/'ownership_arrays.npz')['kept_occupancy']
 color_names=[n for n in names if n.startswith('pixel_') or n.startswith('top_tile_')];rgb=np.array([[int(palette[n][i:i+2],16) for i in (0,2,4)] for n in color_names])
 blocks=[];edge_links=[];expected_edge={};used=set()
 for view,zs in [('front',[77,78,79]),('back',[0,1,2])]:
  for y in range(76,112):
   for x in range(96):
    X=(x-48+.5)*.125;Y=(y+.5)*.125;line=ridge-slope*abs(X)
    if not(line-.65<=Y<=line+.125 and .25<abs(X)<6):continue
    zz=[z for z in zs if kept[y,x,z] and 0<=mats[y,x,z]<=3]
    if not zz:continue
    require(zz==zs,'Mixed depth source block');u=64+x*4 if view=='front' else 1088+(95-x)*4;v=496-(y+1)*4;p=im[v:v+4,u:u+4];mask=fg(p)
    blocks.append({'view':view,'source_yx':[y,x],'original_z_cells':zs,'source_box_px':[u,v,u+4,v+4],'foreground_pixels':int(mask.sum()),'background_pixels':int((~mask).sum())})
    for dv,du in np.argwhere(mask):
     du,dv=int(du),int(dv);xx=x*4-192+(du if view=='front' else 3-du);yy=y*4+3-dv;col=color_names[int(np.argmin(((rgb-p[dv,du].astype(float))**2).sum(1)))];oid=f'edge_{view}_y{y}_x{x}_v{dv}_u{du}'
     edge_links.append({'operation':oid,'view':view,'source_pixel_uv':[u+du,v+dv],'source_rgb':p[dv,du].tolist(),'source_parent_yx':[y,x],'material':col,'foreground_rule_identical_to_original_reconstruct':True})
     expected={'id':oid,'part':'foreground_resampled_gable_edge','action':'paint','material':col,'shape':{'kind':'box','min':[xx*PITCH,yy*PITCH,(zs[0]-40)*.125],'max':[(xx+1)*PITCH,(yy+1)*PITCH,(zs[-1]-39)*.125]}}
     require(ops.get(oid)==expected,'Foreground operation, footprint or material mismatch');used.add(oid)
     for z in range(zs[0]*4-160,(zs[-1]+1)*4-160):expected_edge[(xx,yy,z)]=(col,oid)
 require(plan['edge_blocks']==blocks,'Edge source block mask mismatch');require(plan['edge_source_links']==edge_links,'Source foreground/color record mismatch')
 require(len(blocks)==46 and len(edge_links)==460 and len(expected_edge)==5520,'Edge source count mismatch')
 # Actual source ROI intervals and color evidence, independently verified.
 tiledata=read(ARCH/'roof_repair_r01/tile_measurement_r01/tile_regions.json');coef=tiledata['conditional_mapping']['coefficients'];sx,sz,tx,tz=[coef[k] for k in ('sx','sz','tx','tz')]
 diag=read(OLD/'gap_diagnostic_r01/source_shadow/diagnostic.json');regions=diag['minimal_extension_candidates'];C=[868,795,908,849];E=[865,795,925,879];strips={s['id']:s for s in tiledata['strips']}
 expected_boxes=[]
 for r in tiledata['rejected_regions']:
  b=r['bbox_px']
  if r['reason']!='Intersects excluded ridge/chimney/shadow ROI' or not overlap(b,E) or overlap(b,C) or not(5<=b[3]-b[1]<=21):continue
  p=im[b[1]+1:b[3]-1,b[0]+2:b[2]-2].reshape(-1,3).astype(float);good=(p[:,0]>p[:,1]*1.45)&(p[:,1]>p[:,2]*1.15)&(p[:,0]>90)
  if int(good.sum())>=3:expected_boxes.append((r['strip'],b))
 require([(r['original_rejected_strip'],r['bbox_px']) for r in regions]==expected_boxes,'Shadow selection differs from observed original intervals')
 require(len(regions)==15 and len(plan['tile_source_links'])==15,'Unobserved extension count')
 tile_rgb=np.array([[int(palette[f'top_tile_{i:02d}'][j:j+2],16) for j in (0,2,4)] for i in range(6)])
 shadow_links={}
 for reg,link in zip(regions,plan['tile_source_links']):
  b=reg['bbox_px'];u0,v0,u1,v1=b;oid=reg['id'];strip=strips[reg['original_rejected_strip']];require(not overlap(b,C),'Hidden occluder fill');require([u0,u1]==strip['u_interval_px'],'Unobserved source U boundary');require(v0 in strip['local_v_troughs_px'] and v1 in strip['local_v_troughs_px'],'Unobserved source V boundary')
  vs=strip['local_v_troughs_px'];require(vs.index(v1)==vs.index(v0)+1,'Skipped observed trough')
  ib=[u0+2,v0+1,u1-2,v1-1];pixels=im[ib[1]:ib[3],ib[0]:ib[2]].reshape(-1,3).astype(float);good=(pixels[:,0]>pixels[:,1]*1.45)&(pixels[:,1]>pixels[:,2]*1.15)&(pixels[:,0]>90);med=np.median(pixels[good],axis=0)
  require(ib==reg['interior_bbox_px'] and int(good.sum())==reg['terracotta_support_pixels'] and med.tolist()==reg['median_rgb'],'Shadow source color evidence mismatch')
  uu,vv=reg['actual_sample_px'];require(im[vv,uu].tolist()==reg['actual_sample_rgb'] and ib[0]<=uu<ib[2] and ib[1]<=vv<ib[3],'Shadow source sample mismatch')
  x0,x1,z0,z1=sx*(u0+.5)+tx,sx*(u1-.5)+tx,sz*(v0+.5)+tz,sz*(v1-.5)+tz;material=f'top_tile_{int(np.argmin(((tile_rgb-med)**2).sum(1))):02d}'
  require(link=={'operation':oid,'source':reg,'material':material,'horizontal_footprint_xz':[x0,z0,x1,z1],'geometry_prior_identical_to_r02':True},'Shadow source coordinates/material mismatch')
  c=1/math.sqrt(1+slope*slope);width=z1-z0;xs=[-width/2,-width/4,0,width/4,width/2];hh=[0,.046875,.0625,.046875,0];polygon=[[x,h-.0625] for x,h in zip(xs,hh)]+[[x,h] for x,h in reversed(list(zip(xs,hh)))];basis=[[0,slope*c,c],[0,c,-slope*c],[-1,0,0]]
  shape={'kind':'extrusion','polygon':polygon,'z_min':-.125,'z_max':(x1-x0)/c+.125};transform={'translation':[x0,ridge-slope*abs(x0)-.0625,(z0+z1)/2],'basis':basis}
  require(ops.get(oid)=={'id':oid,'part':'observed_shadow_tile_extensions','action':'paint','material':material,'shape':shape,'transform':transform},'Shadow geometry prior changed');used.add(oid)
  # Independently derive crop box corners directly, without common shape prepare.
  points=[]
  for xx in [-width/2,width/2]:
   for yy in [-.0625,.0625]:
    for zz in [shape['z_min'],shape['z_max']]:points.append([sum(basis[i][j]*[xx,yy,zz][j] for j in range(3))+transform['translation'][i] for i in range(3)])
  lo=[min(p[i] for p in points)-PITCH for i in range(3)];hi=[max(p[i] for p in points)+PITCH for i in range(3)]
  for tag,left,right in [('left',lo[0],x0),('right',x1,hi[0])]:
   op=ops.get(oid+'_crop_'+tag);expected={'id':oid+'_crop_'+tag,'part':'observed_shadow_tile_extensions','action':'cut','selector':{'feature':oid},'shape':{'kind':'box','min':[left,lo[1],lo[2]],'max':[right,hi[1],hi[2]]}}
   require(op==expected,'Source crop boundary changed');used.add(oid+'_crop_'+tag)
  shadow_links[oid]=link
 require(set(ops)==used,'Unowned geometry operation');require(all(not overlap(a['bbox_px'],b['bbox_px']) for i,a in enumerate(regions) for b in regions[i+1:]),'Overlapping new source regions')
 return {'blocks':blocks,'edge':expected_edge,'shadow':shadow_links,'names':names,'ids':ids,'slope':slope,'ridge':ridge,'occ':occ,'mats':mats,'master':master,'source_report':{'source_fg_rule_matches_original':True,'edge_blocks':46,'original_front_coarse_cells':69,'original_back_coarse_cells':69,'actual_foreground_pixels':460,'foreground_depth_prior_m':.375,'foreground_fine_cells':5520,'background_fine_cells_removed':3312,'new_observed_shadow_regions':15,'source_occluder_intersections':0,'source_interval_endpoints_match_original':True,'unchanged_r02_thickness_and_crest_m':.0625,'nearest_unchanged_source_palette':True,'all_new_operations_source_owned':True,'brightness_to_height':False}}

def stream_compiled_cells(path):
 from validate_render import JsonStream
 with gzip.open(path,'rt') as f:
  p=JsonStream(f);p.eat('{')
  while p.peek()!='}':
   key=p.value();p.eat(':')
   if key=='cells':
    p.eat('[')
    while p.peek()!=']':
     yield p.value()
     if p.peek()==',':p.eat(',')
     else:break
    p.eat(']')
   else:p.value()
   if p.peek()==',':p.eat(',')
   else:break
  p.eat('}');require(p.peek()=='','Compiled trailing content')

def check_row(actual,wanted,labels,wanted_labels):
 require(np.array_equal(actual,wanted),'Cell union differs from exact allowed source delta')
 require(np.array_equal(labels,wanted_labels),'Delta ownership classification differs')

def cell_proof(ctx,mutation=None):
 priorfile=np.load(OLD/'upper_union_arrays.npz');newfile=np.load(R/'upper_union_arrays.npz');prior=priorfile['materials'];new=newfile['materials'];ownership=np.load(R/'delta_ownership_arrays.npz');labels=ownership['delta_class']
 if mutation is not None:mutation(new,labels,prior)
 require(prior.shape==new.shape==labels.shape==(148,400,328),'Unexpected grid bounds');require(newfile['origin_cell_xyz'].tolist()==[-200,300,-164] and newfile['pitch_m']==PITCH and newfile['join_y_m']==9.5,'Grid source boundary changed');require(newfile['material_names'].tolist()==priorfile['material_names'].tolist()==ctx['names'],'Material ID reorder')
 compilation=read(R/'compile.json');cpath=ROOT/compilation['delta']['path'];require(sha(cpath)==compilation['delta']['sha256'],'Compiled delta hash');compiled=read(cpath);require(compiled['valid'] and compiled['pitch']==PITCH and compiled['grid_origin']==[0,0,0],'Compiled schema');require(core.digest(compiled['cells'])==compiled['payload_hash'] and core.digest(ctx['master'])==compiled['master_hash'],'Compiled payload/master mismatch')
 rows={};seen=set();edges={};shadow={};ids=ctx['ids'];tilechecked=0
 for x,y,z,instance,part,material,feature in compiled['cells']:
  key=(x,y,z);require(key not in seen,'Duplicate compiled cell');seen.add(key);require(-200<=x<200 and 304<=y<448 and -164<=z<164,'Source bounds expansion');rows.setdefault(y-300,[]).append((x+200,z+164,part,ids[material],feature))
  if part=='foreground_resampled_gable_edge':edges[key]=(material,feature)
  else:
   require(part=='observed_shadow_tile_extensions' and feature in ctx['shadow'],'Unobserved extension compiled');link=ctx['shadow'][feature];require(link['material']==material,'Compiled wrong tile material');u0,v0,u1,v1=link['source']['bbox_px'];x0,z0,x1,z1=link['horizontal_footprint_xz'];require(x0-1e-9<=(x+.5)*PITCH<x1+1e-9 and z0-1e-9<=(z+.5)*PITCH<z1+1e-9,'Compiled tile center outside source boundary');co=read(ARCH/'roof_repair_r01/tile_measurement_r01/tile_regions.json')['conditional_mapping']['coefficients'] if tilechecked==0 else co
   raw=[co['sx']*u0+co['tx'],co['sz']*v0+co['tz'],co['sx']*u1+co['tx'],co['sz']*v1+co['tz']];require(raw[0]-1e-9<=x*PITCH and (x+1)*PITCH<=raw[2]+1e-9 and raw[1]-1e-9<=z*PITCH and (z+1)*PITCH<=raw[3]+1e-9,'Solid tile crosses observed source interval');shadow[key]=feature;tilechecked+=1
 require(edges==ctx['edge'],'Compiled source foreground incomplete or background treated as foreground');require(len(seen)==compilation['cells'],'Compiled count mismatch')
 del compiled;gc.collect();X=(np.arange(400)-200+.5)*PITCH;stats={'restored_original_occupied_fine_cells':0,'edge_original_cells_cleared':0,'shadow_cells_added':0,'shadow_support_cells_replaced':0,'shadow_blocked_by_retained':0,'changed_cells':0};topclass=np.zeros((400,328),np.uint8);topmat=np.full((400,328),-1,np.int16);restplus=0
 for iy in range(148):
  wanted=prior[iy].copy();wl=np.zeros((400,328),np.uint8);source=np.full((400,328),-1,np.int16);source[8:392,4:324]=np.where(ctx['occ'][(iy+300)//4],ctx['mats'][(iy+300)//4],-1).repeat(4,0).repeat(4,1)
  restore=(wanted<0)&(source>=0)&((iy+300+.5)*PITCH<ctx['ridge']-ctx['slope']*np.abs(X)[:,None]-.1875)&(iy>=4);wanted[restore]=source[restore];wl[restore]=1;stats['restored_original_occupied_fine_cells']+=int(restore.sum())
  for b in ctx['blocks']:
   y,x=b['source_yx'];zs=b['original_z_cells']
   if y*4<=iy+300<(y+1)*4:
    sl=(slice(x*4+8,(x+1)*4+8),slice(zs[0]*4+4,(zs[-1]+1)*4+4));require(np.all(wanted[sl]==ctx['mats'][y,x,zs[0]]),'Non-source edge ownership');stats['edge_original_cells_cleared']+=int((wanted[sl]>=0).sum());wanted[sl]=-1;wl[sl]=2
  for ix,iz,part,mid,feature in rows.get(iy,[]):
   if part=='foreground_resampled_gable_edge':require(wl[ix,iz]==2 and wanted[ix,iz]<0,'Foreground outside exact source block');wanted[ix,iz]=mid
   else:
    old=int(wanted[ix,iz]);require(wl[ix,iz]!=2,'Tile overwrites foreground ownership')
    if old>=0 and (old<15 or old>=21):stats['shadow_blocked_by_retained']+=1;continue
    stats['shadow_cells_added' if old<0 else 'shadow_support_cells_replaced']+=1;wanted[ix,iz]=mid;wl[ix,iz]=3
  check_row(new[iy],wanted,labels[iy],wl);stats['changed_cells']+=int((new[iy]!=prior[iy]).sum())
  occupied=new[iy]>=0;topclass[occupied]=wl[occupied];topmat[occupied]=new[iy][occupied]
  if iy<147:restplus+=int(((wl==1)&(new[iy]>=0)&(new[iy+1]<0)).sum())
 require(stats['restored_original_occupied_fine_cells']==791384 and restplus==0 and not (topclass==1).any(),'Restored source exposed as upper blade');require(np.array_equal(topclass,ownership['top_first_hit_delta_class']) and np.array_equal(topmat,ownership['top_first_hit_material']),'TOP first-hit ownership mismatch')
 # Every overlapping legacy compiler cell must be support; existing 339 tiles/chimney stay exact.
 overlaps={};legacy_checked=0;tile_features=set();chimney=0;source_blocked_candidates=0
 for record in read(OLD/'compile.json')['chunks']:
  path=ROOT/record['compiled']['path'];require(sha(path)==record['compiled']['sha256'],'Legacy compilation changed')
  for x,y,z,instance,part,material,feature in stream_compiled_cells(path):
   if (x,y,z) in shadow:require(part=='thin_roof_support','New tile overwrites existing tile/chimney');overlaps[part]=overlaps.get(part,0)+1
   if part in ('measured_tile_regions','finite_chimney_prior'):
    point=(y-300,x+200,z+164)
    if prior[point]>=15:require(new[point]==prior[point],'Existing actual tile/chimney changed');legacy_checked+=1
    else:source_blocked_candidates+=1
    if part=='measured_tile_regions':tile_features.add(feature)
    else:chimney+=1
  gc.collect()
 require(len(tile_features)==339 and chimney==64000,'Legacy feature count mismatch');require(overlaps=={'thin_roof_support':2424},'Unexpected legacy overlap')
 stats.update(lower_halo_exact=True,lower_foundation_cells_unchanged=True,all_upper_cells_checked=int(new.size),outside_allowed_delta_changes=0,restoration_outside_original_occupancy=0,restoration_above_backing_bottom=0,restored_top_first_hits=0,restored_exposed_plus_y_faces=restplus,legacy_tile_features_unchanged=len(tile_features),legacy_chimney_fine_cells_unchanged=chimney,legacy_tile_chimney_cells_checked=legacy_checked,legacy_compiler_candidates_blocked_by_source=source_blocked_candidates,legacy_overlap_parts=overlaps,observed_shadow_compiled_cells_checked=tilechecked,source_bounds_unchanged=True)
 return stats

def main():
 t=time.monotonic();before=pins();ctx=source_proof();proof=cell_proof(ctx);require(all(sha(ROOT/p)==h for p,h in before.items()),'Inputs modified')
 report={'schema':'riverstone.roof_repair_r03.independent_source_delta.v1','status':'TECHNICAL_PASS','source_proof':ctx['source_report'],'cell_proof':proof,'input_files':before,'source_pins_unchanged':True,'validator':ref(Path(__file__)),'sampling_calls':0,'mesher_calls':0,'full_house_fine_volume_allocated':False,'address_space_limit_mib':256,'cpu_limit_seconds':60,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-t,'visual_acceptance':'PENDING_ACTUAL_CAPTURE_REVIEW'}
 save(HERE/'delta_validation.json',report);print(json.dumps({k:v for k,v in report.items() if k!='input_files'},sort_keys=True))
if __name__=='__main__':main()
