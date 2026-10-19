"""Fixed-cache paired ranges open side courts for four held private entries."""
from . import geometry as g
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
import math,copy
OUT=g.HERE/'hard_core_native_refit_r01'
IDS=['BLOCK_001:R8_C003','BLOCK_001:R8_C004','BLOCK_003:R8_C003','BLOCK_004:R8_C004']

def run():
 OUT.mkdir(exist_ok=True);lp=g.CITY/'registered_topography/revisions/r17_district_batches/contour_bulk_r01/effective_source_layout_r03.json';layout=g.load(lp);oldlayout=copy.deepcopy(layout);np=g.HERE/'b07_terrace_refit_r02/BLOCK_007/native_local.json';native=g.load(np)['assets'];scene=g.load(g.R7);ix=a.TriangleIndex(scene,[h['holding_polygon_xz_m']for h in layout['holdings']if h['id']in IDS]);audits=[];budget=[]
 for h in layout['holdings']:
  if h['id']not in IDS:continue
  hid=h['id'];oldps=[p for p in layout['placements']if p['holding_id']==hid];old=oldps[0];yaw=old['yaw_rad'];center=[old['position_m'][0],old['position_m'][2]]
  if hid=='BLOCK_001:R8_C004':key='ordinary_r2_661e6b2a06cce8';offsets=[[0,-7.5],[0,7.5]];yaws=[yaw+math.pi/2,yaw-math.pi/2];court=g.rect(-7,-4.25,7,4.25);gate=[9.5,0]
  elif hid=='BLOCK_003:R8_C003':key='working_r01_market_lodging';offsets=[[-8,0],[8,0]];yaws=[yaw-math.pi/2,yaw+math.pi/2];court=g.rect(-3.25,-10.5,3.25,10.5);gate=[0,15]
  else:key='working_r01_market_lodging';offsets=[[0,-8],[0,8]];yaws=[yaw,yaw+math.pi];court=g.rect(-10.5,-3.25,10.5,3.25);gate=[13,0]
  newps=[];doors=[];n=native[key]
  for i,(off,pyaw)in enumerate(zip(offsets,yaws),1):
   c=g.xform(off,center,yaw);p=copy.deepcopy(old);p.update(id=hid+f':FABRIC:{i}',asset_key=key,position_m=[c[0],h['floor_y_m']-.5,c[1]],yaw_rad=pyaw,scale=[1,1,1],native_foundation_polygons_xz_m=g.transform(n['foundation_local_polygons_xz_m'],c,pyaw),native_walking_obstacles_xz_m=g.transform(n['walking_local_polygons_xz_m'],c,pyaw),native_roof_polygons_xz_m=g.transform(n['roof_local_polygons_xz_m'],c,pyaw),actual_door_ids=[],roof_area_m2=n['roof_area_m2'],foundation_area_m2=n['foundation_area_m2'],role=n['asset']['native_metadata']['role'],palette_id=n['asset']['native_metadata']['palette']);newps.append(p)
   for d0 in n['doors']:
    d=copy.deepcopy(d0);q=d['actual_local_xyz_m'];xz=g.xform([q[0],q[2]],c,pyaw);d.update(id=p['id']+':'+d['id'],parcel_id=p['id'],holding_id=hid,actual_door_xyz_m=[xz[0],h['floor_y_m']-.5+q[1],xz[1]],outward_xz=g.xform(d['outward_local_xz'],[0,0],pyaw),threshold_lip_xz_m=g.xform(d['threshold_lip_local_xz_m'],c,pyaw),render_sha256=n['asset']['render_sha256']);doors.append(d);p['actual_door_ids'].append(d['id'])
  core=g.transform([court],center,yaw);feet=[q for p in newps for q in p['native_foundation_polygons_xz_m']];queries=[a.audit_polygon(ix,p,None,grade_limit=math.inf)for p in feet+core];parts=[p for q in queries for p in q['source_pieces']];lo=min(p['min_y_m']for p in parts);hi=max(p['max_y_m']for p in parts);interval=[hi-2.5,lo+2.5];floor=max(interval[0],min(interval[1],h['floor_y_m']));inside=all(abs(g.geo.intersection_area(q,h['holding_polygon_xz_m'])-g.geo.polygon_area(q))<1e-7 for p in newps for q in p['native_roof_polygons_xz_m']);pairs=sum(g.geo.intersection_area(x,y)for i,p in enumerate(newps)for q in newps[:i]for x in p['native_walking_obstacles_xz_m']for y in q['native_walking_obstacles_xz_m']);court_overlap=sum(g.geo.intersection_area(q,p)for q in core for z in newps for p in z['native_walking_obstacles_xz_m']);row=dict(holding_id=hid,required_core_actual_min_y_m=lo,required_core_actual_max_y_m=hi,required_core_floor_interval_m=interval,old_floor_y_m=h['floor_y_m'],proposed_floor_y_m=floor,native_roof_inside_holding=inside,pair_overlap_m2=pairs,court_native_overlap_m2=court_overlap,old_native_roof_m2=h['native_roof_area_m2'],new_native_roof_m2=sum(p['roof_area_m2']for p in newps),roof_change_m2=sum(p['roof_area_m2']for p in newps)-h['native_roof_area_m2'],new_compilations=0,required_core_source_pieces=parts,passes=interval[0]<=interval[1]+1e-7 and inside and pairs<=1e-7 and court_overlap<=1e-7);audits.append(row);print({k:v for k,v in row.items()if k!='required_core_source_pieces'},flush=True)
  if not row['passes']:continue
  delta=floor-h['floor_y_m']
  for p in newps:p['position_m'][1]+=delta;p['finished_floor_y_m']=floor
  for d in doors:d['actual_door_xyz_m'][1]+=delta
  layout['placements']=[p for p in layout['placements']if p['holding_id']!=hid]+newps;layout['actual_doors']=[d for d in layout['actual_doors']if d['holding_id']!=hid]+doors
  h.update(floor_y_m=floor,core_court_polygons_xz_m=core,gate_position_xz_m=g.xform(gate,center,yaw),native_roof_area_m2=row['new_native_roof_m2'],component_placement_ids=[p['id']for p in newps],native_refit_source=g.ref(lp),native_refit_intent='Two fixed native ranges with a genuinely open shared side court; continuous external access remains pending finite proof.');budget.append(dict(id=hid,maximum_required_core_cut_m=max(0.,hi-floor),maximum_required_core_fill_m=max(0.,floor-lo)))
 layout['source_proposal_only']=True;layout['native_local']=g.ref(np);g.write(OUT/'selected_layout_candidate.json',layout);g.write(OUT/'required_core_budget.json',dict(rows=budget));g.write(OUT/'native_refit_audit.json',dict(source_layout=g.ref(lp),native_caches=g.ref(np),source_scene=g.ref(g.R7),author=g.ref(__file__),rows=audits,new_native_compiles=0,policy='This is a bounded native/core proposal. No sealed source or retirement is activated; private routes and native boundary/internal-door rebinding remain mandatory.'));print(g.ref(OUT/'selected_layout_candidate.json'))
if __name__=='__main__':run()
