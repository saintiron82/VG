"""Pixel mutation, deterministic common compile and actual CPU projections.
No topology repair, rendered-image retouch or learned image substitution.
"""
from pathlib import Path
import copy,math,sys,numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
from measured_panels import *
sys.path.insert(0,str(ROOT.parent/'r08'/'tools'))
from render_evaluate import raster
CPU_SOURCE=ROOT.parent/'r08'/'tools'/'render_evaluate.py'

def components(rows):
 ps=np.array([r[:3] for r in rows],int)
 if not len(ps):return {'six_connected_components':0,'sizes':[],'enclosed_empty_cells':None}
 lo=ps.min(0)-1;g=np.zeros(tuple(ps.max(0)-lo+2),bool);g[tuple((ps-lo).T)]=True;cc,n=ndi.label(g)
 return {'six_connected_components':int(n),'sizes':sorted(np.bincount(cc.ravel())[1:].tolist(),reverse=True),'enclosed_empty_cells':int((ndi.binary_fill_holes(g)&~g).sum()),'repair_performed':False}

def project(render,view,height):
 x0,y0,x1,y1=view['crop'];im=Image.new('1',(x1-x0,y1-y0));d=ImageDraw.Draw(im);t=math.radians(view['yaw_degrees']);s=height/view['scale_px_per_unit']
 for group in render['groups']:
  for quad in group['quads']:
   pts=[(view['axis_u']+(math.cos(t)*x-math.sin(t)*z)/s-x0,view['sole_y']-y/s-y0) for x,y,z in quad];d.polygon(pts,fill=1)
 return np.array(im,dtype=bool)

def projections(render,m,c,save=False):
 a=np.load(m['masks_path']);source=np.array(Image.open(m['source_path']).convert('RGB'));out=ROOT/'generated'/'region';stats={};overlays=[]
 for name in ['front','side','back']:
  v=m['views'][name];pred=project(render,v,c['alignment']['character_height_m_for_test']);fg=a[name+'_foreground'];target=(a['front_patch_labels']>0) if name=='front' else None;count=int(pred.sum());inside=int((pred&fg).sum());s={'projected_pixels':count,'foreground_support_coverage':inside/count if count else None,'projected_outside_foreground_pixels':int((pred&~fg).sum()),'panel_target_status':'measured visible patch union' if name=='front' else 'unknown: whole foreground is support only, not this panel ground truth'}
  x0,y0,x1,y1=v['crop'];rgb=source[y0:y1,x0:x1].astype(float)
  if target is not None:
   overlap=pred&target;extra=pred&~target;missing=target&~pred;s.update(panel_union_IoU=float(overlap.sum()/(pred|target).sum()),target_pixels=int(target.sum()),missed_target_pixels=int(missing.sum()),extra_pixels=int(extra.sum()))
   rgb[overlap]=rgb[overlap]*.45+[22,110,35];rgb[extra]=rgb[extra]*.4+[145,12,12];rgb[missing]=rgb[missing]*.5+[15,40,110]
  else:
   rgb[pred&fg]=rgb[pred&fg]*.5+[20,100,40];rgb[pred&~fg]=rgb[pred&~fg]*.4+[145,12,12];s['panel_union_IoU']=None
  stats[name]=s
  if save:
   img=Image.fromarray(np.clip(rgb,0,255).astype('uint8'));img.save(out/f'{name}_projection_overlay.png');crop=img.crop((0,470-y0,x1-x0,624-y0));crop.thumbnail((480,250));overlays.append(crop)
 return stats,overlays

