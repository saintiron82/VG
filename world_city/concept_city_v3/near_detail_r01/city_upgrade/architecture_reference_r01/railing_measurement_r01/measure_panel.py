"""One raster-measured railing evidence panel at its original building position.
Semantic regions select material classes, never hand-draw the bars. Unknown
pixels are not certified as solid or void. Original image/source stay unchanged.
"""
import gzip,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(ROOT));from voxel_character.common import core
O=Path(__file__).resolve().parent;P=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01';ROI=(152,250,216,298);PITCH=1/32;THICKNESS=2;LABELS={0:'other_owner',1:'positive_wood',2:'observed_aperture',3:'shadow_unresolved_depth',4:'plant_occlusion',5:'uncertain'};COLORS=np.array([[190,190,190],[191,127,60],[60,160,230],[84,68,127],[45,158,70],[236,65,179]],np.uint8)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.resolve().relative_to(ROOT)),'sha256':sha(p)}
def save(p,o):
 assert not p.exists();b=json.dumps(o,separators=(',',':'),allow_nan=False).encode();p.write_bytes(gzip.compress(b,mtime=0) if p.suffix=='.gz' else b)
def classify(crop):
 r,g,b=np.moveaxis(crop.astype(float),-1,0);lum=crop.mean(2);yy,xx=np.indices(crop.shape[:2]);x=xx+ROI[0];y=yy+ROI[1];panel=(y>=254)&(y<292);labels=np.zeros(panel.shape,np.uint8);labels[panel]=5
 wood=(r>=90)&(r-g>=12)&(g-b>=12)&(r>=1.3*b)&(lum>=80);labels[panel&wood]=1
 shadow=panel&(y>=257)&(y<264)&(lum<105)&(r>g)&(g>b);labels[shadow]=3
 plant_region=(x>=210)&(y<270);plant=((g>r*.95)&(g>b*1.1)&(lum<190))|((r-g>70)&(r-b>80)&(g<95));labels[panel&plant_region&plant]=4
 holes=[]
 for ident,box in [('diamond_upper',[156,264,166,274]),('diamond_lower',[157,276,165,285])]:
  x0,y0,x1,y1=box;region=(x>=x0)&(x<x1)&(y>=y0)&(y<y1);dark=(lum<62)&(crop.max(2)<100);mask=panel&region&dark;labels[mask]=2;holes.append({'id':ident,'semantic_roi_px':box,'automatic_dark_pixels':int(mask.sum()),'evidence':'Dark diamond enclosed by visible wood; manually annotated aperture interpretation. Single image cannot independently prove hidden backface absence.'})
 return labels,holes

def make_source(crop,labels,palette):
 # Lower-bound occupied cells only: certified positive wood. Dark/bright ambiguous
 # pixels are retained as separate evidence masks, not silently declared holes.
 wood=labels==1;mi=np.argmin(((crop.astype(float)[:,:,None,:]-palette[None,None,:,:])**2).sum(3),axis=2);ops=[]
 for yy in range(48):
  xx=0
  while xx<64:
   if not wood[yy,xx]:xx+=1;continue
   x0=xx;mat=int(mi[yy,xx]);xx+=1
   while xx<64 and wood[yy,xx] and int(mi[yy,xx])==mat:xx+=1
   sx0=ROI[0]+x0;sx1=ROI[0]+xx;sy=ROI[1]+yy
   ops.append({'id':f'raster_wood_y{sy}_x{sx0}_{sx1}','part':'measured_railing_positive','action':'paint','material':f'measured_wood_{mat}','shape':{'kind':'box','min':[(sx0-256)/32,(496-sy-1)/32,5-THICKNESS/32],'max':[(sx1-256)/32,(496-sy)/32,5]}})
 return {'schema':core.SCHEMA,'id':'architecture_A_railing_measured_positive_r01','revision':1,'grid_origin':[0,0,0],'axes':{'up':'+Y','front':'+Z','right':'+X'},'materials':{f'measured_wood_{i}':''.join(f'{int(x):02x}' for x in c) for i,c in enumerate(palette)},'components':[{'id':'measured_railing_pixels','parts':[{'id':'measured_railing_positive','pivot':[0,0,0]}],'operations':ops}],'instances':[{'id':'at_actual_front_gallery_position','component':'measured_railing_pixels'}],'assembly_cuts':[],'constraints':[{'id':'measured_positive_nonempty','kind':'nonempty'}],'metadata':{'diagnostic_only':True,'production_gate_open':False,'occupancy_scope':'positive evidence lower bound; uncertain/shadow/plant pixels are not certified void','source_roi_px':list(ROI),'source_image':ref(P/'generated_candidate_r03.png'),'depth_prior_m':THICKNESS/32,'not_recentered':True,'other_owners':['upper wall/glazing y250..253','deck fascia y292..297','structuralposts and gallery rearwall outside this pixel panel'],'no_backplate_or_sidewall_added':True,'original_building_unchanged':True}}

