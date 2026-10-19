"""Stitch finite fixed profiles into the screened shared public height field."""
import json,math,time
from .height_field import HeightField,fixed_sources,HERE
from .grid_candidate import grade
from ..r17_district_batches import author as a
from ..r17_district_batches import side_clearance
from world_city.concept_city_v3.assemblies.waterworks.registered_water_completion_r01.approaches_r02 import finite

def split(poly,u,v):
 # Infinite line partition is used only within this finite grid cell.
 length=math.dist(u,v)
 if length<1e-10:return[poly]
 lifted=[[p[0],0,p[1]]for p in poly]
 fn=lambda p:a.geo._cross(u,v,[p[0],p[2]])/length
 out=[]
 for sign in(-1,1):
  q=a.common.clean([[p[0],p[2]]for p in side_clearance.halfspace(lifted,lambda x:sign*fn(x))])
  if q:out.append(q)
 return out

def triangulate_best(poly,field):
 vertices=[[p[0],field.value(*p),p[1]]for p in poly];choices=[]
 for j in sorted({int(k*len(vertices)/min(8,len(vertices)))for k in range(min(8,len(vertices)))}):
  v=vertices[j:]+vertices[:j];tris=[t for i in range(1,len(v)-1)for t in a.fan_upward([v[0],v[i],v[i+1]])if a.normal_y(t)>1e-12]
  if tris:choices.append(tris)
 center=[sum(p[k]for p in poly)/len(poly)for k in(0,1)];cv=[center[0],field.value(*center),center[1]]
 center_choice=[t for p,q in zip(vertices,vertices[1:]+vertices[:1])for t in a.fan_upward([cv,p,q])if a.normal_y(t)>1e-12]
 if center_choice:choices.append(center_choice)
 return min(choices,key=lambda ts:max(grade(t)for t in ts))

def main():
 start=time.monotonic();grid=json.loads((HERE/'grid_screen.json').read_bytes());assert not grid['held_cells']
 regions,segments,refs=fixed_sources();assert grid['source_refs']==refs,'Changed field constraints';field=HeightField(regions,segments);ri=a.geo._SpatialIndex(4);si=a.geo._SpatialIndex(4)
 for i,r in enumerate(regions):ri.add(i,r['polygon_xz_m'])
 for i,r in enumerate(segments):si.add(i,[[p[0],p[2]]for p in r['xyz_m']])
 pieces=[]
 for c in grid['cells']:
  x,z=c['origin_xz_m'];s=c['size_m'];cell=[[x,z],[x+s,z],[x+s,z+s],[x,z+s]];remaining=[cell];fixed=[]
  for j in sorted(ri.candidates(cell)):
   mask=regions[j]['polygon_xz_m'];nextparts=[]
   for p in remaining:
    q=finite.intersect(p,mask)
    if not q:nextparts.append(p);continue
    nextparts.extend(finite.subtract([p],[mask]));fixed.append(q)
   remaining=nextparts
  # Compatible fixed overlaps represent the same height. Do not repeatedly
  # split already-assigned coplanar regions by redundant source triangulation.
  # Fixed regions already encode every compatible internal segment exactly.
  # Split only the remaining field by finite segments that touch this cell.
  for j in sorted(si.candidates(cell)):
   u,v=[[p[0],p[2]]for p in segments[j]['xyz_m']]
   if finite.interval(u,v,cell) is None:continue
   remaining=[q for p in remaining for q in split(p,u,v)]
  parts=fixed+remaining
  area=sum(a.geo.polygon_area(p)for p in parts)
  if abs(area-s*s)>1e-6:
   (HERE/'expanded_cell_partition_failure.json').write_text(json.dumps(dict(cell=cell,parts=parts,expected=s*s,actual=area),indent=2)+'\n')
   raise ValueError('Cell partition failed')
  pieces.extend(parts)
 print('partitioned',len(grid['cells']),'cells into',len(pieces),'pieces',round(time.monotonic()-start,2),flush=True)
 # Every collinear boundary point is inserted on both sides. This also catches
 # finite-partition T-junctions and prevents interpolation cracks.
 pointmap={tuple(round(v,12)for v in p)for poly in pieces for p in poly};points=[list(p)for p in sorted(pointmap)];pi=a.geo._SpatialIndex(2)
 for i,p in enumerate(points):pi.add(i,[p])
 triangles=[];held=[];area=0.
 for piece_index,poly in enumerate(pieces):
  ring=[]
  for u,v in zip(poly,poly[1:]+poly[:1]):
   L=math.dist(u,v)
   if L<1e-10:continue
   candidates=[]
   candidates=[(0.,u)]
   bounds=a.bounds([u,v]);query=[[bounds[0]-1e-7,bounds[1]-1e-7],[bounds[2]+1e-7,bounds[3]+1e-7]]
   for j in pi.candidates(query):
    p=points[j];t=sum((p[k]-u[k])*(v[k]-u[k])for k in(0,1))/(L*L)
    if -1e-11<=t<1-1e-11 and abs(a.geo._cross(u,v,p))/L<1e-10:candidates.append((max(0,t),p))
   ring.extend(p for _,p in sorted(candidates,key=lambda q:q[0]))
  # Deduplicate only consecutive points; all straight-edge knots are retained.
  clean=[]
  for p in ring:
   if not clean or math.dist(p,clean[-1])>1e-10:clean.append(p)
  if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-10:clean.pop()
  if len(clean)<3:raise ValueError('Lost finite polygon')
  ts=triangulate_best(clean,field);g=max(grade(t)for t in ts);expected=a.geo.polygon_area(poly);actual=sum(a.normal_y(t)/2 for t in ts)
  if abs(expected-actual)>1e-6:
   (HERE/'tessellation_partition_failure.json').write_text(json.dumps(dict(poly=poly,ring=clean,triangles=ts,expected=expected,actual=actual),indent=2)+'\n')
   raise ValueError('Tessellation area mismatch')
  if g>.12+1e-7:held.append(dict(polygon_xz_m=clean,max_grade=g,triangles_xyz_m=ts))
  triangles.extend(ts);area+=actual
  if piece_index%2000==0:print('tessellated',piece_index,'of',len(pieces),'held',len(held),'seconds',round(time.monotonic()-start,2),flush=True)
 report=dict(schema='riverstone.r18.stitched_public_field.v1',source_refs=refs,source_code_sha256=a.sha(__file__),height_code_sha256=a.sha(HERE/'height_field.py'),status='FIELD_TESSELLATION_READY'if not held else'HELD_TRIANGLE_GRADES',grid_cells=len(grid['cells']),pieces=len(pieces),vertices=len(points),triangles=len(triangles),max_grade=max(grade(t)for t in triangles),total_area_m2=area,held=held,elapsed_s=time.monotonic()-start,activation=False,limits=['Field still needs finite public ownership clipping, native/water exclusions and old boundary closure.'])
 (HERE/'field_tessellation.json').write_text(json.dumps(dict(report=report,triangles_xyz_m=triangles),separators=(',',':'))+'\n');(HERE/'tessellation_review.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print({k:v for k,v in report.items()if k not in('source_refs','held')});print('held',len(held))
if __name__=='__main__':main()
