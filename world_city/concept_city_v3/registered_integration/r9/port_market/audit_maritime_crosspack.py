"""Read-only source-bound maritime and canopy cross-pack geometry exclusion audit."""
import collections,hashlib,itertools,json,math
from pathlib import Path
from .author import HERE,ROOT,BASE,BASE_SHA,load,sha,ref,ring,overlap
from voxel_character.common import core
from world_city.runtime_city.checks import placement as geo
DRAW=ROOT/'world_city/concept_city_v3/assemblies/waterworks/registered_bridge/drawbridge_candidate'
CARGO=HERE/'pack_r02.json';CANOPY=HERE/'market_canopy/pack.json'

def bounds_of(points):return {'min':[min(p[k]for p in points)for k in range(3)],'max':[max(p[k]for p in points)for k in range(3)]}
def poly_bounds(p):return [min(q[0]for q in p),min(q[1]for q in p),max(q[0]for q in p),max(q[1]for q in p)]
def broad_overlap(a,b):return a[0]<b[2]and b[0]<a[2]and a[1]<b[3]and b[1]<a[3]
def segment_dist(p,a,b):
 dx,dz=b[0]-a[0],b[1]-a[1];v=dx*dx+dz*dz;t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dz)/v))if v else 0
 return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dz)
def poly_dist(a,b):
 if overlap(a,b):return 0
 return min([segment_dist(p,u,v)for p in a for u,v in zip(b,b[1:]+b[:1])]+[segment_dist(p,u,v)for p in b for u,v in zip(a,a[1:]+a[:1])])
def world_box(b,frame):
 corners=[core.apply(frame,p)for p in itertools.product(*zip(b['min'],b['max']))];bound=bounds_of(corners);q=[core.apply(frame,[x,0,z])for x,z in [(b['min'][0],b['min'][2]),(b['max'][0],b['min'][2]),(b['max'][0],b['max'][2]),(b['min'][0],b['max'][2])]]
 return [[p[0],p[2]]for p in q],bound

