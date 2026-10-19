"""Bind local service terminals to retained named landmark approaches and road seams."""
import json,math,collections
from .select_drawhouses import HERE,CITY,rect
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.runtime_city.checks import placement as g
PROFILE=CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json'
def run():
 loc=json.loads((HERE/'retained_entry_location_candidates.json').read_text());rec=json.loads(PROFILE.read_text());scene=a.load_scene();out=[]
 for fixture in loc['drawhouses']:
  group={'CATHEDRAL_DRAW':'cathedral','MONASTERY_DRAW':'monastery','CASTLE_DRAW':'castle'}[fixture['id']];target=fixture['walk_centerline_xz_m'][-1];sources=[r for k in ('approaches','landings')for r in rec[k]['triangles']if r['group_id'] in (group,group+'_public_landing')];si=g._SpatialIndex(8)
  for i,r in enumerate(sources):si.add(i,r['polygon_xz_m'])
  xzs=[v for r in sources for v in r['polygon_xz_m']];win=[[min(v[0]for v in xzs)-1,min(v[1]for v in xzs)-1],[max(v[0]for v in xzs)+1,min(v[1]for v in xzs)-1],[max(v[0]for v in xzs)+1,max(v[1]for v in xzs)+1],[min(v[0]for v in xzs)-1,max(v[1]for v in xzs)+1]]
  ix=a.TriangleIndex(scene,[win]);rows=[];seed=[];landing=set();road_seams=[r for r in rec['landings']['masks']if r['group_id']==group+'_public_landing']
  for row in ix.rows:
   if row['material']not in ('road','alley'):continue
   p=row['polygon_xz_m'];q=[sum(v[0]for v in p)/3,sum(v[1]for v in p)/3];matches=[sources[j]for j in si.candidates(p)if g.point_in_convex_polygon(q,sources[j]['polygon_xz_m']) and abs(a.common.height(a.common.plane(sources[j]['triangle_xyz_m']),q)-a.common.height(row['plane_y_xz_m'],q))<1e-5]
   if not matches:continue
   i=len(rows);rows.append(dict(row,recovered_owner_ids=[r['owner_id']for r in matches]))
   if g.point_in_convex_polygon(target,p):seed.append(i)
   if any(r['group_id'].endswith('public_landing')for r in matches):landing.add(i)
  # Equal XYZ edges and collinear split edges both count; point-only contact does not.
  lines=collections.defaultdict(list);adj=collections.defaultdict(set)
  for i,row in enumerate(rows):
   p=row['polygon_xz_m']
   for u,v in zip(p,p[1:]+p[:1]):
    dx,dz=v[0]-u[0],v[1]-u[1];n=math.hypot(dx,dz)
    if n<1e-8:continue
    ux,uz=dx/n,dz/n
    if ux<-1e-10 or(abs(ux)<1e-10 and uz<0):ux,uz=-ux,-uz
    c=-uz*u[0]+ux*u[1];key=(round(ux,6),round(uz,6),round(c,5));aa=ux*u[0]+uz*u[1];bb=ux*v[0]+uz*v[1];lines[key].append((min(aa,bb),max(aa,bb),i,u,v))
  for edges in lines.values():
   edges.sort()
   for j,e in enumerate(edges):
    lo,hi,i,u,v=e
    for other in edges[j+1:]:
     ll,hh,k,uu,vv=other
     if ll>=hi-1e-7:break
     if i==k or min(hi,hh)-max(lo,ll)<1e-7:continue
     # All vertices on the shared line must agree at the overlap midpoint.
     ux,uz=(v[0]-u[0]),(v[1]-u[1]);n=math.hypot(ux,uz);ux/=n;uz/=n
     if ux<-1e-10 or(abs(ux)<1e-10 and uz<0):ux,uz=-ux,-uz
     t=(max(lo,ll)+min(hi,hh))/2;c=-uz*u[0]+ux*u[1];q=[ux*t-uz*c,uz*t+ux*c]
     if abs(a.common.height(rows[i]['plane_y_xz_m'],q)-a.common.height(rows[k]['plane_y_xz_m'],q))>1e-5:continue
     adj[i].add(k);adj[k].add(i)
  prev={i:None for i in seed};todo=collections.deque(seed);end=None
  while todo:
   i=todo.popleft()
   if i in landing:end=i;break
   for k in adj[i]:
    if k not in prev:prev[k]=i;todo.append(k)
  chain=[]
  if end is not None:
   i=end
   while i is not None:chain.append(i);i=prev[i]
   chain.reverse()
  named_seams=[r for r in road_seams if end is not None and g.polygon_area(g.convex_intersection(rows[end]['polygon_xz_m'],r['polygon_xz_m']))>1e-9]
  assert end is None or named_seams
  recrow=dict(fixture_id=fixture['id'],status='PASS'if end is not None else'NO_CONNECTED_PUBLIC_LANDING',group_id=group,terminal_xz_m=target,terminal_actual_triangle_ids=[rows[i]['triangle_index']for i in seed],terminal_recovered_owner_ids=sorted(set(v for i in seed for v in rows[i]['recovered_owner_ids'])),actual_mesh_triangle_count=len(rows),connected_count=len(prev),continuation_triangle_count=len(chain),continuation_triangle_ids=[rows[i]['triangle_index']for i in chain],named_public_road_ids=sorted(set(r['road_id']for r in named_seams)),named_landing_mask_ids=[r['owner_id']for r in named_seams],connected_landing_recovered_owner_ids=rows[end]['recovered_owner_ids']if end is not None else[],source_profile_sha256=a.sha(PROFILE),method='Hash-bound R7 public top triangles matched to retained named R3 approach/landing owners. Positive-length shared XYZ edge graph; point-only contacts rejected. The preserved source landing has explicit named-road seam ownership.',limits=['This proves continuous rendered-top connectivity of retained entry path, not fresh character/controller replay or structural engineering.'])
  out.append(recrow);print(group,recrow['status'],len(rows),len(prev),len(chain),flush=True)
 result=dict(schema='riverstone.r8.named_public_continuation.v1',base_scene_sha256=a.SCENE_SHA256,retained_profiles=dict(path=str(PROFILE.relative_to(CITY.parents[1])),sha256=a.sha(PROFILE)),fixtures=out)
 (HERE/'public_continuation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':run()
