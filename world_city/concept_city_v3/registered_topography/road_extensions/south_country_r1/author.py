"""Reconstructed finite south-bank route after workspace loss; native data rechecked."""
import json,math,hashlib
from pathlib import Path
from world_city.concept_city_v3.registered_source.controls import inverse
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[2];ROOT=CITY.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def xyz(tr,x,y,z):return [tr['translation'][i]+sum(tr['basis'][i][j]*[x,y,z][j] for j in range(3)) for i in range(3)]
def area(p):return geo.polygon_area(p)
def main():
 path=CITY/'assemblies/waterworks/registered_bridge/drawbridge_candidate/resolved_placements.json';d=json.loads(path.read_bytes());assert sha(path)=='de1663faae0ee408876c4d984e8d85072010cbf5bcf714e9e1993b8a5953f90e'
 tr=d['bridge_to_world'];asset=d['assets']['stone_approaches'];render=json.loads((ROOT/asset['render_path']).read_bytes());assert sha(ROOT/asset['render_path'])==asset['render_sha256'];matching=[]
 for g in render['groups']:
  for q in g['quads']:
   u=[q[1][i]-q[0][i] for i in range(3)];v=[q[2][i]-q[0][i] for i in range(3)];ny=u[2]*v[0]-u[0]*v[2]
   if ny>0 and all(abs(p[1]-1.25)<1e-8 for p in q) and min(p[0] for p in q)<=71 and max(p[0] for p in q)==72 and min(p[2] for p in q)<=-3.5 and max(p[2] for p in q)>=3.5:matching.append(q)
 assert matching,'Native terminal floor does not cover new road width'
 centers=[xyz(tr,72,1.25,0),inverse([983,969],1.25),inverse([991,997],1.0),inverse([1006,1045],1.0)];width=7.;sections=[]
 for i,p in enumerate(centers):
  if i==0:n=[tr['basis'][0][2],tr['basis'][2][2]]
  else:
   a=centers[max(0,i-1)];b=centers[min(len(centers)-1,i+1)];dx,dz=b[0]-a[0],b[2]-a[2];L=math.hypot(dx,dz);n=[-dz/L,dx/L]
  sections.append([[p[0]+s*n[0]*width/2,p[1],p[2]+s*n[1]*width/2] for s in (-1,1)])
 triangles=[];polys=[];grades=[]
 for i in range(len(centers)-1):
  q=[sections[i][0],sections[i+1][0],sections[i+1][1],sections[i][1]];polys.append([[v[0],v[2]] for v in q]);grades.append(abs(centers[i+1][1]-centers[i][1])/math.dist([centers[i][0],centers[i][2]],[centers[i+1][0],centers[i+1][2]]))
  for j,ids in enumerate(((0,1,2),(0,2,3))):
   vs=[q[k] for k in ids];triangles.append(dict(owner_id=f'SOUTH_COUNTRY_ROAD:{i}:{j}',route_id='SOUTH_COUNTRY_ROAD',kind='country_road_preview',material='road',material_hint='road',polygon_xz_m=[[v[0],v[2]] for v in vs],vertices_xyz_m=vs,render_surface=True))
 t=json.loads((CITY/'registered_topography/revisions/r08_park_interface/contract.json').read_bytes());water_hits=[]
 for i,p in enumerate(polys):
  for w in t['water_domain_polygons']:
   hit=geo.convex_intersection(p,w['polygon_xz_m']);n=area(hit) if hit else 0
   if n>1e-7:water_hits.append(dict(segment=i,water=w['surface_id'],area_m2=n))
 assert not water_hits,water_hits
 overlap=sum(area(geo.convex_intersection(a,b)) for i,a in enumerate(polys) for b in polys[i+1:]);assert overlap<1e-7
 out=dict(schema='riverstone.finite_country_road.v1',status='reconstructed_source_profile_validated_pending_owned_terrain_integration',source_plan=dict(path='world_city/concept_city_v3/registered_source/plan.json',sha256=sha(CITY/'registered_source/plan.json')),native_bridge=dict(path=str(path.relative_to(ROOT)),sha256=sha(path),render_path=asset['render_path'],render_sha256=asset['render_sha256']),route_id='SOUTH_COUNTRY_ROAD',width_m=width,centerline_xyz_m=centers,cross_sections_xyz_m=sections,triangles=triangles,ownership_polygons_xz_m=polys,observed_controls_pixel_xy=[[983,969],[991,997],[1006,1045]],evidence='First point is an actual native terminal edge. Continuation follows foreground bridge-axis alignment; last point extends beyond the painting as a country-route inference.',gate_status='The painted southern barbican is not modeled.',native_shared_edge_xyz_m=sections[0],native_floor_y_m=1.25,maximum_centerline_grade=max(grades),road_length_m=sum(math.dist(a,b) for a,b in zip(centers,centers[1:])),area_m2=sum(area(p) for p in polys),road_self_overlap_m2=overlap,water_overlap=water_hits,terrain_owner_policy='Replace inherited ground/shoulder/old terminal MAIN_BRIDGE preview only inside finite polygons; preserve native deck and water.',reconstruction='Regenerated from retained design after 2026-10-18 workspace loss. Restored source/cache checks and finite geometry tests rerun; not byte restoration of the lost candidate.',limits=['Source profile; native common compilation and character/cart test pending.','Triangle grade, cut/fill and full-width ownership seam need terrain integration validation.','Endpoint is explicit off-city boundary, not completed countryside.'])
 (HERE/'contract.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(path=str((HERE/'contract.json').relative_to(ROOT)),sha256=sha(HERE/'contract.json'),length_m=out['road_length_m'],max_grade=max(grades),water_hits=water_hits),indent=2))
if __name__=='__main__':main()
