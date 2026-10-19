import json,math,collections,time
from .height_field import HERE
from . import finite_geometry_r03 as g
from .classify_top_holes_r02 import a,b,ref

def main():
 start=time.monotonic();rp=HERE/'north_mask_restoration_r02_candidate.json';d=json.loads(rp.read_bytes());polys=d['uncovered_polygons_xz_m'];sp=a.CITY/'evidence/r8_district_r04/scene.json';scene=json.loads(sp.read_bytes());idx=a.geo._SpatialIndex(4)
 for i,p in enumerate(polys):idx.add(i,p)
 rows=[];refs=[ref(rp),ref(sp)];summary=collections.defaultdict(float)
 for inst in scene['common_instances']:
  if not inst['id'].startswith('BRIDGE_MAIN_RIVER'):continue
  asset=scene['common_assets'][inst['asset_key']];p=a.ROOT/asset['render_path'];assert a.sha(p)==asset['render_sha256'];render=json.loads(p.read_bytes());refs.append(ref(p))
  for gi,group in enumerate(render['groups']):
   for qi,quad in enumerate(group['quads']):
    world=[b.transform(v,inst)for v in quad]
    if a.normal_y(world[:3])<=1e-12:continue
    poly=[[v[0],v[2]]for v in world]
    for i in idx.candidates(poly):
     q=g.clip(poly,polys[i])
     if not q:continue
     row=dict(native_instance_id=inst['id'],asset_key=inst['asset_key'],quad=[gi,qi],material=group.get('material'),polygon_xz_m=q,plane_y_xz_m=a.common.plane(world[:3]),area_m2=g.area(q));rows.append(row);summary[inst['id']]+=row['area_m2']
 coverage=g.union([r['polygon_xz_m']for r in rows]);left=g.subtract(polys,coverage);out=dict(status='NATIVE_PROJECTION_DIAGNOSTIC_NOT_WALKING_OWNER_APPROVAL',sources=refs,rows=rows,summary=dict(summary),uncovered_after_all_native_upface_projection_xz_m=left,uncovered_after_native_projection_area_m2=math.fsum(g.area(p)for p in left),seconds=time.monotonic()-start);op=HERE/'north_residual_native_projection_r01.json';op.write_text(json.dumps(out,separators=(',',':'))+'\n');print(out['summary'],out['uncovered_after_native_projection_area_m2'],out['seconds'],ref(op))
if __name__=='__main__':main()
