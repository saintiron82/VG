"""Exact-triangle search for moved joins without changing public road heights."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import analyze_joins as j
s=j.s
import json,math,numpy as np

def ribbons(line,w):
 ps=[s.a.geo.road_ribbon(a,b,w)for a,b in zip(line,line[1:])]
 r=w/2/math.cos(math.pi/16)
 ps += [[[q[0]+r*math.cos(i*math.pi/8),q[1]+r*math.sin(i*math.pi/8)]for i in range(16)]for q in line[1:-1]]
 return ps

def audit(polys):
 maximum=0.;coverage_error=0.;maxg=0.
 for p in polys:
  covered=0
  for i in s.INDEX.candidates(p):
   r=s.TRIS[i];q=s.a.polygon(s.a.geo.convex_intersection(p,r['polygon_xz_m']))
   if not q:continue
   covered+=s.a.geo.polygon_area(q);maximum=max(maximum,max(abs(s.height(r,v)-2.5)for v in q));maxg=max(maxg,math.hypot(*r['plane_y_xz_m'][:2]))
   if maximum>1e-7:return False,maximum,maxg,0.
  coverage_error=max(coverage_error,abs(covered-s.a.geo.polygon_area(p)))
 return coverage_error<1e-7,maximum,maxg,coverage_error

def run():
 allrows=[]
 for n,h in enumerate(s.H['terminal_grade_holds']):
  start=np.array(h['polyline_xz_m'][0]);direction=np.array(h['polyline_xz_m'][1])-start;direction/=np.linalg.norm(direction);rows=[];attempts=0
  for prefix in [1.,2.,3.]:
   bend=start+direction*prefix
   for x in np.arange(213.5,218.01,.25):
    for z in np.arange(133.0,137.51,.25):
     line=[start.tolist(),bend.tolist(),[float(x),float(z)]];end=s.end_edge(line,h['review_width_m']);pr=s.profile(*end);attempts+=1
     if pr['incompatible_height_knots']or pr['grade_violations']:continue
     if abs(sum(r['length_m']for r in pr['pieces']if r['source']['material']=='road')-h['review_width_m'])>1e-7:continue
     if any(abs(v[1]-2.5)>1e-7 for r in pr['pieces']for v in r['vertices_xyz_m']):continue
     ps=ribbons(line,h['review_width_m']);ok,delta,g,err=audit(ps)
     if not ok:continue
     length=sum(math.dist(a,b)for a,b in zip(line,line[1:]));rows.append(dict(line_xz_m=line,length_m=length,width_m=h['review_width_m'],maximum_source_height_delta_from_2_5_m=delta,maximum_source_triangle_gradient=g,max_polygon_coverage_error_m2=err,full_width_end_profile=pr))
  rows.sort(key=lambda r:(r['length_m'],math.dist(r['line_xz_m'][-1],h['polyline_xz_m'][-1])))
  allrows.append(dict(index=n,route_id=h['route_id'],attempt_count=attempts,level_candidate_count=len(rows),best_candidates=rows[:20]));print(n,'success',len(rows),'best',[(r['length_m'],r['line_xz_m'])for r in rows[:3]],flush=True)
 (HERE/'level_approach_candidates.json').write_text(json.dumps(allrows,indent=2)+'\n')
if __name__=='__main__':run()
