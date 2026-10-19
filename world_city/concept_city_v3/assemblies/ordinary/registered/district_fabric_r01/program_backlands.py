"""Produce plane-preserving private ground and support-tested native use clusters."""
from . import geometry as g
from .design import HERE as SOURCE
from .allocate_backlands import OUT
from .route_backlands import window
from .finalize_coherent import overlap
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as ta
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as tc

def run():
 alloc=g.load(OUT/'ground_owner_allocation.json');accesspath=OUT/'access_handoff_final.json';access=g.load(accesspath);connections={r['ground_owner_id']:r for r in access['routes']};scene=g.load(g.R7);keys=['productive_bed','domestic_wash_barrel','drying_frame','workbench','b13_workyard_wood_stack'];assets={k:scene['common_assets'][k]for k in keys};assets['district_r01_boundary_2m']=g.load(SOURCE/'compile_report.json')['assets']['district_r01_boundary_2m'];native={}
 for k,a in assets.items():
  r=g.load(g.ROOT/a['render_path']);lo=a['bounds']['min'][1];native[k]=dict(foot=slab_rectangles(r,lo+.001,lo+min(.124,a.get('pitch_m',.125)-.001)),walk=slab_rectangles(r,.01,3))
 windows=[p for o in alloc['owners']for p in o['polygon_parts_xz_m']];idx=ta.TriangleIndex(scene,windows);print('Indexed',len(idx.rows),'actual source top triangles',flush=True);main=g.load(SOURCE/'coherent_regrade_r01/bulk_placements_r02.json');contour=g.load(SOURCE/'contour_revision_r01/bulk_contour_proposals_final.json');retired=set(main['replaced_placement_ids'])|set(contour['replaced_placement_ids']);oldrows=g.load(g.CITY/'registered_topography/revisions/r17_district_batches/all_blocks_r01/retirement_candidates.json')['rows'];retained_access=[q for r in oldrows if r['source_id']not in retired for a in r['actual_old_access_records']for q in a['reserved_connection_polygons_xz_m']];density=g.load(g.CITY/'assemblies/ordinary/registered/r1/resolved_placements.json');retained_access+=[q for a in density['access_proposals']for q in a['reserved_connection_polygons_xz_m']];retained_access+=[q for r in density['court_paths']+g.load(g.CITY/'assemblies/ordinary/registered/r1/owned_grounds.json')['paths']for q in r['reserved_polygons_xz_m']]+[r['polygon_xz_m']for r in density['courts']];routepolys=[p for r in access['routes']for p in r['polygons_xz_m']]+retained_access;placements=[];grounds=[];held=[];sourcepieces=[];enclosures=[];asset_fail=0
 def support(key,center,yaw):
  foot=g.transform(native[key]['foot'],center,yaw);pieces=[]
  for q in foot:
   rows=list(idx.covering(q));missing=tc.subtract([q],[r['intersection_polygon_xz_m']for r in rows])
   if sum(g.geo.polygon_area(r)for r in missing)>1e-7:return None
   pieces.extend(rows)
  ys=[tc.height(r['plane_y_xz_m'],p)for r in pieces for p in r['intersection_polygon_xz_m']];relief=max(ys)-min(ys)if ys else 999;embed=-assets[key]['bounds']['min'][1]
  if relief>embed-0.015 or not ys:return None
  return dict(origin_y_m=max(ys),minimum_source_y_m=min(ys),maximum_source_y_m=max(ys),native_embed_depth_m=embed,source_relief_m=relief,footing_polygons_xz_m=foot,source_refs=[dict(material=r['material'],triangle_index=r['triangle_index'],sha256=r['source_triangle_sha256'])for r in pieces])
 def instance(id,key,o,c,yaw,role,proof):
  return dict(id=id,asset_key=key,ground_owner_id=o['id'],holding_id=o['named_owner'],position_m=[c[0],proof['origin_y_m'],c[1]],yaw_rad=yaw,scale=[1,1,1],native_foundation_polygons_xz_m=proof['footing_polygons_xz_m'],native_walking_obstacles_xz_m=g.transform(native[key]['walk'],c,yaw),support_proof=proof,palette_id='native_court_timber_and_stone',palette_override={},role=role,implementation_tier='exterior_only',source_pack='ordinary_backland_completion_r01')
 for oi,o in enumerate(alloc['owners']):
  if o['id']not in connections:held.append(dict(id=o['id'],reason='No connected source route yet',area_m2=o['area_m2']));continue
  route=connections[o['id']];polys=o['polygon_parts_xz_m'];window(polys);mask=g.raster(polys);routemask=g.raster(routepolys,True);reserved=routemask.copy();rows=[];missing=[];steep=[]
  for p in polys:
   pp=list(idx.covering(p));missing+=tc.subtract([p],[r['intersection_polygon_xz_m']for r in pp])
   for r in pp:
    poly=r['intersection_polygon_xz_m'];grade=g.math.hypot(*r['plane_y_xz_m'][:2]);walking=grade<=.12+1e-9;material='ground_earth';material='ground_grass'if not walking else material;rows.append(dict(source_material=r['material'],source_triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=poly,plane_y_xz_m=r['plane_y_xz_m'],target_material=material,surface_use=o['planned_function']if walking else'retained_nonwalking_productive_slope_verge',actual_source_gradient=grade))
  open_area=sum(g.geo.polygon_area(r['polygon_xz_m'])for r in rows);slopes=sum(g.geo.polygon_area(r['polygon_xz_m'])for r in rows if r['actual_source_gradient']>.12+1e-9);own=[];enclosure=None;free=mask&~reserved;dt=g.ndimage.distance_transform_edt(free)*g.GRID;zz,xx=g.np.where(dt>=2);candidates=sorted([(float(dt[z,x]),[float(g.XS[x]),float(g.ZS[z])])for z,x in zip(zz[::4],xx[::4])],reverse=True)
  # Functional equipment is placed in a coherent cluster, clear of the reserved walk.
  garden='garden'in o['planned_function']or'allotment'in o['planned_function'];work='craft'in o['planned_function']or'merchant'in o['planned_function'];needs=['productive_bed']*min(64,max(2,int(o['area_m2']/65)))if garden else(['b13_workyard_wood_stack']*2+['workbench','drying_frame']if work else['domestic_wash_barrel','drying_frame','drying_frame'])
  for j,key in enumerate(needs):
   chosen=None
   for dist,c in ([(0,[float(x),float(z)])for x in g.np.arange(g.math.ceil((g.BOUNDS[0]-.25)/8)*8+.25,g.BOUNDS[2],8)for z in g.np.arange(g.math.ceil((g.BOUNDS[1]-.25)/5)*5+.25,g.BOUNDS[3],5)] if key=='productive_bed' else candidates[:150]):
    centerrows=list(idx.covering(g.rect(c[0]-.01,c[1]-.01,c[0]+.01,c[1]+.01)));plane=centerrows[0]['plane_y_xz_m']if centerrows else[0,0,0];contour_yaw=g.math.atan2(plane[0],plane[1])if g.math.hypot(*plane[:2])>.001 else 0
    for yaw in[contour_yaw,0,g.math.pi/2]:
     box=g.transform([g.local_box(assets[key],.4)],c,yaw)[0];bm=g.raster([box],True)
     if g.np.any(bm&~mask)or g.np.any(bm&reserved):continue
     proof=support(key,c,yaw)
     if not proof:continue
     chosen=instance(o['id']+f':USE:{j:03}',key,o,c,yaw,o['planned_function'],proof);reserved|=bm;break
    if chosen:break
   if chosen:own.append(chosen)
  # One continuous small enclosure, gate deliberately open toward its reserved walk.
  if o['area_m2']>=180:
   for width,depth in[(16,20),(12,16),(8,12),(6,8)]:
    if enclosure:break
    for dist,c in candidates[:60]:
     ep=g.rect(c[0]-width/2,c[1]-depth/2,c[0]+width/2,c[1]+depth/2);em=g.raster([ep],True)
     if g.np.any(em&~mask):continue
     segs=[];gaps=[];proofok=True
     # Gate is the pair of panels nearest the route, so the boundary never seals access.
     edgepoints=[]
     for e,(a,b)in enumerate(zip(ep,ep[1:]+ep[:1])):
      length=g.math.dist(a,b);ux,uz=(b[0]-a[0])/length,(b[1]-a[1])/length;yaw=g.math.atan2(-uz,ux)
      for n in range(round(length/2)):
       cc=[a[0]+ux*(2*n+1),a[1]+uz*(2*n+1)];edgepoints.append((e,n,cc,yaw))
     gate=min(edgepoints,key=lambda v:min(g.math.dist(v[2],q)for q in route['polyline_xz_m']));gate_edge=gate[0];gate_n=gate[1]
     for e,n,cc,yaw in edgepoints:
      if e==gate_edge and abs(n-gate_n)<=1:gaps.append(dict(edge=e,panel=n,center_xz_m=cc,reason='Intentional shared private gate'));continue
      q=g.transform([g.local_box(assets['district_r01_boundary_2m'],.05)],cc,yaw)[0];bm=g.raster([q],True)
      if g.np.any(bm&routemask):gaps.append(dict(edge=e,panel=n,center_xz_m=cc,reason='Intentional gate for preserved actual access ribbon'));continue
      if g.np.any(bm&reserved):proofok=False;break
      proof=support('district_r01_boundary_2m',cc,yaw)
      if not proof:proofok=False;break
      segs.append(instance(o['id']+f':ENCLOSURE:{e}:{n}','district_r01_boundary_2m',o,cc,yaw,'continuous_private_backland_boundary',proof))
     if proofok:
      primarygaps=[q for q in gaps if q['reason']=='Intentional shared private gate'];gatecenter=[sum(q['center_xz_m'][k]for q in primarygaps)/len(primarygaps)for k in(0,1)];near=min(route['polyline_xz_m'],key=lambda q:g.math.dist(q,gatecenter));ln=g.math.dist(gatecenter,c);inside=[gatecenter[k]+(c[k]-gatecenter[k])*min(2.0,ln)/max(ln,1e-9)for k in(0,1)];gatepath=[inside,gatecenter,near];gatepolys=g.ribbons(gatepath,2.0);gm=g.raster(gatepolys,True);allowed=mask|routemask
      if g.np.any(gm&~allowed)or overlap(gatepolys,[q for p in own+segs for q in p['native_walking_obstacles_xz_m']])>1e-7:proofok=False
     if proofok:
      enclosure=dict(id=o['id']+':ENCLOSURE',ground_owner_id=o['id'],polygon_xz_m=ep,boundary_ids=[p['id']for p in segs],gate_gaps=gaps,full_width_gate_access=dict(width_m=2.0,polyline_xz_m=gatepath,polygons_xz_m=gatepolys,connects_route_id=route['id']),native_support_status='All cached bottom footprints have complete original-plane support and relief within embedded base depth.');own+=segs;enclosures.append(enclosure);break
  holes=[q for p in own for q in p['native_foundation_polygons_xz_m']];placements+=own;grounds.append(dict(id=o['id'],named_owner=o['named_owner'],block_id=o['block_id'],planned_function=o['planned_function'],finite_owner_polygons_xz_m=polys,material_source_pieces=rows,native_hole_polygons_xz_m=holes,route_id=route['id'],native_placement_ids=[p['id']for p in own],enclosure_id=enclosure['id']if enclosure else None,source_ground_area_m2=open_area,nonwalking_slope_verge_area_m2=slopes,missing_original_top_area_m2=sum(g.geo.polygon_area(q)for q in missing),missing_original_top_polygons_xz_m=missing,old_fragment_unit_ids=o['old_fragment_unit_ids'],completion_status='NATIVE_GROUND_SOURCE_REQUIRES_R17_ROUTE_SIDE_AND_FINAL_NATIVE_COLLISION_ACCEPTANCE'))
  if oi%20==0:print(oi,'ground',len(grounds),'placements',len(placements),'enclosures',len(enclosures),flush=True)
 summary=dict(ground_owners=len(grounds),actual_source_ground_area_m2=sum(r['source_ground_area_m2']for r in grounds),nonwalking_slope_verge_area_m2=sum(r['nonwalking_slope_verge_area_m2']for r in grounds),missing_original_top_area_m2=sum(r['missing_original_top_area_m2']for r in grounds),native_placements=len(placements),productive_beds=sum(p['asset_key']=='productive_bed'for p in placements),continuous_enclosures=len(enclosures),boundary_segments=sum(p['asset_key']=='district_r01_boundary_2m'for p in placements),new_compilations=0,held_owner_count=len(held));out=dict(schema='riverstone.district_fabric.backland_program.v1',allocation=g.ref(OUT/'ground_owner_allocation.json'),access=g.ref(accesspath),base_scene=g.ref(g.R7),assets=assets,placements=placements,ground_owners=grounds,enclosures=enclosures,preserved_retained_access_polygons_xz_m=retained_access,held_ground_owners=held,summary=summary,implementation_tier='exterior_only',integration_policy='Paint only exact clipped original source top pieces, preserve their planes, subtract every native footing hole, and atomically supersede the named older ground fragments. Shared access reservations take precedence over private use. No new floor plate or global pad.',status='SOURCE_NATIVE_PROGRAM_REQUIRES_ROUTE_TERRAIN_RETAINED_SIDE_AND_INTEGRATED_ACCEPTANCE');g.write(OUT/'native_ground_program_final.json',out);print(summary)
if __name__=='__main__':run()
