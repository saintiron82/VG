import json,math
from pathlib import Path
from .cover_upper import frac,area,diff
from ..north_junction_transition_r01.author import ROOT,CITY,a,g,ref,dump
HERE=Path(__file__).resolve().parent

def distseg(p,u,v):
 dd=sum((v[k]-u[k])**2 for k in(0,1));t=max(0,min(1,sum((p[k]-u[k])*(v[k]-u[k])for k in(0,1))/dd))if dd else 0
 return math.dist(p,[u[k]+t*(v[k]-u[k])for k in(0,1)])
def main():
 pp=HERE.parent/'finite_field_candidate_r07_native_bound.json';pub=json.loads(pp.read_bytes());idx=a.geo._SpatialIndex(4)
 for i,r in enumerate(pub['records']):idx.add(i,r['polygon_xz_m'])
 output=[]
 for name in ['market_north','central_west_radial']:
  sp=HERE/(name+'_local_faces.json');src=json.loads(sp.read_bytes());m=src['source_matches'][0];poly=[[v[0],v[2]]for v in m['triangle_xyz_m']];P=frac(poly);parts=[P];covers=[];near=[]
  for i in sorted(idx.candidates(poly)):
   r=pub['records'][i];Q=frac(r['polygon_xz_m'])
   if not area(Q):continue
   rem=[];ov=0
   for part in parts:
    rest,inside=diff(part,Q);rem+=rest;ov+=area(inside)
   parts=rem
   if ov:covers.append(dict(owner_id=r['id'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],area_m2=float(ov)))
   for u,v in zip(r['polygon_xz_m'],r['polygon_xz_m'][1:]+r['polygon_xz_m'][:1]):
    distances=[distseg(x,u,v)for x in poly]
    if max(distances)<1e-7:near.append(dict(owner_id=r['id'],edge_xz_m=[u,v],maximum_endpoint_distance_m=max(distances),plane_y_xz_m=r['plane_y_xz_m'],old_minus_public_at_vertices_m=[x[1]-a.common.height(r['plane_y_xz_m'],[x[0],x[2]])for x in m['triangle_xyz_m']]))
  output.append(dict(route=name,source=ref(sp),source_match=m,current_public_cover_records=covers,source_projected_area_m2=float(area(P)),uncovered_area_m2=float(sum(area(q)for q in parts)),uncovered_polygons_xz_m=[[[float(x)for x in v]for v in q]for q in parts],actual_public_edge_contacts=near))
 out=dict(status='EXACT_RATIONAL_LOCAL_OWNER_PROOF',source=ref(pp),rows=output);print(dump(HERE/'other_owner_coverage.json',out))
 for r in output:print(r['route'],'area',r['source_projected_area_m2'],'missing',r['uncovered_area_m2'],'edges',r['actual_public_edge_contacts'])
if __name__=='__main__':main()