def audit():
 paths=[CARGO,CANOPY,HERE/'market_canopy/proof.json',DRAW/'candidate.json',DRAW/'geometry_audit.json',DRAW/'motion_envelopes.json',DRAW/'operation_r01/contract.json',DRAW/'resolved_placements.json']
 hashes={p:sha(p)for p in paths};assert sha(BASE)==BASE_SHA
 cargo=load(CARGO);canopy=load(CANOPY);candidate=load(DRAW/'candidate.json');audit=load(DRAW/'geometry_audit.json');motion=load(DRAW/'motion_envelopes.json');operation=load(DRAW/'operation_r01/contract.json');scene=load(BASE)
 frame=candidate['bridge_to_world'];assert frame==motion['coordinate_frame']==operation['bridge_to_world']==scene['bridge_mechanism']['bridge_to_world']
 assert scene['bridge_mechanism']['provenance']['source_pack_sha256']==sha(DRAW/'resolved_placements.json')
 assert scene['bridge_mechanism']['provenance']['geometry_audit']['sha256']==sha(DRAW/'geometry_audit.json')
 assert cargo['remove_instance_ids']==[] and not cargo.get('replace_instances')
 assert all(r['id'].startswith('MARKET_stall_')for r in canopy['replace_instances'])
 assert canopy['remove_instance_ids']==[] and canopy['add_instances']==[]
 cargo_bounds=[]
 for p in cargo['add_instances']:
  a=cargo['common_assets'][p['asset_key']];q=ring(a['bounds'],p);cargo_bounds.append(dict(id=p['id'],polygon=q,aabb=poly_bounds(q),lo=p['position_m'][1]+a['bounds']['min'][1],hi=p['position_m'][1]+a['bounds']['max'][1]))
 reservations=[]
 def box(id,kind,b,source):
  q,w=world_box(b,frame);reservations.append(dict(id=id,kind=kind,source=source,bounds_bridge_local_m=b,world_bounds_m=w,world_polygon_xz_m=q,lo=w['min'][1],hi=w['max'][1]))
 for v in audit['navigation']:box(v['asset_key']+':FULL_TRAVEL', 'full_vessel_travel',v['full_source_cache_swept_envelope_bridge_m'],relpath(DRAW/'geometry_audit.json'))
 for row in motion['leaf_swept_volumes']:box(row['id'],'leaf_interval_sweep',row['bounds_bridge_local_m'],relpath(DRAW/'motion_envelopes.json'))
 for row in motion['other_swept_volumes']:box(row['id'],'other_mechanism_sweep',row['bounds_bridge_local_m'],relpath(DRAW/'motion_envelopes.json'))
 for kind,rows in operation['volumes'].items():
  for row in rows:box(row['id'],'controller_'+kind,row['bounds'],relpath(DRAW/'operation_r01/contract.json'))
 for kind,rows in [('navigation_hold',candidate['navigation_hold_regions']),('barrier_access_wait',candidate['waiting_regions'])]:
  for row in rows:reservations.append(dict(id=row['id'],kind=kind,source=relpath(DRAW/'candidate.json'),world_polygon_xz_m=row['polygon_xz_m'],lo=None,hi=None))
 maritime_hits=[];row_results=[]
 for r in reservations:
  q=r['world_polygon_xz_m'];bb=poly_bounds(q);hits=[]
  for p in cargo_bounds:
   if not broad_overlap(bb,p['aabb']):continue
   if r['lo']is not None and (r['hi']<=p['lo']or p['hi']<=r['lo']):continue
   if overlap(q,p['polygon']):hits.append(p['id'])
  maritime_hits.extend(dict(reservation=r['id'],cargo_id=id)for id in hits);row_results.append(dict(id=r['id'],kind=r['kind'],cargo_intersection_ids=hits))
 # Distances are horizontal and deliberately conservative for all-height source pockets.
 summary=[]
 for kind in sorted({r['kind']for r in reservations}):
  rr=[r for r in reservations if r['kind']==kind];allq=[p for r in rr for p in r['world_polygon_xz_m']];bb=poly_bounds(allq);q=[[bb[0],bb[1]],[bb[2],bb[1]],[bb[2],bb[3]],[bb[0],bb[3]]]
  nearest=min((poly_dist(q,p['polygon']),p['id'])for p in cargo_bounds)
  summary.append(dict(kind=kind,source_volume_count=len(rr),conservative_union_world_xz_bounds=bb,minimum_cargo_horizontal_gap_to_union_aabb_m=nearest[0],closest_cargo_id=nearest[1],intersection_count=sum(len(r['cargo_intersection_ids'])for r in row_results if r['kind']==kind)))
 base_instances={p['id']:p for p in scene['common_instances']};canopy_rows=[];canopy_hits=[];nearest=(float('inf'),None,None)
 for r in canopy['replace_instances']:
  p=base_instances[r['id']];assert p['asset_key']==r['expected_asset_key']and p['position_m']==r['expected_position_m']and p['yaw_rad']==r['expected_yaw_rad']
  a=canopy['common_assets'][r['asset_key']];q=ring(a['bounds'],p);lo=p['position_m'][1]+a['bounds']['min'][1];hi=p['position_m'][1]+a['bounds']['max'][1];hits=[]
  for c in cargo_bounds:
   distance=poly_dist(q,c['polygon'])
   if distance<nearest[0]:nearest=(distance,c['id'],r['id'])
   if c['hi']>lo and c['lo']<hi and overlap(q,c['polygon']):hits.append(c['id']);canopy_hits.append(dict(canopy_id=r['id'],cargo_id=c['id']))
  canopy_rows.append(dict(id=r['id'],asset_key=r['asset_key'],world_y_interval_m=[lo,hi],cargo_intersection_ids=hits))
 # Also retain exact fixed base ship poses and check all native bound hull/rig silhouettes.
 ship_rows=[]
 for p in scene['common_instances']:
  if not p['id'].startswith(('PORT_BARGE_','PORT_RIGGED_BARGE')):continue
  a=scene['common_assets'][p['asset_key']];q=ring(a['bounds'],p);lo=p['position_m'][1]+a['bounds']['min'][1];hi=p['position_m'][1]+a['bounds']['max'][1]
  hits=[c['id']for c in cargo_bounds if c['hi']>lo and c['lo']<hi and overlap(q,c['polygon'])]
  ship_rows.append(dict(id=p['id'],asset_key=p['asset_key'],position_m=p['position_m'],yaw_rad=p['yaw_rad'],bounds_local_m=a['bounds'],cargo_intersection_ids=hits))
 assert all(sha(p)==h for p,h in hashes.items());assert sha(BASE)==BASE_SHA
 report=dict(schema='riverstone.r9.maritime_and_canopy_exclusion.v1',status='PASS'if not maritime_hits and not canopy_hits and not any(r['cargo_intersection_ids']for r in ship_rows)else'FAIL',sources=[ref(p)for p in paths],base_scene=dict(path=relpath(BASE),sha256=BASE_SHA),actual_base_bridge_frame_matches_source=True,actual_base_geometry_pack_and_audit_hashes_match=True,bridge_to_world=frame,full_vessel_reservations=[r for r in reservations if r['kind']=='full_vessel_travel'],source_reservation_count=len(reservations),cargo_instances_checked=len(cargo_bounds),canopy_replacements_checked=len(canopy_rows),reservation_summary=summary,maritime_hits=maritime_hits,all_reservation_results=row_results,canopy_crosscheck=dict(complete_native_bounds_used=True,intersection_count=len(canopy_hits),hits=canopy_hits,minimum_horizontal_gap_m=nearest[0],closest_cargo_id=nearest[1],closest_canopy_id=nearest[2],rows=canopy_rows),retained_base_ships=ship_rows,base_ship_and_bridge_poses_unchanged_by_both_packs=True,frozen_inputs_unchanged=True,limits=['Read-only conservative static exclusion against the existing source-defined full rigged vessel sweep, all transition envelopes and controller volumes; no new ship, bridge, capsule or physics simulation.','Full vessel envelope inherits normal-stage level vessel assumptions, without flood, roll, wave or hydrodynamic certification.','Distances to category union world AABBs are conservative lower bounds; detailed collision checks use transformed native horizontal polygons and vertical overlap.','This audits the two named packs against the exact base and their mutual native bounds, not unknown later changes by other packs.'])
 (HERE/'maritime_crosspack_report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],source_reservations=len(reservations),cargo_instances=len(cargo_bounds),canopies=len(canopy_rows),maritime_hits=len(maritime_hits),canopy_hits=len(canopy_hits),nearest_canopy_gap_m=nearest[0],navigation_summary=[s for s in summary if s['kind']=='full_vessel_travel'])))
 return report

def relpath(p):return str(p.relative_to(ROOT))
if __name__=='__main__':audit()
