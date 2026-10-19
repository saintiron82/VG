"""Retained native court/floor surfaces and exact walking-height bodies.
Read-only support evidence; this does not add duplicate terrain to the city.
"""
from resolve_pack import *
SELECT=('registered_property_r1_','registered_precinct_union_','registered_training_r09_recovered_','registered_castle_court','registered_institutional_site_common_')

def main():
 source=load(HERE/'actual_native_projection.json');scene=terrain.load_scene();r=np.load(HERE/'terrain_raster.npz');h=r['height'].copy();g=r['grade'].copy();obstacle=np.zeros(b.SHAPE,bool);walktris=[];triowners=[];assetrows={};rows=[]
 for p in source['instances']:
  key=p['asset_key'];selected=key.startswith(SELECT)
  if not selected:obstacle|=b.mask(p['native_parts_xz_m']);continue
  a=source['assets'][key]
  if key not in assetrows:
   mesh=load(ROOT/a['cache']['path']);body=slab_rectangles(mesh,.01,2.2);tops=horizontal(mesh,0,True);assetrows[key]={'body':body,'tops':tops,'source':a['source'],'cache':a['cache']}
  ar=assetrows[key];obstacle|=b.mask([b.xform(q,p)for q in ar['body']]);ps=[b.xform(q,p)for q in ar['tops']];w=b.mask(ps);height=p['position_m'][1];valid=w&(~np.isfinite(h)|(abs(h-height)<.05));h[valid]=height;g[valid]=0
  for q in ps:
   for tri in terrain.fan_upward([[v[0],height,v[1]]for v in q]):triowners.append({'native_instance_id':p['id'],'asset_key':key,'cache':ar['cache'],'native_floor_y_m':height});walktris.extend(tri)
  rows.append({'id':p['id'],'asset_key':key,'floor_y_m':height,'native_walk_parts_xz_m':ps,'walking_body_parts_xz_m':[b.xform(q,p)for q in ar['body']],'floor_area_m2':sum(geo.polygon_area(q)for q in ps)})
 np.savez_compressed(HERE/'native_walk_raster.npz',height=h,grade=g,obstacle=obstacle);write('native_walk_support.json',{'scene':ref(terrain.SCENE_PATH),'instances':rows,'source_assets':assetrows,'triangles_xyz_m':walktris,'triangle_owners':triowners,'policy':'Actual native upward faces at instance localY=0 of explicitly selected existing court/infrastructure families; exact occupied2.2m slab replaces their full-floor collision envelope. Other native instances remain fully reserved. Never applied as scene terrain.','summary':{'instances':len(rows),'triangles':len(walktris)//3}});print('nativewalk',len(rows),len(walktris)//3)
if __name__=='__main__':main()

class CompositeSupportIndex:
 def __init__(self,scene,windows):
  self.ground=terrain.TriangleIndex(scene,windows);native=load(HERE/'native_walk_support.json');self.native=terrain.TriangleIndex({'surfaces':{'retained_native_floor':native['triangles_xyz_m']}},windows)
 def covering(self,poly):
  rows=list(self.ground.covering(poly));claimed=[r['intersection_polygon_xz_m']for r in rows]
  for row in rows:yield row
  # Existing terrain is canonical where already present. Native cached floor
  # faces are support owners only in actual terrain holes; no fake new surface.
  for r in self.native.covering(poly):
   for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
    if geo.polygon_area(q)>1e-8:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)
