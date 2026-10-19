"""Native closed-mesh slice immediately below each finished port floor.
No generated geometry is edited. The output is an ownership/validation overlay.
"""
import json,math,hashlib,collections
from pathlib import Path
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
ROOT=Path(__file__).resolve().parents[4];CITY=ROOT/'world_city/concept_city_v3';HERE=Path(__file__).resolve().parent
P=CITY/'assemblies/landmarks/registered/port_r01/resolved_placements.json';d=json.loads(P.read_bytes());placements={x['id']:x for x in d['placements']};assets={x['id']:x for x in d['assets']};cache={};rows=[]
def area(p):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1])))/2
def world(q,p):
 c,s=math.cos(p['yaw_rad']),math.sin(p['yaw_rad']);o=p['position_m'];return[o[0]+c*q[0]+s*q[1],o[2]-s*q[0]+c*q[1]]
def slices(rd,y):
 pitch=rd['pitch'];origin=rd['grid_origin'];cells=collections.Counter()
 for g in rd['groups']:
  for q in g['quads']:
   if max(v[1] for v in q)-min(v[1] for v in q)>1e-8 or q[0][1]<=y:continue
   a=[q[1][i]-q[0][i] for i in range(3)];b=[q[2][i]-q[0][i] for i in range(3)];normal=a[2]*b[0]-a[0]*b[2]
   if abs(normal)<1e-9:continue
   sign=1 if normal>0 else -1
   ix0=round((min(v[0] for v in q)-origin[0])/pitch);ix1=round((max(v[0] for v in q)-origin[0])/pitch)
   iz0=round((min(v[2] for v in q)-origin[2])/pitch);iz1=round((max(v[2] for v in q)-origin[2])/pitch)
   for ix in range(ix0,ix1):
    for iz in range(iz0,iz1):cells[ix,iz]+=sign
 assert set(cells.values())<={0,1},set(cells.values())
 remaining={p for p,v in cells.items() if v==1};rects=[]
 while remaining:
  x,z=min(remaining);x1=x+1
  while (x1,z) in remaining:x1+=1
  z1=z+1
  while all((xx,z1) in remaining for xx in range(x,x1)):z1+=1
  for xx in range(x,x1):
   for zz in range(z,z1):remaining.remove((xx,zz))
  rects.append([[origin[0]+xx*pitch,origin[2]+zz*pitch] for xx,zz in[(x,z),(x1,z),(x1,z1),(x,z1)]])
 return rects
for f in d['owned_floors']:
 pp=placements[f['placement_id']];a=assets[pp['asset_key']];rd=cache.setdefault(pp['asset_key'],json.loads((ROOT/a['cache']['path']).read_bytes()));faces=[clean([world(v,pp) for v in q]) for q in slices(rd,f['floor_y_m']-pp['position_m'][1]-1e-6)]
 pieces=[f['polygon_xz_m']]
 for face in faces:pieces=[q for piece in pieces for cut in geo.convex_difference(piece,face) if(q:=clean(cut))]
 rows.append(dict(id=f['id'],placement_id=pp['id'],datum=f['datum'],floor_y_m=f['floor_y_m'],mask_area_m2=area(f['polygon_xz_m']),actual_solid_section_polygons_xz_m=faces,unbacked_mask_area_m2=sum(area(q) for q in pieces),unbacked_polygons_xz_m=pieces,cache_sha256=a['cache']['sha256']))
report=dict(schema='riverstone.port.native_finished_floor_section.v1',source_pack_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),method='Winding-number native grid slice1micrometre below finished floor, then greedy exact rectangle union. Includes wall bases, excludes roof overhang with air below; no mesh or source mutation.',rows=rows,total_unbacked_mask_area_m2=sum(r['unbacked_mask_area_m2'] for r in rows),masks_with_unbacked_area=sum(r['unbacked_mask_area_m2']>1e-7 for r in rows),limits=['Per-placement audit; neighboring independent floors can cover some differences.','Floor ownership only; upper clearance, doors and collision remain separately audited.'])
(HERE/'native_floor_section_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2));print([(r['placement_id'],round(r['unbacked_mask_area_m2'],3)) for r in rows if r['unbacked_mask_area_m2']>1e-7])
