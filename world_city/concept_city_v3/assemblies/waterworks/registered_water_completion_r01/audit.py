"""Hash-bound actual R7 water geometry audit; no scene mutation."""
import json,math,collections
from pathlib import Path
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.assemblies.waterworks.registered_services_r01.select_drawhouses import ribbon
from world_city.runtime_city.checks import placement as g
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[2];ROOT=a.ROOT
CONTRACT=CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json'
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=a.sha(p))
def write(name,obj):(HERE/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def pose(v,p):
 c,s=math.cos(p['yaw_rad']),math.sin(p['yaw_rad']);x,y,z=p['position_m'];return[x+c*v[0]+s*v[2],y+v[1],z-s*v[0]+c*v[2]]
class Index:
 def __init__(self):self.rows=[];self.ix=g._SpatialIndex(16)
 def add(self,t,**kw):
  poly=[[v[0],v[2]]for v in t]
  if a.normal_y(t)<=1e-10:return
  self.ix.add(len(self.rows),poly);self.rows.append(dict(polygon_xz_m=poly,plane_y_xz_m=a.common.plane(t),**kw))
 def covering(self,p):
  for i in self.ix.candidates(p):
   r=self.rows[i];q=g.convex_intersection(p,r['polygon_xz_m'])
   if g.polygon_area(q)>1e-8:yield r,a.common.clean(q)

def run():
 s=a.load_scene();c=json.loads(CONTRACT.read_text());wet=Index();dry=Index();native=Index();assets=[]
 for m,vs in s['surfaces'].items():
  if m=='water':continue
  for j in range(0,len(vs),3):
   t=vs[j:j+3]
   if a.normal_y(t)>1e-10:(wet if m=='bank' else dry).add(t,material=m,triangle_index=j//3,source_triangle_sha256=a.canonical_sha(t))
 print('terrain indexed',len(wet.rows),len(dry.rows),flush=True)
 for p in s['common_instances']:
  if not (p['source_pack']in('reservoir','port','southern_repair_r02')or p['id']in('MARKET_FOUNTAIN','TRAIN:water_trough:6')):continue
  asset=s['common_assets'][p['asset_key']];path=ROOT/asset['render_path'];assert a.sha(path)==asset['render_sha256'];r=json.loads(path.read_text());assets.append(dict(instance=p,source=ref(ROOT/asset['master_path']),cache=ref(path),bounds=r.get('bounds'),quad_count=r['quad_count']))
  for gi,group in enumerate(r['groups']):
   for qi,q in enumerate(group['quads']):
    v=[pose(v,p)for v in q]
    for tri in [v[:3],[v[0],v[2],v[3]]]:native.add(tri,instance_id=p['id'],asset_key=p['asset_key'],group_index=gi,quad_index=qi,material=group['material'])
 print('native indexed',len(native.rows),'assets',len(assets),flush=True)
 wr=[];vs=s['surfaces']['water']
 for j in range(0,len(vs),3):
  t=vs[j:j+3];p=[[v[0],v[2]]for v in t];plane=a.common.plane(t);covers=[];depths=[];owners=[]
  for index in(wet,native):
   for r,q in index.covering(p):
    ds=[a.common.height(plane,x)-a.common.height(r['plane_y_xz_m'],x)for x in q]
    if min(ds)<.05 or max(ds)>5:continue
    covers.append(q);depths+=ds;owners.append({k:v for k,v in r.items()if k not in('polygon_xz_m','plane_y_xz_m')})
  missing=a.common.subtract([p],covers);domains=[]
  for d in c['water_domain_polygons']:
   area=g.polygon_area(g.convex_intersection(p,d['polygon_xz_m']))
   if area>1e-6:domains.append(dict(surface_id=d['surface_id'],area_m2=area))
  wr.append(dict(water_triangle_index=j//3,source_triangle_sha256=a.canonical_sha(t),area_m2=g.polygon_area(p),domains=domains,bed_missing_area_m2=sum(g.polygon_area(q)for q in missing),bed_uncovered_polygons_xz_m=missing,minimum_support_depth_m=min(depths)if depths else None,maximum_support_depth_m=max(depths)if depths else None,bed_owners=owners))
 print('water scanned',sum(r['bed_missing_area_m2']for r in wr),flush=True)
 crossings=[]
 for road in c['roads']:
  for j,(u,v)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   if math.dist(u,v)<1e-8:continue
   rp=ribbon(u,v,road['width_m'])
   for k in range(0,len(vs),3):
    t=vs[k:k+3];wp=[[x[0],x[2]]for x in t];q=g.convex_intersection(rp,wp)
    if g.polygon_area(q)<.01:continue
    plane=a.common.plane(t);covers=[];owners=[];heads=[]
    for index in(dry,native):
     for r,qq in index.covering(q):
      ds=[a.common.height(r['plane_y_xz_m'],x)-a.common.height(plane,x)for x in qq]
      if min(ds)<.25:continue
      covers.append(qq);owners.append({k:v for k,v in r.items()if k not in('polygon_xz_m','plane_y_xz_m')});heads+=ds
    missing=a.common.subtract([q],covers)
    crossings.append(dict(road_id=road['id'],road_segment=j,water_triangle_index=k//3,water_domains=wr[k//3]['domains'],polygon_xz_m=q,area_m2=g.polygon_area(q),missing_deck_area_m2=sum(g.polygon_area(z)for z in missing),minimum_deck_above_water_m=min(heads)if heads else None,actual_deck_owners=owners))
 write('actual_geometry_audit.json',dict(schema='riverstone.actual_water_geometry_audit.v1',base_scene=ref(a.SCENE_PATH),water_contract=ref(CONTRACT),scope='Actual R7 faces including upward bank bed faces and exact native cache quads. Bed test proves projected underwater coverage, not physical simulation or containment by itself.',counts=dict(water_triangles=len(wr),bank_top_triangles=len(wet.rows),dry_top_triangles=len(dry.rows),native_top_triangles=len(native.rows),native_assets=len(assets)),water_triangles=wr,road_water_intersections=crossings,native_assets=assets))
 for r in crossings:
  print(r['road_id'],r['road_segment'],r['water_triangle_index'],round(r['area_m2'],2),round(r['missing_deck_area_m2'],2),r['minimum_deck_above_water_m'],sorted(set(o.get('instance_id',o.get('material'))for o in r['actual_deck_owners'])),flush=True)
if __name__=='__main__':run()
