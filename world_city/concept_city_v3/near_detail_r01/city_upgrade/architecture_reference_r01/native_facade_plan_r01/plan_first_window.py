"""Read-only first-patch classification/cost contract; no source/voxel emission."""
from audit_facade import *
from collections import Counter
BOX=(1168,216,1240,288)
def run():
 start=time.monotonic();source=np.asarray(Image.open(S).convert('RGB'));x0,y0,x1,y1=BOX;c=source[y0:y1,x0:x1];r,g,b=np.moveaxis(c.astype(float),-1,0);lum=c.mean(2);yy,xx=np.indices(lum.shape);px=x0+xx;py=y0+yy
 frame_region=(px>=1176)&(px<1232)&(py>=220)&(py<278)
 pane=(px>=1184)&(px<1224)&(py>=228)&(py<270)&(b>r*1.05)&(g>r*1.1)&(lum>=20)&(lum<150)
 wood=frame_region&(r>=75)&(r-g>=12)&(g-b>=10)&(r>=1.3*b)&(lum>=55)
 light=~frame_region&(lum>=160)&((c.max(2).astype(int)-c.min(2).astype(int))<80)
 labels=np.zeros(lum.shape,np.uint8);labels[light]=1;labels[wood]=2;labels[pane]=3
 # Explicit uncertainty keeps frame-cast shadows, mixed glass/wood edges, narrow dark
 # seams, and any unclassified appearance unchanged. None becomes a geometry cut.
 names={0:'unresolved_keep_existing',1:'light_masonry_plaster_appearance',2:'positive_window_timber_appearance',3:'blue_pane_appearance'}
 data=np.load(A/'foundation_repair_r01/foundation_arrays.npz');a=np.where(data['occupancy'],data['materials'],-1);hits=[];candidate=[];missing=0
 for y in range(c.shape[0]):
  for x in range(c.shape[1]):
   hit=ray_hit('back',world('back',x0+x,y0+y),a)
   if hit is None:missing+=1;continue
   cy,cx,cz=hit['coarse_array_yxz'];native=(1279-(x0+x),495-(y0+y),(cz-40)*4);hits.append(native)
   if labels[y,x]>0:candidate.append(native)
 count=Counter(p[2] for p in hits);assert len(hits)==72*72 and missing==0
 oldpal=np.load(A/'reconstruction_proof_r01/image_derived_arrays.npz')['palette'];mean=blockmean(c);oldq=nearest(mean,oldpal);material_tests=[];display=oldq.astype(np.uint8).copy();palette_registry={}
 for label,budget in [(1,12),(2,16),(3,8)]:
  mask=labels==label;pixels=c[mask];pi=Image.fromarray(pixels[None,:,:]).quantize(colors=budget,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE);palette=np.asarray(pi.getpalette()[:budget*3],np.uint8).reshape(budget,3);quant=nearest(c,palette);display[mask]=quant[mask].astype(np.uint8)
  material_tests.append({'owner':names[label],'candidate_pixels':int(mask.sum()),'palette_limit':budget,'palette_rgb':palette.tolist(),'old_4x4_shared12_error':error(c[mask],oldq[mask]),'native_owner_limited_palette_error':error(c[mask],quant[mask]),'perceptual_interpretation':'RGB appearance error only; no albedo, transmission or material chemistry inference.'});palette_registry[names[label]]=palette.tolist()
 # Geometrically existing solid cells allow a one-native-cell material replacement,
 # not occupancy additions/removals. Each owner surface preserves its inherited depth.
 unique=set(candidate);halo=set()
 for x,y,z in unique:
  for dx in (-1,0,1):
   for dy in (-1,0,1):
    for dz in (-1,0,1):halo.add((x+dx,y+dy,z+dz))
 report={'schema':'riverstone.native_facade.first_window_contract.v1','status':'READ_ONLY_PLAN_NOT_IMPLEMENTED','source':ref(S),'source_roi_half_open':BOX,'world_xy_bounds_m':{'x':[1.25,3.5],'y':[6.5,8.75]},'existing_surface_native_z_histogram':dict(sorted(count.items())),'existing_front_faces_m':{str(k):k/32 for k in sorted(count)},'existing_hit_pixels':len(hits),'missing_existing_solid_pixels':missing,'proposed_single_layer_cells':len(unique),'proposed_layer_thickness_m':1/32,'candidate_plus_one_cell_26_neighbor_halo_unique_cells':len(halo),'all_roi_box_with_one_cell_halo_if_one_depth':74*74*3,'planned_chunk_layout_native_pixels':[[0,0,36,36],[36,0,72,36],[0,36,36,72],[36,36,72,72]],'per_chunk_max_owner_pixels':36*36,'per_chunk_max_sample_cells_for_one_flat_depth':38*38*3,'layered_policy':'Replace material only in already occupied first-hit native subcells. Keep occupancy, face position, all further depth cells and uncertain labels exact. No silhouette fill, rear-wall relocation, frame extrusion or transparency claim.','mask_counts':{names[k]:int((labels==k).sum()) for k in names},'manual_semantic_regions':{'window_timber_candidate_box':[1176,220,1232,278],'pane_candidate_box':[1184,228,1224,270],'masonry':'Bright low-chroma source pixels outside window box only; plaster versus brick substance remains unresolved.'},'classification_thresholds':{'masonry':'lum>=160 and channel range<80 outside frame box','wood':'r>=75,r-g>=12,g-b>=10,r>=1.3b,lum>=55 in frame box','pane':'b>1.05r,g>1.1r,20<=lum<150 in pane box','uncertain':'Everything else, preserving original occupancy/material.'},'semantic_palette_limit_total':36,'palette_tests':material_tests,'source_shadow_is_not_depth':True,'measured_3d_window_or_frame_depth':False,'existing_window_geometry':'First-hit inherited voxel surface only. BACK does not receive the original FRONT-only glass-recess operation. Different actual depths here come from existing hull, not newly measured reveals.','frozen_owners':['roof_r05 and y>=9.5m join','foundation and y<1.5m','all gallery owners and the repaired FRONT panel','all openings/empty cells','unclassified pixels','all nonselected surface owners'],'required_future_tests':['Actual pixel RGB mutation changes only its accepted native surface material and no occupancy.','Source semantic mutation to uncertainty leaves prior surface unchanged, never creates a hole.','Exact occupancy of all voxels before/after; exact geometry unit faces; expected source material faces.','Per-chunk owner plus one-cell halo, exact partial-quad clipping and material seam equivalence.','Frozen roof group order/array/color hashes; separate normal binding if full render SHA changes.','Actual6orthographic + oblique before/after and close window view; no art promotion if any missing.'],'sampling_calls':0,'mesher_calls':0,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 save('first_window_contract.json',report)
 colors=np.asarray([[130,130,130],[237,220,196],[190,112,53],[45,120,190]],np.uint8);maskimage=colors[labels];board=Image.new('RGB',(1420,440),'#f6f3ed');d=ImageDraw.Draw(board);font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
 d.text((18,12),'BACK window + wall | source-defined planning only; NO geometry compiled',font=font(22),fill='black')
 for i,(im,title) in enumerate([(c,'Original72x72pixels'),(oldq.astype(np.uint8),'Old4x4 + shared12colors'),(maskimage,'Candidate labels; gray stays existing'),(display,'Native owner palette preview, NOT render')]):
  board.paste(Image.fromarray(im).resize((324,324),Image.Resampling.NEAREST),(18+i*350,74));d.text((18+i*350,48),title,font=font(14),fill='black')
 d.text((18,414),'36 colors maximum: light masonry12 / wood16 / blue pane8. No hidden depth, raised frames or shadow-as-geometry.',font=font(16),fill='black');board.save(O/'first_window_plan_board.png')
 print(json.dumps(report),flush=True)
if __name__=='__main__':run()
