"""Repair three native sampled-boundary conflicts; preserve the complete r1 pack."""
import copy,json,math,time
from pathlib import Path
from .. import author as q
from ... import author as a
from ...audit import candidate_budget
from voxel_character.common import coordinate_planes,render_data
HERE=Path(__file__).resolve().parent
TARGETS={'E1':{'E1:registered:servants:door:0:r1_route','E1:registered_r1:garden_walk'},'E6':{'E6:registered:servants:door:0:r1_route'}}
def write(p,v):p.write_text(json.dumps(v,separators=(',',':'),allow_nan=False)+'\n')
def boundary_obstacles(r):
 poly=r['plot']['polygon_xz_m'];pieces=[]
 for u,v in zip(poly,poly[1:]+poly[:1]):
  t=a.unit(u,v);n=[-t[1],t[0]];p=[u,v,a.add(v,n,1.6),a.add(u,n,1.6)]
  for tri in a.triangulate(poly):
   z=a.geom.convex_intersection(p,tri)
   if a.geom.polygon_area(z)>1e-7:pieces.append(z)
 for g in r['gates']:
  cut=a.geom.road_ribbon(g['inside_point_xz_m'],g['outside_point_xz_m'],4.)
  pieces=[p for z in pieces for p in a.geom.convex_difference(z,cut) if a.geom.polygon_area(p)>1e-7]
 cleaned=[]
 for p in pieces:
  z=[]
  for v in p:
   if not z or math.dist(v,z[-1])>1e-7:z.append(v)
  if len(z)>1 and math.dist(z[0],z[-1])<1e-7:z.pop()
  if len(z)>=3 and a.geom.polygon_area(z)>1e-7:cleaned.append(z)
 return cleaned

