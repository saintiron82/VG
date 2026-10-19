"""Image-constrained occupied volumes with explicit, unmeasured depth priors.
Not full 3D reconstruction. No source image texture or billboard geometry.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,math,sys
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1];COMMON=ROOT/'evidence/compiler_snapshot/common';sys.path.insert(0,str(COMMON))
from core import compile_master,digest
from render_data import make_render_data
from continuous_fields import fields

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')

def build(aid):
 continuous=read(ROOT/'data/continuous_rules.json');rules=read(ROOT.parent/'image_measured_r01/data/volume_rules.json');rules['sampling'].update(continuous['sampling']);a=next(a for a in read(ROOT/'data/annotations.json')['assets'] if a['id']==aid);d=ROOT.parent/'image_measured_r01/measurements'/aid;m=read(d/'measurements.json');pixels=np.load(d/'pixels.npz');mask=pixels['mask'];sem=pixels['semantic'];colors=pixels['colors'];palette=pixels['palette'];base_colors=m['palette_base_colors'];excluded=pixels['excluded'];h,w=mask.shape;source=(ROOT/'data'/a['source']).resolve();assert sha(source)==a['expected_sha256']==m['source_sha256']
 out=ROOT/'generated'/aid;assert not out.exists(),'Refuse overwrite prototype';out.mkdir()
 bbox=m['automatic']['foreground_bbox'];mpp=rules['projection']['frame_height_m']/(bbox[3]-bbox[1]);source_rgb=np.asarray(Image.open(source).convert('RGB'));field_lo,field_hi,field_part,section_records=fields(continuous,pixels,source_rgb,mpp,out);dump(out/'cross_section_evidence.json',section_records);bulk=rules['sampling']['bulk_m'];detail=rules['sampling']['detail_m'];micro=rules['sampling']['micro_m'];labels={int(k):v for k,v in m['semantic_labels'].items()}
 materials={'p'+str(i):{'albedo':'#'+''.join('%02x'%c for c in rgb),'role':'measured_source_rgb'} for i,rgb in enumerate(palette)}
 # Existing common materials use `color`; both are recorded for clarity.
 for v in materials.values():v['color']=v['albedo']
 rear={}
 for sid,name in labels.items():
  if sid==0:continue
  observed=colors[(sem==sid)&mask&~excluded];counts=np.bincount(observed,minlength=len(palette));rear[sid]=int(counts.argmax())
 distances={sid:ndi.distance_transform_edt(sem==sid) for sid in labels if sid!=0}
 eye_rois=a['eye_rois'];head=a['head_roi'];ops=[];columns=[];tier_ids={'bulk':[],'detail':[],'micro':[]}
 def pixel_box(x,y,p):
  return [max(0,int(math.ceil(x/mpp+w/2-.5))),max(0,int(math.ceil(h-(y+p)/mpp-.5))),min(w,int(math.ceil((x+p)/mpp+w/2-.5))),min(h,int(math.ceil(h-y/mpp-.5)))]
 def overlap(b,c):return b[0]<c[2] and b[2]>c[0] and b[1]<c[3] and b[3]>c[1]
 def author(ix,iy,p,tier):
  x=ix*p;y=iy*p;b=pixel_box(x,y,p);x0,y0,x1,y1=b
  if x1<=x0 or y1<=y0:return
  region=mask[y0:y1,x0:x1];coverage=float(region.mean())
  if coverage<.025:return
  values=sem[y0:y1,x0:x1][region];sid=int(np.bincount(values,minlength=9).argmax())
  need_fine=(coverage<.97 or any(np.mean(values==v)>.08 for v in rules['sampling']['fine_semantics']) or overlap(b,head))
  if tier=='bulk' and need_fine:
   for dx in [0,1]:
    for dy in [0,1]:author(ix*2+dx,iy*2+dy,detail,'detail')
   return
  if tier=='detail' and any(overlap(b,[q[0]-4,q[1]-4,q[2]+4,q[3]+4]) for q in eye_rois):
   for dx in [0,1]:
    for dy in [0,1]:author(ix*2+dx,iy*2+dy,micro,'micro')
   return
  if coverage<rules['sampling']['foreground_cell_coverage_min']:return
  vals=colors[y0:y1,x0:x1][region];special=vals[vals>=base_colors]
  color=int(np.bincount(special).argmax()) if len(special)>=max(1,len(vals)*.08) else int(np.bincount(vals,minlength=len(palette)).argmax())
  if np.mean(values==7)>.20:sid=7
  name=labels[sid];lo_values=field_lo[y0:y1,x0:x1][region];hi_values=field_hi[y0:y1,x0:x1][region]
  zlo=math.floor(float(np.median(lo_values))/p)*p;zhi=math.ceil(float(np.median(hi_values))/p)*p
  if zhi-zlo<p:zhi=zlo+p
  ids=field_part[y0:y1,x0:x1][region];pid=int(np.bincount(ids,minlength=14).argmax())
  part={1:'head',2:'neck',3:'torso',4:'left_arm',5:'right_arm',6:'left_leg',7:'right_leg',8:'hair',9:'skirt',10:'halo',11:'bouquet',12:'ribbon',13:'uncertain_surface'}[pid]
  key='column_'+str(len(columns));column={'id':key,'part':part,'tier':tier,'pitch':p,'pixel_box':b,'foreground_coverage':coverage,'palette_id':color,'depth_assumed_m':[zlo,zhi]};columns.append(column)
  for suffix,mat,lo,hi in [('rear',rear[sid],zlo,zhi),('visible',color,max(zlo,zhi-p),zhi)]:
   oid=key+'_'+suffix;ops.append({'id':oid,'part':part,'action':'paint','material':'p'+str(mat),'shape':{'kind':'box','min':[x,y,lo],'max':[x+p,y+p,hi],'minimum_cells':[1,1,1]}});tier_ids[tier].append(oid)
 for ix in range(math.floor((bbox[0]-w/2)*mpp/bulk),math.ceil((bbox[2]-w/2)*mpp/bulk)):
  for iy in range(math.floor((h-bbox[3])*mpp/bulk),math.ceil((h-bbox[1])*mpp/bulk)):author(ix,iy,bulk,'bulk')
 parts=sorted({o['part'] for o in ops});frame={'meters_per_pixel':mpp,'image_pixels':[w,h],'origin_pixel':[w/2,h],'front_axis':'+Z','camera_center_m':[0,h*mpp/2,0],'camera_orthographic_height_m':h*mpp,'alignment_fit':'none; declared source-coordinate map'}
 anchors=[{**lm,'world_m':[(lm['pixel'][0]-w/2)*mpp,(h-lm['pixel'][1])*mpp,0],'z_status':'not measured'} for lm in m['landmarks']]
 master={'schema':'riverstone.voxel.master.v1','id':'image_measured_'+aid,'revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':materials,'components':[{'id':'character','parts':[{'id':v,'pivot':[0,0,0]} for v in parts],'operations':ops}],'instances':[{'id':'character','component':'character'}],'constraints':[],'extensions':{'prototype_class':'single-view constrained continuous volume prototype; hidden depth assumed','source_sha256':sha(source),'measurement_sha256':sha(d/'measurements.json'),'pixel_data_sha256':sha(d/'pixels.npz'),'annotation_sha256':sha(ROOT/'data/annotations.json'),'rules_sha256':sha(ROOT/'data/continuous_rules.json'),'generator_sha256':sha(Path(__file__)),'continuous_field_source_sha256':sha(ROOT/'tools/continuous_fields.py'),'compiler_snapshot':str(COMMON.relative_to(ROOT)),'frame':frame,'landmark_anchors':anchors,'tier_operation_ids':tier_ids,'depth_status':'authored priors, not measured; single-view projection does not determine full 3D','not_a_texture':True}}
 dump(out/'master.json',master);dump(out/'projection_columns.json',columns)
 compileds=[];renders=[];provenance=[];total=0
 for tier,pitch in [('bulk',bulk),('detail',detail),('micro',micro)]:
  layer=copy.deepcopy(master);ids=set(tier_ids[tier]);layer['components'][0]['operations']=[o for o in ops if o['id'] in ids]
  if not layer['components'][0]['operations']:continue
  compiled=compile_master(layer,{'pitch':pitch},max_candidate_cells=rules['sampling']['max_candidate_cells'],max_output_cells=rules['sampling']['max_total_cells']);assert compiled['valid'];total+=len(compiled['cells']);assert total<=rules['sampling']['max_total_cells'];render=make_render_data(compiled);compileds.append(compiled);renders.append(render)
  f=out/(tier+'.cells.json.gz')
  with gzip.GzipFile(filename=str(f),mode='wb',mtime=0) as gz:gz.write(json.dumps(compiled,separators=(',',':'),sort_keys=True).encode())
  provenance.append({'tier':tier,'pitch':pitch,'derived_master_hash':compiled['master_hash'],'payload_hash':compiled['payload_hash'],'file':f.name,'sha256':sha(f),'cells':len(compiled['cells']),'common':render['provenance']})
 render={'schema':'riverstone.voxel.render.v1','unit':'m','source_id':master['id'],'source_revision':1,'master_hash':digest(master),'payload_hash':digest([x['payload_hash'] for x in compileds]),'pitch':bulk,'grid_origin':[0,0,0],'materials':materials,'bounds':{'min':[min(x['bounds']['min'][i] for x in renders) for i in range(3)],'max':[max(x['bounds']['max'][i] for x in renders) for i in range(3)]},'cell_count':total,'quad_count':sum(x['quad_count'] for x in renders),'groups':sum([x['groups'] for x in renders],[]),'provenance':{'master_hash':digest(master),'layers':provenance},'frame':frame,'limitations':rules['limitations']}
 assert render['quad_count']<=rules['sampling']['max_quads'];dump(out/'character.render.json',render)
 # Orthographic rasterization of actual compiled front cells, not of source input columns.
 zbuf=np.full((h,w),-np.inf);pred=np.full((h,w),-1,np.int16)
 for comp in compileds:
  pitch=comp['pitch'];front={}
  for row in comp['cells']:
   xy=tuple(row[:2]);old=front.get(xy)
   if old is None or row[2]>old[2]:front[xy]=row
  for row in front.values():
   x0,y0,x1,y1=pixel_box(row[0]*pitch,row[1]*pitch,pitch);z=(row[2]+1)*pitch;update=z>zbuf[y0:y1,x0:x1];zbuf[y0:y1,x0:x1][update]=z;pred[y0:y1,x0:x1][update]=int(row[5][1:])
 pm=pred>=0;union=(mask|pm).sum();inter=(mask&pm).sum();ed=mask&~ndi.binary_erosion(mask);pe=pm&~ndi.binary_erosion(pm);chamfer=(float(ndi.distance_transform_edt(~ed)[pe].mean())+float(ndi.distance_transform_edt(~pe)[ed].mean()))/2
 rgb=np.asarray(Image.open(source).convert('RGB'));project=np.full_like(rgb,255);project[pm]=palette[pred[pm]];Image.fromarray(project).save(out/'projected_compiled_albedo.png')
 overlay=(rgb.astype(float)*.52+project.astype(float)*.48).astype(np.uint8);overlay[ed]=[255,0,180];overlay[pe]=[0,180,255];Image.fromarray(overlay).save(out/'projection_overlay.png')
 errors=[]
 for lm in m['landmarks']:
  if not lm['method'].startswith('source'):continue
  i=int(lm['id'].rsplit('_',1)[1]);roi=eye_rois[i];valid=(pred==base_colors+i);yy,xx=np.where(valid)
  if len(xx):pos=[float(xx.mean()),float(yy.mean())];error=float(np.linalg.norm(np.array(pos)-lm['pixel']))
  else:pos=None;error=None
  errors.append({'id':lm['id'],'target_pixel':lm['pixel'],'compiled_projection_pixel':pos,'error_pixels':error,'status':'measured color centroid' if pos else 'not retained'})
 coverage=[]
 for i in range(len(palette)):
  target=mask&~excluded&(colors==i);match=pm&(pred==i)&~excluded;den=int(target.sum());coverage.append({'palette_id':i,'target_pixels':den,'intersection_pixels':int((target&match).sum()),'recall':float((target&match).sum()/den) if den else None,'iou':float((target&match).sum()/((target|match).sum())) if (target|match).any() else None})
 metrics={'silhouette_iou':float(inter/union),'boundary_chamfer_pixels':chamfer,'visible_eye_landmark_errors':errors,'color_region_coverage':coverage,'weighted_color_region_recall':float(sum(v['intersection_pixels'] for v in coverage)/sum(v['target_pixels'] for v in coverage)),'mask_target':'Algorithmically extracted, ROI-assisted source mask. Not independent ground-truth annotation.','landmark_boundary':'Only source-color eye centers have an independent color-centroid error. Manual joints are input anchors and are not counted as automatically recovered landmarks.','projection_source':'actual common-compiled occupied cells; source dimensions and camera held fixed','depth_quality':'not established by these front-projection scores'}
 dump(out/'projection_metrics.json',metrics);dump(out/'manifest.json',{'id':aid,'master_hash':digest(master),'source_sha256':sha(source),'render_sha256':sha(out/'character.render.json'),'cells':total,'quads':render['quad_count'],'columns':len(columns),'frame':frame,'metrics':metrics,'status':'single-view depth-prior volumetric prototype, not complete 3D reconstruction','files':{p.name:sha(p) for p in out.iterdir() if p.is_file()}})
 print(json.dumps({'id':aid,'cells':total,'quads':render['quad_count'],'columns':len(columns),'silhouette_iou':metrics['silhouette_iou'],'boundary_chamfer_pixels':chamfer,'eye_errors':errors,'color_recall':metrics['weighted_color_region_recall']},ensure_ascii=False),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('asset',choices=['violet']);build(p.parse_args().asset)
