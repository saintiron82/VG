"""Allocate finite residual ground to existing named households and work holdings.

This creates a source ownership and route-search contract. It cannot certify
terrain support, native boundaries or actual scene completion by itself.
"""
from . import geometry as g
from .design import HERE as SOURCE
from scipy.spatial import cKDTree
from collections import Counter
OUT=SOURCE/'backland_completion_r01'

def setup(base):
 g.GRID=1.;g.BOUNDS=base['bounds'].tolist();g.NZ,g.NX=base['block_labels'].shape;g.SHAPE=(g.NZ,g.NX);g.XS=g.BOUNDS[0]+g.np.arange(g.NX)+.5;g.ZS=g.BOUNDS[1]+g.np.arange(g.NZ)+.5

def run():
 OUT.mkdir(exist_ok=True);plan=g.CITY/'registered_integration/r8/coverage_plan';base=g.np.load(plan/'baseline_masks.npz');setup(base);mainpath=SOURCE/'coherent_regrade_r01/bulk_placements_r02.json';contourpath=SOURCE/'contour_revision_r01/bulk_contour_proposals_final.json';main=g.load(mainpath);contour=g.load(contourpath);districts={d['block_id']:d for d in main['districts']};districts.update({d['block_id']:d for d in contour['districts']});layouts={bid:g.load(g.ROOT/g.load(g.ROOT/d['pack']['path'])['layout']['path'])for bid,d in districts.items()};packs={bid:g.load(g.ROOT/d['pack']['path'])for bid,d in districts.items()};retired={i for l in layouts.values()for i in l['retired_source_ids']};projection=g.load(plan/'native_projection.json')['instances'];retained=[p for p in projection if p['id']not in retired];scene=g.load(g.R7);nativepolys=[q for p in retained for q in p['roof_parts_xz_m']]+[q for l in layouts.values()for p in l['placements']for q in p['native_roof_polygons_xz_m']];native=g.raster(nativepolys,True);holding=g.raster([q for l in layouts.values()for h in l['holdings']for q in h.get('ground_owner_polygons_xz_m',[h['holding_polygon_xz_m']])],True);routepolys=[q for l in layouts.values()for h in l['holdings']for q in h['external_route_polygons_xz_m']]+[q for l in layouts.values()for r in l['shared_private_routes']for q in r['polygons_xz_m']];routes=g.raster(routepolys,True);special=g.raster(g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'],True);protected=g.np.logical_or.reduce([base[k]for k in['spaces','estates','water','road','wall','retained_native','retained_access']])|special;mill=g.load(SOURCE/'coherent_regrade_r01/mill_reservation_check.json');protected|=g.raster([r['polygon']for r in mill['protected_regions']],True)
 # Explicit public service reservations are accounted separately, never labelled private gardens.
 bank=g.ndimage.distance_transform_edt(~base['water'])<=4.75;shoulder=g.ndimage.distance_transform_edt(~base['road'])<=2.75;public_service=(bank|shoulder)&~protected;protected|=bank|shoulder;residual=(base['block_labels']>0)&~(protected|native|holding|routes);old=g.load(plan/'ground_program_units.json');oldlabels=g.np.load(plan/'ground_unit_labels.npz')['unit_labels'];oldrows={i:u for i,u in enumerate(old['units'],1)};oldret=g.load(g.CITY/'registered_topography/revisions/r17_district_batches/all_blocks_r01/retirement_candidates.json')['rows'];records={r['source_id']:r for r in oldret};bdefs=g.load(plan/'baseline_blocks.json')['blocks'];sourceplan=g.load(g.CITY/'registered_source/plan.json');roles={b['id']:b['district_id']for b in sourceplan['blocks']};allowners=[];components=[];allocation=g.np.zeros(g.SHAPE,g.np.int32);owner_index=0
 for bi,b in enumerate(bdefs,1):
  bid=b['block_id'];mask=residual&(base['block_labels']==bi);labels,n=g.ndimage.label(mask);candidates=[]
  for h in layouts.get(bid,{}).get('holdings',[]):
   hp=h['holding_polygon_xz_m'];candidates.append(dict(id=h['id'],kind='new_native_holding',anchor_xz_m=h['gate_position_xz_m'],land_anchor_xz_m=[sum(p[0]for p in hp)/len(hp),sum(p[1]for p in hp)/len(hp)],ground_polygons_xz_m=h.get('ground_owner_polygons_xz_m',[hp]),existing_route_polygons_xz_m=h['external_route_polygons_xz_m'],role=h.get('planned_role',h.get('role','shared_domestic')),source_layout=g.ref(g.ROOT/g.load(g.ROOT/districts[bid]['pack']['path'])['layout']['path']),floor_y_m=h['floor_y_m']))
  for p in retained:
   r=records.get(p['id'])
   if not r or r['block_id']!=bid:continue
   access=r['actual_old_access_records'];a=access[0]if access else None
   if not a:continue
   candidates.append(dict(id=p['id'],kind='retained_native_household',anchor_xz_m=a['actual_door_xz_m'],land_anchor_xz_m=[p['position_m'][0],p['position_m'][2]],ground_polygons_xz_m=[],existing_route_polygons_xz_m=[q for a in access for q in a['reserved_connection_polygons_xz_m']],actual_door_ids=[a['id']for a in access],role='retained_'+scene['common_assets'][p['asset_key']].get('author_metadata',{}).get('style','household'),source_native_id=p['id'],floor_y_m=r['existing_finished_floor_y_m']))
  if bid=='BLOCK_013':
   dp=g.CITY/'assemblies/ordinary/registered/r1/resolved_placements.json';density=g.load(dp);doors={a['id']:a for a in density['access_proposals']}
   for d in density['placements']:
    aa=[doors[k]for k in d['actual_entrance_ids']if k in doors]
    if not aa:continue
    candidates.append(dict(id=d['id'],kind='retained_dense_native_group',anchor_xz_m=[aa[0]['actual_door_xyz_m'][0],aa[0]['actual_door_xyz_m'][2]],land_anchor_xz_m=[d['position_m'][0],d['position_m'][2]],ground_polygons_xz_m=[],existing_route_polygons_xz_m=[q for a in aa for q in a['reserved_connection_polygons_xz_m']],actual_door_ids=[a['id']for a in aa],role='dense_shared_domestic_workyard',source_density_pack=g.ref(dp),floor_y_m=d['pad_floor_y_m']))
  for ci in range(1,n+1):
   cm=labels==ci;amount=int(cm.sum());zz,xx=g.np.where(cm)
   if amount<25:continue
   cid=bid+f':BACKLAND_COMPONENT:{ci:04}';points=g.np.column_stack((g.XS[xx],g.ZS[zz]));tree=cKDTree(points);near=[]
   for c in candidates:
    dist,idx=tree.query(c['land_anchor_xz_m'])
    if dist<=65:near.append((c,float(dist)))
   if not near:
    components.append(dict(id=cid,block_id=bid,area_m2=amount,polygon_parts_xz_m=g.parts(cm),status='HELD_NO_NAMED_NATIVE_OWNER_WITHIN_65M',owner_ids=[]));continue
   seeds=g.np.array([c['land_anchor_xz_m']for c,d in near]);_,nearest=cKDTree(seeds).query(points);componentowners=[]
   for oi,(c,dist)in enumerate(near):
    take=nearest==oi
    if not take.any():continue
    pm=g.np.zeros(g.SHAPE,bool);pm[zz[take],xx[take]]=True;ar=int(pm.sum())
    if ar<25:continue
    owner_index+=1;allocation[pm]=owner_index;ids,counts=g.np.unique(oldlabels[pm],return_counts=True);prior=Counter()
    for ui,count in zip(ids,counts):
     if ui in oldrows:prior[oldrows[int(ui)]['source_function']]+=int(count)
    districtrole=roles.get(bid,'D_MIXED');role=c['role'];function='productive_kitchen_and_fuel_garden'
    if districtrole=='D_POOR' or'compact'in role or'domestic'in role or bid in ['BLOCK_007','BLOCK_013','BLOCK_015']:function='shared_domestic_washing_drying_and_fuel_yard'
    if 'work'in role or'craft'in role:function='craft_material_sorting_and_drying_ground'
    if 'merchant'in role or'lodge'in role:function='merchant_loading_sorting_and_dry_storage_court'
    if bid=='BLOCK_013':function='shared_domestic_washing_drying_and_fuel_yard'
    if ar>900 and function=='shared_domestic_washing_drying_and_fuel_yard':function='shared_domestic_yard_with_productive_allotments'
    if prior and prior.most_common(1)[0][0]in['estate_productive_gardens','institutional_edge_garden','precinct_margin_productive_service','estate_service_compound']:function='household_productive_service_garden'
    centre=points[take].mean(axis=0).tolist();r=dict(id=cid+':OWNER:'+c['id'],block_id=bid,component_id=cid,named_owner=c['id'],owner_kind=c['kind'],owner_source=c,area_m2=ar,polygon_parts_xz_m=g.parts(pm),source_program_area_m2=dict(prior),planned_function=function,representative_point_xz_m=centre,physical_ground_mode='preserve_actual_R7_source_planes_outside_new_native_holes',gate_and_access_status='Finite full-width connected route must pass native and actual-terrain proof before activation.',native_equipment_status='Pending coherent enclosure and function-specific native equipment.',old_fragment_unit_ids=[oldrows[int(i)]['id']for i in ids if i in oldrows],actual_scene_complete=False);allowners.append(r);componentowners.append(r['id'])
   components.append(dict(id=cid,block_id=bid,area_m2=amount,owner_ids=componentowners,status='NAMED_PRIVATE_GROUND_SOURCE_REQUIRING_NATIVE_ROUTE_AND_SUPPORT'))
  print(bid,'residual',int(mask.sum()),'owners',sum(r['block_id']==bid for r in allowners),flush=True)
 tiny=residual&(allocation==0);report=dict(schema='riverstone.district_fabric.backland_allocation.v1',sources=dict(original_native_bulk=g.ref(mainpath),contour_native_bulk=g.ref(contourpath),old_ground_program=g.ref(plan/'ground_program_units.json'),base_scene=g.ref(g.R7)),planning_grid_m=1,source_geometry_note='Finite cell-edge owner polygons are source geometry. Final ground material surfaces clip actual source triangles without changing their planes. No terrain acceptance is implied by accounting.',public_service_reserved_grid_m2=int(public_service.sum()),public_service_rule='Water receives a conservative 4 m dry service reservation, public roads a conservative 2 m walking-side reservation. These are excluded private ownership, not invented parks.',owners=allowners,components=components,summary=dict(named_owners=len(allowners),meaningful_components=len(components),assigned_private_ground_m2=sum(r['area_m2']for r in allowners),unassigned_or_subthreshold_grid_m2=int(tiny.sum()),planned_function_area_m2=dict(Counter({k:sum(r['area_m2']for r in allowners if r['planned_function']==k)for k in{r['planned_function']for r in allowners}}))),status='SOURCE_OWNERSHIP_ONLY_NOT_SCENE_COMPLETION');g.write(OUT/'ground_owner_allocation.json',report);g.np.savez_compressed(OUT/'allocation_masks.npz',allocation=allocation,residual=residual,protected=protected,native=native,holding=holding,routes=routes,public_service=public_service,bounds=base['bounds']);print(report['summary'])
if __name__=='__main__':run()
