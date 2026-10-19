"""Source-bound institutional landscape inputs; no inferred ownership inheritance."""
import json,math
from pathlib import Path
from world_city.concept_city_v3.assemblies.property.registered import author as a
HERE=Path(__file__).resolve().parent;CITY=a.CITY;ROOT=a.ROOT
PATHS=dict(plan=CITY/'registered_source/plan.json',landmarks=CITY/'assemblies/landmarks/registered/assembly_r01/resolved_placements.json',landmark_manifest=CITY/'assemblies/landmarks/registered/assembly_r01/sources_manifest.json',ordinary=CITY/'assemblies/ordinary/registered/resolved_placements.json',approaches=CITY/'validation/landmark_access_candidate/candidate_42369c6f30d9_c0982ceea5f7.json')
def load():
 data={k:json.loads(p.read_text()) for k,p in PATHS.items()};data['sources']={k:dict(path=str(p.relative_to(ROOT)),sha256=a.file_sha(p)) for k,p in PATHS.items()};terrain_path=CITY/'registered_topography/author.py';data['sources']['terrain_author']=dict(path=str(terrain_path.relative_to(ROOT)),sha256=a.file_sha(terrain_path));ex=[]
 def add(key,poly,kind):ex.append(dict(id=key,polygon_xz_m=poly,kind=kind))
 for r in data['plan']['roads']:
  for j,(u,v) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):add(r['id']+':'+str(j),a.geom.road_ribbon(u,v,r['width_m']+1),'public_road_and_half_metre_shoulder')
 for r in data['plan']['paths']:
  points=(r.get('polyline_xz_m') or [])
  for j,(u,v) in enumerate(zip(points,points[1:])):
   if math.dist(u,v)>.001:add(r['id']+':'+str(j),a.geom.road_ribbon(u,v,r.get('width_m',1.8)),'existing_source_path_reservation')
 for p in data['landmarks']['placements']:add(p['id'],p['outer_footprint_xz_m'],'native_landmark_outer_envelope')
 for p in data['landmarks']['owned_floors']:add(p['id'],p['polygon_xz_m'],'native_landmark_floor_owner')
 for p in data['ordinary']['placements']:add(p['id'],p['actual_outer_footprint_xz_m'],'native_ordinary_outer_envelope')
 for p in data['plan']['water_reservations']['finite_water_polygons']:add(p.get('id','water:'+str(len(ex))),p['polygon_xz_m'],'finite_water')
 for r in data['approaches']['routes']:
  for j,p in enumerate((r.get('reserved_ribbon_polygons_xz_m') or [])):add(r['entrance_id']+':approach:'+str(j),p,'native_door_approach_pending_vertical_repair')
  for j,p in enumerate((r.get('polyline_xz_m') or [])):add(r['entrance_id']+':round_join:'+str(j),[[p[0]+(.9/math.cos(math.pi/16))*math.cos(i*math.tau/16),p[1]+(.9/math.cos(math.pi/16))*math.sin(i*math.tau/16)] for i in range(16)],'native_approach_round_join')
 data['exclusions']=ex;return data

def diagram():
 d=load();s=['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1400" viewBox="-430 -390 830 710">','<rect x="-430" y="-390" width="830" height="710" fill="#eeeade"/>']
 def poly(p,fill,stroke='none'):return '<polygon points="'+' '.join(f'{x},{z}' for x,z in p)+f'" fill="{fill}" stroke="{stroke}" stroke-width=".5"/>'
 for sp in d['plan']['spaces']:
  if sp['id'] in ('SITE_CLERGY','SITE_MONASTERY','SITE_COMMON','SITE_CEMETERY','SITE_CLOISTER'):
   s.append(poly(sp['polygon_xz_m'],'#d0d9b2','#64734d'));c=a.centre(sp['polygon_xz_m']);s.append(f'<text x="{c[0]}" y="{c[1]}" font-size="9">{sp["id"]}</text>')
 colors={'public_road_and_half_metre_shoulder':'#b5aa91','native_landmark_outer_envelope':'#ad9787','native_landmark_floor_owner':'#b2a497','native_ordinary_outer_envelope':'#aca39c','finite_water':'#7bafbd','native_door_approach_pending_vertical_repair':'#cd5d4a'}
 for e in d['exclusions']:
  if e['kind'] in colors:s.append(poly(e['polygon_xz_m'],colors[e['kind']]))
 for x in range(-400,401,50):
  s.append(f'<path d="M{x},-380V310" stroke="#555" stroke-width=".15"/><text x="{x}" y="-380" font-size="6">{x}</text>')
 for z in range(-350,301,50):s.append(f'<path d="M-420,{z}H395" stroke="#555" stroke-width=".15"/><text x="-420" y="{z}" font-size="6">{z}</text>')
 s.append('</svg>');(HERE/'context.svg').write_text('\n'.join(s));return d
if __name__=='__main__':diagram()
