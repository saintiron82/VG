"""Compare finite port floor masks with actual native cached coplanar faces."""
import json,math,hashlib
from pathlib import Path
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
ROOT=Path(__file__).resolve().parents[4];CITY=ROOT/'world_city/concept_city_v3';HERE=Path(__file__).resolve().parent
p=CITY/'assemblies/landmarks/registered/port_r01/resolved_placements.json';d=json.loads(p.read_bytes());placements={x['id']:x for x in d['placements']};assets={x['id']:x for x in d['assets']};cache={};rows=[]
def area(p):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1])))/2
def world(q,p):
 c,s=math.cos(p['yaw_rad']),math.sin(p['yaw_rad']);o=p['position_m'];return[o[0]+c*q[0]+s*q[2],o[2]-s*q[0]+c*q[2]]
for f in d['owned_floors']:
 pp=placements[f['placement_id']];a=assets[pp['asset_key']];rd=cache.setdefault(pp['asset_key'],json.loads((ROOT/a['cache']['path']).read_bytes()));faces=[]
 for g in rd['groups']:
  for q in g['quads']:
   if max(abs(v[1]+pp['position_m'][1]-f['floor_y_m']) for v in q)<1e-7:
    ring=clean([world(v,pp) for v in q])
    if ring:faces.append(ring)
 pieces=[f['polygon_xz_m']]
 for face in faces:
  pieces=[q for piece in pieces for cut in geo.convex_difference(piece,face) if(q:=clean(cut))]
 rows.append(dict(id=f['id'],placement_id=pp['id'],datum=f['datum'],declared_mask_area_m2=area(f['polygon_xz_m']),actual_floor_faces=faces,unbacked_mask_area_m2=sum(area(q) for q in pieces),unbacked_polygons_xz_m=pieces))
report=dict(source_pack_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='Local floor-mask minus actual coplanar cached geometry per placement. Adjacent independent floors may cover a subset; no capsule or full-city visual claim.',rows=rows,total_unbacked_mask_area_m2=sum(r['unbacked_mask_area_m2'] for r in rows),masks_with_unbacked_area=sum(r['unbacked_mask_area_m2']>1e-7 for r in rows))
(HERE/'native_floor_mask_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2));print([(r['placement_id'],round(r['unbacked_mask_area_m2'],3)) for r in rows if r['unbacked_mask_area_m2']>1e-7])
