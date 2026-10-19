"""Read-only geometry inventory from approved pixels and explicit semantic ROIs.
Search windows are not automatically recovered sewing panels or output masks.
Overlapping/unassigned pixels are retained as uncertainty, not silently allocated.
"""
import json,hashlib,gzip,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;REPO=ROOT.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def run():
 c=read(BASE/'data/chart_inventory.json');src=REPO/c['approved_source']['path'];assert sha(src)==c['approved_source']['sha256'];im=np.array(Image.open(src).convert('RGB'));alignment=read(ROOT/'data/measurement_contract.json');arrays={};stats={};display=Image.fromarray(im[:630].copy());draw=ImageDraw.Draw(display)
 for name,v in alignment['views'].items():
  x0,y0,x1,y1=v['crop'];rgb=im[y0:y1,x0:x1].astype(float);chroma=rgb.max(2)-rgb.min(2);white=(rgb.min(2)>=243)&(chroma<=12);seed=np.zeros_like(white);seed[0]=white[0];seed[-1]=white[-1];seed[:,0]=white[:,0];seed[:,-1]=white[:,-1];exterior=ndi.binary_propagation(seed,mask=white);guide=(rgb[:,:,2]>=245)&(rgb[:,:,2]-rgb[:,:,0]>=25)&(rgb[:,:,2]-rgb[:,:,1]>=15)&(rgb[:,:,1]-rgb[:,:,0]>=6);eligible=(~exterior)&(~guide)&(rgb.mean(2)>=145)&(chroma<=80)&(rgb[:,:,2]-rgb[:,:,0]>=-10);eligible[:c['view_scope_min_y'][name]-y0]=False;arrays[name+'_pale_surface_candidate']=eligible
  count=np.zeros_like(eligible,np.uint8);measured=np.zeros_like(eligible);occluded_search=np.zeros_like(eligible);items=[]
  for item in c['charts']:
   spec=item.get('views',{}).get(name)
   if not spec:continue
   q=np.zeros_like(eligible)
   if 'frozen_measurement_path' in spec:
    fp=ROOT/spec['frozen_measurement_path'];m=dict(np.load(fp));q=m[spec['mask_key']];measured|=q;assert q.shape==eligible.shape
   else:
    a,b,cc,d=spec['search_box_xyxy'];q[max(0,b-y0):min(y1-y0,d-y0),max(0,a-x0):min(x1-x0,cc-x0)]=True;q&=eligible
   count+=q.astype(np.uint8);arrays[name+'_'+item['id']]=q
   box=spec.get('search_box_xyxy');
   if box:
    color=(65,100,240) if item['status']=='candidate_search_window' else (40,170,80);draw.rectangle(box,outline=color,width=1);draw.text((box[0]+2,box[1]+2),item['short_id'],fill=color)
   items.append({'chart_id':item['id'],'candidate_pixels':int(q.sum()),'status':item['status'],'observed_boundary_complete':False,'independent_patch_mask_available':item['status']=='measured_visible_patch','boundary_includes_explicit_manual_unknown_segments':True,'sewn_identity_confirmed':False})
  for box in c['occluder_search_regions'][name]:
   a,b,cc,d=box['box'];occluded_search[max(0,b-y0):min(y1-y0,d-y0),max(0,a-x0):min(x1-x0,cc-x0)]=True;draw.rectangle(box['box'],outline=(235,130,20),width=1)
  unc=eligible&(count==0);amb=eligible&(count>1);arrays[name+'_unassigned_candidate']=unc;arrays[name+'_overlap_ambiguous_candidate']=amb;arrays[name+'_occluder_search_unknown']=eligible&occluded_search
  # These colors mark observational inventory; no occupancy is created or edited.
  a0=np.array(display);tile=a0[y0:y1,x0:x1].astype(float);tile[unc]=.6*tile[unc]+[90,0,0];tile[amb]=.6*tile[amb]+[80,40,0];a0[y0:y1,x0:x1]=np.clip(tile,0,255).astype(np.uint8);display=Image.fromarray(a0);draw=ImageDraw.Draw(display)
  stats[name]={'pale_surface_candidate_pixels':int(eligible.sum()),'frozen_measured_patch_pixels_inside_candidates':int((eligible&measured).sum()),'unassigned_candidate_pixels':int(unc.sum()),'multiply_claimed_search_pixels':int(amb.sum()),'occluder_search_unknown_candidate_pixels':int((eligible&occluded_search).sum()),'unique_search_assignment_pixels':int((eligible&(count==1)).sum()),'charts':items,'denominator_warning':'Only color-eligible pale visible surface candidates, not exact costume mask. White bouquet, lace, footwear and background/outline classification can disagree. Ambiguity is retained.'}
 canvas=Image.new('RGB',(1536,690),'white');canvas.paste(display,(0,0));dd=ImageDraw.Draw(canvas);dd.text((12,639),'APPROVED VIOLET r06 | chart SEARCH inventory only, not final masks or geometry. Blue boxes:candidates; green:existing measured patch.',fill='black');dd.text((12,658),'Amber:overlapping candidate ownership. Red:unassigned pale pixels (also background holes/flowers). These are retained unknowns, not repaired cloth.',fill='black');canvas.save(BASE/'generated/full_costume_chart_inventory.jpg',quality=92);np.savez_compressed(BASE/'evidence/view_chart_candidates.npz',**arrays);write(BASE/'evidence/chart_inventory_measurement.json',{'source_sha256':sha(src),'actual_RGB_pixel_sha256':hashlib.sha256(im.tobytes()).hexdigest(),'semantic_contract_sha256':sha(BASE/'data/chart_inventory.json'),'measurement_code_sha256':sha(__file__),'candidate_arrays_sha256':sha(BASE/'evidence/view_chart_candidates.npz'),'views':stats,'geometry_created':False,'automatic_sewing_recovery_claimed':False,'ambiguity_resolved_by_priority':False});print(json.dumps(stats))
if __name__=='__main__':run()
