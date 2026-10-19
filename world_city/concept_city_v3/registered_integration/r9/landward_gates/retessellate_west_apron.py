"""Flip one interior diagonal of an exact coplanar convex road quadrilateral.
Source-bound to r08. No vertex, height, footprint, route, or fixture is moved.
"""
import json,shutil,math,numpy as np
from .build_corridors import H,ref,sha,convex_parts,xz,up,area3,write,DomainCut
from world_city.runtime_city.checks import placement as geo
P=H/'candidate_r08';source=P/'surface_patch.json';assert sha(source)=='6aeb892b2bf524a2056a78fb35c4d60575f530e8fd805711e8a3919ac7dbe07a';patch=json.load(open(source));vs=patch['appended_surfaces']['road'];ids=[1663,1666];old=[vs[i*3:i*3+3]for i in ids];points=[]
for t in old:
 for v in t:
  if v not in points:points.append(v)
assert len(points)==4 and all(v[1]==21. for v in points)
new=[up([points[[xz(v)for v in points].index(q)]for q in t])for t in convex_parts([xz(v)for v in points])];assert len(new)==2
for dtype in [None,np.float32]:
 a=old if dtype is None else np.asarray(old,dtype=dtype).astype(float).tolist();b=new if dtype is None else np.asarray(new,dtype=dtype).astype(float).tolist();aa=[[xz(v)for v in t]for t in a];bb=[[xz(v)for v in t]for t in b]
 for before,after in [(aa,bb),(bb,aa)]:
  remaining=sum(geo.polygon_area(q)for t in before for q in DomainCut([dict(polygon_xz_m=v)for v in after]).subtract(t));assert remaining<1e-8,remaining
 assert abs(sum(area3(t)for t in a)-sum(area3(t)for t in b))<1e-8
for i,t in zip(ids,new):vs[3*i:3*i+3]=t
for name in ['ground_ownership.json','farm_pack.json','source_tests.json','float32_filter_report.json']:shutil.copyfile(P/name,H/name)
routes=json.load(open(P/'routes.json'));routes['routes']=[r for r in routes['routes']if 'gate_waypoint_index'in r];write('routes.json',routes);write('surface_patch.json',patch)
wheel=[-393.598419189453,-226.950073242188];common_old=set(tuple(v)for v in old[0])&set(tuple(v)for v in old[1]);common_new=set(tuple(v)for v in new[0])&set(tuple(v)for v in new[1]);assert len(common_old)==len(common_new)==2
record=dict(schema='riverstone.exact_coplanar_retriangulation.v1',parent_candidate=ref(P/'FROZEN.json'),source_patch=ref(source),parent_producer=ref(P/'source_snapshot/manifest.json'),parent_one_ulp_canonicalization=ref(P/'road_vertex_canonicalization.json'),source_faces=ids,original_triangles_xyz_m=old,replacement_triangles_xyz_m=new,union_area_m2=sum(area3(t)for t in old),proof='Convex four-vertex coplanar union, zero symmetric difference in double and float32 projections, identical exterior edges and exact Y21. Counts and all routes/fixtures unchanged.',source_bound_missing_wheel_xz_m=wheel,old_diagonal_distance_m=geo.point_segment_distance(wheel,*[xz(v)for v in common_old]),new_diagonal_distance_m=geo.point_segment_distance(wheel,*[xz(v)for v in common_new]),runtime_status='pending_original_controller_replay');write('coplanar_retriangulation.json',record);print('Exact coplanar diagonal flipped, area',record['union_area_m2'])
