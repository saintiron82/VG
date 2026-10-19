"""Measured semantic stone pixels -> bounded common part runs.
Foundation-only ground registration; existing upper source is immutable.
No schematic box plinth, hidden planter infill, or invented stair tread.
"""
import copy,gzip,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'voxel_character/common/core.py').exists());O=Path(__file__).resolve().parent;D=O.parent/'reconstruction_proof_r01';sys.path.insert(0,str(ROOT));from voxel_character.common import core
P=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01';pitch=.125
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def save(p,o):
 assert not p.exists();raw=json.dumps(o,separators=(',',':'),allow_nan=False).encode();p.write_bytes(gzip.compress(raw,mtime=0) if p.suffix=='.gz' else raw)
def classify(c):
 r,g,b=np.moveaxis(c.astype(float),-1,0);lum=c.mean(2);stone=(c.max(2).astype(float)-c.min(2)<=40)&(lum>=35)&(lum<=220)&(np.abs(r-g)<=15)&(np.abs(b-r)<=18);foliage=((g-r>10)&(g-b>5))|((r-g>35)&(r-b>30)&(g<100));warm=(r-b>20)&(r-g>12);return stone,foliage,warm
start=time.monotonic();trace=json.loads((O/'loss_trace.json').read_text());a=np.load(D/'image_derived_arrays.npz');old_occ=a['occupancy'];old_mats=a['materials'];occ=old_occ.copy();mats=old_mats.copy();im=np.asarray(Image.open(P/'generated_candidate_r03.png').convert('RGB'));maps={};samples=[];records=[]
for d in trace['views']:
 n=d['view'];x0,_,x1,_=d['source_grid_roi'];ground=d['automatic_ground_boundary_y_px'];crop=im[ground-36:ground,x0:x1];stone,plants,warm=classify(crop)
 # Broad semantic material band; door/pot/foliage RGB cannot become stone.
 cov=stone.reshape(9,4,(x1-x0)//4,4).mean((1,3));fg=cov>=.40;rgb=np.zeros((9,(x1-x0)//4,3),float);uncertain=(cov>0)&(cov<.4)
 for y in range(9):
  for u in range((x1-x0)//4):
   block=crop[4*y:4*y+4,4*u:4*u+4];mask=stone[4*y:4*y+4,4*u:4*u+4];rgb[y,u]=np.median(block[mask],axis=0) if mask.any() else [150,150,150]
 fg=fg[::-1];rgb=rgb[::-1];cov=cov[::-1];uncertain=uncertain[::-1]
 if n in ('right','back'):fg=fg[:,::-1];rgb=rgb[:,::-1];cov=cov[:,::-1];uncertain=uncertain[:,::-1]
 maps[n]={'stone':fg.copy(),'rgb':rgb.copy(),'coverage':cov.copy(),'uncertain':uncertain.copy()};samples.append(rgb[fg].astype(np.uint8));records.append({'view':n,'source_semantic_band_px':[x0,ground-36,x1,ground],'measured_ground_y_px':ground,'source_template_ground_y_px':d['source_grid_roi'][3],'part_registration_only':True,'world_ground_y_m':0,'world_upper_limit_m':1.125,'source_pixels_per_meter':32,'reconstructed_stone_mask_cells':int(fg.sum()),'uncertain_mixed_mask_cells':int(uncertain.sum()),'foliage_pixels_excluded':int((plants&~stone).sum()),'warm_door_pot_pixels_excluded':int((warm&~stone).sum()),'method':'Actual neutral stone pixels in broad semantic band,4x4 coverage>=.4, no contour painting, no hole-fill, no occluded planter reconstruction.'})
px=np.concatenate(samples);q=Image.fromarray(px[None,:,:],'RGB').quantize(colors=3,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE);pal=np.array(q.getpalette()[:9],dtype=np.uint8).reshape(3,3);repair=np.zeros_like(occ);rm=np.full_like(mats,-1);protected_old=np.zeros_like(occ)
for n in ['front','back','right','left']:
 m=maps[n];labels=np.argmin(((m['rgb'][:,:,None]-pal[None,None,:,:])**2).sum(3),axis=2)
 for y,u in np.argwhere(m['stone']):
  # Thickness is explicit existing shell prior. No measured stair rear or side
  # protrusion is invented; all parts stay in the original12x10m envelope.
  if n=='front':coords=[(y,u,z) for z in range(77,80)]
  elif n=='back':coords=[(y,u,z) for z in range(3)]
  elif n=='right':coords=[(y,x,u) for x in range(93,96)]
  else:coords=[(y,x,u) for x in range(3)]
  for c in coords:
   # Preserve all previously occupied material, including plants, doors, pots.
   # This revision only adds measured stone in previously absent cells.
   if old_occ[c]:protected_old[c]=True;continue
   repair[c]=True;rm[c]=12+labels[y,u];occ[c]=True;mats[c]=12+labels[y,u]
master=json.loads(gzip.decompress((D/'image_derived.master.json.gz').read_bytes()));original=copy.deepcopy(master);master['id']+='__foundation_semantic_r01';master['revision']=2
for i,c in enumerate(pal):master['materials'][f'stone_pixel_{i:02d}']=''.join(f'{int(x):02x}' for x in c)
ops=[]
for y,x in np.argwhere(repair.any(2)):
 z=0
 while z<80:
  if not repair[y,x,z]:z+=1;continue
  z0=z;mat=int(rm[y,x,z]);z+=1
  while z<80 and repair[y,x,z] and int(rm[y,x,z])==mat:z+=1
  ops.append({'id':f'measured_stone_y{y}_x{x}_z{z0}','part':'measured_foundation','action':'paint','material':f'stone_pixel_{mat-12:02d}','shape':{'kind':'box','min':[(int(x)-48)*pitch,int(y)*pitch,(z0-40)*pitch],'max':[(int(x)-47)*pitch,(int(y)+1)*pitch,(z-40)*pitch]}})
master['components'].append({'id':'foundation_semantic_pixels_r01','parts':[{'id':'measured_foundation','pivot':[0,0,0]}],'operations':ops});master['instances'].append({'id':'foundation_semantic_pixels_r01','component':'foundation_semantic_pixels_r01'});master['metadata']['foundation_repair']={'source_image':ref(P/'generated_candidate_r03.png'),'original_master':ref(D/'image_derived.master.json.gz'),'ground_registration':'Per semantic foundation band only; originalupper image/source untouched','stone_thickness_prior_m':.375,'side_protrusion':'Unresolved; no extension beyond original12x10m envelope','stair_tread_depth':'Unresolved; observed front threshold band only','occluded_planter_back':'Not reconstructed','new_palette':'Three median-cut stone tones from actual neutral stone pixels, not random cell colors'}
core.validate_master(master,pitch);assert master['components'][:-1]==original['components'] and master['instances'][:-1]==original['instances'];assert np.array_equal(occ[9:],old_occ[9:]) and np.array_equal(mats[9:],old_mats[9:]);assert np.array_equal(mats[old_occ],old_mats[old_occ]);assert occ.any(2)[0].any();save(O/'foundation_revised.master.json.gz',master)
np.savez_compressed(O/'foundation_arrays.npz',occupancy=occ,materials=mats,added=repair,palette=pal,**{n+'_'+k:v for n,d in maps.items() for k,v in d.items()})
front=maps['front']['stone'];actual=occ.any(2)[:9];visible_covered=front&actual
r={'schema':'riverstone.image_foundation.repair_source.v1','original_source':ref(D/'image_derived.master.json.gz'),'revised_source':ref(O/'foundation_revised.master.json.gz'),'source_image':ref(P/'generated_candidate_r03.png'),'arrays':ref(O/'foundation_arrays.npz'),'script':ref(Path(__file__)),'loss_trace':ref(O/'loss_trace.json'),'diagnostic_only':True,'production_gate_open':False,'pixel_annotations':records,'added_cell_count':int(repair.sum()),'original_cell_count':int(old_occ.sum()),'revised_cell_count':int(occ.sum()),'new_run_operations':len(ops),'stone_palette_rgb':pal.tolist(),'world_bounds':{'min':[-6,0,-5],'max':[6,13.875,5]},'bounded_patch':{'min':[-6,0,-5],'max':[6,1.25,5],'common_cell_bounds_min':[-48,0,-40],'common_cell_bounds_max':[48,11,40],'owned_y_cells':[0,10],'halo_cells':1},'tests':{'original_components_operations_instances_exact':True,'upper_y_ge_1_125_occupancy_exact':True,'upper_y_ge_1_125_material_exact':True,'all_original_occupied_cell_materials_exact':True,'only_missing_cells_added':True,'ground_y0_has_stone':True,'front_visible_stone_mask_fully_covered':bool(np.all(visible_covered[front]))},'front_coverage':{'visible_stone_mask_cells':int(front.sum()),'covered':int(visible_covered.sum()),'uncovered':int((front&~actual).sum()),'bottom_row_visible_stone_columns':int(front[0].sum()),'bottom_row_revised_occupancy_columns':int(actual[0].sum())},'no_claims':['No unique metric side protrusion was recovered. Original envelope retained.','Image shows a threshold/base course under the front door; tread depth and distinct stair count are unresolved.','No plants or pots generated by this repair. Old occupied materials are untouched.','Hidden stone behind occluding plants is not inferred. Remaining occluded gaps are disclosed.','Part ground alignment is a semantic diagnostic revision; global sheet registration still fails.'],'seconds':time.monotonic()-start};save(O/'source_contract.json',r);print(json.dumps({'contract':ref(O/'source_contract.json'),'added':r['added_cell_count'],'ops':len(ops),'front':r['front_coverage'],'seconds':r['seconds']}))
