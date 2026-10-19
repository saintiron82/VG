"""Read-only gallery loss audit. Only this directory receives small evidence files.
No core sampler, mesher, GUI, geometry generation, or source-raster edits.
"""
import os,sys,resource,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(110,110))
START=time.monotonic()
from pathlib import Path
import json,gzip,hashlib,importlib.util
import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion,label
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'voxel_character/common/core.py').exists())
O=Path(__file__).resolve().parent;A=O.parent;D=A/'reconstruction_proof_r01';P=ROOT/'world_city/reference/house_quality_photos_20261019';SRC=P/'six_views_r01/generated_candidate_r03.png'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def dump(name,d):
 data=(json.dumps(d,indent=2)+'\n').encode();assert len(data)<1000000
 (O/name).write_bytes(data)
def loadmod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=loadmod('gallery_audit_original',D/'reconstruct.py')
im=np.asarray(Image.open(SRC).convert('RGB'));maps,palette=r.extract(im);saved=np.load(D/'image_derived_arrays.npz')
mask_exact=all(np.array_equal(maps[n][k],saved[n+'_'+k]) for n in r.ROIS for k in maps[n])
f,b,right,left=[maps[n]['silhouette'] for n in ('front','back','right','left')]
hull=(f&b)[:,:,None]*np.ones((1,1,80),bool);hull[:76]&=(right&left)[:76,None,:]
shell=hull&~binary_erosion(hull,iterations=3,border_value=0);floors=shell.copy()
for y in (4,28,52,76):floors[max(0,y-2):y]|=hull[max(0,y-2):y]
occ=floors.copy();rgb=maps['front']['rgb'];wood=(rgb[:,:,0]>rgb[:,:,2]*1.3)&(rgb[:,:,1]>rgb[:,:,2]*1.08)&(rgb.mean(2)>55);dark=rgb.mean(2)<60
stages={'hull':hull,'shell':shell,'shell_plus_floors':floors};gallery_rows=[];frontskin=np.zeros((112,96),bool);frontz=np.where(hull.any(2),79-np.argmax(hull[:,:,::-1],2),-1)
for g in r.GALLERIES:
 before=occ.copy();roi=r.pixels_roi_grid(g['roi_px']);ys=494-np.arange(112)*4;rail=(ys[:,None]>=g['rail_y_px'][0])&(ys[:,None]<g['rail_y_px'][1]);xs=66+np.arange(96)*4
 posts=((xs>=78)&(xs<=96))|((xs>=421)&(xs<=438));preserve=roi&wood&~dark&(rail|posts[None,:])
 for yy,xx in np.argwhere(roi&f):
  zs=np.flatnonzero(hull[yy,xx])
  if not len(zs):continue
  z=int(zs[-1]);back=max(int(zs[0]),z-9);occ[yy,xx,back+1:z+1]=False
  occ[yy,xx,max(0,back-2):back+1]=hull[yy,xx,max(0,back-2):back+1]
  if preserve[yy,xx]:occ[yy,xx,z]=True;frontskin[yy,xx]=True
 removed=before&~occ;added=~before&occ;proj_before=before.any(1);proj_after=occ.any(1)
 gallery_rows.append({'id':g['id'],'source_roi_half_open':g['roi_px'],'rail_y_half_open':g['rail_y_px'],'original_carve_depth_cells':9,'final_removed_cells':int(removed.sum()),'final_added_backwall_cells':int(added.sum()),'lost_side_projection_cells':int((proj_before&~proj_after).sum()),'restored_front_skin_pixels':int((preserve&hull.any(2)).sum()),'deleted_existing_floor_cells':int((removed&(floors&~shell)).sum()),'lost_side_yz_bbox':None if not (proj_before&~proj_after).any() else [np.argwhere(proj_before&~proj_after).min(0).tolist(),(np.argwhere(proj_before&~proj_after).max(0)+1).tolist()]})
 stages[g['id']]=occ.copy()
glass=(rgb[:,:,2]>rgb[:,:,0]*1.05)&(rgb[:,:,1]>rgb[:,:,0]*1.1)&(rgb.mean(2)<150)&f
for yy,xx in np.argwhere(glass):
 zs=np.flatnonzero(occ[yy,xx])
 if len(zs):
  top=int(zs[-1]);target=max(0,top-2);occ[yy,xx,target+1:top+1]=False;occ[yy,xx,target]=True
