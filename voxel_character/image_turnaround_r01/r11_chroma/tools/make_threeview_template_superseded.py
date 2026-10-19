"""Deterministic blank registration sheet, independent masks and pixel contract."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np,json,hashlib
B=Path(__file__).resolve().parents[1];R=B.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
W,H=1536,1024;BG=(0,255,0);im=Image.new('RGB',(W,H),BG);grid=Image.new('1',(W,H));markers=Image.new('1',(W,H));labels=Image.new('1',(W,H));d=ImageDraw.Draw(im);g=ImageDraw.Draw(grid);m=ImageDraw.Draw(markers);l=ImageDraw.Draw(labels)
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';font=ImageFont.truetype(fontpath,14);small=ImageFont.truetype(fontpath,11)
def text(xy,s,f=font):d.text(xy,s,font=f,fill='black');l.text(xy,s,font=f,fill=1)
def line(xy,color=(0,188,0),width=1):d.line(xy,fill=color,width=width);g.line(xy,fill=1,width=width)
panels=[]
for j,name in enumerate(['front','side90_left','back']):
 x0=24+512*j;x1=x0+464;axis=256+512*j;box=[x0,48,x1,592];text((x0,13),['FRONT 0 deg | full 1x','LEFT PROFILE 90 deg | full 1x','BACK 180 deg | full 1x'][j]);d.rectangle(box,outline='black',width=2);m.rectangle(box,outline=1,width=2)
 for x in range(axis-240,axis+241,30):
  if x0<x<x1:line([(x,49),(x,591)])
 for y in range(66,592,30):line([(x0+1,y),(x1-1,y)])
 for y,s in [(96,'crown 96'),(246,'chin 246'),(396,'2H 396'),(546,'sole 546')]:line([(x0+1,y),(x1-1,y)],(0,135,0),2);text((x0+5,y+2),s,small)
 line([(axis,49),(axis,591)],(0,145,0),2)
 # Four independent asymmetric marker blocks outside the character drawing box.
 for k,(cx,cy) in enumerate([(x0-12,48),(x1+12,48),(x0-12,592),(x1+12,592)]):
  d.rectangle([cx-5,cy-5,cx+5,cy+5],fill='black');m.rectangle([cx-5,cy-5,cx+5,cy+5],fill=1);d.rectangle([cx-2,cy-2,cx+2,cy+2],fill='white');m.rectangle([cx-2,cy-2,cx+2,cy+2],fill=1)
  if k%2==0:d.point((cx-3,cy-3),fill='white')
 panels.append({'id':name,'role':'whole_figure','box':box,'axis_x':axis,'target_visible_hair_crown_y':96,'target_chin_y':246,'target_sole_y':546,'target_height_px':450,'target_head_height_px':150,'target_ratio':3,'nominal_yaw_deg':[0,90,180][j],'markers_centers':[[x0-12,48],[x1+12,48],[x0-12,592],[x1+12,592]],'world_normalization_m':1.2,'metres_per_pixel':1.2/450})
for j,(name,title,scale)in enumerate([('face_front','FACE FRONT | same head 2x',2),('face_side','FACE LEFT PROFILE | same head 2x',2),('gloved_hands_bouquet','SAME GLOVED HANDS + BOUQUET | 3x',3)]):
 x0=24+512*j;x1=x0+464;box=[x0,648,x1,1008];text((x0,618),title);d.rectangle(box,outline='black',width=2);m.rectangle(box,outline=1,width=2)
 for x in range(x0+30,x1,30):line([(x,649),(x,1007)])
 for y in range(678,1008,30):line([(x0+1,y),(x1-1,y)])
 if j<2:
  for y in [674,974]:line([(x0+1,y),(x1-1,y)],(0,135,0),2)
  text((x0+5,677),'crown 674',small);text((x0+5,977),'chin 974',small)
 panels.append({'id':name,'role':'detail','box':box,'source_view':'front' if j!=1 else 'side90_left','magnification_relative_to_full':scale,'target_crown_y':674 if j<2 else None,'target_chin_y':974 if j<2 else None,'target_head_height_px':300 if j<2 else None,'meaning':'Same actual face magnified; not another redesign' if j<2 else 'Same visible gloved hands holding bouquet; hidden fingers remain unknown, no bare hands or new pose'})
p=B/'reference/registration_template.png';im.save(p);grid.save(B/'reference/template_grid_mask.png');markers.save(B/'reference/template_marker_mask.png');labels.save(B/'reference/template_label_mask.png')
contract={'schema':'riverstone.chroma_template.v1','canvas':[W,H],'background_srgb':list(BG),'selected_by':'evidence/chroma_collision_audit.json','grid_spacing_px':30,'grid_line_srgb':[0,188,0],'panels':panels,'mask_policy':'Grid, labels and registration markers are separate source masks. Do not erase entire grid-coordinate rows through character pixels. Classify only actual visible guide colors at registered coordinates; ambiguous overlap is unknown.','generation_limit':'Requested coordinates and nominal orthographic views are targets, not imagegen guarantees. Actual output must be independently registered and measured.','head_definition':'Visible hair crown to chin, halo excluded. Hidden skull crown not observable.','source_sha256':sha(R/'three_head_reference_r01/violet_costume_skin_candidate_r06.png'),'template_sha256':sha(p),'generator_sha256':sha(Path(__file__))}
(B/'data/template_contract.json').write_text(json.dumps(contract,indent=2)+'\n');print(json.dumps({'template_sha256':sha(p),'bytes':p.stat().st_size}))
