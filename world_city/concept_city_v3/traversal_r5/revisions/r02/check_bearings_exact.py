"""Whole native-column bearing coverage, retaining original terrain planes."""
import check_native as n
import math,collections,json
from pathlib import Path
g=n.g;A=n.A;H=n.H;ROOT=n.ROOT
p=n.read(A/'profile.json');pack=n.read(A/'resolved_placements.json');co=n.read(ROOT/pack['assets']['recessed_fixed']['compiled']['path']);fi=n.read(ROOT/pack['assets']['visible_cover']['compiled']['path']);cc=n.columns(co);fc=n.columns(fi);pitch=fi['pitch'];b=p['frame']['basis'];t=p['frame']['translation']
world=lambda x,z:[t[i]+b[i][0]*x+b[i][2]*z for i in [0,2]]
tris=n.read(n.CITY/'traversal_r5/geometry/SOUTH_NATIVE_TERMINAL_TO_COUNTRY.json')['triangles'];rows=[];index=collections.defaultdict(list)
for tri in tris:
 poly=[[v[0],v[2]] for v in tri]
 if g.polygon_area(poly)<1e-10:continue
 gx,gz=n.plane(tri);a=tri[0];bb=n.bounds(poly);j=len(rows);rows.append((poly,gx,gz,a[1]-gx*a[0]-gz*a[2]))
 for ix in range(math.floor(bb[0]),math.floor(bb[2])+1):
  for iz in range(math.floor(bb[1]),math.floor(bb[3])+1):index[ix,iz].append(j)
def norm(q):
 out=[]
 for v in q:
  if not out or math.dist(v,out[-1])>1e-10:out.append(v)
 if len(out)>1 and math.dist(out[0],out[-1])<1e-10:out.pop()
 return out
def above(poly,gx,gz,c,bottom):
 out=[];prev=poly[-1];pv=gx*prev[0]+gz*prev[1]+c-bottom
 for cur in poly:
  cv=gx*cur[0]+gz*cur[1]+c-bottom
  if (cv>=0)!=(pv>=0):
   f=pv/(pv-cv);out.append([prev[i]+f*(cur[i]-prev[i]) for i in range(2)])
  if cv>=0:out.append(cur)
  prev,pv=cur,cv
 return norm(out)
coarse_count=0;terrain_count=0;uncovered=[];min_embed=1e9;whole_area=0.;residual=0.;clipcount=0
for (ix,iz),(bottom,top) in fc.items():
 whole_area+=pitch*pitch;owner=cc.get((ix//5,iz//5))
 if owner and owner[1]>=bottom-1e-12:
  coarse_count+=1;min_embed=min(min_embed,owner[1]-bottom);continue
 terrain_count+=1;poly=[world((ix+dx)*pitch,(iz+dz)*pitch) for dx,dz in [(0,0),(1,0),(1,1),(0,1)]];bb=n.bounds(poly);ids=set()
 for x in range(math.floor(bb[0]),math.floor(bb[2])+1):
  for z in range(math.floor(bb[1]),math.floor(bb[3])+1):ids.update(index[x,z])
 parts=[poly]
 for j in sorted(ids):
  q,gx,gz,c=rows[j];hit=g.convex_intersection(poly,q)
  if g.polygon_area(hit)<1e-13:continue
  hit=above(hit,gx,gz,c,bottom)
  if len(hit)<3 or g.polygon_area(hit)<1e-13:continue
  clipcount+=1;min_embed=min(min_embed,min(gx*x+gz*z+c-bottom for x,z in hit));new=[]
  for part in parts:
   if g.intersection_area(part,hit)<1e-13:new.append(part)
   else:new.extend(norm(v) for v in g.convex_difference(part,hit))
  parts=[q for q in new if len(q)>2 and g.polygon_area(q)>1e-12]
  if not parts:break
 area=sum(g.polygon_area(q) for q in parts);residual+=area
 if area>1e-9:uncovered.append({'cell_xz':[ix,iz],'bottom':bottom,'area_m2':area,'pieces':parts})
result={'status':'pass_exact_finite_column_bearing_coverage' if not uncovered else 'fail','native_columns':len(fc),'coarse_cell_containment_proofs':coarse_count,'terrain_plane_partition_proofs':terrain_count,'terrain_intersections':clipcount,'native_footprint_area_m2':whole_area,'residual_unsupported_area_m2':residual,'uncovered':uncovered,'minimum_support_plane_above_native_bottom_m':min_embed,'sources':{'profile':n.ref(A/'profile.json'),'pack':n.ref(A/'resolved_placements.json'),'original_scene_collision':n.ref(n.CITY/'traversal_r5/geometry/SOUTH_NATIVE_TERMINAL_TO_COUNTRY.json'),'checker':n.ref(Path(__file__))},'scope':'Exact finite column plan area covered by native coarse cell top or original R5 triangle plane above the bottom. This is a geometric bearing proof, not a physical stress or cart-load simulation.'}
n.write(H/'evidence/exact_bearing_audit.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['sources','uncovered']}));raise SystemExit(bool(uncovered))
