"""Exact native/core partitions that preserve owned rise within a holding."""
from . import geometry as g
from .coherent_bulk import config
from .refit_four_native_entries import PublicField
from .activate_backlands_subset import MaskIndex
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
import math,copy,time
OUT=g.HERE/'paired_contour_entry_refit_r04'
IDS=['BLOCK_007:R8_C001']

def area(ps):return sum(g.geo.polygon_area(p)for p in ps)
def inv(q,c,yaw):return g.xform([q[0]-c[0],q[1]-c[1]],[0,0],-yaw)

def run():
 start=time.monotonic();OUT.mkdir(exist_ok=True);r17=g.CITY/'registered_topography/revisions/r17_district_batches';lp=r17/'contour_bulk_r01/effective_source_layout_r03.json';layout=g.load(lp);b07p=g.HERE/'b07_terrace_refit_r02/BLOCK_007/selected_layout.json';b07=g.load(b07p);layout['holdings']+=b07['holdings'];layout['placements']+=b07['placements'];layout['actual_doors']+=b07['actual_doors'];np=g.HERE/'b07_terrace_refit_r02/BLOCK_007/native_local.json';native=g.load(np)['assets'];fieldp=g.CITY/'registered_topography/revisions/public_corridors_r18/finite_field_candidate_r04_common.json';field=PublicField(g.load(fieldp)['records']);ix=a.TriangleIndex(g.load(g.R7),[h['holding_polygon_xz_m']for h in layout['holdings']if h['id']in IDS]);records=[];failures=[]
 for hid in IDS:
  h=copy.deepcopy(next(q for q in layout['holdings']if q['id']==hid));oldps=[p for p in layout['placements']if p['holding_id']==hid];old=oldps[0];center=[sum(q[k]for q in h['holding_polygon_xz_m'])/4 for k in [0,1]];yaw=old['yaw_rad'];floor=h['floor_y_m'];hp=h['holding_polygon_xz_m'];loc=[inv(q,center,yaw)for q in hp];zfront=max(q[1]for q in loc);fullflat=hid=='BLOCK_003:R8_C003'
  if hid=='BLOCK_007:R8_C001':
   components=[('working_r01_bank_joinery',[0,-8.75],0),('ordinary_r2_661e6b2a06cce8',[-7.,5.5],-math.pi/2),('ordinary_r2_661e6b2a06cce8',[7.,5.5],math.pi/2)];court=g.rect(-16,-3.7,-11,2.5);anchor=[-13.5,-.25];profilelocal=g.rect(-11,-1.25,17,.75);seam=[[-11,-1.25],[-11,.75]];gate=[17,-.25]
   target=h['external_route'][-1];h['external_route']=[g.xform(gate,center,yaw),g.xform([16.5,-14.5],center,yaw),target];h['external_route_polygons_xz_m']=g.ribbons(h['external_route'],2.)
  else:
   components=[(oldps[0]['asset_key'],[0,-8.5],0),(oldps[1]['asset_key'],[0,8.5],math.pi)];court=g.rect(11.5,-3.5,15.5,3.5);anchor=[13.5,0];profilelocal=g.rect(-17,-1,11.5,1);seam=[[11.5,-1],[11.5,1]];gate=[-17,0]
  ps=[];ds=[]
  for i,(key,offset,dyaw)in enumerate(components,1):
   n=native[key];c=g.xform(offset,center,yaw);pyaw=yaw+dyaw;p=copy.deepcopy(old);p.update(id=hid+f':FABRIC:{i}',asset_key=key,position_m=[c[0],floor-.5,c[1]],yaw_rad=pyaw,scale=[1,1,1],finished_floor_y_m=floor,native_foundation_polygons_xz_m=g.transform(n['foundation_local_polygons_xz_m'],c,pyaw),native_walking_obstacles_xz_m=g.transform(n['walking_local_polygons_xz_m'],c,pyaw),native_roof_polygons_xz_m=g.transform(n['roof_local_polygons_xz_m'],c,pyaw),actual_door_ids=[],roof_area_m2=n['roof_area_m2'],foundation_area_m2=n['foundation_area_m2'],role=n['asset']['native_metadata']['role'],palette_id=n['asset']['native_metadata']['palette']);ps.append(p)
   for d0 in n['doors']:
    d=copy.deepcopy(d0);q=d['actual_local_xyz_m'];xz=g.xform([q[0],q[2]],c,pyaw);d.update(id=p['id']+':'+d['id'],parcel_id=p['id'],holding_id=hid,actual_door_xyz_m=[xz[0],floor-.5+q[1],xz[1]],outward_xz=g.xform(d['outward_local_xz'],[0,0],pyaw),threshold_lip_xz_m=g.xform(d['threshold_lip_local_xz_m'],c,pyaw),render_sha256=n['asset']['render_sha256'],exterior_route_width_m=min(1.5,d['exterior_route_width_m']));ds.append(d);p['actual_door_ids'].append(d['id'])
  core=g.transform([court],center,yaw);feet=[q for p in ps for q in p['native_foundation_polygons_xz_m']];obstacles=[q for p in ps for q in p['native_walking_obstacles_xz_m']];guard=g.transform([profilelocal],center,yaw)if profilelocal else[];anchorworld=g.xform(anchor,center,yaw);gateworld=g.xform(gate,center,yaw);config(dict(polygon_xz_m=hp));g.GRID=.25;config(dict(polygon_xz_m=hp));obmask=g.raster(obstacles,True);allowed=g.raster([hp]);gmask=g.raster(guard,True)if guard else g.np.zeros(g.SHAPE,bool);routes=[];bad=[]
  for d in ds:
   w=d['exterior_route_width_m'];n=d['outward_xz'];lip=d['threshold_lip_xz_m'];approach=[lip[k]+n[k]*(w/2+.75)for k in[0,1]];free=allowed&~obmask&~gmask;clear=g.ndimage.distance_transform_edt(free)*g.GRID>=w/2+.1;src=g.nearest(clear,approach,2);end=g.nearest(clear,anchorworld,1.5);goals=g.np.zeros(g.SHAPE,bool)
   if end:goals[end]=True
   line=g.astar(clear,src,goals)if src and end else None
   if ':native_row:'in d['id']:
    local=inv(lip,center,yaw);sgn=1 if local[0]>0 else -1;way=[[sgn*15.25,5.5],[sgn*15.25,1.85],[-12.25,1.85],anchor];line=[g.xform(q,center,yaw)for q in way]
   if line is None:bad.append(dict(door_id=d['id'],reason='No flat route around reserved graded entry'));continue
   line=line+[anchorworld];pw=min(w,min(f['width_m']for f in d['native_face_evidence'])-.125);neck=[lip[k]+n[k]*(pw/2+.4)for k in[0,1]];portal=[lip,neck,line[0]];polys=g.ribbons(portal,pw,caps=False)+g.ribbons(line,w);hits=MaskIndex([dict(id=str(i),polygon_xz_m=p)for i,p in enumerate(obstacles+guard)]).hit(polys)
   if hits:bad.append(dict(door_id=d['id'],reason='Exact flat door ribbon contacts native or graded strip',overlap_area_m2=area([v['polygon_xz_m']for v in hits])));continue
   routes.append(dict(id=d['id']+':COURT_LINK',door_id=d['id'],holding_id=hid,parcel_id=d['parcel_id'],floor_y_m=floor,width_m=w,polyline_xyz_m=[[q[0],floor,q[1]]for q in [lip,neck]+line],polyline_xz_m=[lip,neck]+line,polygons_xz_m=polys,joins_flat_court_xz_m=anchorworld,native_walking_overlap_area_m2=0))
  if bad:failures.append(dict(holding_id=hid,failed_doors=bad));print('DOOR_HOLD',hid,bad,flush=True);continue
  flat=a.common.disjoint_union(feet+core+[q for r in routes for q in r['polygons_xz_m']]);external=copy.deepcopy(h['external_route']);external[0]=gateworld;ext=g.ribbons(external,h['external_width_m']);internal=g.ribbons([anchorworld,gateworld],h['external_width_m'])if fullflat else guard
  if fullflat:
   # The already-passing candidate fixes the holding; preserve its exact public
   # approach while correcting only the native orientation and door links.
   internal=proposal['internal_court_link_polygons_xz_m'];flat=a.common.disjoint_union(flat+internal);prof=a.common.subtract(ext,flat);inner=[]
  else:
   prof=a.common.disjoint_union(a.common.subtract(guard+ext,flat));inner=[dict(endpoints_xz_m=g.transform([seam],center,yaw)[0],floor_y_m=floor)]
  overlap=sum(g.geo.intersection_area(p,q)for p in flat for q in prof);margin=a.common.subtract([hp],flat+prof);required=[p for q in flat for p in a.audit_polygon(ix,q,None,grade_limit=math.inf)['source_pieces']];lo=min(p['min_y_m']for p in required);hi=max(p['max_y_m']for p in required);interval=[hi-2.5,lo+2.5]
  native_inside=all(abs(g.geo.intersection_area(q,hp)-g.geo.polygon_area(q))<1e-7 for p in ps for q in p['native_roof_polygons_xz_m']);uncovered=sum(area(a.common.subtract([q],flat))for q in feet+[q for r in routes for q in r['polygons_xz_m']]);fixed=field.intersection(prof);logical=area([hp]);partition=area(a.common.disjoint_union([p for q in flat+prof for p in ([a.clip(q,hp)]if a.clip(q,hp)else[])]))+area(margin)
  h.update(floor_y_m=floor,component_placement_ids=[p['id']for p in ps],core_court_polygons_xz_m=core,gate_position_xz_m=gateworld,external_route=external,external_route_polygons_xz_m=ext,native_roof_area_m2=sum(p['roof_area_m2']for p in ps),flat_owner_polygons_xz_m=flat,profile_domain_polygons_xz_m=prof,surface_following_margin_polygons_xz_m=margin,shared_inner_seams_xz_m=inner,ground_owner_policy='Only exact native feet, internal pedestrian links and compact required court are flat. The explicit entry strip is profiled; residual logical margins retain source planes.')
  checks=dict(all_doors_have_native_clear_flat_links=len(routes)==len(ds),native_roofs_inside_holding=native_inside,flat_profile_intersection_area_m2=overlap,missing_flat_foot_or_door_area_m2=uncovered,logical_partition_error_m2=abs(logical-partition),required_core_floor_interval_m=interval,current_floor_within_core_interval=interval[0]-1e-7<=floor<=interval[1]+1e-7)
  row=dict(holding_id=hid,candidate_index=0,floor_y_m=floor,gate_point_xz_m=gateworld,gate_xz_m=gateworld,width_m=h['external_width_m'],polygons_xz_m=prof,flat_owner_polygons_xz_m=flat,profile_domain_polygons_xz_m=prof,shared_inner_seams_xz_m=inner,surface_following_margin_polygons_xz_m=margin,fixed_public_regions=fixed,required_core_floor_interval_m=interval,replacement_holding=h,replacement_native_placements=ps,replacement_actual_doors=ds,replacement_door_routes=routes,checks=checks,required_core_source_pieces=required,original_layout=g.ref(b07p if hid.startswith('BLOCK_007')else lp),native_local=g.ref(np),public_field=g.ref(fieldp),additional_retirement_ids=[],activation='SOURCE_PROPOSAL_ONLY; BOUNDARY_FIXTURE_AND_FINITE_TERRAIN_REBIND_REQUIRED');records.append(row);print(hid,checks,flush=True)
 report=dict(schema='riverstone.explicit_flat_core_entry_candidates.v1',source_layout=g.ref(lp),native_local=g.ref(np),public_field=g.ref(fieldp),author=g.ref(__file__),records=records,source_holds=failures,new_compilations=0,seconds=time.monotonic()-start);g.write(OUT/'source_candidates.json',report);print(g.ref(OUT/'source_candidates.json'),flush=True)

if __name__=='__main__':run()
