"""Finite cluster regrade screening, retaining old private relief as evidence."""
import json,time
from . import author as a,native_clearance

def run():
 source=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/coherent_regrade_r01/BLOCK_007/ground_proposal.json';folder=a.HERE/'coherent_b07_r01';folder.mkdir(exist_ok=True);out=folder/'source_screen.json'
 if out.exists():raise SystemExit('Preserve screen')
 start=time.monotonic();d=json.loads(source.read_bytes());layout=native_clearance.require_ref(d['layout']);scene=a.load_scene();polys=[p for c in d['clusters']for p in c['ground_owner_polygons_xz_m']];index=a.TriangleIndex(scene,polys);rows=[]
 for c in d['clusters']:
  y=c['datum']['floor_y_m']
  for hid,p in zip(c['holding_ids'],c['ground_owner_polygons_xz_m']):
   pieces=list(index.covering(p));changes=[y-a.common.height(r['plane_y_xz_m'],q)for r in pieces for q in r['intersection_polygon_xz_m']];holes=[]
   for r in d['retirement_records']:
    q=a.clip(p,r['old_terrain_body_hole_polygon_xz_m'])
    if q:holes.append(dict(source_id=r['source_id'],area_m2=a.geo.polygon_area(q),old_floor_y_m=r['existing_finished_floor_y_m'],polygon_xz_m=q))
   missing=a.common.subtract([p],[r['intersection_polygon_xz_m']for r in pieces]+[h['polygon_xz_m']for h in holes]);rows.append(dict(id=hid,floor_y_m=y,polygon_xz_m=p,area_m2=a.geo.polygon_area(p),maximum_cut_m=max([-v for v in changes]+[0]),maximum_fill_m=max(changes+[0]),retired_holes=holes,unknown_hole_area_m2=sum(a.geo.polygon_area(q)for q in missing),unknown_holes_xz_m=missing,source_triangles=len(pieces)))
 result=dict(schema='riverstone.r17.coherent_cluster_screen.v1',base_scene_sha256=a.SCENE_SHA256,proposal=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),rows=rows,elapsed_s=time.monotonic()-start,policy='This measures proposed private regrading. Retained public/water/special boundaries, exterior closure, native supports and finite public profiles remain separate acceptance gates.',activation=False);out.write_text(json.dumps(result,separators=(',',':'))+'\n');print([{k:r[k]for k in('id','area_m2','maximum_cut_m','maximum_fill_m','unknown_hole_area_m2')}for r in rows]);print(a.sha(out))
if __name__=='__main__':run()
