"""One shared actual-plane index for city-wide coherent court screening."""
import json,math,time
from . import author as a,native_clearance,side_clearance

def height_part(poly,plane,low=None,high=None):
 q=[[x,a.common.height(plane,[x,z]),z]for x,z in poly]
 if low is not None:q=side_clearance.halfspace(q,lambda v:v[1]-low)
 if high is not None:q=side_clearance.halfspace(q,lambda v:high-v[1])
 return a.common.clean([[v[0],v[2]]for v in q])
def run():
 folder=a.HERE/'city_coherent_budget_r01';folder.mkdir(exist_ok=True);out=folder/'terrain_budget.json'
 if out.exists():raise SystemExit('Preserve budget')
 t0=time.monotonic();path=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/coherent_regrade_r01/bulk_placements.json';bulk=json.loads(path.read_bytes());districts=[];windows=[]
 for district in bulk['districts']:
  proposal=native_clearance.require_ref(district['ground_proposal']);layout=native_clearance.require_ref(proposal['layout']);districts.append((district,proposal,layout));windows.extend(h['holding_polygon_xz_m']for h in layout['holdings'])
 index=a.TriangleIndex(a.load_scene(),windows);rows=[]
 for district,proposal,layout in districts:
  for h in layout['holdings']:
   p=h['holding_polygon_xz_m'];floor=h['floor_y_m'];pieces=list(index.covering(p));extrema=[a.common.height(r['plane_y_xz_m'],q)for r in pieces for q in r['intersection_polygon_xz_m']];area=a.geo.polygon_area(p);coverage=[r['intersection_polygon_xz_m']for r in pieces];retired=[]
   for r in proposal['retirement_records']:
    q=a.clip(p,r['old_terrain_body_hole_polygon_xz_m'])
    if q:retired.append(dict(source_id=r['source_id'],polygon_xz_m=q,old_floor_y_m=r['existing_finished_floor_y_m']))
   unknown=a.common.subtract([p],coverage+[r['polygon_xz_m']for r in retired]);hi=[];lo=[];weighted=[]
   for r in pieces:
    poly=r['intersection_polygon_xz_m'];plane=r['plane_y_xz_m'];q=height_part(poly,plane,low=floor+2.5)
    if q:hi.append(q)
    q=height_part(poly,plane,high=floor-2.5)
    if q:lo.append(q)
    ar=a.geo.polygon_area(poly);c=[sum(v[k]for v in poly)/len(poly)for k in(0,1)];weighted.append((a.common.height(plane,c),ar))
   total=sum(w for _,w in weighted);quantiles={}
   for fraction in(.1,.25,.5,.75,.9):
    s=0.
    for y,w in sorted(weighted):
     s+=w
     if s>=total*fraction:quantiles[str(fraction)]=y;break
   route=h.get('external_route',[]);length=sum(math.dist(u,v)for u,v in zip(route,route[1:]));public=h.get('public_target_evidence',{});public_y=public.get('y_m');rows.append(dict(id=h['id'],block_id=district['block_id'],floor_y_m=floor,holding_polygon_xz_m=p,area_m2=area,actual_source_min_y_m=min(extrema,default=None),actual_source_max_y_m=max(extrema,default=None),maximum_cut_m=max([y-floor for y in extrema]+[0]),maximum_fill_m=max([floor-y for y in extrema]+[0]),weighted_centroid_height_quantiles_m=quantiles,cut_over_2_5m_polygons_xz_m=hi,fill_over_2_5m_polygons_xz_m=lo,cut_over_2_5m_area_m2=sum(a.geo.polygon_area(q)for q in hi),fill_over_2_5m_area_m2=sum(a.geo.polygon_area(q)for q in lo),unknown_hole_area_m2=sum(a.geo.polygon_area(q)for q in unknown),unknown_holes_xz_m=unknown,retired_hole_parts=retired,entry_length_m=length,selected_public_anchor_y_m=public_y,minimum_centerline_grade=abs(floor-public_y)/length if public_y is not None and length else None,status='REASSIGN_TERRACE_OR_RESHAPE_PARCEL'if hi or lo else'MODEST_FINITE_REGRADE_SOURCE_CANDIDATE'))
 summary={}
 for d,_,_ in districts:
  rr=[r for r in rows if r['block_id']==d['block_id']];summary[d['block_id']]=dict(holdings=len(rr),modest=sum(r['status']=='MODEST_FINITE_REGRADE_SOURCE_CANDIDATE'for r in rr),contour_reassignment=sum(r['status']!='MODEST_FINITE_REGRADE_SOURCE_CANDIDATE'for r in rr),area_m2=sum(r['area_m2']for r in rr),maximum_cut_m=max(r['maximum_cut_m']for r in rr),maximum_fill_m=max(r['maximum_fill_m']for r in rr))
 result=dict(schema='riverstone.r17.city_coherent_terrain_budget.v1',base_scene_sha256=a.SCENE_SHA256,bulk_source=dict(path=str(path.relative_to(a.ROOT)),sha256=a.sha(path)),district_sources=[d['ground_proposal']for d,_,_ in districts],rows=rows,summary=summary,actual_indexed_triangles=len(index.rows),elapsed_s=time.monotonic()-t0,screening_policy='The 2.5 m cut/fill flag is an explicit design-review threshold for preserving the concept hill, not a traversal or structural approval. Weighted centroid quantiles are datum suggestions, not exact area quantiles. Public/native/water boundaries and actual finite profile/side proofs remain mandatory.',activation=False);out.write_text(json.dumps(result,separators=(',',':'))+'\n');print(summary);print('seconds',result['elapsed_s']);print(a.sha(out))
if __name__=='__main__':run()
