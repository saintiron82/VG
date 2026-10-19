"""Explicit finite shared work courts, reserved but not disguised as built ground."""
from .design import *
from .access import raster,XS,ZS,GRID,ribbons,nearest_free,astar,ndimage,np,point
from .ground import geo,ActualGround

def run():
 s=load(HERE/'selection.json');n=load(HERE/'native_geometry.json');a=load(HERE/'access_handoff.json');grounds=ActualGround();courts=[];roofs=[q for p in n['placements']for q in p['native_roof_polygons_xz_m']];obs=raster(roofs,True)
 specs=[('B15_MARKET_LODGING:1','MARKET_SHARED_WORK_COURT','Shared wash/work',8,5,[166,153],'Shared laundering, repair and domestic outdoor work; no household count inferred.'),('B15_UPPER_BANK_WORK:1','BANK_DRY_WORK_COURT','Dry work court',10,7,[243,185],'Shared timber assembly, dry goods sorting and manual handling space; no water discharge or cart-turn certificate.')]
 for hid,cid,label,w,d,preferred,purpose in specs:
  h=next(h for h in s['selected_holdings']if h['id']==hid);allowed=raster(h['polygon_parts_xz_m']);zz,xx=np.where(allowed&~obs);order=np.argsort((XS[xx]-preferred[0])**2+(ZS[zz]-preferred[1])**2);found=None
  for idx in order[::max(1,len(order)//500)][:500]:
   center=[float(XS[xx[idx]]),float(ZS[zz[idx]])];poly=[xform(q,center,math.radians(-48))for q in rect(-w/2,-d/2,w/2,d/2)];touch=raster([poly],True)
   if not touch.any()or np.any(touch&~allowed)or np.any(touch&obs):continue
   area=sum(geo.intersection_area(poly,q)for q in h['polygon_parts_xz_m']);
   if abs(area-w*d)>1e-6:continue
   if any(geo.intersection_area(poly,q)>1e-7 for q in roofs):continue
   found=(center,poly);break
  assert found,cid;center,poly=found;audit=grounds.audit([poly]);assert audit['fully_covered']and abs(audit['min_y_m']-2.5)<1e-7 and abs(audit['max_y_m']-2.5)<1e-7
  # A short source connection joins a proven internal door lane, preserving exact obstacles.
  paths=[r for r in a['internal_routes']if r['holding_id']==hid];targets=[q for r in paths for q in r['polyline_xz_m']];target=min(targets,key=lambda q:math.dist(q,center));free=allowed&~raster([q for p in n['placements']for q in p['native_walking_obstacles_xz_m']],True);clear=ndimage.distance_transform_edt(free)*GRID>=1+.707107;st=nearest_free(clear,center);end=nearest_free(clear,target);line=astar(clear,st,end);assert line,cid;line=[center]+line;ps=ribbons(line,2);link_audit=grounds.audit(ps);assert link_audit['fully_covered']and abs(link_audit['max_y_m']-2.5)<1e-7
  courts.append(dict(id=cid,holding_id=hid,short_label=label,purpose=purpose,polygon_xz_m=poly,area_m2=w*d,finished_floor_y_m=2.5,ground_audit=audit,access_link=dict(width_m=2,polyline_xz_m=line,ribbon_and_join_polygons_xz_m=ps,ground_audit=link_audit,joins_proven_internal_lane=True),native_implementation_status='Unimplemented finite court source. A later native continuous ground/boundary/facility recipe is required.',unimplemented=['Continuous native court surface','Functional wash or work equipment','Enclosure and real gate leaves','Native drainage design'],no_flatten_entire_holding=True))
 out=dict(schema='riverstone.working_ranges.courts.v1',selection=ref(HERE/'selection.json'),native_geometry=ref(HERE/'native_geometry.json'),courts=courts,total_reserved_court_m2=sum(c['area_m2']for c in courts),status='Finite source courts only, not counted as native completed land');write(HERE/'court_plan.json',out);print([(c['id'],c['area_m2'])for c in courts])
if __name__=='__main__':run()
