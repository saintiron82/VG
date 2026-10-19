"""Preserve finite retained-road incident steps with explicit private risers.

Only conflicting public boundary vertices are duplicated. All other private
vertices stay shared. Every duplicate retains an actual fixed source height;
no averaging or public-plane edits. Vertical triangles close radial interfaces.
"""
import collections,json,math,time
from pathlib import Path
from .. import author as a,regeneration
from ..contour_bulk_r01 import profile_mesh
from ..coherent_batch18_r01.route_interval import interval
HERE=Path(__file__).resolve().parent
INPUT=a.HERE/'public_dependency_review_r01'
IDS=['BLOCK_002:R8_C004','BLOCK_003:R8_C001','BLOCK_006:R8_C003']
def write(p,d):
 assert not p.exists();p.write_text(json.dumps(d,separators=(',',':'))+'\n')
def index(regions):
 ix=a.geo._SpatialIndex(4)
 for i,r in enumerate(regions):ix.add(i,r['polygon_xz_m'])
 return ix

def solve_one(group,source):
 public=source['public_fixed_regions'];fixed_regions=group['gate_fixed_regions']+public;domains=source['private_domain_polygons_xz_m']
 parts,cells=profile_mesh.grid_parts(domains,fixed_regions,pitch=1.)
 points,tris,proof=profile_mesh.topology(parts,seam_points=[p for r in fixed_regions for p in r['polygon_xz_m']]);original_tris=[t[:]for t in tris];ix=index(fixed_regions);fixed={};conflicts={};candidates={}
 for i,p in enumerate(points):
  matches=[j for j in sorted(ix.candidates([p]))if a.geo.point_in_convex_polygon(p,fixed_regions[j]['polygon_xz_m'],1e-9)]
  if not matches:continue
  clusters=[]
  for j in matches:
   y=a.common.height(fixed_regions[j]['plane_y_xz_m'],p)
   found=next((c for c in clusters if abs(c['y']-y)<1e-7),None)
   if found is None:clusters.append(dict(y=y,region_indices=[j]))
   else:found['region_indices'].append(j)
  if len(clusters)==1:fixed[i]=clusters[0]['y']
  else:
   if any(j<len(group['gate_fixed_regions'])for c in clusters for j in c['region_indices']):return dict(status='HELD_COURT_PUBLIC_CONFLICT',point_xz_m=p,clusters=clusters)
   conflicts[i]=clusters
  candidates[i]=matches
 # Each boundary star is split into source-bound sectors. Adjacent triangles
 # share a sector until a declared radial retaining edge separates them.
 original_points=[p[:]for p in points];sector_ledger=[]
 for v,clusters in conflicts.items():
  incident=[j for j,t in enumerate(original_tris)if v in t];adj={j:[]for j in incident};anchors={}
  for j in incident:
   t=original_tris[j];neighbors=[k for k in t if k!=v];eligible=set()
   for other in neighbors:
    u,w=points[v],points[other];length=math.dist(u,w)
    for ci,c in enumerate(clusters):
     if any((span:=interval(u,w,fixed_regions[k]['polygon_xz_m']))and(span[1]-span[0])*length>1e-7 for k in c['region_indices']):eligible.add(ci)
   if len(eligible)>1:return dict(status='HELD_TWO_PUBLIC_PLANES_ON_SINGLE_PRIVATE_SECTOR',vertex=points[v],triangle=t,eligible_clusters=sorted(eligible))
   if eligible:anchors[j]=next(iter(eligible))
   for k in incident:
    if j<k and len(set(t)&set(original_tris[k]))==2:adj[j].append(k);adj[k].append(j)
  if set(anchors.values())!=set(range(len(clusters))):return dict(status='HELD_UNANCHORED_INCIDENT_SOURCE',point_xz_m=points[v],clusters=clusters,anchors=anchors)
  distance={}
  for j,ci in anchors.items():
   todo=collections.deque([(j,0)])
   while todo:
    k,d=todo.popleft();key=(k,ci)
    if key in distance:continue
    distance[key]=d;todo.extend((n,d+1)for n in adj[k])
  assignment={j:min(range(len(clusters)),key=lambda ci:(distance.get((j,ci),10**8),ci))for j in incident}
  assignment.update(anchors);copies=[]
  for ci,c in enumerate(clusters):
   k=v if ci==0 else len(points)
   if ci:points.append(points[v][:])
   fixed[k]=c['y'];copies.append(k)
  for j,ci in assignment.items():tris[j]=[copies[ci]if k==v else k for k in tris[j]]
  sector_ledger.append(dict(point_xz_m=original_points[v],clusters=clusters,source_fixed_regions=[fixed_regions[k]for c in clusters for k in c['region_indices']],sector_anchors=anchors,triangle_sectors=assignment,copies=copies))
 targets=[min(group['gate_targets'],key=lambda r:math.dist(p,r['point_xz_m']))['floor_y_m']for p in points]
 result=regeneration.solve_field(points,tris,fixed,targets,limit=.12)
 if result['status']!='PASSED_FINITE_TRIANGLE_GRADE':return dict(status=result['status'],result=result,incident_sector_ledger=sector_ledger)
 faces=result['triangles'];ys=result['heights_m'];edges=collections.defaultdict(list)
 for j,t in enumerate(original_tris):
  for u,v in zip(t,t[1:]+t[:1]):edges[tuple(sorted((u,v)))].append(j)
 risers=[];boundary_errors=[];maxstep=0.
 for (u,v),inc in edges.items():
  p,q=original_points[u],original_points[v]
  def values(j):
   mapping=dict(zip(original_tris[j],tris[j]));return[ys[mapping[k]]for k in(u,v)]
  if len(inc)==2:
   left,right=inc;ly,ry=values(left),values(right);delta=[ly[k]-ry[k]for k in(0,1)]
   if max(map(abs,delta))<=1e-7:continue
   if delta[0]*delta[1]<-1e-14:return dict(status='HELD_CROSSING_RISER_HEIGHTS',edge=[p,q],deltas=delta)
   maxstep=max(maxstep,*map(abs,delta));low,high=(ry,ly)if sum(delta)>0 else(ly,ry);lowj=right if sum(delta)>0 else left
   quad=[[p[0],low[0],p[1]],[q[0],low[1],q[1]],[q[0],high[1],q[1]],[p[0],high[0],p[1]]]
   center=[sum(original_points[k][axis]for k in original_tris[lowj])/3 for axis in(0,1)];mid=[(p[k]+q[k])/2 for k in(0,1)];emitted=[]
   for tri in([quad[0],quad[1],quad[2]],[quad[0],quad[2],quad[3]]):
    b=[tri[1][k]-tri[0][k]for k in range(3)];c=[tri[2][k]-tri[0][k]for k in range(3)];n=[b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0]]
    if math.sqrt(sum(v*v for v in n))<1e-12:continue
    if n[0]*(center[0]-mid[0])+n[2]*(center[1]-mid[1])<0:tri=[tri[0],tri[2],tri[1]]
    emitted.append(tri)
   risers.append(dict(edge_xz_m=[p,q],left_heights_m=ly,right_heights_m=ry,triangles_xyz_m=emitted,maximum_step_m=max(map(abs,delta)),material='bank',walking_surface=False))
  elif len(inc)==1:
   y=values(inc[0])
   for j in ix.candidates([p,q]):
    r=fixed_regions[j];span=interval(p,q,r['polygon_xz_m'])
    if not span or(span[1]-span[0])*math.dist(p,q)<1e-7:continue
    error=max(abs((1-t)*y[0]+t*y[1]-a.common.height(r['plane_y_xz_m'],[(1-t)*p[k]+t*q[k]for k in(0,1)]))for t in span)
    if error>1e-7:boundary_errors.append(dict(edge_xz_m=[p,q],source_region_id=r['id'],maximum_error_m=error))
  else:return dict(status='HELD_NONMANIFOLD_SOURCE_EDGE',edge=[p,q],incident=inc)
 expected=sum(a.geo.polygon_area(p)for p in domains);got=sum(a.geo.polygon_area(t['polygon_xz_m'])for t in faces)
 return dict(status='PASSED_FINITE_PROFILE_WITH_DECLARED_INCIDENT_RISERS'if not boundary_errors and abs(got-expected)<1e-7 else'HELD_BOUNDARY_OR_COVERAGE',result=result,incident_sector_ledger=sector_ledger,vertical_risers=risers,boundary_errors=boundary_errors,maximum_step_m=maxstep,domain_area_m2=expected,triangulated_area_m2=got,topology_proof=proof,cell_partition_checks=cells)

def run():
 groups=json.loads((a.HERE/'contour_bulk_r01/shared_private_groups_r03.json').read_bytes())['groups'];rows=[]
 for hid in IDS:
  g=next(g for g in groups if g['holding_ids']==[hid]);p=INPUT/'private_profiles'/(g['id'].replace(':','_')+'.json');source=json.loads(p.read_bytes());path=HERE/(hid.replace(':','_')+'.json')
  if path.exists():out=json.loads(path.read_bytes())
  else:
   start=time.monotonic();result=solve_one(g,source);out=dict(id=g['id'],holding_ids=g['holding_ids'],source=dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p)),private_domain_polygons_xz_m=source['private_domain_polygons_xz_m'],public_fixed_regions=source['public_fixed_regions'],result=result,elapsed_s=time.monotonic()-start,activation=False,runtime_approval=False);write(path,out)
  brief=dict(holding_id=hid,status=out['result']['status'],path=str(path.relative_to(a.ROOT)),sha256=a.sha(path),elapsed_s=out['elapsed_s']);rows.append(brief);print(brief,flush=True)
 write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