def run():
 cp=ROOT/'data/measurement_contract.json';mp=ROOT/'generated/measured/measurements.json.gz';m,c=verify_measurement(mp);out=ROOT/'generated/region';master=gzread(out/'master.json.gz');compiled=gzread(out/'compiled.cells.json.gz');render=gzread(out/'region.render.json.gz');report={}
 try:verify_measurement(ROOT/'evidence/missing_input.json.gz');report['missing_measurement_rejected']=False
 except ValueError:report['missing_measurement_rejected']=True
 repeat,arrays=extract(cp);report['same_pixels_same_sections']=repeat['sections']==m['sections'];report['same_pixels_same_fold_edges']=repeat['measured_fold_edges']==m['measured_fold_edges']
 repeat_master,_=geometry(m,c);report['same_measurements_same_master']=repeat_master==master
 rebuilt=compile_master(master,{'pitch':c['compile']['pitch_m']},max_candidate_cells=c['compile']['max_candidates'],max_output_cells=c['compile']['max_cells']);report['independent_common_compile_exact']=rebuilt==compiled;report['independent_common_mesh_exact']=make_render_data(rebuilt)==render
 # Actual PNG fixture: remove a local outer-skirt notch to genuine white background.
 # Neither semantic annotations nor measured geometry are edited for this test.
 pixels=np.array(Image.open(m['source_path']).convert('RGB'));before=pixels.copy();box=[70,548,215,560];pixels[box[1]:box[3],box[0]:box[2]]=[255,255,255];mutant=ROOT/'evidence/local_pixel_mutation_fixture.png';Image.fromarray(pixels).save(mutant)
 recipe={'parent_sha256':m['source_sha256'],'mutant_sha256':sha(mutant),'purpose':'regression fixture only; not an approved or edited production reference','box_xyxy':box,'changed_pixel_count':int(np.any(pixels!=before,2).sum()),'new_rgb':[255,255,255],'annotations_changed':False}
 write(ROOT/'evidence/local_pixel_mutation_recipe.json',recipe);mm=verify_measurement(ROOT/'generated/mutated_measurement/measurements.json.gz')[0] if (ROOT/'generated/mutated_measurement/measurements.json.gz').exists() else save_measurement(cp,ROOT/'generated/mutated_measurement',mutant,recipe);mmaster,_=geometry(mm,c);mut=compile_master(mmaster,{'pitch':c['compile']['pitch_m']},max_candidate_cells=c['compile']['max_candidates'],max_output_cells=c['compile']['max_cells']);changed_rows=[a['source_front_row'] for a,b in zip(m['sections'],mm['sections']) if a!=b];expected=set(range(box[1],box[3]));aset={tuple(r[:3]) for r in compiled['cells']};bset={tuple(r[:3]) for r in mut['cells']};delta=aset^bset
 oldops={op['id']:op for op in master['components'][0]['operations']};newops={op['id']:op for op in mmaster['components'][0]['operations']};changed_op_ids=[key for key in sorted(oldops.keys()|newops.keys()) if oldops.get(key)!=newops.get(key)];op_rows={int(key.split('_')[0][3:]) for key in changed_op_ids};cell_y=[(p[1]+.5)*compiled['pitch'] for p in delta];allowed=[(c['views']['front']['sole_y']-box[3])*m['metres_per_front_pixel'],(c['views']['front']['sole_y']-box[1])*m['metres_per_front_pixel']]
 mutated_render=make_render_data(mut);baseproj,_=projections(render,m,c);mutproj,_=projections(mutated_render,mm,c);proj_rows={}
 for name,v in m['views'].items():
  beforemask=project(render,v,c['alignment']['character_height_m_for_test']);aftermask=project(mutated_render,v,c['alignment']['character_height_m_for_test']);ys=np.where((beforemask^aftermask).any(1))[0];px=c['alignment']['character_height_m_for_test']/v['scale_px_per_unit'];allowed_projection_rows=[math.floor(v['sole_y']-(max(cell_y)+compiled['pitch']/2)/px)-v['crop'][1],math.ceil(v['sole_y']-(min(cell_y)-compiled['pitch']/2)/px)-v['crop'][1]] if cell_y else [0,-1]
  proj_rows[name]={'changed_projection_pixels':int((beforemask^aftermask).sum()),'changed_local_rows':ys.tolist(),'view_crop_y0':v['crop'][1],'allowed_rows_including_cell_face_extent':allowed_projection_rows,'locality_pass':bool(len(ys)) and int(ys.min())>=allowed_projection_rows[0] and int(ys.max())<=allowed_projection_rows[1]}
 report['pixel_change']={**recipe,'changed_measurement_rows':changed_rows,'changed_operation_rows':sorted(op_rows),'changed_operations':len(changed_op_ids),'changed_occupancy_cells':len(delta),'delta_y_m':[min(cell_y),max(cell_y)] if cell_y else None,'allowed_y_m':allowed,'measurement_locality_pass':bool(changed_rows) and set(changed_rows)<=expected,'geometry_locality_pass':bool(op_rows) and op_rows<=expected,'cell_locality_pass':bool(delta) and min(cell_y)>=allowed[0]-1e-9 and max(cell_y)<=allowed[1]+1e-9,'side_back_measurements_exact':all(a['views']['side']==b['views']['side'] and a['views']['back']==b['views']['back'] for a,b in zip(m['sections'],mm['sections'])),'projection_regression':proj_rows,'base_projection_metrics':baseproj,'mutated_projection_metrics':mutproj,'mutant_master_hash':digest(mmaster),'mutant_payload_hash':mut['payload_hash']}
 # Contradiction changes a diagnostic measurement copy, not the approved image:
 # foreground support removed -> no occupied row can have feasible depth.
 contradiction=copy.deepcopy(m)
 for row in contradiction['sections']:row['views']['side']['foreground_intervals_px']=[]
 cm,cr=geometry(contradiction,c);contradiction_rejected=not cm['components'][0]['operations'] and all(r['feasible_width_m']==0 for r in cr)
 badcompiled=compile_master(cm,{'pitch':c['compile']['pitch_m']});report['contradictory_view_compile_rejected']=not badcompiled['valid'];report['contradictory_view_failed_constraints']=badcompiled['constraints']
 try:make_render_data(badcompiled);report['contradictory_view_render_rejected']=False
 except ValueError as e:report['contradictory_view_render_rejected']=True;report['contradiction_exception']=str(e)
 report['diagnostic_correction']='Initial diagnostic incorrectly equated rejection with a thrown compile exception; common compiler returns valid=false and failed nonempty constraint. Initial report and mislabeled contact sheet are preserved in evidence. Corrected sheet explicitly orders front, side, back.'
 report['contradictory_measurement_has_no_feasible_geometry']=contradiction_rejected
 report['topology']=components(compiled['cells']);report['yaw_uncertainty']=[]
 for yaw in [60,90]:
  ym,yr=geometry(m,c,yaw);yc=compile_master(ym,{'pitch':c['compile']['pitch_m']},max_candidate_cells=c['compile']['max_candidates'],max_output_cells=c['compile']['max_cells']);ys={tuple(r[:3]) for r in yc['cells']};report['yaw_uncertainty'].append({'yaw_degrees':yaw,'cells':len(ys),'cells_different_from_75_degree_hypothesis':len(ys^aset),'payload_hash':yc['payload_hash'],'interpretation':'sensitivity only; no hypothesis is calibrated or selected as recovered depth'})
 report['source_preserved']=sha(m['source_path'])==c['source_sha256'];report['original_preserved']=sha(REPO/c['original'])==c['original_sha256'];report['compiler_sha256']=sha(COMMON/'core.py');report['validator_sha256']=sha(__file__);report['measurement_file_sha256']=sha(mp);report['master_file_sha256']=sha(out/'master.json.gz');report['reconstruction_approved']=False;write(ROOT/'evidence/regression.json',report)
 metrics,overlays=projections(render,m,c,save=True);write(out/'projection_metrics.json',metrics);lo=np.array(render['bounds']['min']);hi=np.array(render['bounds']['max']);center=(lo+hi)/2;span=float(max(hi-lo)*1.3);views=[]
 for name,yaw,pitch in [('front',0,0),('three_quarter',45,15),('side',90,0),('back',180,0)]:
  im=raster(render,math.radians(yaw),math.radians(pitch),center,span,size=384);d=ImageDraw.Draw(im);d.rectangle((0,0,384,25),fill='white');d.text((8,8),name+' / actual common mesh CPU',fill='black');im.save(out/f'cpu_{name}.png');views.append(im)
 sheet=Image.new('RGB',(1560,920),'white');d=ImageDraw.Draw(sheet);d.text((20,15),'r10 APPROVED IMAGE -> MEASURED PATCHES -> SECTION FEASIBILITY -> COMMON VOXELS',fill='black');d.text((20,40),'One skirt ROI. Feasible depth volume, NOT recovered cloth surface or approved 3D asset.',fill='black')
 for i,(name,im) in enumerate(zip(['front','side','back'],overlays)):
  sheet.paste(im,(20+i*515,80));d.text((20+i*515,270),name+(' | measured patch IoU %.3f'%metrics[name]['panel_union_IoU'] if name=='front' else ' | panel correspondence UNKNOWN'),fill='black')
 for i,im in enumerate(views):sheet.paste(im,(10+i*388,310))
 lines=['Native pixel masks -> 105 row sections -> intersection with side/back foreground support. No ellipse or hand-sculpted curve.',f'Actual common compile: {len(compiled["cells"])} cells. 6-connected components: {report["topology"]["six_connected_components"]}. No deletion/filling/thickness repair.',f'Local real-image notch: {recipe["changed_pixel_count"]} changed pixels -> {len(changed_rows)} measurement rows -> {len(delta)} occupancy cells.',f'Side 75 deg is a hypothesis. 60/90 deg tests change occupancy; unseen depth and panel identity remain unresolved.','Front: green overlap, red model extra, blue missed. Side/back: green supported, red outside foreground; no panel IoU claimed.','Reference approved by user; this technical prototype is not garment/art approval. GPU, rig/socket and final AI correction pending.']
 for i,t in enumerate(lines):d.text((20,730+i*27),t,fill='black')
 sheet.save(out/'measurement_pipeline_comparison.jpg',quality=88);write(out/'cpu_provenance.json',{'renderer_path':str(CPU_SOURCE.relative_to(REPO)),'renderer_sha256':sha(CPU_SOURCE),'mesh_input_sha256':sha(out/'region.render.json.gz'),'camera_center_m':center.tolist(),'span_m':span,'views':[{'name':n,'sha256':sha(out/f'cpu_{n}.png')} for n in ['front','three_quarter','side','back']],'comparison_sha256':sha(out/'measurement_pipeline_comparison.jpg'),'GPU_screenshot':False});budget();print(json.dumps({'checks':{k:v for k,v in report.items() if isinstance(v,bool)},'pixel_locality':{k:v for k,v in report['pixel_change'].items() if k.endswith('pass')},'topology':report['topology'],'projection':metrics,'disk_bytes':budget()}))
if __name__=='__main__':run()
