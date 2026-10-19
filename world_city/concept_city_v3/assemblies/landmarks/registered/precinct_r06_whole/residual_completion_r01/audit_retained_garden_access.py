"""Exact retained garden internal and exterior walks, with real cemetery floor."""
from pathlib import Path
import sys,json,time
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
from native_walks import CompositeSupportIndex
OUT=Path(__file__).resolve().parent

class GardenSupportIndex:
 def __init__(self,scene,windows):
  self.base=CompositeSupportIndex(scene,windows);projection=load(BASE/'actual_native_projection.json');vs=[]
  for p in projection['instances']:
   if not p['asset_key'].startswith(('registered_institutional_site_cemetery_','registered_institutional_site_clergy_','registered_institutional_site_monastery_')):continue
   mesh=load(ROOT/projection['assets'][p['asset_key']]['cache']['path'])
   for q in horizontal(mesh,0,True):
    for tri in terrain.fan_upward([[v[0],p['position_m'][1],v[1]]for v in b.xform(q,p)]):vs.extend(tri)
  self.native=terrain.TriangleIndex({'surfaces':{'retained_institutional_garden_floor':vs}},windows)
 def covering(self,p):
  rows=list(self.base.covering(p));claimed=[r['intersection_polygon_xz_m']for r in rows]
  yield from rows
  for r in self.native.covering(p):
   for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
    if geo.polygon_area(q)>1e-8:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)

def main():
 t=time.monotonic();src=CITY/'assemblies/landscape/registered/resolved_placements.json';pack=load(src);routes=[r for r in pack['external_connections']if 'ribbon_polygons_xz_m'in r];routes+=pack['internal_routes'];windows=[q for r in routes for q in r['ribbon_polygons_xz_m']];scene=terrain.load_scene();support=GardenSupportIndex(scene,windows);sides=SideIndex(scene,windows);projection=load(BASE/'actual_native_projection.json');native=[];cache={}
 for p in projection['instances']:
  # Only local walk-height solids obstruct each site floor. Floor surfaces at
  # zero and high roofs are tested through support/headroom rather than AABBs.
  key=p['asset_key'];a=projection['assets'][key]
  if key not in cache:cache[key]=slab_rectangles(load(ROOT/a['cache']['path']),.01,2.2)
  native.extend({'id':p['id'],'asset':key,'floor_y_m':p['position_m'][1],'polygon_xz_m':b.xform(q,p)}for q in cache[key])
 ni=geo._SpatialIndex(16)
 for i,p in enumerate(native):ni.add(i,p['polygon_xz_m'])
 graphs={name:load(BASE/f'entry_graph_{name}.json')for name in('cathedral','monastery')};out=[]
 for r in routes:
  site=next((s for s in pack['sites']if r['id'].startswith(s['id']+':')),None)
  if site is None:continue
  floor=r.get('finished_floor_y_m',site['floor']);checks=[terrain.audit_polygon(support,q,floor)for q in r['ribbon_polygons_xz_m']];contacts=[]
  for q in r['ribbon_polygons_xz_m']:
   for i in ni.candidates(q):
    n=native[i]
    if abs(n['floor_y_m']-floor)>.05:continue
    ar=geo.intersection_area(q,n['polygon_xz_m'])
    if ar>1e-7:contacts.append({'native_id':n['id'],'area_m2':ar})
  sc=sides.audit([{'id':r['id'],'polygon_xz_m':q,'floor_y_m':floor}for q in r['ribbon_polygons_xz_m']]);binding=None
  if r in pack['external_connections']:
   group='cathedral'if r['id'].startswith('CLERGY')else'monastery';graph=graphs[group];point=r['polyline_xz_m'][-1];seeds=[i for i,row in enumerate(graph['rows'])if geo.point_in_convex_polygon(point,row['polygon_xz_m'])and str(i)in graph['parent']];chain=[]
   if seeds:
    i=seeds[0]
    while i is not None:chain.append(i);i=graph['parent'][str(i)]
   named=[s for s in graph['road_seams']if chain and geo.intersection_area(graph['rows'][chain[-1]]['polygon_xz_m'],s['polygon_xz_m'])>1e-8];binding={'graph_source':ref(BASE/f'entry_graph_{group}.json'),'status':'PASS'if named else'NO_NAMED_CONTINUATION','actual_terminal_triangle_ids':[graph['rows'][i]['triangle_index']for i in seeds],'continuation_triangle_ids':[graph['rows'][i]['triangle_index']for i in chain],'named_public_road_ids':sorted({s['road_id']for s in named})}
  row={'id':r['id'],'source_route':r,'floor_y_m':floor,'surface_checks':checks,'native_contacts':contacts,'bank_contacts':sc['contacts'],'public_binding':binding,'support_native_bank_pass':all(c['passes_existing_surface']for c in checks)and not contacts and not sc['contacts']};out.append(row);print(r['id'],row['support_native_bank_pass'],'missing',sum(c['missing_area_m2']for c in checks),'native',len(contacts),'bank',len(sc['contacts']),binding['status']if binding else'',flush=True)
 report={'source':ref(src),'scene':ref(terrain.SCENE_PATH),'routes':out,'summary':{'routes':len(out),'static_pass':sum(r['support_native_bank_pass']for r in out),'seconds':time.monotonic()-t},'runtime_player_pass':False,'method':'Exact actual top support; actual native occupied .01–2.2 m slab and finite bank clearance. Retained cemetery floor is actual local Y0 mesh, never new fake terrain.'};(OUT/'retained_garden_access_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(report['summary'])
if __name__=='__main__':main()
