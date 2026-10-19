"""Labelled drill-ground source plan, not a scene render."""
import json
from . import author as t
from world_city.concept_city_v3.assemblies.property.registered import author as a
from ..diagram import poly,label

def run():
 p=json.loads((t.OUT/'source_pack.json').read_text());w=json.loads((t.OUT/'ground_wrapper.json').read_text());d=t.source_inputs();svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1120" viewBox="-423 -254 205 143.5">','<rect x="-423" y="-254" width="205" height="143.5" fill="#f2eee3"/>']
 svg.append(poly(p['source_space']['polygon_xz_m'],'#d5dec0','#596c46',.6))
 for e in d['exclusions']:
  if e['kind']=='public_road_and_half_metre_shoulder':svg.append(poly(e['polygon_xz_m'],'#b7ae9b'))
  elif e['kind']=='native_fortification_outer_envelope':svg.append(poly(e['polygon_xz_m'],'#7a7970'))
 for r in w['owned_floor_regions']:svg.append(poly(r['polygon_xz_m'],'#cfba8a' if r['material']=='earth' else '#e5dbbf'))
 svg.append(poly(t.CORE,'#c8ac76','#998256',.25))
 for r in p['internal_routes']:
  for q in r['ribbon_polygons_xz_m']:svg.append(poly(q,'#decca5' if r.get('kind')=='open_field_access' else '#efe4c7'))
 for q in p['external_surface']['polygon_regions_xz_m']:svg.append(poly(q,'#d9c17a','#8d7132',.25))
 colors={'barrack':'#856b4f','stable':'#9c805d','lodge':'#a47359','practice_target':'#eee2bb','practice_rack':'#806849','water_trough':'#719ba3'}
 for v in p['placements']:
  svg.append(poly(v['footprint_xz_m'],colors[v['role']],'#3c453a',.25))
  for door in v.get('entrances',[]):
   x,y,z=door['door_xyz_m'];svg.append(f'<circle cx="{x}" cy="{z}" r=".55" fill="#d5d2ba" stroke="#463a2e" stroke-width=".18"/>')
 for txt,x,z in [('Two low barrack ranges',-416,-182),('Stable + stores',-374,-131),('4 practice butts',-389,-230),('Clear drill core: 6,048 m²',-355,-181),('12 m / 3 m approach',-291,-146),('Y=18 entry',-284,-139)]:svg.append(label(x,z,txt,2.7))
 svg.append(label(-419,-247,'REGISTERED TRAINING GROUND | native-size cached buildings | SOURCE PLAN',3.5));svg.append(label(-419,-241,'4 buildings, 8 actual doors, 7 practice/service props; original road and traced boundary retained.',2.7));svg.append(label(-419,-118,'Ramp 8.854% max; public landing 10.004%; sampled cut/fill 0.2005 m. Terrain interface review pending.',2.65));svg.append('</svg>');(t.OUT/'training_source_plan.svg').write_text('\n'.join(svg))
if __name__=='__main__':run()
