"""Partition shared finite court owners and bind explicit source route chains."""
from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import config,nearest_road,PublicSamples
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as tc
from collections import deque
import sys

def area(ps):return sum(g.geo.polygon_area(p)for p in ps)
def box(ps):return(min(q[0]for p in ps for q in p),min(q[1]for p in ps for q in p),max(q[0]for p in ps for q in p),max(q[1]for p in ps for q in p))if ps else(0,0,0,0)
def overlap_box(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8
def overlap(ps,qs):
 if not overlap_box(box(ps),box(qs)):return 0.
 return sum(g.geo.intersection_area(p,q)for p in ps for q in qs)
def run():
 rootname=next((a.split('=',1)[1]for a in sys.argv if a.startswith('--root=')),'coherent_regrade_r01');sys.argv=[a for a in sys.argv if not a.startswith('--root=')]
 blocks={b['block_id']:b for b in g.load(g.CITY/'registered_integration/r8/coverage_plan/baseline_blocks.json')['blocks']};scene=g.load(g.R7);samples=PublicSamples(scene);roads=g.load(g.CITY/'registered_source/plan.json')['roads'];mill=g.load(SOURCE/'coherent_regrade_r01/mill_reservation_check.json');results=[]
 for out in sorted((SOURCE/rootname).glob('BLOCK_*')):
  if len(sys.argv)>1 and out.name not in sys.argv[1:]:continue
  config(blocks[out.name]);g.HERE=out;l=g.load(out/'selected_layout.json');a=g.load(out/'access_handoff.json');c=g.load(out/'court_equipment.json');a['layout']=g.ref(out/'selected_layout.json');g.write(out/'access_handoff.json',a);hs=l['holdings'];ps=l['placements'];removed=[];keep=[]
  verges=[q['polygon_xz_m']for h in hs for q in h.get('nonwalking_slope_verges',[])]
  for p in c['placements']:
   if p['role']=='low_private_parcel_boundary'and (overlap(p['native_foundation_polygons_xz_m'],verges)>1e-7 or any(h['id']!=p['holding_id']and overlap(p['native_walking_obstacles_xz_m'],[h['holding_polygon_xz_m']])>1e-7 for h in hs)):removed.append(p['id'])
   else:keep.append(p)
  c['placements']=keep;allholes=[q for p in ps+keep for q in p['native_foundation_polygons_xz_m']];prior=[];ground_by={z['holding_id']:z for z in c['holding_grounds']};grounds=[];badlevels=[]
  for h in hs:
   hp=h['holding_polygon_xz_m'];z=ground_by[h['id']]
   for oh in hs:
    if oh['id']<h['id']and abs(oh['floor_y_m']-h['floor_y_m'])>1e-6 and overlap([hp],[oh['holding_polygon_xz_m']])>1e-7:badlevels.append([h['id'],oh['id']])
   holes=[q for q in allholes if overlap_box(box([hp]),box([q]))];owners=h.get('ground_owner_polygons_xz_m',[hp]);ground=tc.subtract(owners,holes+prior);prior.extend(owners);court=[p for raw in h['core_court_polygons_xz_m']for q in ground if(p:=tc.clean(g.geo.convex_intersection(raw,q)))];z.update(polygon_parts_xz_m=ground,native_hole_polygons_xz_m=holes,core_court_polygons_xz_m=court,ground_mode='bounded_cluster_regrade',shared_ground_partition_order=len(prior)-1,ownership_policy='Whole holding envelopes are unioned once by subtracting earlier finite owners; every new native hole is removed, including neighbouring shared-court buildings.',limits=['Exact native foundations remain occupied holes. Finite coherent court grading and public transitions require R17 acceptance.','No simulated commerce, drainage or open interior claim.']);z['boundary_segments']=sum(p['holding_id']==h['id']and p['role']=='low_private_parcel_boundary'for p in keep);z['equipment_placement_ids']=[i for i in z['equipment_placement_ids']if i in {p['id']for p in keep}];grounds.append(z)
  c.update(holding_grounds=grounds,layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),removed_shared_internal_boundary_ids=removed);c['summary'].update(native_equipment=sum(p['role']!='low_private_parcel_boundary'for p in keep),native_boundary_segments=sum(p['role']=='low_private_parcel_boundary'for p in keep),unique_owned_open_ground_area_m2=area([q for z in grounds for q in z['polygon_parts_xz_m']]));g.write(out/'court_equipment.json',c)
  nodes=[dict(id=h['id']+':GATE_LINK',holding_id=h['id'],floor_y_m=h['floor_y_m'],width_m=h['external_width_m'],polygons_xz_m=h['external_route_polygons_xz_m'],polyline_xz_m=h['external_route'],public_road_id=h.get('public_road_id'),public_target_evidence=h.get('public_target_evidence'))for h in hs]+[dict(r)for r in l['shared_private_routes']];adj={n['id']:[]for n in nodes};edges=[];roots=[]
  for i,n in enumerate(nodes):
   for m in nodes[:i]:
    if abs(n['floor_y_m']-m['floor_y_m'])>1e-6:continue
    ar=overlap(n['polygons_xz_m'],m['polygons_xz_m'])
    if ar>1e-6:adj[n['id']].append(m['id']);adj[m['id']].append(n['id']);edges.append(dict(a=n['id'],b=m['id'],finite_polygon_overlap_sum_m2=ar))
   candidates=[]
   for road in roads:
    if n.get('public_road_id')and road['id']!=n['public_road_id']:continue
    for endpoint in [n['polyline_xz_m'][0],n['polyline_xz_m'][-1]]if n['polyline_xz_m']else[]:
     dist,seg,t,q=nearest_road(endpoint,road)
     if dist<=road['width_m']/2+n['width_m']/2+1:
      ar=overlap(n['polygons_xz_m'],[g.geo.road_ribbon(road['polyline_xz_m'][seg],road['polyline_xz_m'][seg+1],road['width_m'])]);ev=samples.at(q)
      if ar>1e-6 and ev:candidates.append(dict(node_id=n['id'],public_road_id=road['id'],public_segment=seg,canonical_overlap_sum_m2=ar,public_center_anchor=ev,proposed_floor_y_m=n['floor_y_m'],boundary_status='Proposed canonical public-strip contact. R17 exact edge seam and graded profile remain required.',endpoint_distance_m=dist))
   if candidates:roots.append(min(candidates,key=lambda v:(abs(v['public_center_anchor']['y_m']-n['floor_y_m']),v['endpoint_distance_m'])))
  rootmap={r['node_id']:r for r in roots};chains=[];unresolved=[]
  for h in hs:
   start=h['id']+':GATE_LINK';todo=deque([[start]]);seen={start};chain=None
   while todo:
    path=todo.popleft()
    if path[-1]in rootmap:chain=path;break
    for nn in adj[path[-1]]:
     if nn not in seen:seen.add(nn);todo.append(path+[nn])
   row=dict(holding_id=h['id'],door_link_ids=[r['id']for r in a['routes']if r['holding_id']==h['id']],external_gate_route_id=start,gate_xz_m=h['gate_position_xz_m'],route_ids_to_public=chain or[],public_root=rootmap.get(chain[-1])if chain else None,status='Finite source chain; exact R17 public seam pending'if chain else'UNRESOLVED_PUBLIC_CHAIN')
   chains.append(row)
   if not chain:unresolved.append(h['id'])
  native_conflicts=[];route_conflicts=[]
  for i,p in enumerate(ps):
   for q in ps[:i]:
    ar=overlap(p['native_roof_polygons_xz_m'],q['native_roof_polygons_xz_m'])
    if ar>1e-6:native_conflicts.append(dict(a=p['id'],b=q['id'],area_m2=ar))
  obstacles=[q for p in ps for q in p['native_walking_obstacles_xz_m']]
  for n in nodes:
   ar=overlap(n['polygons_xz_m'],obstacles)
   if ar>1e-6:route_conflicts.append(dict(id=n['id'],native_overlap_m2=ar))
  graph=dict(schema='riverstone.district_fabric.route_graph.v1',layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),nodes=nodes,edges=edges,proposed_public_roots=roots,court_route_chains=chains,unresolved_holding_ids=unresolved,not_terrain_acceptance=True);g.write(out/'route_graph.json',graph)
  proposal=g.load(out/'ground_proposal.json');proposal.update(layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'),route_graph=g.ref(out/'route_graph.json'),mill_reservation=g.ref(SOURCE/'coherent_regrade_r01/mill_reservation_check.json'),exact_nonoverlapping_ground_owners=grounds);g.write(out/'ground_proposal.json',proposal)
  report=dict(block_id=out.name,layout=g.ref(out/'selected_layout.json'),source_ground_area_m2=area([h['holding_polygon_xz_m']for h in hs]),unique_owned_open_ground_area_m2=c['summary']['unique_owned_open_ground_area_m2'],removed_internal_shared_boundary_count=len(removed),different_level_ground_overlap_pairs=badlevels,native_roof_conflicts=native_conflicts,external_route_native_conflicts=route_conflicts,unresolved_public_chain_holding_ids=unresolved,passed=not(badlevels or native_conflicts or route_conflicts or unresolved));g.write(out/'source_spatial_audit.json',report);results.append(report);print(out.name,{k:len(report[k])for k in['different_level_ground_overlap_pairs','native_roof_conflicts','external_route_native_conflicts','unresolved_public_chain_holding_ids']},flush=True)
 g.write(SOURCE/rootname/'spatial_summary.json',dict(districts=results,passed=all(r['passed']for r in results)))
if __name__=='__main__':run()
