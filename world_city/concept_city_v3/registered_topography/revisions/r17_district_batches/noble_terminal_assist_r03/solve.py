"""Bounded immutable noble terminal finite mesh proposals."""
import json,math,time
from pathlib import Path
from .. import author as a
from ..bounded_profile_r01 import finite as profile_mesh
HERE=Path(__file__).resolve().parent
SOURCE=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02/tail_solve_inputs.json'
SHA='6254994dd9e6bdaabfb51b19dc521376187c4070853cfe1a3fa06b03855a9785'
def write(p,d):
 assert not p.exists();p.write_text(json.dumps(d,separators=(',',':'))+'\n')
def point_distance(p,poly):
 if profile_mesh.inside(p,poly,1e-10):return 0.
 distances=[]
 for u,v in zip(poly,poly[1:]+poly[:1]):
  l=sum((v[k]-u[k])**2 for k in(0,1));t=max(0,min(1,sum((p[k]-u[k])*(v[k]-u[k])for k in(0,1))/l))if l else 0
  distances.append(math.dist(p,[u[k]+t*(v[k]-u[k])for k in(0,1)]))
 return min(distances)
def run():
 assert a.sha(SOURCE)==SHA;source=json.loads(SOURCE.read_bytes());rows=[]
 for entry in sorted([r for r in source['owners'] if r['owner_id']!='E3'],key=lambda r:['E1','E2','E5','E4','E6','E7','E3'].index(r['owner_id'])):
  path=HERE/(entry['owner_id']+'_proposal.json')
  if path.exists():proposal=json.loads(path.read_bytes())
  else:
   start=time.monotonic();ref=entry['target_profile'];p=a.ROOT/ref['path'];assert a.sha(p)==ref['sha256'];old=json.loads(p.read_bytes())['top_pieces'];ix=a.geo._SpatialIndex(2)
   for i,r in enumerate(old):ix.add(i,r['polygon_xz_m'])
   fallback=[]
   def target(point):
    hits=[r for i in sorted(ix.candidates([point]))if profile_mesh.inside(point,(r:=old[i])['polygon_xz_m'],1e-9)]
    if hits:return a.common.height(hits[0]['plane_y_xz_m'],point)
    j,dist=min(((i,point_distance(point,r['polygon_xz_m']))for i,r in enumerate(old)),key=lambda r:r[1]);fallback.append(dict(point_xz_m=point,distance_to_old_domain_m=dist,source_piece_index=j))
    # Authorized finite extrapolation is a soft objective only, never an existing owner or fixed support datum.
    return a.common.height(old[j]['plane_y_xz_m'],point)
   omitted=[p for p in entry['private_domain_polygons_xz_m']if a.geo.polygon_area(p)<=1e-12];domains=[p for p in entry['private_domain_polygons_xz_m']if a.geo.polygon_area(p)>1e-12]
   try:result=profile_mesh.solve(domains,entry['fixed_regions'],target,pitch=.5,limit=.12,seam_points=[p for r in entry['fixed_regions']for p in r['polygon_xz_m']])
   except Exception as e:result=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
   proposal=dict(owner_id=entry['owner_id'],source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=SHA),target_source=ref,private_domain_polygons_xz_m=domains,fixed_regions=entry['fixed_regions'],result=result,numerical_zero_area_source_fragments=omitted,numerical_zero_area_sum_m2=sum(a.geo.polygon_area(p)for p in omitted),target_perimeter_fallbacks=fallback,elapsed_s=time.monotonic()-start,soft_target_policy='Nearest old plane may be extrapolated only as a soft optimization target in the finite new collar. Actual fixed public and inner seams are unchanged; new support remains the native producer obligation.',activation=False);write(path,proposal)
  brief=dict(owner_id=entry['owner_id'],status=proposal['result']['status'],maximum_gradient=proposal['result'].get('maximum_gradient'),conflicts=len(proposal['result'].get('conflicts',[])),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path),elapsed_s=proposal['elapsed_s']);rows.append(brief);print(brief,flush=True)
 write(HERE/'summary.json',dict(rows=rows,source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=SHA),activation=False))
if __name__=='__main__':run()
