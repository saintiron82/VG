"""Bounded exact side-road extension of the measured native causeway profile."""
import json,math,copy,time,collections
from . import screen as s
from ..north_junction_transition_r01.author import sha,ref,dump,fan
from .. import finite_geometry_r03 as g
from ...r17_district_batches import author as a
from world_city.concept_city_v3.registered_integration.r8 import finite_boundary_index as side
from world_city.concept_city_v3.registered_integration.r6 import merge_patches as merger
C=s.C.resolve();D=s.D.resolve();ROOT=C.parents[1]
def ref(path):
 path=path.resolve();return dict(path=str(path.relative_to(ROOT)),sha256=sha(path))
def bbox(poly):return [min(p[0]for p in poly),min(p[1]for p in poly),max(p[0]for p in poly),max(p[1]for p in poly)]
def cells(poly,pls):
 out=[]
 for i in [0,1]:
  q=s.half(poly,s.minus(pls[i],pls[1-i]))
  for j in [i,2,3]:
   p=q
   for k in [i,2,3]:
    if k!=j:p=s.half(p,s.minus(pls[k],pls[j]))
   if p and g.area(p)>g.MIN_AREA:out.append((p,pls[j],j))
 return out

def prepare():
 domains=[]
 for r,sign in zip(s.survey['interfaces'],[-1,1]):
  pls=s.sideplanes(sign,.066);u,v=r['source_polyline_tail_xz_m'][:2];dx,dz=v[0]-u[0],v[1]-u[1];L=math.hypot(dx,dz);pls.append([.12*dx/L,.12*dz/L,1-.12*(dx*u[0]+dz*u[1])/L])
  masks=g.union([g.clean(p)for p in r['finite_public_side_polygons_xz_m']if g.area(g.clean(p))>g.MIN_AREA])
  domains.append(dict(id=r['id'],source=r,polygons=masks,planes=pls))
 return domains