def run():
 old=json.loads((q.HERE/'resolved_placements.json').read_text());pack=copy.deepcopy(old);manifest=pack['asset_manifest'];repairs=[];newassets=[];newrecipes={};checks=[]
 masks={m['property_id']:m for m in old['ownership_masks']}
 for pid,ids in TARGETS.items():
  r=json.loads((q.OUT/(pid+'.recipe.json')).read_text());g=r['gates'][0];floor=r['plot']['pad_floor_y_m'];wallcaps=[t['polygon_xz_m'] for t in masks[pid]['compiled_upward_faces'] if t['y_m']>floor+1];obstacles=[p['footprint_xz_m'] for p in r['placements']]+boundary_obstacles(r)
  for path in r['entrance_routes']:
   if path['id'] not in ids:continue
   before=copy.deepcopy(path);isdoor='door_id' in path;start=path['polyline_xz_m'][1 if isdoor else 0];middle=a.route_in_parcel(start,g['inside_point_xz_m'],r['plot']['polygon_xz_m'],obstacles,path['width_m'])
   if not middle:raise ValueError('No bounded route after native-wall clearance: '+path['id'])
   points=([path['polyline_xz_m'][0]] if isdoor else [])+middle+[g['center_xz_m']];path.update(id=path['id']+':repair01',polyline_xz_m=points,ribbon_polygons_xz_m=[a.geom.road_ribbon(u,v,path['width_m']) for u,v in zip(points,points[1:]) if math.dist(u,v)>1e-7],full_polyline_xyz_m=([before['full_polyline_xyz_m'][0]] if isdoor else [])+[[p[0],floor,p[1]] for p in points]);repairs.append(dict(property_id=pid,superseded_route_id=before['id'],replacement_route_id=path['id'],before=before,after=path,reason='independent actual compiled walking-slab overlap; boundary margin corrected before paint'))
  hits=[dict(route=p['id'],wall_index=i) for p in r['entrance_routes'] for z in p['ribbon_polygons_xz_m'] for i,w in enumerate(wallcaps) if a.overlap(z,w)]
  assert not hits,str(hits)
  assert a.validate_recipe(r)['valid'];checks.append(dict(property_id=pid,all_r1_ribbons_tested=len(r['entrance_routes']),compiled_wall_cap_intersections=hits,boundary_reservation_depth_m=1.6,source_gate_clear_cut_m=4))
  r['infrastructure_spec']=a.infrastructure_spec(r);r['infrastructure_spec']['external_surface']=r['external_surface'];master=q.append_surface(a.make_infrastructure_master(r['infrastructure_spec']),r['external_surface'],r['origin_xz_m'],floor);budget=candidate_budget(master);assert budget['within_candidate_cap'];write(HERE/(pid+'.recipe.json'),r);mp=HERE/(pid+'.master.json');write(mp,master);newrecipes[pid]=r
  start=time.monotonic();print(json.dumps(dict(property_id=pid,status='compile_start',candidate_visits=budget['exact_candidate_visits_without_cell_sampling'])),flush=True);compiled=coordinate_planes.compile_master(master,{'pitch':.5},max_candidate_cells=300000,max_output_cells=100000);assert compiled['valid'];render=render_data.make_render_data(compiled);rp=HERE/(master['id']+'.render.json');write(rp,render);key=master['id'];m=dict(asset_key=key,master_path=str(mp),master_file_sha256=a.file_sha(mp),master_source_sha256=a.sha(master),compiled_asset_ref=str(rp),render_sha256=a.file_sha(rp),sampling_resource={'pitch':.5},pitch_m=.5,bounds=render['bounds'],cell_count=render['cell_count'],quad_count=render['quad_count'],common_master_hash=compiled['master_hash'],common_payload_hash=compiled['payload_hash']);manifest[key]=m
  ins=next(p for p in pack['placements'] if p['id']==pid+':registered_r1:infrastructure');oldkey=ins['asset_key'];ins.update(asset_key=key,compiled_asset_ref=m['compiled_asset_ref'],render_sha256=m['render_sha256'],local_bounds=m['bounds']);del manifest[oldkey]
  tops=[];origin=r['origin_xz_m'];gatehits=[];passage=a.geom.road_ribbon(g['inside_point_xz_m'],g['outside_point_xz_m'],4)
  for group in render['groups']:
   for quad in group['quads']:
    n=q.cross(q.sub(quad[1],quad[0]),q.sub(quad[2],quad[0]))
    if n[1]<=1e-7:continue
    p=[[v[0]+origin[0],v[2]+origin[1]] for v in quad];tops.append(dict(polygon_xz_m=p,y_m=quad[0][1]+floor,material=group['material']))
    if quad[0][1]>1 and a.overlap(p,passage):gatehits.append(p)
  assert not gatehits
  mask=next(m for m in pack['ownership_masks'] if m['property_id']==pid);mask.update(compiled_upward_faces=tops,terrain_exclusion_regions_xz_m=[t['polygon_xz_m'] for t in tops],sampling_pitch_m=.5,sampled_render_sha256=m['render_sha256']);ins['surface_ownership']=mask
  # Geometry is unchanged except floor paint; test the new actual face layout too.
  newwalls=[t['polygon_xz_m'] for t in tops if t['y_m']>floor+1]
  assert not any(a.overlap(z,w) for p in r['entrance_routes'] for z in p['ribbon_polygons_xz_m'] for w in newwalls)
  stat=dict(property_id=pid,new_asset_key=key,old_asset_key=oldkey,candidate_cells=compiled['candidate_cells'],occupied_cells=render['cell_count'],elapsed_s=round(time.monotonic()-start,3));newassets.append(stat);print(json.dumps(stat),flush=True)
 for record in repairs:
  pack['internal_routes']=[record['after'] if p['id']==record['superseded_route_id'] else p for p in pack['internal_routes']]
 pack.update(revision='r1_access_repair01',parent_r1_pack_sha256=a.file_sha(q.HERE/'resolved_placements.json'),private_route_repair_ledger=repairs,repair_source_recipe_sha256={pid:a.file_sha(HERE/(pid+'.recipe.json')) for pid in TARGETS},status='compiled_private_routes_repaired_pending_independent_acceptance',terrain_exclusion_policy='Exact union of compiled_upward_faces XZ polygons; logical source plot and profile bounds do not erase uncovered corners or foundation cutouts.',shared_terminal_seam_policy='Use existing r1 terrain_handoff_addendum and share its piecewise-linear endpoint seams; external surfaces unchanged.')
 q.write(HERE/'cache_manifest.json',dict(assets=pack['asset_manifest'],status='complete_2_replacements_14_cached_reuses',parent_r1_cache_manifest_sha256=a.file_sha(q.HERE/'cache/manifest.json')));pack['cache_manifest_sha256']=a.file_sha(HERE/'cache_manifest.json')
 q.write(HERE/'resolved_placements.json',pack);q.write(HERE/'repair_report.json',dict(schema='riverstone.registered_property.native_wall_route_repair.v1',source_r1_pack_sha256=a.file_sha(q.HERE/'resolved_placements.json'),new_pack_sha256=a.file_sha(HERE/'resolved_placements.json'),original_source_overlay_sha256=old['source_overlay_sha256'],independent_failure_report='world_city/concept_city_v3/validation/evidence/registered_property_access_b723a96936ef_cd4068a31b59.json',changed_private_routes=len(repairs),changed_wrapper_count=2,building_and_prop_poses_unchanged=True,external_surface_profiles_unchanged=True,source_checks=checks,compile_results=newassets,runtime_ready=False,applied_to_scene=False))
 return pack
if __name__=='__main__':run()
