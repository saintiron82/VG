"""Finite junction-extension candidates with actual outer-section heights.
No old steep overlap planes are fixed. No scene/road/source asset is edited.
"""
import bisect,collections,hashlib,importlib.util,json,math,pathlib,sys,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;B=H.parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));CITY=ROOT/'world_city/concept_city_v3'
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.r01_ownership import author as ownership
sp=importlib.util.spec_from_file_location('retained_source_clip',B/'fixed_interfaces_r18_r01/add_retained_boundaries.py');u=importlib.util.module_from_spec(sp);sp.loader.exec_module(u)
geo=a.geo

def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(name,obj):
 with(H/name).open('x')as f:json.dump(obj,f,separators=(',',':'),allow_nan=False);f.write('\n')
def cross(p,q,r):return(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
def point(p,q,t):return[p[k]+t*(q[k]-p[k])for k in(0,1)]
def height(r,p):v=r['plane_y_xz_m'];return v[0]*p[0]+v[1]*p[1]+v[2]
def sr(r):return{k:r[k]for k in('material','triangle_index','source_triangle_sha256','vertices_xyz_m','plane_y_xz_m')}
def interval(p,q,tri):
 sign=1 if cross(*tri)>0 else -1;lo,hi=0.,1.
 for x,y in zip(tri,tri[1:]+tri[:1]):
  b=sign*cross(x,y,p);m=sign*(cross(x,y,q)-cross(x,y,p))
  if abs(m)<1e-13:
   if b< -1e-9:return None
  elif m>0:lo=max(lo,-b/m)
  else:hi=min(hi,-b/m)
 if hi-lo<1e-10:return None
 return max(0.,lo),min(1.,hi)
def profile(index,p,q):
 pieces=[]
 for i in sorted(index.index.candidates([p,q])):
  r=index.rows[i];it=interval(p,q,r['polygon_xz_m'])
  if it:pieces.append(dict(t_interval=list(it),source=sr(r)))
 knots=[]
 for t in sorted([0.,1.]+[t for r in pieces for t in r['t_interval']]):
  if not knots or t-knots[-1]>1e-10:knots.append(t)
 gaps=[];duplicate=[];mismatch=[];xyz=[]
 for t in knots:
  pnt=point(p,q,t);votes=[height(r['source'],pnt)for r in pieces if r['t_interval'][0]-1e-9<=t<=r['t_interval'][1]+1e-9]
  if not votes:continue
  if max(votes)-min(votes)>1e-7:mismatch.append(dict(t=t,spread_m=max(votes)-min(votes),heights=votes))
  xyz.append([pnt[0],votes[0],pnt[1]])
 for lo,hi in zip(knots,knots[1:]):
  hits=[r for r in pieces if r['t_interval'][0]<(lo+hi)/2<r['t_interval'][1]]
  if not hits:gaps.append([lo,hi])
  if len(hits)>1:duplicate.append([lo,hi])
 maxgrade=max((math.hypot(*r['source']['plane_y_xz_m'][:2])for r in pieces),default=0)
 return dict(edge_xz_m=[p,q],knots_xyz_m=xyz,pieces=pieces,uncovered_t_intervals=gaps,multiple_face_intervals=duplicate,incompatible_height_knots=mismatch,max_source_triangle_grade=maxgrade,valid=bool(pieces)and not gaps and not mismatch and maxgrade<=.12+1e-7)
class Road:
 def __init__(self,r):
  self.r=r;self.id=r['id'];self.ps=r['polyline_xz_m'];self.w=r['width_m'];self.ss=[0.]
  for p,q in zip(self.ps,self.ps[1:]):self.ss.append(self.ss[-1]+math.dist(p,q))
  self.total=self.ss[-1];self.polys=list(ownership.corridor(self.ps,self.w))
 def station(self,p):
  best=None
  for i,(x,y)in enumerate(zip(self.ps,self.ps[1:])):
   d=[y[k]-x[k]for k in(0,1)];l2=sum(v*v for v in d);t=max(0,min(1,sum((p[k]-x[k])*d[k]for k in(0,1))/l2));dist=math.dist(p,point(x,y,t));v=(dist,self.ss[i]+t*math.sqrt(l2),i)
   if best is None or v<best:best=v
  return best[1]
 def pose(self,s):
  i=min(len(self.ps)-2,max(0,bisect.bisect_right(self.ss,s)-1));t=(s-self.ss[i])/(self.ss[i+1]-self.ss[i]);p=point(self.ps[i],self.ps[i+1],t);d=[(self.ps[i+1][k]-self.ps[i][k])/(self.ss[i+1]-self.ss[i])for k in(0,1)];return p,d,i
 def edge(self,s):
  p,d,i=self.pose(s);n=[-d[1]*self.w/2,d[0]*self.w/2];return [[p[k]+sign*n[k]for k in(0,1)]for sign in(-1,1)]
 def masks(self,lo,hi):
  points=[self.pose(lo)[0]]+[p for s,p in zip(self.ss,self.ps)if lo+1e-9<s<hi-1e-9]+[self.pose(hi)[0]];parts=[]
  for x,y in zip(points,points[1:]):
   p=ownership.base._strip(x,y,self.w)
   if p:parts.append(p)
  # Actual source round joins only, never a new cap at an artificial cut.
  for s,p in zip(self.ss,self.ps):
   if lo-1e-9<=s<=hi+1e-9:parts.append(ownership.circle(p,self.w/2))
  for s,keep in [(lo,1),(hi,-1)]:
   if s<1e-9 or s>self.total-1e-9:continue
   e=self.edge(s);parts=[q for p in parts if(q:=u.clean(geo._clip_halfplane(p,*e,-keep,0,True)))]
  return u.union_parts(parts)
def merge(items):
 out=[]
 for lo,hi,ids in sorted(items):
  if out and lo<=out[-1][1]+.5:out[-1][1]=max(hi,out[-1][1]);out[-1][2].update(ids)
  else:out.append([lo,hi,set(ids)])
 return out

def main():
 t0=time.monotonic();inv=read(B/'primary_inventory/inventory.json');prior=read(B/'public_corridor_priorities_r01/priorities.json');old=read(B/'fixed_interfaces_r18_r01/fixed_interfaces_complete.json');summ=read(B/'network_batch_r01/evidence/summary.json');passed={r['road_id']for r in summ['road_corridor_results']if r['both_directions_pass']};repair=set(prior['minimum_public_ground_corridors']);roads={r['id']:Road(r)for r in inv['roads']};pairs=[p for p in prior['full_width_shared_domains']if p['a_is_regeneration_candidate']!=p['b_is_regeneration_candidate']and set(p['roads'])&passed]
 affected=collections.defaultdict(list)
 for p in pairs:
  rid=next(r for r in p['roads']if r in passed);r=roads[rid];stations=[r.station(v)for q in p['raw_overlap_parts']for v in q['polygon_xz_m']];affected[rid].append([max(0,min(stations)-.001),min(r.total,max(stations)+.001),{'|'.join(p['roads'])}])
 # Broaden the junction interval to include the entire actual bad source face
 # where it lies inside this retained traffic strip, not only its old overlap clip.
 bad=collections.defaultdict(dict)
 for r in old['regions']:
  if r.get('kind')!='actual_retained_corridor_overlap'or math.hypot(*r['plane_y_xz_m'][:2])<=.12+1e-7:continue
  rid=next(k for k in r['roads']if k in passed);key=(r['source']['material'],r['source']['triangle_index']);bad[rid][key]=r
 for rid,rows in bad.items():
  r=roads[rid]
  for row in rows.values():
   tri=[[v[0],v[2]]for v in row['triangle_xyz_m']];cuts=[q for p in r.polys if(q:=u.clean(geo.convex_intersection(tri,p)))];st=[r.station(v)for p in cuts for v in p]
   if st:affected[rid].append([max(0,min(st)-.001),min(r.total,max(st)+.001),{'BAD_SOURCE:'+row['source']['material']+':'+str(row['source']['triangle_index'])}])
 scene=a.load_scene();windows=[p for rid in affected for p in roads[rid].polys];index=a.TriangleIndex(scene,windows)
 repairparts=[p for rid in repair for p in roads[rid].polys];ri=geo._SpatialIndex(8)
 for i,p in enumerate(repairparts):ri.add(i,p)
 def intersects_repair(poly):
  return sum(geo.polygon_area(geo.convex_intersection(poly,repairparts[i]))for i in ri.candidates(poly))>1e-8
 attempts=[];terminals=[];extensions=[];holds=[]
 for rid,items in affected.items():
  r=roads[rid];ranges=merge(items);print('ROAD',rid,len(ranges),flush=True)
  cache={}
  def test(s,side):
   key=(round(s,10),side)
   if key in cache:return cache[key]
   p,q=r.edge(s);pr=profile(index,p,q);out=dict(road_id=rid,station_m=s,side=side,source_segment_index=r.pose(s)[2],profile=pr,valid=pr['valid'])
   # A finite outward collar must lie outside the repaired corridors and use
   # only covered <=12% actual planes. Its two outer rails are also continuous.
   a0,b0=sorted([s,s+side*.25]);collar=r.masks(max(0,a0),min(r.total,b0))
   if not collar or any(intersects_repair(poly)for poly in collar):out['valid']=False;out['reason']='still_inside_regeneration_junction'
   elif out['valid']:
    audits=[a.audit_polygon(index,p)for p in collar];out['collar_review']=[{k:v for k,v in aa.items()if k!='source_pieces'}for aa in audits]
    if not all(aa['passes_existing_surface']for aa in audits):out['valid']=False;out['reason']='outer_collar_missing_duplicate_or_steep'
    else:
     e2=r.edge(s+side*.25);rail=[profile(index,p,e2[0]),profile(index,q,e2[1]),profile(index,*e2)];out['collar_boundary_profiles']=rail
     if not all(x['valid']for x in rail):out['valid']=False;out['reason']='outer_collar_boundary_discontinuity'
   if not out['valid']and'reason'not in out:out['reason']='section_missing_discontinuous_or_steep'
   cache[key]=out;attempts.append(out);return out
  extended=[]
  for n,(lo,hi,ids)in enumerate(ranges):
   found=[]
   for s,side in[(lo,-1),(hi,1)]:
    chosen=None;distance=0.
    while True:
     cand=s+side*(.25+distance)
     if cand<.25 or cand>r.total-.25:break
     # Avoid choosing a terminal inside another affected band.
     if not any(x-.25<=cand<=y+.25 for x,y,_ in ranges):
      rr=test(cand,side)
      if rr['valid']:chosen=rr;break
     distance+=.5
    found.append(chosen)
   newlo=found[0]['station_m']if found[0]else 0.;newhi=found[1]['station_m']if found[1]else r.total
   extended.append([newlo,newhi,ids]);
  # Sections swallowed by another extension are not final boundaries.
  for j,(lo,hi,ids)in enumerate(merge(extended)):
   record=dict(id='RETAINED_JUNCTION:'+rid+':'+str(j),road_id=rid,width_m=r.w,station_interval_m=[lo,hi],trigger_ids=sorted(ids),polygons_xz_m=r.masks(lo,hi),terminal_ids=[])
   for s,side in[(lo,-1),(hi,1)]:
    if s<=1e-9 or s>=r.total-1e-9:
     holds.append(dict(extension_id=record['id'],road_id=rid,endpoint='start'if side<0 else'end',station_m=s,reason='Entire retained branch reaches its original finite road cap before an acceptable outer section; no invented fixed endpoint. Parent must reconcile any native/other-road termination.'))
     continue
    rr=test(s,side);assert rr['valid'];tid=record['id']+(':START'if side<0 else':END');record['terminal_ids'].append(tid);terminals.append(dict(id=tid,**rr))
   extensions.append(record)
 segments=[]
 for r in terminals:
  knots=r['profile']['knots_xyz_m']
  for i,(p,q)in enumerate(zip(knots,knots[1:])):segments.append(dict(id=r['id']+':'+str(i),xyz_m=[p,q],road_id=r['road_id'],station_m=r['station_m'],source_terminal_id=r['id']))
 sources=[B/'primary_inventory/inventory.json',B/'public_corridor_priorities_r01/priorities.json',B/'fixed_interfaces_r18_r01/fixed_interfaces_complete.json',B/'network_batch_r01/evidence/summary.json',a.SCENE_PATH,pathlib.Path(a.__file__),pathlib.Path(ownership.__file__),pathlib.Path(u.__file__),pathlib.Path(__file__)]
 out=dict(schema='riverstone.retained_junction_extension_candidates.v1',status='FINITE_OWNERSHIP_AND_EXACT_TERMINAL_CANDIDATES_NOT_ACTIVATED',sources=[ref(p)for p in sources],extensions=extensions,terminals=terminals,segments=segments,endpoint_reconciliation_required=holds,limits=['Only the final terminal segments are fixed. None of the old defective overlap planes is fixed.','Extension masks are unchanged canonical traffic footprints between stations, including existing finite round joins; native, water and accepted interface exclusions remain mandatory.','A retained corridor centerline pass is not a new junction or full-width controller pass.','Endpoint reconciliation records have no accepted frozen height; final ownership and connections must be checked by the composer.'])
 write('junction_extensions.json',out);write('section_search_evidence.json',dict(attempts=attempts))
 report=dict(output=ref(H/'junction_extensions.json'),retained_roads=len(affected),old_pair_count=len(pairs),extensions=len(extensions),valid_terminals=len(terminals),fixed_segments=len(segments),endpoint_reconciliation_count=len(holds),section_attempts=len(attempts),accepted_max_source_grade=max((t['profile']['max_source_triangle_grade']for t in terminals),default=0),rejected_old_bad_region_count=len(old['retained_corridor_review']['above_12_percent_regions']),seconds=time.monotonic()-t0)
 write('report.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
