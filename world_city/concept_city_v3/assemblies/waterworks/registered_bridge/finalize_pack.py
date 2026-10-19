"""Verify genuine common occupancy/render boundaries and emit one placement pack."""
import hashlib,json,math,time
from collections import defaultdict
from pathlib import Path
from voxel_character.common import core
from .author import HERE,ROOT,sha,ref,write,world_point,unit,sub
from .compile_bridge import deck_y,SEALED,CANDIDATE,PITCH
from world_city.concept_city_v3.registered_topography import author as terrain

def finalize():
 p=json.loads(CANDIDATE.read_text());overlay=json.loads((HERE/'continuous_deck_overlay.json').read_text());report=json.loads((HERE/'compile_report.json').read_text());c=json.loads((ROOT/report['compiled']['path']).read_text());r=json.loads((ROOT/report['render']['path']).read_text())
 assert sha(CANDIDATE)==SEALED and c['valid'] and all(t['pass'] for t in c['constraints'])
 assert core.digest(c['cells'])==c['payload_hash']==r['payload_hash']
 occupied={tuple(row[:3]) for row in c['cells']};columns=defaultdict(list)
 for x,y,z in occupied:columns[x,z].append(y)
 for key in columns:columns[key].sort()
 expected=set()
 for q in occupied:
  for axis in range(3):
   for sign in (-1,1):
    n=list(q);n[axis]+=sign
    if tuple(n) not in occupied:expected.add((*q,axis,sign))
 exposed_count=len(expected);render_unit_faces=0;duplicate_faces=0;bad=[]
 for group in r['groups']:
  for quad in group['quads']:
   grid=[[int(round(v/PITCH)) for v in point] for point in quad];a=[quad[1][i]-quad[0][i] for i in range(3)];b=[quad[2][i]-quad[1][i] for i in range(3)];normal=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];axis=max(range(3),key=lambda i:abs(normal[i]));sign=1 if normal[axis]>0 else -1;plane=grid[0][axis];axes=[i for i in range(3) if i!=axis];bounds=[(min(q[i] for q in grid),max(q[i] for q in grid)) for i in axes]
   for u in range(*bounds[0]):
    for v in range(*bounds[1]):
     cell=[0,0,0];cell[axis]=plane-1 if sign>0 else plane;cell[axes[0]]=u;cell[axes[1]]=v;face=(*cell,axis,sign);render_unit_faces+=1
     if face not in expected:bad.append({'face':face,'material':group['material']})
     else:expected.remove(face)
 assert not bad and not expected,(len(bad),len(expected))
 # Inspect actual sampled cells, not only the source footing labels.
 support=[]
 for bay in p['bays']:
  t=unit(sub(bay['endpoints_xz_m'][1],bay['endpoints_xz_m'][0]));center=bay['center_xz_m']
  for foot in bay['footings']:
   for lateral in (-6,-3,0,3,6):
    q=world_point(center,t,foot['end_sign']*7.5,lateral);ground=terrain.height_at(*q);local=core.apply(overlay['world_to_bridge'],[q[0],0,q[1]]);ix,iz=math.floor(local[0]/PITCH),math.floor(local[2]/PITCH);ys=columns.get((ix,iz),[]);probe=math.floor(min(ground-.25,bay['arch_top_y_m']-.25)/PITCH);exists=(ix,probe,iz) in occupied;bottom=min(ys)*PITCH if ys else None
    support.append({'bay_id':bay['id'],'end_sign':foot['end_sign'],'world_xz_m':q,'exact_ground_or_bed_y_m':ground,'probe_y_m':(probe+.5)*PITCH,'occupied_below_bed':exists,'actual_column_bottom_y_m':bottom,'actual_geometric_embed_m':ground-bottom if bottom is not None else None})
 assert all(s['occupied_below_bed'] and s['actual_geometric_embed_m']>=.35 for s in support)
 nav=next(b for b in p['bays'] if b['id']==p['navigation_channel']['bay_id']);navigation=[]
 for xi in range(25):
  x=-3+xi*.25
  for zi in range(57):
   z=-7+zi*.25;world=core.apply(nav['transform'],[x,0,z]);local=core.apply(overlay['world_to_bridge'],world);head=terrain.river_water_y(world[0]);ix,iz=math.floor(local[0]/PITCH),math.floor(local[2]/PITCH);above=[y for y in columns.get((ix,iz),[]) if (y+1)*PITCH>head+.01];ceiling=min(above)*PITCH if above else None
   navigation.append({'xz_m':[world[0],world[2]],'water_y_m':head,'actual_cell_soffit_y_m':ceiling,'clearance_m':ceiling-head if ceiling is not None else None})
 finite=[n['clearance_m'] for n in navigation if n['clearance_m'] is not None];assert finite and min(finite)>=3
 floors=[]
 for bay in p['bays']:
  a,b=bay['endpoints_xz_m'];t=unit(sub(b,a))
  for i in range(1,32):
   q=[a[j]+t[j]*i*.5 for j in(0,1)];local=core.apply(overlay['world_to_bridge'],[q[0],0,q[1]]);col=columns[math.floor(local[0]/PITCH),math.floor(local[2]/PITCH)];top=(max(col)+1)*PITCH;floor=deck_y(overlay,*q);floors.append({'xz_m':q,'authored_y_m':floor,'actual_cell_top_y_m':top,'difference_m':top-floor})
 junction=json.loads((HERE/'local_junction_criterion.json').read_text());interface=json.loads((HERE/'port_tie_interface.json').read_text());portal_samples=[]
 for region in interface['parapet_cut_regions']:
  poly=region['polygon_xz_m'];q=[sum(v[k] for v in poly)/len(poly) for k in (0,1)];local=core.apply(overlay['world_to_bridge'],[q[0],0,q[1]]);floor=deck_y(overlay,*q);ix,iz=math.floor(local[0]/PITCH),math.floor(local[2]/PITCH);blocked=[(ix,iy,iz) for iy in range(math.ceil((floor+.3)/PITCH),math.floor((floor+1.8)/PITCH)) if (ix,iy,iz) in occupied];portal_samples.append({'region_id':region['id'],'xz_m':q,'datum_y_m':floor,'overhead_blocked_cells':len(blocked)})
 assert not any(q['overhead_blocked_cells'] for q in portal_samples)
 proof={'schema':'riverstone.registered_bridge_actual_geometry.v1','compiled':report['compiled'],'render':report['render'],'candidate':ref(str(CANDIDATE.relative_to(ROOT))),'overlay':ref(str((HERE/'continuous_deck_overlay.json').relative_to(ROOT))),'compiled_payload_verified':True,'port_opening_samples':portal_samples,'port_tie_interface':ref(str((HERE/'port_tie_interface.json').relative_to(ROOT))),'local_junction_criterion':junction,'occupancy_connected':next(t for t in c['constraints'] if t['id']=='bridge_unified_connected'),'render_face_proof':{'exposed_occupancy_unit_faces':exposed_count,'render_expanded_unit_faces':render_unit_faces,'internal_or_duplicate_unit_faces':len(bad),'missing_exterior_unit_faces':len(expected),'method':'Every rendered greedy quad expanded to cell faces, compared bijectively with the boundary of final composited occupancy. Internal bay/cap/joint faces are absent.'},'support_samples':support,'minimum_actual_sampled_foundation_embed_m':min(s['actual_geometric_embed_m'] for s in support),'navigation_samples':navigation,'minimum_actual_sampled_navigation_clearance_m':min(finite),'navigation_rays_without_ceiling':sum(n['clearance_m'] is None for n in navigation),'central_lane_floor_samples':floors,'maximum_actual_floor_quantization_delta_m':max(abs(f['difference_m']) for f in floors),'physics_claim':'Static occupied-cell and mesh checks only. No capsule, load, scour, flood or moving-boat simulation.'}
 write(HERE/'actual_geometry_proof.json',proof)
 asset_key='registered_main_bridge_union_025';frame=overlay['bridge_to_world'];yaw=math.atan2(-frame['basis'][2][0],frame['basis'][0][0]);asset={'key':asset_key,'master_path':report['assembly_source']['path'],'master_sha256':report['assembly_source']['sha256'],'render_path':report['render']['path'],'render_sha256':report['render']['sha256'],'compiled_path':report['compiled']['path'],'compiled_sha256':report['compiled']['sha256'],'bounds':r['bounds'],'cell_count':r['cell_count'],'quad_count':r['quad_count'],'pitch_m':PITCH,'constraints':c['constraints'],'seconds':report['total_seconds'],'author_metadata':{'assembly':'static_bridge_union','scale_policy':'rigid_transform_only','genuine_arch_voids':True,'component_sources_native':True}}
 placement={'id':'BRIDGE_MAIN_RIVER:COMMON_UNION','asset_key':asset_key,'position_m':frame['translation'],'yaw_rad':yaw,'transform':frame,'scale_xyz':[1,1,1],'source_bridge_id':'BRIDGE_MAIN_RIVER','source_road_id':'MAIN_BRIDGE','replaces_proxy_ids':['BRIDGE_MAIN_RIVER'],'actual_sampled_bounds_local_m':r['bounds'],'support_regions':[f for b in p['bays'] for f in b['footings']],'deck_ownership_overlay':ref(str((HERE/'continuous_deck_overlay.json').relative_to(ROOT))),'navigation_channel':p['navigation_channel'],'collision_policy':'Static concave mesh from genuine exterior quads; never substitute a single convex hull or solid AABB, which would close the arches.'}
 pack={'schema':'riverstone.registered_bridge_placement_pack.v1','status':'compiled_common_candidate_pending_scene_and_capsule_review','candidate':ref(str(CANDIDATE.relative_to(ROOT))),'source_plan_path':p['source_plan']['path'],'source_plan_sha256':p['source_plan']['sha256'],'terrain_author_sha256':p['terrain_author']['sha256'],'continuous_deck_overlay':ref(str((HERE/'continuous_deck_overlay.json').relative_to(ROOT))),'assembly_source':report['assembly_source'],'port_tie_interface':ref(str((HERE/'port_tie_interface.json').relative_to(ROOT))),'junction_uplift_contract':ref(str((HERE/'junction_uplift_contract.json').relative_to(ROOT))),'local_junction_criterion':ref(str((HERE/'local_junction_criterion.json').relative_to(ROOT))),'compile_report':ref(str((HERE/'compile_report.json').relative_to(ROOT))),'actual_geometry_proof':ref(str((HERE/'actual_geometry_proof.json').relative_to(ROOT))),'assets':{asset_key:asset},'placements':[placement],'summary':{'assemblies':1,'native_arch_bays':9,'cell_count':r['cell_count'],'quad_count':r['quad_count'],'compile_seconds':report['total_seconds'],'peak_rss_mib':report['peak_rss_mib'],'minimum_actual_navigation_clearance_m':min(finite),'minimum_actual_foundation_embed_m':proof['minimum_actual_sampled_foundation_embed_m'],'maximum_floor_quantization_delta_m':proof['maximum_actual_floor_quantization_delta_m'],'internal_render_faces':0,'local_junction_maximum_gradient':junction['measured_maximum_triangle_gradient'],'local_service_ramp_gradient_ceiling':.15,'main_span_profile_gradient_ceiling':.10,'maximum_source_triangle_datum_error_m':junction['native_continuous_top_approximation']['maximum_sampled_top_plane_error_m']},'surface_ownership':{'visible_deck_owner':placement['id'],'suppress_original_road_and_bridge_faces_inside_overlay':True,'terrain_below':'Preserve the finite river water and bed below the elevated deck; only narrow support footings occupy the water domain.','avoid_duplicate_floor':'The compiled bridge supplies visible/collision deck geometry. Do not paint a coplanar terrain or road floor over it. The continuous overlay is the design datum and ownership contract; actual coarse floor quantization is measured separately.'},'limits':['Terminal continuity is tolerance-bounded: 0.214 mm exact rail residual and 0.939 mm near-boundary residual, accepted at1 mm; not exact mathematical continuity.','Local port junction uses an explicit15% service-ramp exception with measured12.3631% source triangles, pending capsule/cart review.','Actual common source, sampled geometry and hash-bound placement pose exist. No scene file was changed.','Capsule traversal and matched-camera review are still required.','Actual visible floor has 0.25 m grid quantization; use the reported delta, not a false exact-height claim.','The central normal-stage clearance does not certify masted ships, flooding or hydraulic capacity.']}
 write(HERE/'resolved_placements.json',pack);print(json.dumps({'pack':ref(str((HERE/'resolved_placements.json').relative_to(ROOT))),**pack['summary']},indent=2));return pack
if __name__=='__main__':finalize()
