"""Boundary-only source membership and actual cache slice audit; no compiler or geometry export."""
import collections,json,math,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[7];OUT=pathlib.Path(__file__).parent
r=json.loads((ROOT/'world_city/concept_city_v3/assemblies/landmarks/registered/precinct_r04/contact_repair_r01/resolved_placements.json').read_text())
def pin(x,y,points):
 inside=False
 for i,(a,b)in enumerate(points):
  c,d=points[i-1]
  if (b>y)!=(d>y)and x<(c-a)*(y-b)/(d-b)+a:inside=not inside
 return inside
def components(cells,diagonal=False):
 seen=set();sizes=[];directions=[(x,z)for x in range(-1,2)for z in range(-1,2)if(x or z)and(diagonal or abs(x)+abs(z)==1)]
 for p in cells:
  if p in seen:continue
  seen.add(p);todo=[p];size=0
  while todo:
   x,z=todo.pop();size+=1
   for dx,dz in directions:
    q=(x+dx,z+dz)
    if q in cells and q not in seen:seen.add(q);todo.append(q)
  sizes.append(size)
 return sorted(sizes,reverse=True)
rows=[]
for a in r['assets']:
 if a.get('compound_id')not in ['CLERGY_GUEST_ALMS','CLERGY_CANONS_CLOSE','CLERGY_SCHOOL_SERVICE']:continue
 m=json.loads((ROOT/a['source']['path']).read_text());b=next(c for c in m['components']if c['id']=='court_and_boundary__boundary');expected=set()
 for o in b['operations']:
  poly=o['shape']['polygon'];lo=[math.floor(min(p[i]for p in poly)/.5)for i in [0,1]];hi=[math.ceil(max(p[i]for p in poly)/.5)for i in [0,1]]
  cells={(x,-v-1)for x in range(lo[0],hi[0])for v in range(lo[1],hi[1])if pin((x+.5)*.5,(v+.5)*.5,poly)}
  if o['action']=='paint':expected|=cells
  else:expected-=cells
 cache=json.loads((ROOT/a['cache']['path']).read_text());events=collections.defaultdict(list)
 for g in cache['groups']:
  for q in g['quads']:
   if not all(p[0]==q[0][0]for p in q):continue
   if not min(p[1]for p in q)<=1.25<max(p[1]for p in q):continue
   u=[q[1][i]-q[0][i]for i in range(3)];v=[q[2][i]-q[0][i]for i in range(3)];cross_x=u[1]*v[2]-u[2]*v[1];sign=1 if cross_x>0 else -1
   for z in range(round(min(p[2]for p in q)*2),round(max(p[2]for p in q)*2)):events[z].append((round(q[0][0]*2),sign))
 actual=set()
 for z,ev in events.items():
  start=None
  for x,sgn in sorted(ev):
   if sgn<0:start=x
   else:actual.update((xx,z)for xx in range(start,x))
 selected=expected&actual;face=components(selected);edge=components(selected,True)
 rows.append({'id':a['compound_id'],'slice_local_y_m':1.25,'slice_world_y_m':15.25,'source_expected_boundary_cells':len(expected),'boundary_cells_in_actual_cache':len(selected),'missing_source_boundary_cells':len(expected-actual),'face_connected_component_count':len(face),'face_connected_sizes':face,'edge_or_face_connected_component_count':len(edge),'edge_or_face_connected_sizes':edge,'interpretation':'Many source-solid belt runs connect only diagonally in this slice, hence only at vertical voxel edges in 3D. Counts exclude adjoining building cells and are not whole-asset connectivity counts.'})
report={'method':'Source polygon center-membership at one height, intersected with actual cache occupancy reconstructed from signed X quads at that height. No compiler or render invocation.','dominant_yaw_degrees':32.3,'boundary_width_m':.6,'pitch_m':.5,'conservative_grid_width_for_arbitrary_phase_at_32_3deg_m':.5*(math.cos(math.radians(32.3))+math.sin(math.radians(32.3))),'rows':rows}
(OUT/'boundary_slice_audit.json').write_text(json.dumps(report,indent=2)+'\n')
for a in rows:print({k:v for k,v in a.items()if not k.endswith('_sizes')})