stages['final_original']=occ
assert mask_exact and np.array_equal(hull,saved['hull']) and np.array_equal(occ,saved['occupancy'])
foundation=np.load(A/'foundation_repair_r01/foundation_arrays.npz')['occupancy'];assert np.array_equal(occ[12:76],foundation[12:76])
# Pure source observations at native pixel resolution; ROI labels are human semantics.
PROBES={
 'right_upper_rail':{'view':'right','roi':[624,246,690,300],'kind':'rail plus cap/fascia; plants may occlude outer edge'},
 'left_upper_rail':{'view':'left','roi':[334,740,407,794],'kind':'rail plus cap/fascia; plants may occlude outer edge'},
 'right_upper_front_support':{'view':'right','roi':[618,190,640,249],'kind':'outer post; background and bracket overlap'},
 'left_upper_front_support':{'view':'left','roi':[379,687,404,744],'kind':'outer post; background and bracket overlap'},
 'right_upper_deck':{'view':'right','roi':[619,289,695,309],'kind':'visible fascia/underside; no complete hidden deck'},
 'left_upper_deck':{'view':'left','roi':[334,779,413,802],'kind':'visible fascia/underside; no complete hidden deck'},
 'front_upper_deck':{'view':'front','roi':[73,290,439,313],'kind':'visible fascia and brackets, vegetation occludes center'},
 'front_center_flowers':{'view':'front','roi':[214,238,295,410],'kind':'foliage and flowers mixed with railing/background'}
}
probe_results=[]
for name,p in PROBES.items():
 x0,y0,x1,y1=p['roi'];crop=im[y0:y1,x0:x1];rr,gg,bb=np.moveaxis(crop.astype(float),-1,0);lum=crop.mean(2)
 warm=(rr>=90)&(rr-gg>=12)&(gg-bb>=12)&(rr>=1.3*bb)&(lum>=80)
 plant=((gg>rr*1.08)&(gg>bb*1.15))|((rr-gg>65)&(rr-bb>65)&(gg<135))
 px,py=np.meshgrid(np.arange(x0,x1),np.arange(y0,y1));view=p['view'];rx,ry,rx1,ry1=r.ROIS[view];yi=(ry1-1-py)//4;ci=(px-rx)//4
 if view=='right':ci=79-ci
 valid=(yi>=0)&(yi<112)&(ci>=0)&(ci<(96 if view=='front' else 80))
 yi=np.clip(yi,0,111);ci=np.clip(ci,0,95 if view=='front' else 79)
 projection=lambda ar:ar.any(2) if view=='front' else ar.any(1)
 prior=projection(floors)[yi,ci]&valid;final=projection(occ)[yi,ci]&valid;sil=maps[view]['silhouette'][yi,ci]&valid
 obj={'id':name,**p,'annotation':'Manual broad owner candidate ROI; automatic RGB predicate, not a hand-drawn contour','crop_raw_rgb_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'color_candidate_limit':'Plant-color counts are candidates, not semantic truth; especially warm wood can satisfy the red-color clause.','positive_warm_pixels':int(warm.sum()),'plant_color_pixels':int(plant.sum()),'warm_outside_original_grid':int((warm&~valid).sum()),'warm_supported_by_own_silhouette':int((warm&sil).sum()),'warm_present_before_gallery_carve':int((warm&prior).sum()),'warm_missing_after_gallery_carve':int((warm&prior&~final).sum()),'warm_missing_after_gallery_carve_fraction_of_prior':float((warm&prior&~final).sum()/max(1,(warm&prior).sum())),'native_pixel_coordinates_are_not_cross_view_registered':True}
 if view=='front':
  z=frontz[yi,ci];skin=(z>=0)&occ[yi,ci,np.maximum(z,0)];obj.update({'plant_pixels_without_outer_skin':int((plant&~skin).sum()),'plant_pixels':int(plant.sum())})
 probe_results.append(obj)
# Audited high-resolution panel evidence against actual coarse front skin.
panel=np.load(A/'railing_measurement_r01/pixel_masks.npz');labels=panel['labels'];py,px=np.indices(labels.shape);px+=152;py+=250;xx=(px-64)//4;yy=(495-py)//4;z=frontz[yy,xx];skin=occ[yy,xx,z];apertures=[]
for ident in (2,):
 for k in range(1,label(labels==ident)[1]+1):
  comp=label(labels==ident)[0]==k;coord=np.argwhere(comp);apertures.append({'class':'semantically_annotated_dark_aperture','source_bbox_half_open':[int(coord[:,1].min()+152),int(coord[:,0].min()+250),int(coord[:,1].max()+153),int(coord[:,0].max()+251)],'pixels':int(comp.sum()),'pixels_projecting_to_occupied_coarse_front_skin':int((comp&skin).sum()),'unique_4x4_blocks':len(set(map(tuple,np.stack([yy[comp],xx[comp]],1).tolist()))),'note':'Occupied skin blocks demonstrate loss of measured 2D aperture; missing skin alone would not prove an unobstructed through-hole.'})
classes={int(i):{'source_pixels':int((labels==i).sum()),'source_pixels_mapping_to_occupied_coarse_skin':int(((labels==i)&skin).sum())} for i in np.unique(labels)}
# Verify actual common compiled occupancy, not only an author-side mask.
class JsonStream:
 def __init__(self,f):self.f=f;self.b='';self.p=0;self.eof=False;self.decoder=json.JSONDecoder()
 def fill(self):
  self.b=self.b[self.p:];self.p=0;s=self.f.read(65536);self.eof=not bool(s);self.b+=s
 def peek(self):
  while True:
   while self.p<len(self.b) and self.b[self.p].isspace():self.p+=1
   if self.p<len(self.b):return self.b[self.p]
   if self.eof:return ''
   self.fill()
 def eat(self,c):assert self.peek()==c;self.p+=1
 def val(self):
  self.peek()
  while True:
   try:
    v,e=self.decoder.raw_decode(self.b,self.p)
    if e==len(self.b) and not self.eof:self.fill();continue
    self.p=e;return v
   except json.JSONDecodeError:
    if self.eof:raise
    self.fill()
co=np.zeros_like(occ);compiled_count=0
with gzip.open(D/'diagnostic.compiled.json.gz','rt') as cf:
 j=JsonStream(cf);j.eat('{')
 while j.peek()!='}':
  key=j.val();j.eat(':')
  if key=='cells':
   j.eat('[')
   while j.peek()!=']':
    cell=j.val();co[cell[1],cell[0]+48,cell[2]+40]=True;compiled_count+=1
    if j.peek()==',':j.eat(',')
    else:break
   j.eat(']')
  else:j.val()
  if j.peek()==',':j.eat(',')
  else:break
 j.eat('}')
assert np.array_equal(co,occ);del co
# Witness samples are selected from actually lost side projection with positive side pixels.
side_lost=floors.any(1)&~occ.any(1);witnesses=[]
for yy,zz in [(55,75),(58,75),(34,75),(65,75)]:
 if not side_lost[yy,zz]:continue
 world=[(zz-40+.5)*.125,(yy+.5)*.125]
 item={'array_yz':[yy,zz],'world_yz_center_m':[world[1],world[0]],'each_stage_x_occupancy':{k:int(v[yy,:,zz].sum()) for k,v in stages.items()},'source_pixels':{},'actual_godot_pixels':{}}
 for view in ('right','left'):
  sx=926-4*zz if view=='right' else 98+4*zz;sy=494-4*yy if view=='right' else 1006-4*yy
  item['source_pixels'][view]={'central_sample_xy':[sx,sy],'block_roi':[sx-2,sy-2,sx+2,sy+2],'center_rgb':im[sy,sx].tolist(),'own_silhouette':bool(maps[view]['silhouette'][yy,zz])}
  # Verified orthographic camera anchor slope: 812 px / 18m.
  ax=590+(-1 if view=='right' else 1)*world[0]*812/18;ay=721.777770996094-world[1]*812/18
  rim=np.asarray(Image.open(A/f'roof_repair_r04/actual_godot_r01/after/{view}.png').convert('RGB'));ix,iy=int(ax),int(ay)
  item['actual_godot_pixels'][view]={'pixel_xy':[ix,iy],'rgb':rim[iy,ix].tolist(),'background_reference_rgb':rim[750,900].tolist(),'same_as_background':bool(np.array_equal(rim[iy,ix],rim[750,900]))}
 witnesses.append(item)
# Floor sections identify semantic destruction of the deck, without calling it measured thickness.
decks=[]
for name,rows in [('lower',[26,27]),('upper',[50,51])]:
 decks.append({'level':name,'planned_prior_rows':rows,'world_y_interval_m':[rows[0]*.125,(rows[-1]+1)*.125],'front_region_z_cells':[71,80],'shell_cells':int(shell[rows,:,71:80].sum()),'after_planned_floor_cells':int(floors[rows,:,71:80].sum()),'after_gallery_and_glass_cells':int(occ[rows,:,71:80].sum()),'lost_from_planned_floor':int((floors[rows,:,71:80]&~occ[rows,:,71:80]).sum()),'thickness_is_prior_not_image_measurement':True})
# Evidence citations are hashes plus exact code ranges; downstream mesh proofs already exist.
inputs=[SRC,P/'design_r01/architecture_ab_voxel_preview.png',P/'six_views_r01/registration_r03.json',D/'reconstruct.py',D/'image_derived_arrays.npz',D/'image_derived.master.json.gz',D/'diagnostic.compiled.json.gz',D/'verification.json',A/'foundation_repair_r01/foundation_arrays.npz',A/'foundation_repair_r01/verification.json',A/'railing_measurement_r01/measure_panel.py',A/'railing_measurement_r01/pixel_masks.npz',A/'railing_measurement_r01/source_contract.json',A/'railing_measurement_r01/verification.json',A/'roof_repair_r04/composition.json',A/'roof_repair_r04/validation_r01/render_validation.json',A/'roof_repair_r04/actual_godot_r01/after/capture_report.json']
inputs += [A/f'roof_repair_r04/actual_godot_r01/after/{v}.png' for v in ['front','left','right','back','top','bottom','oblique']]
reg=json.loads((P/'six_views_r01/registration_r03.json').read_text());mesh=json.loads((A/'roof_repair_r04/validation_r01/render_validation.json').read_text());comp=json.loads((A/'roof_repair_r04/composition.json').read_text())
result={'schema':'riverstone.gallery.readonly_loss_audit.v1','diagnostic_only':True,'production_gate_open':False,'no_geometry_artifact_generated':True,'source_image':ref(SRC),'inputs':[ref(p) for p in inputs],'pixel_coordinate_convention':'All ROI [x0,y0,x1,y1] half-open; image origin top-left; no raster warp or rescale for measurements. Inspection PNGs use 3x nearest-neighbor display only.','grid':{'old_pitch_m':.125,'native_pixel_pitch_m':.03125,'front_pixel_center_to_world':'x=(px+0.5-256)/32; y=(496-py-0.5)/32; z depth is not observed','left_pixel_center_to_world':'z=(px+0.5-256)/32; y=(1008-py-0.5)/32; x depth is not observed','right_pixel_center_to_world':'z=(768-px-0.5)/32; y=(496-py-0.5)/32; x depth is not observed'},'replay':{'real_source_masks_equal_saved':mask_exact,'replayed_hull_equal_saved':True,'replayed_occupancy_equal_saved':True,'actual_common_compiled_occupancy_equal_replayed':True,'compiled_cells':compiled_count,'foundation_did_not_change_gallery_y_1_5_to_9_5':True,'sampling_calls':0,'mesher_calls':0},'registration':{'global_pass':reg['registration_pass'],'max_error_px':reg['max_error_px'],'left_y_fiducial_scale':reg['diagnostic_affine_fits']['left']['template_to_output_affine'][1][1],'left_lower_corner_errors_px':[q['error_px'] for q in reg['fiducials'] if q['id'] in ['left_2','left_3']],'affine_fits_applied':False,'caution':'Matching outer fiducials does not establish internal gallery edge correspondence. LEFT/RIGHT native pixel ROI measurements must not be combined into one 3D profile silently.'},'gallery_stages':gallery_rows,'source_native_probes':probe_results,'coarse_panel_vs_native_semantic_labels':{'roi':[152,250,216,298],'class_id_names':{'0':'other_owner','1':'positive_wood','2':'observed_aperture','3':'shadow_unresolved_depth','4':'plant_occlusion','5':'uncertain'},'counts':classes,'apertures':apertures,'native_existing_panel_was_not_integrated':True},'deck_loss':decks,'source_to_actual_witnesses':witnesses,'downstream_mesh_evidence':{'source':ref(A/'roof_repair_r04/validation_r01/render_validation.json'),'existing_verified_lower_quads':mesh.get('original_lower_quads_exact'),'missing_unit_faces':mesh.get('missing_unit_faces'),'extraneous_unit_faces':mesh.get('extraneous_unit_faces'),'artificial_interface_unit_faces':mesh.get('artificial_interface_unit_faces'),'current_composition_lower_quads_retained':comp['lower_original_quads_kept'],'independently_rerun_mesh_verifier':False,'meaning':'Existing SHA-bound mesh report plus independently replayed/compiled gallery occupancy and actual background pixels localize first loss before meshing. No new large mesh verification or GUI run is claimed.'},'limits':['The masks classify appearance, not albedo. Warm plant/flower pixels may enter wood unless separately owned.','No arbitrary dark pixel is a proven hole, no uncertain omitted pixel is certified empty.','Side wall/rail plane position, return thickness, plant volume and hidden deck underside are not uniquely recoverable from these inconsistent generated panels.','Approved style sheet is visual design authority, not a calibrated depth measurement.','TOP/BOTTOM remain globally unregistered and do not certify gallery underside or projection.'], 'elapsed_seconds':time.monotonic()-START,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'address_space_limit_mib':256,'cpu_limit_seconds':110}
dump('diagnosis.json',result)
print(json.dumps({'report':str((O/'diagnosis.json').relative_to(ROOT)),'gallery_stages':gallery_rows,'panel_apertures':apertures,'deck_loss':decks,'witness_count':len(witnesses),'seconds':result['elapsed_seconds'],'peak_rss_kib':result['peak_rss_kib']}))
assert sum(p.stat().st_size for p in O.rglob('*') if p.is_file())<2000000
