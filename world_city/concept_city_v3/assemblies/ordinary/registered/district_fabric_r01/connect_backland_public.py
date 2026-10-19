"""Resolve isolated owner groups by deliberate named public-frontage gates."""
from . import geometry as g
from .design import HERE as SOURCE
from .allocate_backlands import OUT
from .route_backlands import window
from .finalize_coherent import overlap
from .coherent_bulk import nearest_road,PublicSamples

def run():
 alloc=g.load(OUT/'ground_owner_allocation.json');access=g.load(OUT/'access_handoff.json');owners={o['id']:o for o in alloc['owners']};masks=g.np.load(OUT/'allocation_masks.npz');base=g.np.load(g.CITY/'registered_integration/r8/coverage_plan/baseline_masks.npz');bounds=masks['bounds'];bdefs=g.load(g.CITY/'registered_integration/r8/coverage_plan/baseline_blocks.json')['blocks'];bididx={b['block_id']:i for i,b in enumerate(bdefs,1)};plan=g.load(g.CITY/'registered_source/plan.json');scene=g.load(g.R7);samples=PublicSamples(scene);main=g.load(SOURCE/'coherent_regrade_r01/bulk_placements_r02.json');contour=g.load(SOURCE/'contour_revision_r01/bulk_contour_proposals_final.json');ds={d['block_id']:d for d in main['districts']};ds.update({d['block_id']:d for d in contour['districts']});layouts=[g.load(g.ROOT/g.load(g.ROOT/d['pack']['path'])['layout']['path'])for d in ds.values()];retired={i for l in layouts for i in l['retired_source_ids']};proj=g.load(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json')['instances'];native=[q for p in proj if p['id']not in retired for q in p['native_owner_parts_xz_m']]+[q for l in layouts for p in l['placements']for q in p['native_walking_obstacles_xz_m']];special=g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];vs=scene['surfaces']['water'];water=[[[v[0],v[2]]for v in vs[i:i+3]]for i in range(0,len(vs),3)];failed=[];added=[]
 for held in sorted(access['held_owner_routes'],key=lambda r:-r['area_m2']):
  o=owners[held['id']];polys=o['polygon_parts_xz_m'];center=o['representative_point_xz_m'];candidates=[]
  for road in plan['roads']:
   dist,seg,t,q=nearest_road(center,road)
   if dist<=110:
    ev=samples.at(q)
    if ev:candidates.append((dist,road,seg,q,ev))
  success=None
  for dist,road,seg,q,ev in sorted(candidates,key=lambda c:c[0])[:8]:
   aperture=g.rect(q[0]-2.5,q[1]-2.5,q[0]+2.5,q[1]+2.5);window(polys+[aperture]);zi=g.np.clip((g.ZS-bounds[1]).astype(int),0,masks['protected'].shape[0]-1);xi=g.np.clip((g.XS-bounds[0]).astype(int),0,masks['protected'].shape[1]-1);domain=(base['block_labels'][g.np.ix_(zi,xi)]==bididx[o['block_id']])&~(masks['protected'][g.np.ix_(zi,xi)]&~masks['public_service'][g.np.ix_(zi,xi)]);allowed=domain|g.raster([aperture]);blocking=g.raster(native+special+water,True);clear=allowed&(g.ndimage.distance_transform_edt(~blocking)*g.GRID>=1.15);own=g.raster(polys);dd=g.ndimage.distance_transform_edt(own)*g.GRID;dd[~clear]=-1;cell=g.np.unravel_index(g.np.argmax(dd),g.SHAPE);start=tuple(int(v)for v in cell)if dd[cell]>=1.5 else None;goal=g.nearest(clear,q,2);goals=g.np.zeros(g.SHAPE,bool)
   if goal:goals[goal]=True
   line=g.astar(clear,start,goals)if start and goal else None
   if not line:continue
   line+=[q];ps=g.ribbons(line,2.0);checks={k:overlap(ps,qq)for k,qq in[('native',native),('special',special),('water',water)]}
   if any(v>1e-7 for v in checks.values()):continue
   success=dict(id=o['id']+':BACKLAND_WALK',ground_owner_id=o['id'],named_owner=o['named_owner'],width_m=2.0,polyline_xz_m=line,polygons_xz_m=ps,gate_anchor_xz_m=line[0],named_existing_access_join_xz_m=q,target_access_polygons_xz_m=[g.geo.road_ribbon(road['polyline_xz_m'][seg],road['polyline_xz_m'][seg+1],road['width_m'])],length_m=sum(g.math.dist(a,b)for a,b in zip(line,line[1:])),public_road_id=road['id'],public_segment=seg,public_anchor_evidence=ev,projected_clearance=checks,status='EXACT_NATIVE_WATER_SPECIAL_CLEAR_NAMED_PUBLIC_GATE_REQUIRING_FULL_TRANSVERSE_SEAM_AND_TERRAIN_PROFILE');break
  if success:added.append(success);print(o['id'],o['area_m2'],'->',success['public_road_id'],flush=True)
  else:failed.append(held)
 access['routes']+=added;access['held_owner_routes']=failed;access['owner_connections']+=[dict(id=r['ground_owner_id'],route_id=r['id'],usable_court_anchor_xz_m=r['gate_anchor_xz_m'])for r in added];access['summary']=dict(connected_source_owners=len(access['routes']),connected_source_ground_m2=sum(owners[r['ground_owner_id']]['area_m2']for r in access['routes']),held_owners=len(failed),held_ground_m2=sum(r['area_m2']for r in failed));g.write(OUT/'access_public_addendum_r01.json',dict(source_access=g.ref(OUT/'access_handoff.json'),new_routes=added,remaining_holds=failed,summary=access['summary']));g.write(OUT/'access_handoff_public_r01.json',access);print(access['summary'])
if __name__=='__main__':run()
