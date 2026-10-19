"""Independent source-grid coverage, winding, overlap and released-profile audit."""
import json,math,time,collections
from .height_field import HERE
from . import finite_geometry as g
from .grid_candidate import grade
from ..r17_district_batches import author as a

def main():
 start=time.monotonic();path=HERE/'field_refinement_r01.json';mesh=json.loads(path.read_bytes());ts=mesh['triangles_xyz_m'];cells=collections.defaultdict(list);polys=[[[v[0],v[2]]for v in t]for t in ts];boxes=[a.bounds(p)for p in polys]
 for n,t in enumerate(ts):cells[(math.floor(sum(v[0]for v in t)/12)*4,math.floor(sum(v[2]for v in t)/12)*4)].append(n)
 deficits=[];overlaps=[];tiny_overlap=0.;pairs=0;outside=[]
 for key,indices in cells.items():
  x,z=key;area=math.fsum(g.area(polys[i])for i in indices);deficits.append(dict(origin_xz_m=[x,z],area_m2=area,error_m2=area-16))
  for j,n in enumerate(indices):
   if any(not(x-1e-10<=p[0]<=x+4+1e-10 and z-1e-10<=p[1]<=z+4+1e-10)for p in polys[n]):outside.append(n)
   b=boxes[n]
   for m in indices[:j]:
    c=boxes[m]
    if min(b[2],c[2])<=max(b[0],c[0]) or min(b[3],c[3])<=max(b[1],c[1]):continue
    pairs+=1;q=g.clip(polys[n],polys[m]);area=g.area(q)
    if area>1e-8:overlaps.append(dict(first=n,second=m,area_m2=area,polygon_xz_m=q))
    else:tiny_overlap+=area
 grid=json.loads((HERE/'grid_screen.json').read_bytes());expected={tuple(c['origin_xz_m'])for c in grid['cells']};actual=set(cells);released=json.loads((HERE/'frontage_profiles_r01.json').read_bytes());protected={r['source_triangle_index']for entry in released['entries']if entry['status']=='READY_EXACT_R18_PROFILE_PORTIONS'for r in entry['profile_regions']};errors=[r for r in deficits if abs(r['error_m2'])>1e-7]
 report=dict(status='PASS_SOURCE_GRID_PARTITION_WITH_RECORDED_FLOAT_ROUNDOFF'if not(overlaps or errors or outside or expected!=actual)else'HELD_SOURCE_GRID_PARTITION',source_mesh_sha256=a.sha(path),source_refs=mesh['source_refs'],geometry_code_sha256=a.sha(HERE/'finite_geometry.py'),triangles=len(ts),grid_cells=len(cells),downward_or_degenerate=sum(a.normal_y(t)<=0 for t in ts),max_cell_area_error_m2=max(abs(r['error_m2'])for r in deficits),sum_absolute_cell_area_error_m2=math.fsum(abs(r['error_m2'])for r in deficits),positive_overlap_count_above_1e_8=len(overlaps),overlaps=overlaps,smaller_pair_overlap_sum_m2=tiny_overlap,pairs_tested=pairs,missing_grid_cells=[list(k)for k in expected-actual],extra_grid_cells=[list(k)for k in actual-expected],outside_cell_triangles=outside,cell_failures=errors,protected_released_source_triangles=len(protected),released_mesh_binding_matches=released['source_mesh']['sha256']==a.sha(path),seconds=time.monotonic()-start,scope='Finite interpolation source-grid partition and existing released-face identity only. No scene activation, side closure or controller approval. The numerical area ledger is explicit.')
 (HERE/'candidate_geometry_review_r01.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print({k:v for k,v in report.items()if k not in('source_refs','overlaps','cell_failures')},flush=True)
if __name__=='__main__':main()
