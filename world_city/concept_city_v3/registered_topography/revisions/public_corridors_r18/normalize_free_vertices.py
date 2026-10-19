"""Explicit <=0.1 micrometre repair of generated near-duplicate boundary vertices.
Accepted profile/source coordinates are anchors, never edited. Zero-area faces
created by a recorded collapse are removed; finite-domain coverage is re-audited.
"""
import collections,json,math,time
from scipy.spatial import cKDTree
from .height_field import HERE,HeightField,fixed_sources
from .grid_candidate import grade
from ..r17_district_batches import author as a
BOUND=1e-7

def main():
 start=time.monotonic();source=HERE/'field_refinement_r01.json';data=json.loads(source.read_bytes());regions,segments,refs=fixed_sources();field=HeightField(regions,segments);triangles=data['triangles_xyz_m'];keys=sorted(set(tuple(v)for t in triangles for v in t));xz=list(dict.fromkeys((v[0],v[2])for v in keys));yi={(v[0],v[2]):v[1]for v in keys};edges=[];anchors=[];ri=a.geo._SpatialIndex(4);ei=a.geo._SpatialIndex(4)
 for n,r in enumerate(regions):
  p=r['polygon_xz_m'];pl=r['plane_y_xz_m'];ri.add(n,p);vs=[[q[0],a.common.height(pl,q),q[1]]for q in p];anchors+=vs
  edges.extend((u,v)for u,v in zip(vs,vs[1:]+vs[:1]))
 for r in segments:anchors+=r['xyz_m'];edges.append(tuple(r['xyz_m']))
 released_path=HERE/'frontage_profiles_r01.json';released=json.loads(released_path.read_bytes());protected_triangles=set(n for r in released['entries']if r['status']=='READY_EXACT_R18_PROFILE_PORTIONS'for n in [p['source_triangle_index']for p in r['profile_regions']]);protected_xz=set((v[0],v[2])for n in protected_triangles for v in triangles[n]);anchors += [v for n in protected_triangles for v in triangles[n]]
 for n,(u,v)in enumerate(edges):ei.add(n,[[u[0]-BOUND,u[2]-BOUND],[u[0]+BOUND,u[2]+BOUND],[v[0]-BOUND,v[2]-BOUND],[v[0]+BOUND,v[2]+BOUND]])
 tree=cKDTree([[v[0],v[2]]for v in anchors]);mapping={};records=[];protected=0;immutable=set(protected_xz);anchored=set()
 for p in xz:
  if p in protected_xz:mapping[p]=[p[0],yi[p],p[1]];protected+=1;continue
  dist,ai=tree.query(p)
  if dist<=BOUND:q=anchors[int(ai)]
  else:
   q=None;best=BOUND
   for n in ei.candidates([p]):
    u,v=edges[n];L2=(u[0]-v[0])**2+(u[2]-v[2])**2
    if L2<1e-24:continue
    f=max(0.,min(1.,((p[0]-u[0])*(v[0]-u[0])+(p[1]-u[2])*(v[2]-u[2]))/L2));candidate=[u[k]+f*(v[k]-u[k])for k in range(3)];distance=math.dist(p,[candidate[0],candidate[2]])
    if distance<best:q=candidate;best=distance
  if q is None:q=[p[0],yi[p],p[1]]
  # Strictly interior fixed-region samples cannot be displaced by this repair.
  if any(a.geo.point_in_convex_polygon(p,regions[n]['polygon_xz_m'],0) and min(a.geo.point_segment_distance(p,u,v)for u,v in zip(regions[n]['polygon_xz_m'],regions[n]['polygon_xz_m'][1:]+regions[n]['polygon_xz_m'][:1]))>1e-11 for n in ri.candidates([p])):q=[p[0],yi[p],p[1]];protected+=1
  mapping[p]=q
  if q!=[p[0],yi[p],p[1]]:anchored.add(p)
  if protected and q==[p[0],yi[p],p[1]] and any(a.geo.point_in_convex_polygon(p,regions[n]['polygon_xz_m'],0)for n in ri.candidates([p])):immutable.add(p)
 # Merge free near-duplicates only after source anchoring; every merge stays in
 # the original 0.1 micrometre ball, never a transitive unbounded cluster.
 mapped=list(mapping.values());mt=cKDTree([[v[0],v[2]]for v in mapped]);pairs=mt.query_pairs(BOUND)
 for i,j in sorted(pairs):
  pi,pj=xz[i],xz[j]
  if pi in immutable or pj in immutable or (pi in anchored and pj in anchored):continue
  vi,vj=mapping[pi],mapping[pj]
  if math.dist([vi[0],vi[2]],[vj[0],vj[2]])>BOUND:continue
  # Prefer the point with smaller displacement from an exact source anchor.
  di,_=tree.query([vi[0],vi[2]]);dj,_=tree.query([vj[0],vj[2]]);winner=vi if di<=dj else vj;loser=pj if di<=dj else pi
  if math.dist(loser,[winner[0],winner[2]])<=BOUND:mapping[loser]=winner
 out=[];removed=[];changed_triangles=[]
 for n,t in enumerate(triangles):
  nt=[mapping[(v[0],v[2])]for v in t]
  if nt!=t:changed_triangles.append(n)
  if a.normal_y(nt)<=1e-16:
   if a.normal_y(nt)<-1e-12:raise ValueError('Normalization inverted triangle')
   removed.append(dict(source_triangle_index=n,original_triangle_xyz_m=t,normalized_triangle_xyz_m=nt,original_area_m2=abs(a.normal_y(t))/2));continue
  out.append(nt)
 for p,q in mapping.items():
  old=[p[0],yi[p],p[1]]
  if old!=q:records.append(dict(before_xyz_m=old,after_xyz_m=q,xz_displacement_m=math.dist(p,[q[0],q[2]]),height_displacement_m=abs(yi[p]-q[1])))
 assert max((r['xz_displacement_m']for r in records),default=0)<=BOUND+1e-12
 report=dict(status='NORMALIZED_CANDIDATE_PENDING_FINITE_GRADIENT_AND_COVERAGE',source_mesh_sha256=a.sha(source),source_refs=refs,released_profiles_sha256=a.sha(released_path),bound_m=BOUND,input_triangles=len(triangles),output_triangles=len(out),changed_triangles=len(changed_triangles),protected_released_triangles=len(protected_triangles),removed_zero_area_triangles=removed,max_xz_displacement_m=max((r['xz_displacement_m']for r in records),default=0),max_height_displacement_m=max((r['height_displacement_m']for r in records),default=0),total_signed_area_delta_m2=sum(a.normal_y(t)/2 for t in out)-sum(a.normal_y(t)/2 for t in triangles),records=records,seconds=time.monotonic()-start)
 (HERE/'field_normalized_r02.json').write_text(json.dumps(dict(report=report,triangles_xyz_m=out),separators=(',',':'))+'\n');(HERE/'normalization_review_r02.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print({k:v for k,v in report.items()if k not in('source_refs','records','removed_zero_area_triangles')},flush=True)
if __name__=='__main__':main()
