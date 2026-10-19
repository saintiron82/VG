"""Release only complete matched private fields, native holes and retirements."""
import json,time,collections
from .screen import HERE,write
from .. import author as a
from ...r01_ownership import author as ownership
from ...public_corridors_r18 import public_domain

def run():
 start=time.monotonic();prep=json.loads((HERE/'effective_prepared_parcels_r03.json').read_bytes());layout=json.loads((HERE/'effective_source_layout_r03.json').read_bytes());pack=json.loads((HERE/'prepared_native_pack_r03.json').read_bytes());summary=json.loads((HERE/'private_profiles_summary_r02.json').read_bytes());passed={h for r in summary['groups']if r['status']=='PASSED_FINITE_TRIANGLE_GRADE'for h in r['holding_ids']};accepted=set(passed);dependency_holds=[]
 while True:
  bad=set()
  for r in prep['retirement_records']:
   deps=set(r['affected_holding_ids'])
   if deps&accepted and not deps<=accepted:bad|=deps&accepted;dependency_holds.append(dict(source_id=r['source_id'],affected_holding_ids=r['affected_holding_ids']))
  for g in summary['groups']:
   ids=set(g['holding_ids'])
   if ids&accepted and not ids<=accepted:bad|=ids&accepted
  if not bad:break
  accepted-=bad
 expected=set(json.loads((HERE.parent/'public_dependency_review_r01/next20_atomic_rebind_request_r01.json').read_bytes())['matched_next_batch_holding_ids'])
 if accepted!=expected:raise ValueError('Atomic next20 mismatch '+str(accepted^expected))
 existing=set(json.loads((HERE.parent/'public_dependency_review_r01/next20_atomic_rebind_request_r01.json').read_bytes())['already_sealed_holding_ids'])
 public=[];pi=a.geo._SpatialIndex(16)
 for r in json.loads(a.PLAN_PATH.read_bytes())['roads']:
  public.extend(ownership.corridor(r['polyline_xz_m'],r['width_m']))
 public.extend(r['polygon_xz_m']for r in public_domain.records()if r['kind']=='bounded_retained_junction_extension')
 for i,p in enumerate(public):pi.add(i,p)
 def private(p):return a.common.subtract([p],[public[i]for i in pi.candidates(p)])
 owners=[];physical=[];holes=[];public_profiles=[];walk_regions=[];private_masks=[]
 def add(id,poly,kind,floor=None,plane=None,material='ground_earth',hid=None,physical_only=False):
  for j,p in enumerate(private(poly)):
   row=dict(id=id+':'+str(j),holding_id=hid,kind=kind,polygon_xz_m=p,plane_y_xz_m=plane if plane is not None else[0,0,floor],action='field',material=material)
   (physical if physical_only else owners).append(row)
 for parcel in prep['parcels']:
  if parcel['id']not in accepted:continue
  for j,p in enumerate(parcel['footing_polygons_xz_m']):holes.append(dict(id=parcel['id']+':NATIVE:'+str(j),holding_id=parcel['id'],action='hole',kind='native_footing',polygon_xz_m=p))
 for group in summary['groups']:
  if not set(group['holding_ids'])<=accepted:continue
  profile=json.loads((a.ROOT/group['path']).read_bytes());public_profiles.extend(profile['public_fixed_regions']);private_masks.extend(profile['private_domain_polygons_xz_m'])
  for j,r in enumerate(profile['result']['triangles']):
   row=dict(id=group['id']+':PROFILE:'+str(j),holding_ids=group['holding_ids'],kind='private_shared_profile',polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],action='field',material='ground_stone',gradient=r['gradient']);owners.append(row);physical.append(row);walk_regions.append(row)
 for parcel in prep['parcels']:
  hid=parcel['id']
  if hid not in accepted:continue
  for key,kind,mat in [('walk_polygons_xz_m','private_internal_walking','ground_stone'),('court_polygons_xz_m','functional_court','ground_earth'),('whole_holding_polygons_xz_m','coherent_holding','ground_earth')]:
   for j,p in enumerate(parcel[key]):add(hid+':'+kind+':'+str(j),p,kind,parcel['floor_y_m'],material=mat,hid=hid)
  for key in ('walk_polygons_xz_m','court_polygons_xz_m','whole_holding_polygons_xz_m'):
   for j,p in enumerate(parcel[key]):add(hid+':EARTH:'+key+':'+str(j),p,'coherent_holding',parcel['floor_y_m'],hid=hid,physical_only=True)
 records=[r for r in prep['retirement_records']if set(r['affected_holding_ids'])<=accepted]
 for r in records:
  add(r['source_id']+':RESIDUAL',r['old_body_polygon_xz_m'],'retired_private_floor_restoration',r['old_finished_floor_y_m'])
  add(r['source_id']+':RESIDUAL_EARTH',r['old_body_polygon_xz_m'],'retired_private_floor_restoration',r['old_finished_floor_y_m'],physical_only=True)
 def partition(rows,prior=()):
  # Each accepted private group already has a disjoint cell/triangle topology.
  # Its compact source domain is the exclusion mask for later material owners;
  # repeatedly subtracting thousands of its incident triangles adds no geometry.
  idx=a.geo._SpatialIndex(2);masks=list(prior);out=[]
  for i,p in enumerate(masks):idx.add(i,p)
  for r in rows:
   if r['kind']!='private_shared_profile':continue
   p=r['polygon_xz_m'];parts=a.common.subtract([p],[masks[i]for i in sorted(idx.candidates(p))])
   for k,q in enumerate(parts):out.append(dict(r,id=r['id']+':PART:'+str(k),polygon_xz_m=q))
  for p in private_masks:idx.add(len(masks),p);masks.append(p)
  for r in rows:
   if r['kind']=='private_shared_profile':continue
   p=r['polygon_xz_m'];parts=a.common.subtract([p],[masks[i]for i in sorted(idx.candidates(p))])
   for k,q in enumerate(parts):out.append(dict(r,id=r['id']+':PART:'+str(k),polygon_xz_m=q))
   idx.add(len(masks),p);masks.append(p)
  return out
 print("Partitioning",len(owners),len(physical),len(holes),flush=True)
 render=partition(owners,[r['polygon_xz_m']for r in holes]);print("Rendered parts",len(render),flush=True);logical=partition(physical);print("Physical parts",len(logical),flush=True)
 retirement_ids=[r['source_id']for r in records];selected_poses=[r for r in pack['placements']if r['holding_id']in accepted];selected_doors=[r for r in pack['actual_doors']if r['holding_id']in accepted];used={r['asset_key']for r in selected_poses}
 refs=[dict(path=str((HERE/n).relative_to(a.ROOT)),sha256=a.sha(HERE/n))for n in('effective_prepared_parcels_r03.json','effective_source_layout_r03.json','prepared_native_pack_r03.json','private_profiles_summary_r02.json','resolved_public_inputs_r01.json')]+public_domain.source_refs()
 out=dict(schema='riverstone.r17.physical_owner_handoff.v1',status='MATCHED_PROFILE_SOURCE_READY_PENDING_TOP_COVERAGE_AND_JOINT_SIDE_ACCEPTANCE',base_scene=dict(path=str(a.SCENE_PATH.relative_to(a.ROOT)),sha256=a.SCENE_SHA256),source_references=refs,accepted_holding_ids=sorted(accepted),held_holding_ids=sorted({r['id']for r in layout['holdings']}-accepted-existing),already_sealed_holding_ids=sorted(existing),native_holes=holes,rendered_plane_owners=render,physical_earth_owners=logical,public_fixed_regions=public_profiles,retirement_records=records,native_earth_bearings=[r for r in prep['native_earth_bearings']if r['holding_id']in accepted],retirement_dependency_holds=dependency_holds,all_candidate_reservations=[dict(id=h['id'],holding_polygon_xz_m=h['holding_polygon_xz_m'],external_route_polygons_xz_m=h['external_route_polygons_xz_m'],status='selected' if h['id'] in accepted else 'held')for h in layout['holdings']],summary=dict(holdings=len(accepted),native_instances=len(selected_poses),actual_doors=len(selected_doors),retired_ids=len(records),native_holes=len(holes),rendered_plane_owners=len(render),physical_earth_owners=len(logical),maximum_private_triangle_gradient=max([r['gradient']for r in walk_regions]+[0]),elapsed_s=time.monotonic()-start),side_policy='One joint R18/private closure must retire finite old sides and match these new physical earth planes. No separate private retaining faces are emitted.',activation=False)
 write('physical_owner_handoff_r02.json',out)
 np=dict(pack,placements=selected_poses,assets={k:v for k,v in pack['assets'].items()if k in used},actual_doors=selected_doors,replaced_placement_ids=retirement_ids,retired_foundation_proxy_ids=[r['removed_foundation_proxy_id']for r in records],accepted_holding_ids=sorted(accepted),held_holding_ids=out['held_holding_ids'],terrain_handoff=dict(path=str((HERE/'physical_owner_handoff_r02.json').relative_to(a.ROOT)),sha256=a.sha(HERE/'physical_owner_handoff_r02.json')),status=out['status'],summary=out['summary']);write('native_pack_ready_r02.json',np)
 write('shared_retirement_expansion_option_r02.json',dict(passing_holding_ids=sorted(passed),additional_holding_ids=sorted(passed-accepted),shared_retirements=dependency_holds,policy='Not active. Requires explicit adoption of whole shared old-body retirements and residual restoration while neighboring new proposals remain held.',activation=False));print(out['summary'],flush=True)
if __name__=='__main__':run()
