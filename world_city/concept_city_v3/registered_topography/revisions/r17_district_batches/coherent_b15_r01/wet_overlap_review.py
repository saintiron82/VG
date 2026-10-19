import json,collections
from .. import author as a
from .source_preflight import HERE,read,write

def run():
 scene=a.load_scene();wet=scene['terrain_contract']['water_domain_polygons'];wi=a.geo._SpatialIndex(16)
 for i,w in enumerate(wet):wi.add(i,w['polygon_xz_m'])
 hand=read('terrain_handoff.json');rows=[]
 for parcel in hand['parcels']:
  for kind in('footing_polygons_xz_m','walk_polygons_xz_m','court_polygons_xz_m','whole_holding_polygons_xz_m'):
   for j,p in enumerate(parcel[kind]):
    for k in wi.candidates(p):
     w=wet[k];q=a.clip(p,w['polygon_xz_m'])
     if q and a.geo.polygon_area(q)>1e-7:rows.append(dict(owner_id=parcel['id'],kind=kind,polygon_index=j,water_id=w['surface_id'],polygon_xz_m=q,area_m2=a.geo.polygon_area(q),floor_y_m=parcel['floor_y_m']))
 summary={}
 for r in rows:summary.setdefault(r['owner_id'],collections.defaultdict(float))[r['kind']]+=r['area_m2']
 result=dict(base_scene_sha256=a.SCENE_SHA256,contacts=rows,area_sum_by_owner_kind_m2=summary,note='Area sums retain overlapping source ribbon records and are not a union area. Exact contact polygons are authoritative. Water ownership is unchanged.',activation=False);write('wet_overlap_review.json',result);print(summary);print(a.sha(HERE/'wet_overlap_review.json'))
if __name__=='__main__':run()
