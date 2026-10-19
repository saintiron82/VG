import sys,pathlib,json,math
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import author as s, approaches as a,landings as l
f=json.loads((H/'targeted_original_endpoint_failures.json').read_text())['failures'][0];p,q=[[v[0],v[2]] for v in f['edge_xyz_m']];near=[]
for i in l.INDEX.candidates([[p[0]-.01,p[1]-.01],[p[0]+.01,p[1]+.01]]):
 r=l.TRIANGLES[i];poly=r['polygon_xz_m'];distance=min(a.review.prior.base._project(*p,u,v)[0] for u,v in zip(poly,poly[1:]+poly[:1]));near.append((distance,i))
near.sort();out=dict(endpoint=p,edge_length_m=math.dist(p,q),nearest_triangles=[dict(distance_m=d,index=i,record=l.TRIANGLES[i]) for d,i in near[:5]],edge_samples=[])
for t in [0,1e-8,1e-7,1e-6,1e-5,.0001,.001,.01,.1,.5,1]:
 pt=[p[k]+t*(q[k]-p[k]) for k in (0,1)];indices=[i for i in sorted(l.INDEX.candidates([pt])) if a.geo.point_in_convex_polygon(pt,l.TRIANGLES[i]['polygon_xz_m'],1e-7)];o=s.owner_at(*(pt[k]+f['normal_xz_m'][k] for k in (0,1)))
 out['edge_samples'].append(dict(t=t,p=pt,landing_triangles=indices,outward_owner_id=o['owner_id'],outward_kind=o['kind'],road_y=a.review.road_height_at('MARKET_CONTOUR',*pt)))
(H/'finite_gap_measurement.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='nearest_triangles'},indent=2));print('nearest',near[:5])
