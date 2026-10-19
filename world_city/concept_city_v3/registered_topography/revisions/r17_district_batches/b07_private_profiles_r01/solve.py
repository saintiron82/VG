"""Seven B07 source profiles against actual retained and canonical public planes."""
import json,math,time
from pathlib import Path
from .. import author as a
from ..bounded_profile_r01 import finite
from ..public_dependency_review_r01 import review
from ...public_corridors_r18 import public_domain
HERE=Path(__file__).resolve().parent
REQUEST=a.HERE/'entry_continuation_r01/b07_exact_public_reservations_r01.json'
LAYOUT=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/b07_terrace_refit_r02/BLOCK_007/selected_layout.json'
def write(path,data):
 assert not path.exists();path.write_text(json.dumps(data,separators=(',',':'))+'\n')
def run():
 req=json.loads(REQUEST.read_bytes());assert a.sha(LAYOUT)==req['source_layout']['sha256'];layout=json.loads(LAYOUT.read_bytes());assert a.sha(review.R04)==review.R04_SHA
 sources=json.loads(review.R18.read_bytes())['records'];si=review.indexed(sources);traffic=public_domain.records();ti=review.indexed(traffic);scene=json.loads(review.R04.read_bytes());ix=a.TriangleIndex(scene,[p for r in req['entries']for p in r['public_union_parts_xz_m']]);rows=[]
 for entry in req['entries']:
  hid=entry['holding_id'];path=HERE/(hid.replace(':','_')+'.json')
  if path.exists():output=json.loads(path.read_bytes())
  else:
   start=time.monotonic();requested=entry['public_union_parts_xz_m'];active=a.common.disjoint_union([q for p in requested for i in ti.candidates(p)if(q:=a.clip(p,traffic[i]['polygon_xz_m']))]);outside=a.common.subtract(requested,active);regions=[]
   for p in active:
    for i in si.candidates(p):
     s=sources[i];q=a.clip(p,s['polygon_xz_m'])
     if q:regions.append(dict(id=hid+':R18:'+str(len(regions)),source_kind='sealed_r18_finite_plane',source_record_id=s['id'],polygon_xz_m=q,plane_y_xz_m=s['plane_y_xz_m']))
   missing=a.common.subtract(active,[r['polygon_xz_m']for r in regions])
   for p in outside:
    tops=list(ix.covering(p));missing.extend(a.common.subtract([p],[r['intersection_polygon_xz_m']for r in tops]))
    for s in tops:regions.append(dict(id=hid+':R04:'+str(len(regions)),source_kind='actual_retained_r04_top',source_material=s['material'],source_triangle_index=s['triangle_index'],source_triangle_sha256=s['source_triangle_sha256'],polygon_xz_m=s['intersection_polygon_xz_m'],plane_y_xz_m=s['plane_y_xz_m']))
   holding=next(h for h in layout['holdings']if h['id']==hid);full=a.common.disjoint_union(holding['external_route_polygons_xz_m']);domains=a.common.subtract(full,[r['polygon_xz_m']for r in regions]);court=[]
   for h in layout['holdings']:
    masks=h.get('ground_owner_polygons_xz_m',[h['holding_polygon_xz_m']])
    for j,p in enumerate(masks):
     if any(a.clip(p,q)for q in full):court.append(dict(id=h['id']+':COURT:'+str(j),polygon_xz_m=p,plane_y_xz_m=[0,0,h['floor_y_m']]))
   area=sum(a.geo.polygon_area(p)for p in missing)
   if area>1e-7:res=dict(status='HELD_UNCOVERED_PUBLIC_OWNER',uncovered_area_m2=area)
   else:
    try:res=finite.solve(domains,court+regions,lambda p:holding['floor_y_m'],pitch=1.,seam_points=[p for r in regions for p in r['polygon_xz_m']])
    except Exception as e:res=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
   output=dict(holding_id=hid,source_holding=holding,private_domain_polygons_xz_m=domains,court_fixed_regions=court,public_fixed_regions=regions,public_uncovered_polygons_xz_m=missing,result=res,source_refs=[dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))for p in[REQUEST,LAYOUT,review.R18,review.R04]],elapsed_s=time.monotonic()-start,activation=False);write(path,output)
  brief=dict(holding_id=hid,status=output['result']['status'],maximum_gradient=output['result'].get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path),elapsed_s=output['elapsed_s']);rows.append(brief);print(brief,flush=True)
 write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
