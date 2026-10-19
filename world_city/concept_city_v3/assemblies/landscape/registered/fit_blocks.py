"""Finite authored garden blocks; no opportunistic vacant-land fill."""
import math,json
from . import context as c
from world_city.concept_city_v3.assemblies.property.registered import author as a
FRAMES=[
 dict(id='CLERGY_CLOISTER_GARDEN',space='SITE_CLERGY',kind='cloister_garden',position=a.xform([73,43],[203.6285,-211.3007],math.radians(32.3)),width=40,depth=40,yaw=32.3,search=4,floor=14,inherit_enclosure=True),
 dict(id='CLERGY_CEMETERY',space='SITE_CEMETERY',kind='cemetery',position=[140,-251],width=20,depth=58,yaw=20,search=14,floor=14),
 dict(id='CLERGY_KITCHEN_GARDEN',space='SITE_CLERGY',kind='kitchen_garden',position=[310,-133],width=48,depth=42,yaw=32.3,search=4,floor=14),
 dict(id='MONASTERY_KITCHEN_GARDEN',space='SITE_MONASTERY',kind='productive_garden',position=[-240,210],width=84,depth=66,yaw=0,search=4,floor=8),
 dict(id='MONASTERY_ORCHARD',space='SITE_MONASTERY',kind='orchard',position=[-353,130],width=62,depth=110,yaw=10,search=4,floor=8),
 dict(id='MONASTERY_HERB_GARDEN',space='SITE_MONASTERY',kind='herb_garden',position=[-350,8],width=60,depth=40,yaw=0,search=4,floor=8),
 dict(id='PUBLIC_TERRACE_PARK',space='SITE_COMMON',kind='public_park',position=[-343,-69],width=90,depth=30,yaw=-15,search=4,floor=9),
]
def run():
 d=c.load();spaces={s['id']:s for s in d['plan']['spaces']};idx=a.geom._SpatialIndex(20);items={}
 for j,e in enumerate(d['exclusions']):idx.add(str(j),e['polygon_xz_m']);items[str(j)]=e
 out=[]
 for source in FRAMES:
  s=dict(source);found=None;tries=sorted((dx*dx+dz*dz,dx,dz) for dx in range(-s['search'],s['search']+1,2) for dz in range(-s['search'],s['search']+1,2))
  for _,dx,dz in tries:
   center=a.add(s['position'],[dx,dz]);poly=a.rect(center,s['width'],s['depth'],math.radians(s['yaw']))
   if not a.contained(poly,spaces[s['space']]['polygon_xz_m']):continue
   if any(a.overlap(poly,items[k]['polygon_xz_m']) for k in idx.candidates(poly)):continue
   if any(a.overlap(poly,p['polygon_xz_m']) for p in out):continue
   found=(center,poly);break
  if found:s.update(position=found[0],polygon_xz_m=found[1],area_m2=s['width']*s['depth'],fit_adjustment_m=math.dist(source['position'],found[0]),status='bounded_frame_clear')
  else:s.update(status='no_clear_fixed_size_frame')
  out.append(s);print(s['id'],s['status'],s.get('position'),s.get('fit_adjustment_m'),flush=True)
 (c.HERE/'block_proposals.json').write_text(json.dumps(dict(schema='riverstone.registered_institutional_garden_blocks.v1',sources=d['sources'],blocks=out,source_only=True),indent=2)+'\n');return out
if __name__=='__main__':run()
