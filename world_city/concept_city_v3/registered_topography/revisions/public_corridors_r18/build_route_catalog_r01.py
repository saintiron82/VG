"""Source-bound XZ replay catalog. Final scene supplies actual floor/collision Y."""
import json,math,collections
from .height_field import HERE
from . import finite_geometry_r03 as g,public_domain
from .screen_contour_domain_r02 import boundary_interval
from ..r17_district_batches import author as a

B=a.CITY/'traversal_r5/revisions/r06_r8_precinct'
def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def xz(p):return[p[0],p[2]]
def interp(p,q,t):return[p[k]+t*(q[k]-p[k])for k in(0,1)]
def interior(p,q,d=2.):return interp(p,q,min(1.,d/math.dist(p,q)))
def main():
 ip=B/'primary_inventory/inventory.json';bp=B/'network_batch_r01/prepared_runtime.json';lp=B/'public_network_r18_r01/bound_local_controls.json';fp=HERE/'finite_field_candidate_r04_common.json';hp=a.HERE/'contour_bulk_r01/route_handoff_ready_r02.json';inventory=json.loads(ip.read_bytes());old=json.loads(bp.read_bytes());local=json.loads(lp.read_bytes());field=json.loads(fp.read_bytes());lmap={r['id']:r for r in local['routes']};roads={r['id']:r for r in inventory['roads']};records=field['records'];ix=a.geo._SpatialIndex(4)
 for i,r in enumerate(records):ix.add(i,r['polygon_xz_m'])
 def owners(p):
  hits=[]
  for i in ix.candidates([p]):
   r=records[i];poly=r['polygon_xz_m'];sign=1 if g.signed_area(poly)>0 else-1
   if all(sign*g.cross(u,v,p)>=-1e-9*max(math.dist(u,v),1e-12)for u,v in zip(poly,poly[1:]+poly[:1])):hits.append(dict(owner_id=r['id'],source_triangle_index=r['source_triangle_index'],y_m=a.common.height(r['plane_y_xz_m'],p)))
  return hits
 def samples(points):
  out=[]
  for j,(p,q)in enumerate(zip(points,points[1:])):
   n=max(1,math.ceil(math.dist(p,q)/1.))
   for k in range(n):
    pt=interp(p,q,k/n);hits=owners(pt);out.append(dict(segment_index=j,t=k/n,xz_m=pt,r18_owners=hits,status='R18_PLANE_SAMPLE'if hits else'REQUIRES_ACTUAL_RETAINED_OR_NATIVE_FLOOR'))
  out.append(dict(segment_index=len(points)-2,t=1.,xz_m=points[-1],r18_owners=owners(points[-1]),status='FINAL_ACTUAL_STANDING_FLOOR_REQUIRED'))
  return out
 routes=[];substitutions=[]
 for r in old['routes']:
  if r['id'].endswith('_REVERSE')or r.get('expected_failure')or r['id']=='BRIDGE_CLOSED_LEAF_HINGE':continue
  pts=[xz(p)for p in r['points']];basis='UNCHANGED_CANONICAL_XZ';rid=r['id']
  if rid=='ROAD:MAIN_BRIDGE':
   pts=[xz(lmap['NORTH_LANE_0.0']['points_xyz_m'][-2])]+[xz(p)for p in lmap['BRIDGE_CLOSED_LEAF_HINGE']['points_xyz_m']]+[xz(lmap['AUTHORITATIVE_SOUTH_TERMINAL_COUNTRY']['points_xyz_m'][0])];basis='EXACT_NATIVE_AXIS_ENDPOINTS_AND_CLOSED_LEAF_STATIONS'
  elif rid=='ROAD:SOUTH_MARKET_AXIS':
   pts=[xz(lmap['NORTH_LANE_0.0']['points_xyz_m'][0])]+pts[1:];basis='NATIVE_NORTH_PUBLIC_STANDING_POINT_REPLACES_OBSOLETE_BRIDGE_END'
  elif rid=='ROAD:MARKET_NORTH':
   pts=pts[:-1]+[xz(lmap['NORTH_TWO_BRIDGE_INTERIOR_TURN_R03']['points_xyz_m'][10])];basis='ACTUAL_INTERIOR_JUNCTION_STANDING_POINT'
  elif rid=='ROAD:NORTH_BACK_LANE':
   pts=pts[:-1]+[xz(lmap['NORTH_TWO_BRIDGE_INTERIOR_TURN_R03']['points_xyz_m'][11])];basis='ACTUAL_INTERIOR_JUNCTION_STANDING_POINT'
  elif rid=='NATIVE_NORTH_TERMINAL_TO_MARKET':
   pts=[xz(p)for p in reversed(lmap['NORTH_LANE_0.0']['points_xyz_m'])]+pts[7:];basis='ACCEPTED_NORTH_CONNECTOR_THEN_CANONICAL_MARKET_AXIS_AND_FOUNTAIN_BYPASS'
  if basis!='UNCHANGED_CANONICAL_XZ':substitutions.append(dict(route_id=rid,basis=basis,old_polyline_xz_m=[xz(p)for p in r['points']],new_polyline_xz_m=pts))
  routes.append(dict(id=rid,case_class='public_road_or_gate',source_road_ids=r.get('source_road_ids',[]),polyline_xz_m=pts,source_width_m=r.get('source_width_m'),bidirectional=True,bridge_state='ROAD_OPEN',geometry_basis=basis,profile_samples=samples(pts),status='FINAL_SCENE_REPLAY_PENDING'))
 # Named estate routes are exact source chains; actual gate/native collision
 # remains a required test, including the pending E1/E2 access-skin repair.
 for r in inventory['noble_gates']:
  pts=r['polyline_xz_m'];routes.append(dict(id='NOBLE:'+r['id'],case_class='noble_public_gate',source_road_ids=[r['road_id']],polyline_xz_m=pts,source_width_m=r['width_m'],bidirectional=True,profile_samples=samples(pts),status='FINAL_NATIVE_AND_PUBLIC_CHAIN_REPLAY_PENDING'))
 junctions=[];seen=set()
 for r in inventory['endpoint_junction_candidates']:
  aa,bb=r['from_road_id'],r['to_road_id']
  if 'MAIN_BRIDGE'in(aa,bb)or set((aa,bb))==set(('MARKET_NORTH','NORTH_BACK_LANE')):continue
  pa=roads[aa]['polyline_xz_m'];pb=roads[bb]['polyline_xz_m'];end=0 if r['endpoint_index']==0 else len(pa)-1;p=pa[end];near=pa[1]if end==0 else pa[-2];incoming=interior(p,near);j=r['target_segment_index'];u,v=pb[j],pb[j+1];dx,dz=v[0]-u[0],v[1]-u[1];t=max(0.,min(1.,((p[0]-u[0])*dx+(p[1]-u[1])*dz)/(dx*dx+dz*dz)));cross=interp(u,v,t)
  options=[]
  for side,target in [('A',u),('B',v)]:
   if math.dist(cross,target)<.4:continue
   outgoing=interior(cross,target);pts=[incoming,p]
   if math.dist(p,cross)>1e-8:pts.append(cross)
   pts.append(outgoing);key=(tuple(sorted((aa,bb))),tuple(round(x,5)for x in p),side)
   if key in seen:continue
   seen.add(key);junctions.append(dict(id=r['id']+':INTERIOR:'+side,source_road_ids=[aa,bb],polyline_xz_m=pts,bidirectional=True,source_width_m=min(roads[aa]['width_m'],roads[bb]['width_m']),profile_samples=samples(pts),status='FINITE_INTERIOR_SOURCE_TURN_PENDING_ACTUAL_SCENE',source_candidate_id=r['id']))
 controls=[]
 for r in field['report']['exceptions']:
  poly=r['polygon_xz_m'];c=[math.fsum(v[k]for v in poly)/len(poly)for k in(0,1)];pl=r['plane_y_xz_m'];norm=math.hypot(*pl[:2]);direction=[pl[0]/norm,pl[1]/norm]if norm else[1.,0.]
  controls.append(dict(id='DESIGN_EXCEPTION:'+r['id'],source_triangle_index=r['source_triangle_index'],owner_id=r['id'],polygon_xz_m=poly,gradient=r['gradient'],area_m2=r['area_m2'],bounds_xz_m=r['bounds_xz_m'],source_triangle_min_altitude_m=r['source_triangle_min_altitude_m'],height_range_m=r['height_range_m'],crossing_candidate_xz_m=[[c[k]-direction[k]for k in(0,1)],[c[k]+direction[k]for k in(0,1)]],status='EXERCISE_ACTUAL_CAPSULE_IF_FULL_TUBE_SUPPORTED_ELSE_REPORT_UNSUPPORTED',expected='Design target failure is retained. Physical traversal result is measured, never inferred from gradient.'))
 blocks=[]
 for r in inventory['blocks']:
  blocks.append(dict(block_id=r['block_id'],boundary_road_ids=r.get('boundary_road_ids',[]),canonical_entry_route_id='ROAD:'+r['road_id']if r.get('road_id')else None,inventory_candidate=r,status='PENDING_FINAL_SCENE_BLOCK_ENTRY_CHAIN',native_holding_source='Only accepted holding IDs in terrain route_handoff_ready_r02 may be promoted; obsolete source plots are not authority.'))
 out=dict(schema='riverstone.r18.resolved_replay_catalog.v1',status='SOURCE_BOUND_CATALOG_FINAL_SCENE_BINDING_REQUIRED',sources=[ref(p)for p in(ip,bp,lp,fp,hp,HERE/'finite_candidate_active23_seal_r01.json')],controller_implementation_hashes=old['implementation_hashes'],routes=routes,junction_routes=junctions,local_controls=ref(lp),local_expanded_cases=local['expanded_case_count'],ordinary_holding_routes=ref(hp),blocks=blocks,primary_network_goals=inventory['primary_network_goals'],substitutions=substitutions,grade_exception_controls=controls,isolated_controls=[dict(id=r['id'],points_xyz_m=r['points'],expected_failure=r.get('expected_failure'),scope=r.get('test_scope'))for r in old['routes']if r['id'].startswith('NEGATIVE_')and r.get('group')=='isolated_control'],geometry_controls=['Verify every R18 owner/triangle hash against final scene before extraction.','All 43 explicit design-exception sources must remain reported; max-12-percent is not a global passing assertion.','No owner hit means actual retained/native floor resolution is required; never interpolate across missing support.','Exclude native cap masks from public floors and preserve continuous-contract substitution semantics.'],runtime_rules=['Final scene hash and geometry binding required; this catalog does not certify current traversal.','Use unchanged radius0.3/height1.8 no-step controller at60Hz, including strict support checks.','XZ vectors are planned motion only, never snap or teleport the body to them.','Resolve spawn and every destination standing height from final actual collision geometry; old Y hints are intentionally omitted.','Preserve exact native holes, native walls, bridge state and collider policies.','All positive chains are bidirectional. Negative actual wall/rail/water/barrier controls are in the bound local catalog.','Closed northern apex is deliberately not a destination; the accepted R03 interior turn supplies continuity.','No interior, NPC, cart or moving-span occupancy release is implied.'],counts=dict(base_and_noble_routes=len(routes),bidirectional_junction_routes=len(junctions),design_exception_sources=len(controls),blocks=len(blocks)),activation=False)
 path=HERE/'resolved_route_catalog_r01.json';path.write_text(json.dumps(out,separators=(',',':'))+'\n');print(ref(path),out['counts'],flush=True)
if __name__=='__main__':main()
