"""Small clear working fronts selected from actual remaining court space."""
from .resolve import *
def run():
 s=load(HERE/'source_plan.json');p=load(HERE/'resolved_placements.json');rows=[]
 choices=[('WASH_FRONT',0,[-3.5,-.5,-2,.5],[-2.75,0],'Hand-filled shared washing; barrel serves the vessel, no connected water system'),('DRYING_FRONT',0,[-2.25,.5,-1.25,1.375],[-1.75,.9375],'Reachable cloth front; center of court retained for approach'),('DRY_WORK_FRONT',1,[-1.5,1.375,-.5,2],[-1,1.6875],'Compact clear standing/reaching strip at the shared bench and closed tool chest; spare timber stored behind')]
 for id,ci,box,target,role in choices:
  c=s['courts'][ci];poly=transformed([rect(*box)],c['center'],c['yaw'])[0];line=transformed([[[0,0],target]],c['center'],c['yaw'])[0];rs=ribbons(line,.6)+[circle(line[0],.6),circle(line[1],.6)];ps=[q for z in p['placements']if z['court_id']==c['id']for q in z['native_collision_polygons_xz_m']]
  assert all(geo.intersection_area(q,r)<1e-7 for q in [poly]+rs for r in ps)
  assert all(abs(geo.polygon_area(q)-geo.intersection_area(q,c['source']['polygon_xz_m']))<1e-7 for q in [poly]+rs)
  assert all(geo.intersection_area(poly,qq)<1e-7 for r in p['protected_routes']for qq in r['polygons'])
  rows.append(dict(id=id,court_id=c['id'],role=role,clear_workfront_polygon_xz_m=poly,clear_workfront_area_m2=geo.polygon_area(poly),approach_centerline_xz_m=line,approach_width_m=.6,approach_polygons_xz_m=rs,native_obstacle_overlap_area_m2=0,workfront_protected_route_overlap_area_m2=0,access_status='Finite source working-front approach only; not capsule, accessibility, occupancy or animated-use approval'))
 openings=[]
 for key in('domestic_boundary','work_boundary'):
  a=p['assets'][key];m=load(ROOT/a['master_path']);openings.append(dict(asset_key=key,native_source=ref(ROOT/a['master_path']),segments=m['extensions']['boundary_segments'],openings=m['extensions']['opening_intervals']))
 out=dict(schema='riverstone.court_phase01.functional_use.v1',placement_pack=ref(HERE/'resolved_placements.json'),terrain_handoff=ref(HERE/'terrain_handoff.json'),use_fronts=rows,bounded_enclosures=openings,no_interactive_or_occupancy_claim=True,unimplemented=s['unimplemented']);write(HERE/'functional_use.json',out);print('THREE_CLEAR_FUNCTION_FRONTS_PASS');return out
if __name__=='__main__':run()
