"""Trace real private holding boundaries with reused native two-metre rails.

All route crossings are explicit open gates; unsupported intervals stay held.
"""
from . import geometry as g
from .design import HERE as SOURCE
from .allocate_backlands import OUT,setup
from .finalize_coherent import overlap
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as ta
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as tc
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles

def run():
 path=OUT/'native_ground_program_final.json';program=g.load(path);allocation=g.load(OUT/'ground_owner_allocation.json');access=g.load(OUT/'access_handoff_final.json');scene=g.load(g.R7);base=g.np.load(g.CITY/'registered_integration/r8/coverage_plan/baseline_masks.npz');masks=g.np.load(OUT/'allocation_masks.npz');setup(base);ids={o['id']:i for i,o in enumerate(allocation['owners'],1)};active={o['id']for o in program['ground_owners']};asset=program['assets']['district_r01_boundary_2m'];render=g.load(g.ROOT/asset['render_path']);foot=slab_rectangles(render,-.249,-.126);walk=slab_rectangles(render,.01,3);rows=[];placements=[];allroute=[p for r in access['routes']for p in r['polygons_xz_m']]+program['preserved_retained_access_polygons_xz_m'];b15routes=g.load(g.CITY/'registered_topography/revisions/r17_district_batches/coherent_b15_r02/route_handoff.json');allroute+=[q for r in b15routes['nodes']+b15routes['door_routes']for q in r['polygons_xz_m']];den=g.load(g.CITY/'assemblies/ordinary/registered/r1/resolved_placements.json');gr=g.load(g.CITY/'assemblies/ordinary/registered/r1/owned_grounds.json');allroute+=[q for r in den['court_paths']+gr['paths']for q in r['reserved_polygons_xz_m']]+[r['polygon_xz_m']for r in den['courts']];main=g.load(SOURCE/'coherent_regrade_r01/bulk_placements_r02.json');contour=g.load(SOURCE/'contour_revision_r01/bulk_contour_proposals_final.json');retired=set(main['replaced_placement_ids'])|set(contour['replaced_placement_ids']);proj=g.load(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json')['instances'];native=[q for r in proj if r['id']not in retired for q in r['native_owner_parts_xz_m']]+[q for p in program['placements']for q in p['native_walking_obstacles_xz_m']];ds={d['block_id']:d for d in main['districts']};ds.update({d['block_id']:d for d in contour['districts']})
 for d in ds.values():
  l=g.load(g.ROOT/g.load(g.ROOT/d['pack']['path'])['layout']['path']);native+=[q for p in l['placements']for q in p['native_walking_obstacles_xz_m']]
 special=g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];vs=scene['surfaces']['water'];water=[[[v[0],v[2]]for v in vs[j:j+3]]for j in range(0,len(vs),3)];indexes={};sets={'native':native,'route':allroute,'protected':special+water}
 for k,ps in sets.items():
  si=g.geo._SpatialIndex(16)
  for i,p in enumerate(ps):si.add(i,p)
  indexes[k]=si
 def hit(k,qs):return sum(g.geo.intersection_area(p,sets[k][j])for p in qs for j in indexes[k].candidates(p))
 windows=[q for o in allocation['owners']if o['id']in active for q in o['polygon_parts_xz_m']];idx=ta.TriangleIndex(scene,windows);used=set();counts={}
 for oi,o in enumerate(allocation['owners']):
  if o['id']not in active:continue
  m=masks['allocation']==ids[o['id']];zz,xx=g.np.where(m);x0,x1=int(xx.min()),int(xx.max())+1;z0,z1=int(zz.min()),int(zz.max())+1;local=m[z0:z1,x0:x1];edges=[]
  # Maximal collinear cell-edge runs, not individual-cell scatter.
  for z in range(local.shape[0]+1):
   row=(local[z]if z<local.shape[0]else g.np.zeros(local.shape[1],bool))^(local[z-1]if z else g.np.zeros(local.shape[1],bool));ee=g.np.flatnonzero(g.np.diff(g.np.r_[False,row,False]))
   for a,b in zip(ee[::2],ee[1::2]):edges.append(([g.BOUNDS[0]+x0+int(a),g.BOUNDS[1]+z0+z],[g.BOUNDS[0]+x0+int(b),g.BOUNDS[1]+z0+z]))
  for x in range(local.shape[1]+1):
   col=(local[:,x]if x<local.shape[1]else g.np.zeros(local.shape[0],bool))^(local[:,x-1]if x else g.np.zeros(local.shape[0],bool));ee=g.np.flatnonzero(g.np.diff(g.np.r_[False,col,False]))
   for a,b in zip(ee[::2],ee[1::2]):edges.append(([g.BOUNDS[0]+x0+x,g.BOUNDS[1]+z0+int(a)],[g.BOUNDS[0]+x0+x,g.BOUNDS[1]+z0+int(b)]))
  intervals=[]
  for ei,(a,b)in enumerate(edges):
   length=g.math.dist(a,b);n=max(1,g.math.ceil(length/2));ux,uz=(b[0]-a[0])/length,(b[1]-a[1])/length;yaw=g.math.atan2(-uz,ux)
   for j in range(n):
    center=[a[0]+ux*length*(j+.5)/n,a[1]+uz*length*(j+.5)/n];token=tuple(round(v,6)for v in center+[yaw%g.math.pi]);segment=dict(edge_index=ei,panel_index=j,coverage_length_m=length/n,center_xz_m=center,yaw_rad=yaw)
    if token in used:segment['status']='SHARED_NATIVE_BOUNDARY_WITH_ADJACENT_OWNER';intervals.append(segment);continue
    fp=g.transform(foot,center,yaw);wp=g.transform(walk,center,yaw)
    if hit('route',wp)>1e-7:segment['status']='OPEN_GATE_AT_EXPLICIT_FULL_WIDTH_ACCESS';intervals.append(segment);continue
    if hit('protected',wp)>1e-7:segment['status']='HELD_PROTECTED_INTERFACE';intervals.append(segment);continue
    if hit('native',wp)>1e-7:segment['status']='RETAINED_NATIVE_OR_PROGRAM_BOUNDARY_INTERFACE';intervals.append(segment);continue
    pieces=[];gap=0
    for f in fp:
     rr=list(idx.covering(f));gap+=sum(g.geo.polygon_area(q)for q in tc.subtract([f],[r['intersection_polygon_xz_m']for r in rr]));pieces+=rr
    ys=[tc.height(r['plane_y_xz_m'],q)for r in pieces for q in r['intersection_polygon_xz_m']];relief=max(ys)-min(ys)if ys else 999
    if gap>1e-7 or relief>.25-1e-6:segment.update(status='HELD_FINITE_SUPPORT_INTERVAL',missing_top_area_m2=gap,source_relief_m=relief);intervals.append(segment);continue
    pid=o['id']+f':PERIMETER:{ei:04}:{j:03}';p=dict(id=pid,asset_key='district_r01_boundary_2m',ground_owner_id=o['id'],holding_id=o['named_owner'],position_m=[center[0],max(ys),center[1]],yaw_rad=yaw,scale=[1,1,1],palette_id='native_court_timber_and_stone',palette_override={},native_foundation_polygons_xz_m=fp,native_walking_obstacles_xz_m=wp,role='continuous_named_private_boundary',implementation_tier='exterior_only',support_proof=dict(source_relief_m=relief,minimum_source_y_m=min(ys),maximum_source_y_m=max(ys),native_bottom_y_m=max(ys)-.25,missing_top_area_m2=gap,source_refs=[dict(material=r['material'],triangle_index=r['triangle_index'],sha256=r['source_triangle_sha256'])for r in pieces]));placements.append(p);used.add(token);segment.update(status='NATIVE_BOUNDARY_SUPPORT_PROVEN',placement_id=pid);intervals.append(segment)
  cnt={s:sum(r['coverage_length_m']for r in intervals if r['status']==s)for s in{r['status']for r in intervals}};rows.append(dict(ground_owner_id=o['id'],boundary_intervals=intervals,coverage_length_by_status_m=cnt,fully_resolved_boundary=not any(r['status'].startswith('HELD')for r in intervals)));counts[o['id']]=cnt
  if oi%50==0:print(oi,'native panels',len(placements),flush=True)
 out=dict(schema='riverstone.district_fabric.backland_boundaries.v1',native_ground_program=g.ref(path),access=g.ref(OUT/'access_handoff_final.json'),assets={'district_r01_boundary_2m':asset},placements=placements,ground_boundaries=rows,preserved_access_polygons_xz_m=allroute,summary=dict(native_boundary_panels=len(placements),ground_boundaries=len(rows),fully_resolved_owner_boundaries=sum(r['fully_resolved_boundary']for r in rows),boundary_length_by_status_m={s:sum(r['coverage_length_by_status_m'].get(s,0)for r in rows)for s in{ss for r in rows for ss in r['coverage_length_by_status_m']}}),limits=['Native rails may overlap at intended corners and collinear joins; no whole-asset scaling.','Held support intervals cannot be called complete enclosures until finite original-plane support or an explicit physical edge is resolved.','Source top support is proven; final retained vertical-side and integrated capsule checks remain separate.']);g.write(OUT/'native_boundary_addendum_r01.json',out);print(out['summary'])
if __name__=='__main__':run()
