"""Literal image-measurement source and actual paired Godot captures. No scene-image edits."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib,sys
P=Path(__file__).resolve().parent;A=P.parent;R=next(p for p in P.parents if (p/'voxel_character').is_dir())
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';title=ImageFont.truetype(font,25);small=ImageFont.truetype(font,16)
def pin(p):return {'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def place(b,im,box):
 x,y,w,h=box;im=im.copy();im.thumbnail((w,h),Image.Resampling.LANCZOS);b.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2))
before=json.loads((P/'before/capture_report.json').read_text());after=json.loads((P/'after/capture_report.json').read_text());br={r['view']:r for r in before['records']};ar={r['view']:r for r in after['records']}
assert len(br)==len(ar)==9
for v in ar:
 for k in ['eye','target','up','projection','size_m','viewport_size','unshaded','normal_patch','shadows_enabled']:assert br[v][k]==ar[v][k],(v,k)
for mode in ['before','after']:assert (P/mode/'run.exit').read_text().strip()=='0'
b=Image.new('RGB',(1600,1510),'#faf9f6');d=ImageDraw.Draw(b);d.text((20,15),'ONE IMAGE-MEASURED GALLERY PANEL | ACTUAL GODOT',font=title,fill='#222222');d.text((20,52),'43 annotated aperture pixels now clear through the finite recess. Two diamond cutouts are visible.',font=small,fill='#333333')
for y,stem,crop,h in [(100,'rail_front_close',(140,140,1020,700),500),(670,'rail_oblique_close',(220,170,1130,800),510)]:
 for x,mode in [(10,'before'),(810,'after')]:
  d.text((x+10,y-24),stem.upper()+' '+mode.upper(),font=small,fill='#333333');place(b,Image.open(P/mode/(stem+'.png')).convert('RGB').crop(crop),(x,y,780,h))
source=Image.open(A/'railing_measurement_r01/source_crop.png').convert('RGB');source=source.resize((256,192),Image.Resampling.NEAREST);b.paste(source,(35,1230));d.text((320,1245),'Unchanged source crop at 4x. Depth is an explicit prior.',font=small,fill='#333333');d.text((320,1280),'Only this front panel is repaired; side supports, deck and ambiguous holes remain unresolved.',font=small,fill='#8a233c');d.text((320,1315),'Lit wood is too yellow; source lighting is not calibrated albedo. Whole-house art NOT approved.',font=small,fill='#8a233c');d.text((20,1452),'Six orthographic views retained. Five non-front views are pixel-identical; no city promotion or gameplay claim.',font=small,fill='#8a233c');b.save(P/'gallery_panel_before_after.png')
source_path=R/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png';ref=Image.open(source_path).convert('RGB');views=['front','right','back','left','top','bottom'];panels={'front':(0,0,512,512),'right':(512,0,1024,512),'back':(1024,0,1536,512),'left':(0,512,512,1024),'top':(512,512,1024,1024),'bottom':(1024,512,1536,1024)}
b=Image.new('RGB',(1580,2040),'#faf9f6');d=ImageDraw.Draw(b);d.text((20,14),'GALLERY PANEL | SIX ACTUAL ORTHOGRAPHIC VIEWS',font=title,fill='#222222');d.text((20,49),'REFERENCE (globally contradictory)                         BEFORE: frozen roof r04 + normals                         AFTER: one front panel + same normals',font=small,fill='#333333')
for i,v in enumerate(views):
 y=82+i*306;d.text((20,y),v.upper(),font=small,fill='#222222');crop=(260,80,930,760)if v in ['front','back']else(300,80,880,760)if v in ['left','right']else(300,170,880,642)
 place(b,ref.crop(panels[v]),(10,y+22,490,270))
 for x,mode in [(520,'before'),(1050,'after')]:place(b,Image.open(P/mode/(v+'.png')).convert('RGB').crop(crop),(x,y+22,500,270))
d.text((20,1932),'Front panel changes locally. Remaining five orthographic images are pixel-identical below HUD.',font=small,fill='#8a233c');d.text((20,1962),'Missing side returns/deck, roof backing, underside and source contradictions remain. ART GATE FAIL.',font=small,fill='#8a233c');b.save(P/'gallery_panel_six_views.png')
report=json.loads((A/'roof_normal_full_r01/actual_comparison_r01/six_view_review.json').read_text());report['source_render']=pin(A/'gallery_panel_repair_r01/gallery_repaired.render.json.gz');report['reviewer']='city integration reviewer; actual six directions and close/oblique opened 2026-10-19T13:54Z';report['normal_sidecar']=pin(P/'normal_split_rebound.json.gz');report.pop('normal_comparison',None)
for row in report['views']:
 v=row['view'];row['image']=pin(P/'after'/f'{v}.png');row['capture_report']=pin(P/'after/capture_report.json');row['source_render_sha256']=report['source_render']['sha256'];row['comparison']=pin(P/'gallery_panel_six_views.png')
 for observation in row['observations']:
  if v=='front' and observation['topic']=='missing_parts':observation['reason']='One measured front panel now shows vertical plank color divisions and two diamond cutouts. Other railing panels, side supports and deck remain unresolved.'
  elif observation['topic']=='silhouette':observation['reason']='Changed geometry is confined to one front panel owner. Existing roof/body outline retained; gallery side structural omissions remain.'
  elif observation['topic']=='stretching':observation['reason']='Five non-front actual projections are unchanged. One front panel no longer uses coarse color projection; unknown side/bottom depths remain inherited.'
  elif observation['topic']=='color':observation['reason']='Three measured wood colors are preserved; actual lit closeup is overly yellow. Source light/shadow and unknown labels remain unresolved.'
report['next_correction']='Measured side registration and deck/support ownership; roof missing-TOP interval audit. No repeated-panel propagation until structure and material readability pass.'
(P/'six_view_review.json').write_text(json.dumps(report,indent=2));sys.path.insert(0,str(R/'voxel_character/common'));from six_view_review import validate
result=validate(report,R);assert result['evidence_complete']and not result['all_pass'];(P/'six_view_gate_result.json').write_text(json.dumps(result,indent=2));print(result['evidence_complete'],result['all_pass'])
