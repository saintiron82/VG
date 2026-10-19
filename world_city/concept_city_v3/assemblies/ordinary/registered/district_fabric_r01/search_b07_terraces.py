"""Bounded native contour refit search for the two held upper B07 courts."""
from . import geometry as g
from .design import HERE as SOURCE
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as ta
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.bulk_grade_budget import height_part
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as tc

def run():
 src=SOURCE/'coherent_regrade_r01/BLOCK_007';l=g.load(src/'selected_layout.json');native=g.load(SOURCE/'contour_revision_r01/BLOCK_006/native_local.json')['assets'];scene=g.load(g.R7);idx=ta.TriangleIndex(scene,[h['holding_polygon_xz_m']for h in l['holdings']]);rows=g.load(g.CITY/'registered_topography/revisions/r17_district_batches/all_blocks_r01/retirement_candidates.json')['rows'];holes=[r for r in rows if r['source_id']in l['retired_source_ids']];print('hole keys',holes[0].keys(),flush=True);results=[]
 for hid in ['BLOCK_007:R8_C001']:
  h=next(h for h in l['holdings']if h['id']==hid);center=list(g.np.mean(h['holding_polygon_xz_m'],axis=0));old=[p for p in l['placements']if p['holding_id']==hid];yaw=old[0]['yaw_rad'];candidates=[]
  if hid.endswith('C001'):
   for dz in [2,2.5,3,3.5,4]:
    specs=[('working_r01_bank_joinery',[0,-8.75],0),('working_r01_market_lodging',[0,8.5-dz],g.math.pi)];core=[g.rect(-14.5,-3.5,14.5,3.5-dz)];candidates.append((dict(rear_shift_m=dz),specs,core,[8.75,9,9.25]))
  else:
   for z in [-8.25,-8,-7.75,-7.5]:
    specs=[('ordinary_r2_661e6b2a06cce8',[0,z],g.math.pi/2)];core=[g.rect(7.1,z-3,9.25,z+3)];candidates.append((dict(range_local_z_m=z),specs,core,[7,7.5,8,8.5,9]))
  for desc,specs,core,floors in candidates:
   feet=[];ps=[]
   for key,offset,rot in specs:
    c=g.xform(offset,center,yaw);n=native[key];q=g.transform(n['foundation_local_polygons_xz_m'],c,yaw+rot);feet+=q;ps.append(dict(asset_key=key,center_xz_m=c,yaw_rad=yaw+rot,footing_polygons_xz_m=q,roof_polygons_xz_m=g.transform(n['roof_local_polygons_xz_m'],c,yaw+rot)))
   courts=g.transform(core,center,yaw);req=feet+courts;rr=[r for q in req for r in idx.covering(q)];vals=[tc.height(r['plane_y_xz_m'],v)for r in rr for v in r['intersection_polygon_xz_m']]
   for floor in floors:
    cuts=[]
    for r in rr:
     for kw in [dict(low=floor+2.5+1e-7),dict(high=floor-2.5-1e-7)]:
      q=height_part(r['intersection_polygon_xz_m'],r['plane_y_xz_m'],**kw)
      if q:cuts.append(q)
    excess=sum(g.geo.polygon_area(q)for q in cuts);rec=dict(holding_id=hid,description=desc,floor_y_m=floor,native_placements=ps,core_court_polygons_xz_m=courts,required_visible_terrain_min_y_m=min(vals),required_visible_terrain_max_y_m=max(vals),visible_core_excess_area_m2=excess,visible_core_excess_polygons_xz_m=cuts);results.append(rec)
    print(hid,desc,floor,excess,min(vals),max(vals),flush=True)
 out=SOURCE/'b07_terrace_refit_r01';out.mkdir(exist_ok=True);g.write(out/'native_fit_search_r03.json',dict(base_scene=g.ref(g.R7),source_layout=g.ref(src/'selected_layout.json'),rows=results,status='Source geometry search only; retirement restoration heights, access and protected masks remain required.'))
if __name__=='__main__':run()
