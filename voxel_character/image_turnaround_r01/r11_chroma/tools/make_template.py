"""Deterministic six-view blank grid, detail panels and independent guide masks."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib
B=Path(__file__).resolve().parents[1];R=B.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
W=H=2048;BG=(0,255,0);im=Image.new('RGB',(W,H),BG);masks={k:Image.new('1',(W,H))for k in ['grid','marker','label']};d=ImageDraw.Draw(im);ds={k:ImageDraw.Draw(v)for k,v in masks.items()};font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
def text(p,s):d.text(p,s,font=font,fill='black');ds['label'].text(p,s,font=font,fill=1)
def line(xy,c=(0,188,0),w=1):d.line(xy,fill=c,width=w);ds['grid'].line(xy,fill=1,width=w)
panels=[]
rows=[['front','left','back'],['right','top','bottom'],['face_front','face_left','gloved_hands_bouquet']]
for row,names in enumerate(rows):
 for col,name in enumerate(names):
  xoff=col*682;yoff=row*682;x0=xoff+26;x1=xoff+656;y0=yoff+40;y1=min(yoff+668,2036);cx=xoff+341;cy=yoff+354;box=[x0,y0,x1,y1]
  title={'front':'FRONT | 0 deg | 1x','left':'LEFT PROFILE | 90 deg | 1x','back':'BACK | 180 deg | 1x','right':'RIGHT PROFILE | -90 deg | 1x','top':'TOP | +Y | AI INFERRED DESIGN','bottom':'BOTTOM | -Y | AI INFERRED DESIGN','face_front':'SAME FACE FRONT | 2x','face_left':'SAME FACE LEFT PROFILE | 2x','gloved_hands_bouquet':'SAME GLOVED HANDS + BOUQUET | 3x'}[name];text((x0,yoff+8),title);d.rectangle(box,outline='black',width=2);ds['marker'].rectangle(box,outline=1,width=2)
  for x in range(cx-324,cx+325,36):
   if x0<x<x1:line([(x,y0+1),(x,y1-1)])
  for y in range(yoff+60,y1,36):line([(x0+1,y),(x1-1,y)])
  points=[[x0-12,y0],[x1+12,y0],[x0-12,y1],[x1+12,y1]]
  for i,(x,y)in enumerate(points):
   d.rectangle([x-5,y-5,x+5,y+5],fill='black');ds['marker'].rectangle([x-5,y-5,x+5,y+5],fill=1);d.rectangle([x-2,y-2,x+2,y+2],fill='white')
  entry={'id':name,'box':box,'markers_centers':points,'axis_x':cx,'grid_px':36}
  if name in ['front','left','back','right']:
   for y in [yoff+96,yoff+276,yoff+456,yoff+636]:line([(x0+1,y),(x1-1,y)],(0,135,0),2)
   line([(cx,y0+1),(cx,y1-1)],(0,135,0),2);entry.update({'role':'whole_figure_elevation','crown_y':yoff+96,'chin_y':yoff+276,'sole_y':yoff+636,'target_height_px':540,'target_head_px':180,'target_head_ratio':3,'yaw_deg':{'front':0,'left':90,'back':180,'right':-90}[name],'metres_per_pixel':1.2/540})
  elif name in ['top','bottom']:
   line([(cx,y0+1),(cx,y1-1)],(0,135,0),2);line([(x0+1,cy),(x1-1,cy)],(0,135,0),2);entry.update({'role':'whole_figure_plan','center_xy':[cx,cy],'metres_per_pixel':1.2/540,'camera':'+Y down'if name=='top'else'-Y up','right_direction':'+X','up_direction':'-Z'if name=='top'else'+Z','source_status':'UNOBSERVED_AI_INFERRED_DESIGN_NOT_GROUND_TRUTH','coverage':'Opaque garment undersides and shoe soles only; hidden anatomy remains unknown'})
  else:
   entry.update({'role':'detail','source_view':'left'if name=='face_left'else'front','magnification_relative_to_full':2 if name!='gloved_hands_bouquet' else 3,'meaning':'Same actual face/visible glove pose, no redesign; hidden fingers unknown'})
   if name!='gloved_hands_bouquet':
    for y in [1460,1820]:line([(x0+1,y),(x1-1,y)],(0,135,0),2)
    entry.update({'crown_y':1460,'chin_y':1820,'target_head_px':360})
  panels.append(entry)
p=B/'reference/registration_template_sixview.png';im.save(p)
for k,v in masks.items():v.save(B/f'reference/template_sixview_{k}_mask.png')
c={'schema':'riverstone.chroma_template.sixview.v1','canvas':[W,H],'background_srgb':list(BG),'selected_by':'evidence/chroma_collision_audit.json','grid_line_srgb':[0,188,0],'panels':panels,'head_definition':'Visible hair crown to chin; exclude halo. Hidden skull crown null.','reference_height_m':1.2,'physical_height_status':'normalization assumption only','mask_policy':'Separate grid, marker, label masks. Never erase full guide rows through character pixels; only actual registered visible guide-color pixels, ambiguities unknown.','generation_limit':'Coordinates, scale and orthographic angles are requested targets, independently verified after generation. No exact-coordinate or3D reconstruction guarantee.','six_view_gate':'Actual3D source and voxel must be rendered in all six orthogonal directions; side/back AI design, top/bottom unobserved inferred design. Missing independent references may only pass design-section consistency, never observed reconstruction.','approved_source_path':'voxel_character/three_head_reference_r01/violet_costume_skin_candidate_r06.png','source_sha256':sha(R/'voxel_character/three_head_reference_r01/violet_costume_skin_candidate_r06.png'),'template_sha256':sha(p),'generator_sha256':sha(Path(__file__))}
(B/'data/template_contract.json').write_text(json.dumps(c,indent=2)+'\n');print(json.dumps({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}))