def main():
 start=time.monotonic();domains=prepare();sp=C/'evidence/r8_district_61_noble_r02_contracts_runtime/authored_scene.json';scene=json.loads(sp.read_bytes());idx=a.TriangleIndex(scene,[p for r in domains for p in r['polygons']]);print('indexed',len(idx.rows),time.monotonic()-start,flush=True)
 changes=collections.defaultdict(list);owners=[];gaps=[];support=[];stats=[]
 for d in domains:
  covered=[];local=[];area_old=0
  for mask in d['polygons']:
   for ri in idx.index.candidates(mask):
    r=idx.rows[ri];p=g.clip(mask,r['polygon_xz_m'])
    if not p:continue
    covered.append(p);area_old+=g.area(p)
    for q,pl,pi in cells(p,d['planes']):
     raised=s.half(q,s.minus(pl,r['plane_y_xz_m']))
     if not raised or g.area(raised)<=g.MIN_AREA or max(s.val(pl,v)-s.val(r['plane_y_xz_m'],v)for v in raised)<=1e-10:continue
     key=(r['material'],r['triangle_index']);changes[key].append(dict(polygon_xz_m=raised,plane_y_xz_m=pl,road_id=d['id'],plane_index=pi))
     local.append(dict(id=f'{d["id"]}:SOURCE:{r["material"]}:{r["triangle_index"]}:{len(local)}',road_id=d['id'],polygon_xz_m=raised,plane_y_xz_m=pl,material='road',source_scene_key=list(key),source_triangle_sha256=r['source_triangle_sha256'],maximum_raise_m=max(s.val(pl,v)-s.val(r['plane_y_xz_m'],v)for v in raised)))
  missing=g.subtract(d['polygons'],covered)
  upfaces=[]
  for r in d['source']['actual_native_support_quads_in_window']:
   q=r['world_quad_xyz_m'];u=[q[1][i]-q[0][i]for i in range(3)];v=[q[2][i]-q[0][i]for i in range(3)];ny=u[2]*v[0]-u[0]*v[2]
   if ny<=0:continue
   upfaces.append(dict(source=r,polygon_xz_m=[[v[0],v[2]]for v in q],y_m=q[0][1]))
  uncovered=g.subtract(missing,[r['polygon_xz_m']for r in upfaces]);gap_area=sum(g.area(p)for p in missing);unsupported_area=sum(g.area(p)for p in uncovered)
  for i,poly in enumerate(missing):
   for q,pl,pi in cells(poly,d['planes']):local.append(dict(id=f'{d["id"]}:SUPPORTED_APRON:{i}:{len(local)}',road_id=d['id'],polygon_xz_m=q,plane_y_xz_m=pl,material='road',source_kind='exact_native_apron_no_existing_terrain_top',maximum_raise_m=None))
  minclear=None
  for r in local:
   r['triangles_xyz_m']=fan(r['polygon_xz_m'],r['plane_y_xz_m'])
   for sf in upfaces:
    q=g.clip(r['polygon_xz_m'],sf['polygon_xz_m'])
    if q:
     clearance=min(s.val(r['plane_y_xz_m'],v)-sf['y_m']for v in q);minclear=clearance if minclear is None else min(minclear,clearance)
     support.append(dict(owner_id=r['id'],source_native_instance=sf['source']['instance'],group_index=sf['source']['group_index'],quad_index=sf['source']['quad_index'],polygon_xz_m=q,minimum_cover_m=clearance))
  gaps.append(dict(road_id=d['id'],no_old_top_polygons_xz_m=missing,unsupported_polygons_xz_m=uncovered,missing_old_top_area_m2=gap_area,unsupported_area_m2=unsupported_area))
  stats.append(dict(road_id=d['id'],domain_area_m2=sum(g.area(p)for p in d['polygons']),old_top_clip_area_m2=area_old,missing_old_top_area_m2=gap_area,unsupported_area_m2=unsupported_area,changed_area_m2=sum(g.area(r['polygon_xz_m'])for r in local),minimum_native_apron_cover_m=minclear,maximum_new_grade=max(math.hypot(*pl[:2])for pl in d['planes']),maximum_raise_m=max((r['maximum_raise_m']for r in local if r['maximum_raise_m']is not None),default=0)))
  owners+=local
 print('stats',stats,flush=True)
 dump(D/'profile_candidate.json',dict(status='FINITE_SOURCE_CANDIDATE_PENDING_TESTS',survey=ref(s.S),scene=ref(sp),domains=[{k:v for k,v in d.items()if k!='source'}for d in domains],statistics=stats,records=owners,gaps=gaps,apron_support_pieces=support))
 # Match original current triangles, replace their exact finite raised portions.
 index={(r['material'],r['triangle_index']):r for r in idx.rows};led=[]
 for key,parts in changes.items():
  src=index[key];remaining=g.subtract([src['polygon_xz_m']],[r['polygon_xz_m']for r in parts]);new=[t for p in remaining for t in fan(p,src['plane_y_xz_m'])]+[t for r in parts for t in fan(r['polygon_xz_m'],r['plane_y_xz_m'])]
  err=abs(g.area(src['polygon_xz_m'])-sum(g.area([[v[0],v[2]]for v in t])for t in new));assert err<1e-8,(key,err)
  led.append(dict(material=key[0],scene_triangle_index=key[1],source_triangle_sha256=src['source_triangle_sha256'],source_triangle_xyz_m=src['vertices_xyz_m'],replacement_triangles_xyz_m=[t for p in remaining for t in fan(p,src['plane_y_xz_m'])],retired_to_new_road_area_m2=sum(g.area(r['polygon_xz_m'])for r in parts),partition_error_m2=err))
 dump(D/'current_top_replacements.json',dict(source_scene=ref(sp),rows=led))
 outside=[dict(id=r['id'],polygon_xz_m=[[v[0],v[2]]for v in r['triangle_xyz_m']],plane_y_xz_m=r['plane_world_y_xz_m'])for r in s.profile['triangles']]
 bounds=side.interfaces(scene,idx,owners,outside);dump(D/'boundary_candidate.json',dict(sources=[ref(sp),ref(D/'profile_candidate.json'),ref(s.P)],**bounds));print('boundaries',{k:len(v)for k,v in bounds.items()if isinstance(v,list)},'seconds',time.monotonic()-start,flush=True)

if __name__=='__main__':main()
