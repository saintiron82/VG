"""Exact existing cap-edge records outside the enlarged public-junction union."""
import importlib.util,math,pathlib,sys,json
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('junction_build',H/'build.py');b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b)
g=b.geo

def intersections(p,q,a,c):
 u=[q[i]-p[i]for i in(0,1)];v=[c[i]-a[i]for i in(0,1)];d=u[0]*v[1]-u[1]*v[0]
 if abs(d)<1e-12:return []
 w=[a[i]-p[i]for i in(0,1)];t=(w[0]*v[1]-w[1]*v[0])/d;s=(w[0]*u[1]-w[1]*u[0])/d
 return[t]if -1e-10<=t<=1+1e-10 and -1e-10<=s<=1+1e-10 else[]

def main():
 d=b.read(H/'junction_extensions.json');v=b.read(H/'verification.json');prior=b.read(b.B/'public_corridor_priorities_r01/priorities.json');inv=b.read(b.B/'primary_inventory/inventory.json');roads={r['id']:b.Road(r)for r in inv['roads']};parts=[p for rid in prior['minimum_public_ground_corridors']for p in roads[rid].polys]+[p for r in d['extensions']for p in r['polygons_xz_m']];ix=g._SpatialIndex(8)
 for i,p in enumerate(parts):ix.add(i,p)
 caps=[r for r in v['cap_classification']if r['not_already_in_regeneration_area_m2']>1e-7];scene=b.a.load_scene();index=b.a.TriangleIndex(scene,[r['original_end_cap_polygon_xz_m']for r in caps]);records=[];segments=[]
 for cap in caps:
  poly=cap['original_end_cap_polygon_xz_m'];center=[sum(p[i]for p in poly)/len(poly)for i in(0,1)]
  for ei,(p,q)in enumerate(zip(poly,poly[1:]+poly[:1])):
   knots=[0.,1.];near=ix.candidates([p,q])
   for i in near:
    pp=parts[i]
    for aa,cc in zip(pp,pp[1:]+pp[:1]):knots+=intersections(p,q,aa,cc)
   k=[]
   for t in sorted(max(0,min(1,t))for t in knots):
    if not k or t-k[-1]>1e-9:k.append(t)
   for j,(lo,hi)in enumerate(zip(k,k[1:])):
    aa=b.point(p,q,lo);cc=b.point(p,q,hi);mid=b.point(aa,cc,.5);vec=[mid[i]-center[i]for i in(0,1)];length=math.hypot(*vec);outside=[mid[i]+vec[i]*1e-5/length for i in(0,1)]
    if any(g.point_in_convex_polygon(outside,parts[i],1e-10)for i in near):continue
    profile=b.profile(index,aa,cc);rid=cap['extension_id']+':CAP:'+str(ei)+':'+str(j);row=dict(id=rid,road_id=cap['road_id'],endpoint=cap['endpoint'],profile=profile,status='VALID_EXISTING_OUTER_CAP_PROFILE'if profile['valid']else'UNRESOLVED_EXISTING_CAP_GEOMETRY');records.append(row)
    if profile['valid']:
     for ii,(x,y)in enumerate(zip(profile['knots_xyz_m'],profile['knots_xyz_m'][1:])):segments.append(dict(id=rid+':'+str(ii),xyz_m=[x,y],road_id=cap['road_id'],source_cap_record_id=rid))
 out=dict(input=b.ref(H/'junction_extensions.json'),cap_verification=b.ref(H/'verification.json'),records=records,valid_fixed_cap_segments=segments,unresolved_cap_ids=[r['id']for r in records if not r['profile']['valid']],scope='Cap edges are actual original canonical round-join boundaries outside the enlarged traffic union. Invalid old profiles are evidence only, never frozen constraints.')
 b.write('cap_boundary_profiles.json',out);print(json.dumps(dict(report=b.ref(H/'cap_boundary_profiles.json'),records=len(records),segments=len(segments),unresolved=len(out['unresolved_cap_ids']))))
if __name__=='__main__':main()
