"""Exact render-derived bearing masks and protected-space checks for six placements."""
from .author import *
from ..access import ribbons,circle

def downward(r):
 out=[]
 for gi,g in enumerate(r['groups']):
  for qi,q in enumerate(g['quads']):
   if max(v[1]for v in q)-min(v[1]for v in q)>1e-8 or q[0][1]>1e-8:continue
   u=[q[1][k]-q[0][k]for k in range(3)];v=[q[2][k]-q[1][k]for k in range(3)];ny=u[2]*v[0]-u[0]*v[2]
   if ny>=-1e-9:continue
   out.append(dict(group_index=gi,quad_index=qi,material=g['material'],bottom_y_local_m=q[0][1],polygon_local_xz_m=[[v[0],v[2]]for v in q]))
 return out

def run():
 s=load(HERE/'source_plan.json');assets={**load(HERE/'compile_report.json')['assets'],**s['reused_assets']};courts={c['id']:c for c in s['courts']};placements=[];bearings=[];conflicts=[];collision_proofs=[]
 access=load(PARENT/'access_handoff.json');protected=[dict(id=r['id'],kind='entrance_or_public_lane',polygons=r['ribbon_and_join_polygons_xz_m'])for r in access['internal_routes']+access['external_routes']]
 for c in s['courts']:protected.append(dict(id=c['id']+':PRESERVED_LINK',kind='court_link',polygons=c['source']['access_link']['ribbon_and_join_polygons_xz_m']))
 link=[[234.75,180.75],[235.25,181.75]];protected.append(dict(id='BANK_DRY_WORK_COURT:FINITE_CONNECTOR',kind='court_link_correction',polyline_xz_m=link,width_m=2,polygons=ribbons(link,2)+[circle(link[0],2),circle(link[1],2)]))
 for p0 in s['placements']:
  p=copy.deepcopy(p0);c=courts[p['court_id']];p['local_component_id']=p['id'];p['id']=p['court_id']+':'+p['local_component_id'];a=assets[p['asset_key']];r=load(ROOT/a['render_path']);assert ref(ROOT/a['render_path'])['sha256']==a['render_sha256'];world=xform(p['local_center_xz_m'],c['center'],c['yaw']);p.update(position_m=[world[0],2.5,world[1]],yaw_rad=c['yaw']+p['local_yaw_rad'],scale=[1,1,1],holding_id=c['source']['holding_id'],palette_id='native_court_timber_and_stone',palette_override={})
  def worldpoly(poly):return [xform(v,world,p['yaw_rad'])for v in poly]
  polys=slab_rectangles(r,-.251,3);p['native_collision_polygons_xz_m']=[worldpoly(q)for q in polys];p['native_collision_local_polygons_xz_m']=polys;p['bearing_ids']=[]
  for j,b in enumerate(downward(r)):
   poly=worldpoly(b['polygon_local_xz_m']);bid=p['id']+':BEARING:'+str(j);b.update(id=bid,placement_id=p['id'],court_id=p['court_id'],polygon_xz_m=poly,required_ground_hole_y_m=2.5+b['bottom_y_local_m'],original_ground_y_m=2.5,embed_depth_m=-b['bottom_y_local_m'],requires_finite_terrain_cut=b['bottom_y_local_m']<0,render_sha256=a['render_sha256'],bearing_definition='Actual downward-facing native render quad at or below original court ground; footprint is not a bounding box');bearings.append(b);p['bearing_ids'].append(bid)
  for q in p['native_collision_polygons_xz_m']:
   if abs(geo.polygon_area(q)-geo.intersection_area(q,c['source']['polygon_xz_m']))>1e-7:conflicts.append(dict(placement=p['id'],kind='outside_court',area=geo.polygon_area(q)-geo.intersection_area(q,c['source']['polygon_xz_m'])))
   for rr in protected:
    for qq in rr['polygons']:
     area=geo.intersection_area(q,qq)
     if area>1e-7:conflicts.append(dict(placement=p['id'],route=rr['id'],kind='protected_route',area_m2=area))
  placements.append(p)
 for i,p in enumerate(placements):
  for q in placements[i+1:]:
   if p['court_id']!=q['court_id']:continue
   rp=load(ROOT/assets[p['asset_key']]['render_path']);rq=load(ROOT/assets[q['asset_key']]['render_path']);ys=sorted({v[1]for r in(rp,rq)for g in r['groups']for face in g['quads']for v in face});volume=0
   for y0,y1 in zip(ys,ys[1:]):
    pp=transformed(slab_rectangles(rp,y0,y1),p['local_center_xz_m'],p['local_yaw_rad']);qp=transformed(slab_rectangles(rq,y0,y1),q['local_center_xz_m'],q['local_yaw_rad']);volume+=(y1-y0)*sum(geo.intersection_area(a,b)for a in pp for b in qp)
   collision_proofs.append(dict(placements=[p['id'],q['id']],native_volume_overlap_m3=volume))
   if volume>1e-8:conflicts.append(dict(kind='native_mutual_overlap',placements=[p['id'],q['id']],volume_m3=volume))
 out=dict(schema='riverstone.court_phase01.resolved.v1',status='Staged pending final checks and composed R16 support',source_plan=ref(HERE/'source_plan.json'),compile_report=ref(HERE/'compile_report.json'),assets=assets,placements=placements,protected_routes=protected,conflicts=conflicts,native_mutual_collision_proofs=collision_proofs,replaced_placement_ids=[],no_native_paving=True,summary=dict(placements=len(placements),new_sources=4,cached_sources=2,native_quads=sum(a['quad_count']for a in assets.values()),bearing_faces=len(bearings),terrain_cut_faces=sum(b['requires_finite_terrain_cut']for b in bearings),finite_cut_area_m2=sum(geo.polygon_area(b['polygon_xz_m'])for b in bearings if b['requires_finite_terrain_cut']),conflicts=len(conflicts)))
 write(HERE/'resolved_placements.json',out);h=dict(schema='riverstone.court_phase01.terrain_handoff.v1',corrected_r6=ref(R6),placement_pack=ref(HERE/'resolved_placements.json'),owner='R16 court triangle material split; compose these finite native bearing cuts with court regions before sealing',native_bearing_owners=bearings,no_whole_court_exclusion=True,no_native_paving=True,protected_routes=protected,court_finished_ground_y_m=2.5,requires_dependent_revalidation=bool(conflicts));write(HERE/'terrain_handoff.json',h);print(json.dumps(out['summary'],indent=2));print(json.dumps(conflicts,indent=2)[:6000]);return out
if __name__=='__main__':run()
