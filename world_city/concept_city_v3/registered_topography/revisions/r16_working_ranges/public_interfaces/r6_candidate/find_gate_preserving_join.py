"""Keep the original work-lane gate; search a bounded level downstream tail."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from find_level_approaches import s,ribbons,audit
import json,math,numpy as np

def run():
 h=s.H['terminal_grade_holds'][1];route=next(r for r in s.A['external_routes']if r['id']==h['route_id']);gate=route['gate']['position_xz_m'];line=h['polyline_xz_m'];prefix=line[:line.index(gate)+1];w=h['review_width_m'];assert audit(ribbons(prefix,w))[0]
 ends=[]
 for x in np.arange(211,218.01,.5):
  for z in np.arange(129,136.01,.5):
   ends.append([float(x),float(z)])
 rows=[];attempts=0
 for bend in [None]+[[float(x),float(z)]for x in np.arange(215,219.01,.5)for z in [142.,143.,144.]]:
  for end in ends:
   tail=[gate]+([bend]if bend else[])+[end];new=prefix+tail[1:];edge=s.end_edge(tail,w);pr=s.profile(*edge);attempts+=1
   if pr['grade_violations']or pr['incompatible_height_knots']:continue
   if abs(sum(r['length_m']for r in pr['pieces']if r['source']['material']=='road')-w)>1e-7:continue
   if any(abs(v[1]-2.5)>1e-7 for r in pr['pieces']for v in r['vertices_xyz_m']):continue
   # Include the full-width gate turn in the new finite ownership.
   ps=ribbons([prefix[-2]]+tail,w);ok,delta,g,err=audit(ps)
   if not ok:continue
   length=sum(math.dist(a,b)for a,b in zip(new,new[1:]));rows.append(dict(line_xz_m=new,tail_xz_m=tail,length_m=length,width_m=w,maximum_source_height_delta_from_2_5_m=delta,maximum_source_triangle_gradient=g,max_polygon_coverage_error_m2=err,full_width_end_profile=pr,preserved_gate_xz_m=gate))
  if bend is None and rows:break
 rows.sort(key=lambda r:r['length_m'])
 out=dict(index=1,route_id=h['route_id'],attempt_count=attempts,level_candidate_count=len(rows),best_candidates=rows[:20]);(HERE/'gate_preserving_level_candidates.json').write_text(json.dumps(out,indent=2)+'\n');print('success',len(rows),'attempts',attempts,'best',[(r['length_m'],r['tail_xz_m'])for r in rows[:5]],flush=True)
if __name__=='__main__':run()