def run():
 start=time.monotonic();image=np.asarray(Image.open(P/'generated_candidate_r03.png').convert('RGB'));crop=image[250:298,152:216].copy();labels,holes=classify(crop);labels2,_=classify(crop);assert np.array_equal(labels,labels2);wood=crop[labels==1];pal=np.array(Image.fromarray(wood[None,:,:],'RGB').quantize(colors=3,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE).getpalette()[:9],np.uint8).reshape(3,3);master=make_source(crop,labels,pal);core.validate_master(master,PITCH);save(O/'railing_positive.master.json.gz',master)
 Image.fromarray(crop).save(O/'source_crop.png');Image.fromarray(COLORS[labels]).save(O/'semantic_labels.png');np.savez_compressed(O/'pixel_masks.npz',labels=labels,source_rgb=crop,palette=pal,**{n:labels==i for i,n in LABELS.items()})
 for i,n in LABELS.items():Image.fromarray((labels==i).astype(np.uint8)*255).save(O/(n+'.mask.png'))
 # Actual source raster edit, not post-extraction label modification. Select one
 # positive pixel away from semantic ownership edges; replace only that pixel.
 pos=np.argwhere(labels==1);y,x=next((int(y),int(x)) for y,x in pos if 10<x<50 and 15<y<35);changed=image.copy();changed[250+y,152+x]=[255,0,255];mut=changed[250:298,152:216];ml,_=classify(mut);assert ml[y,x]!=1;changed_cells=int(np.count_nonzero((labels==1)!=(ml==1)))*THICKNESS;assert changed_cells==2;alt=make_source(mut,ml,pal);assert core.digest(alt)!=core.digest(master)
 # Keep unknown classes explicit: this is not a completed or structurally
 # validated panel, even though it has the correct actual world placement.
 board=Image.new('RGB',(1280,760),'white');dr=ImageDraw.Draw(board);ff=lambda s:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',s);dr.text((20,15),'ONE ACTUAL GALLERY PANEL |1px=31.25mm | diagnostic evidence',font=ff(24),fill='black');dr.text((20,52),'No bars redrawn. Source at x[-3.25,-1.25],y[6.1875,7.6875],front z5. Depth.0625m prior.',font=ff(18),fill='black');board.paste(Image.fromarray(crop).resize((512,384),Image.Resampling.NEAREST),(20,110));board.paste(Image.fromarray(COLORS[labels]).resize((512,384),Image.Resampling.NEAREST),(650,110));dr.text((20,85),'Unchanged source64x48 crop, display8x',font=ff(18),fill='black');dr.text((650,85),'Measured categorical pixels, display8x',font=ff(18),fill='black')
 for i,n in LABELS.items():
  yy=520+i*32;dr.rectangle((20,yy,45,yy+22),fill=tuple(COLORS[i]));dr.text((55,yy),f'{n}: {int((labels==i).sum())} pixels',font=ff(18),fill='black')
 dr.text((650,525),'Only positive wood enters the lower-bound mesh.',font=ff(18),fill='black');dr.text((650,559),'Unknown gaps do NOT prove real openings.',font=ff(18),fill=(160,30,90));dr.text((650,593),'Bright repeated spots remain uncertain.',font=ff(18),fill='black');dr.text((650,627),'Back wall, deck and posts are separate owners.',font=ff(18),fill='black');dr.text((650,661),'No full-house compile. No hidden backplate.',font=ff(18),fill='black');board.save(O/'mask_contract_board.png')
 c={'schema':'riverstone.image_railing.mask_source_contract.v1','source_image':ref(P/'generated_candidate_r03.png'),'source_crop':ref(O/'source_crop.png'),'masks':ref(O/'pixel_masks.npz'),'label_image':ref(O/'semantic_labels.png'),'mask_board':ref(O/'mask_contract_board.png'),'master':ref(O/'railing_positive.master.json.gz'),'script':ref(Path(__file__)),'diagnostic_only':True,'production_gate_open':False,'source_roi_px':list(ROI),'source_pixel_scale_m':PITCH,'pitch_m':PITCH,'thickness_prior_m':.0625,'roi_world_bounds':{'min':[-3.25,6.1875,4.9375],'max':[-1.25,7.6875,5]},'actual_building_position':True,'source_view_registration':'Original FRONT32px/m coordinates only; global sheet registration remains failed.','manual_semantic_regions':{'panel_y_px':[254,292],'other_owner_y_px':[[250,254],[292,298]],'plant_candidate_roi':[210,250,216,270],'shadow_band_y_px':[257,264],'hole_interpretations':holes},'classification_counts':{n:int((labels==i).sum()) for i,n in LABELS.items()},'automatic_classification':'Actual RGB wood/plant/dark thresholds; semantic broad regions never prescribe bar centers/widths. Mixed/bright repeats remain uncertain.','occupancy_scope':'lower_bound_positive_wood_only','positive_cell_count':int((labels==1).sum())*THICKNESS,'candidate_budget_cells':64*48*2,'source_run_count':len(master['components'][0]['operations']),'original_raster_mutation_test':{'source_pixel_xy':[152+x,250+y],'replacement_rgb':[255,0,255],'changed_occupied_cells':changed_cells,'source_master_changed':True,'original_file_unchanged':sha(P/'generated_candidate_r03.png')=='552b0bd61eba3c3f5bee98a6b3a5fac085362dc8804e049e325db55fb902ec93'},'tests':{'deterministic_masks':True,'actual_raster_edit_changes_mask_and_source':True,'single_pixel_edit_changes_two_depth_cells':True,'unknown_not_claimed_void':True,'real_world_position_not_recentered':True,'no_backwall_deck_or_support_post_generation':True},'compile_estimate_seconds':[1,10],'compile_authorized_scope':'This bounded component only; no fullhouse recompile.','seconds':time.monotonic()-start};save(O/'source_contract.json',c);print(json.dumps({'contract':ref(O/'source_contract.json'),'board':ref(O/'mask_contract_board.png'),'counts':c['classification_counts'],'positive_cells':c['positive_cell_count'],'runs':c['source_run_count'],'mutation':c['original_raster_mutation_test']}))
if __name__=='__main__':run()
