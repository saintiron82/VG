"""Independent exact-surface checks; does not run a renderer or controller."""
import json,math,collections,copy
from . import select_profiles as s,finite,build_patch as b
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a,side_clearance as side
from world_city.concept_city_v3.registered_integration.r6 import merge_patches
from world_city.runtime_city.checks import placement as g
HERE=s.HERE

def apply(scene,patch):
 edits={(r['material'],r['triangle_index']):r for r in patch['surface_edits']};out=dict(scene);out['surfaces']={}
 for m,vs in scene['surfaces'].items():
  new=[]
  for j in range(0,len(vs),3):new.extend(v for t in edits[(m,j//3)]['replacement_triangles_xyz_m']for v in t)if(m,j//3)in edits else new.extend(vs[j:j+3])
  new.extend(patch['appended_surfaces'].get(m,[]));out['surfaces'][m]=new
 return out

def uncovered(spans):return sum(hi-lo for lo,hi in b.subspans(spans))
def field_edge(edge,fields,normal):
 xz=[[v[0],v[2]]for v in edge];spans=[];hits=[]
 for t in fields:
  span=finite.interval(*xz,t['polygon_xz_m'])
  if not span:continue
  if max(sum((v[k]-xz[0][k])*normal[k]for k in(0,1))for v in t['polygon_xz_m'])<1e-9:continue
  deltas=[]
  for u in span:
   v=[edge[0][k]+u*(edge[1][k]-edge[0][k])for k in range(3)];deltas.append(abs(v[1]-a.common.height(t['plane_y_xz_m'],[v[0],v[2]])))
  hits.append(dict(owner_id=t['owner_id'],interval=span,max_height_delta_m=max(deltas)));spans.append(span)
 return dict(uncovered_length_m=uncovered(spans)*math.dist(*xz),maximum_height_delta_m=max((h['max_height_delta_m']for h in hits),default=None),source_intervals=hits)

def run():
 scene=a.load_scene();patch=json.loads((HERE/'surface_patch.json').read_text());fieldsdoc=json.loads((HERE/'fields.json').read_text());report=json.loads((HERE/'patch_report.json').read_text());bridges=json.loads((HERE.parent/'crossing_interfaces.json').read_text())['crossings'];handoff=json.loads((HERE/'public_handoff.json').read_text());fields=[dict(t,owner_id=p['id'])for p in fieldsdoc['profiles']for t in p['triangles']];merge_patches.merge([patch],a.SCENE_SHA256);merge_patches.validate_against_scene(scene,patch);out=apply(scene,patch);checks={};checks['hash_bound_original_indices']=True;checks['old_water_values_and_order_unchanged']=out['surfaces']['water']==scene['surfaces']['water'];checks['original_source_indices_unique']=len(patch['surface_edits'])==len({(r['material'],r['triangle_index'])for r in patch['surface_edits']});checks['retaining_boundaries_fully_supported']=not report['missing_boundary_segments'];checks['all_field_normals_positive']=all(a.normal_y(t['vertices_xyz_m'])>1e-10 for t in fields);checks['all_full_triangle_gradients_within_12_percent']=all(math.hypot(*t['plane_y_xz_m'][:2])<=.12000001 for t in fields)
 # Every raw field polygon is exactly tiled once by its road triangles.
 coverage=[]
 for p in fieldsdoc['profiles']:
  for i,poly in enumerate(p['polygons_xz_m']):
   covered=[finite.intersect(poly,t['polygon_xz_m'])for t in p['triangles']];missing=sum(g.polygon_area(q)for q in finite.subtract([poly],covered));excess=sum(g.polygon_area(q)for q in covered)-g.polygon_area(poly)+missing;coverage.append(dict(id=p['id'],piece=i,missing_area_m2=missing,excess_area_m2=excess))
 checks['field_top_coverage_exact_once']=all(x['missing_area_m2']<1e-7 and abs(x['excess_area_m2'])<1e-7 for x in coverage)
 # Deck edges are checked along the entire authored traffic width, not centers.
 deck_edges=[]
 for br in bridges:
  center=[br['position_m'][0],br['position_m'][2]]
  for j,e in enumerate(br['approach_seams']):
   edge=e['xyz_m'];mid=[sum(v[k]for v in edge)/2 for k in(0,2)];n=[mid[k]-center[k]for k in(0,1)];L=math.hypot(*n);n=[x/L for x in n];audit=field_edge(edge,fields,n);deck_edges.append(dict(bridge_id=br['id'],side=j,width_m=math.dist(*[[v[0],v[2]]for v in edge]),**audit))
 checks['eight_full_width_native_edges_continuous']=all(r['uncovered_length_m']<1e-6 and r['maximum_height_delta_m']is not None and r['maximum_height_delta_m']<1e-6 for r in deck_edges)
 public=[]
 for e in handoff['exact_public_terminals']:
  p=next(p for p in fieldsdoc['profiles']if p['id']==e['id']);center=[sum(v[k]for q in p['polygons_xz_m']for v in q)/sum(len(q)for q in p['polygons_xz_m'])for k in(0,1)];edge=[e['xyz_m'][0],e['xyz_m'][-1]];mid=[sum(v[k]for v in edge)/2 for k in(0,2)];n=[center[k]-mid[k]for k in(0,1)];L=math.hypot(*n);n=[x/L for x in n];audits=[field_edge([u,v],fields,n)for u,v in zip(e['xyz_m'],e['xyz_m'][1:])];public.append(dict(id=e['id'],road_id=e['road_id'],width_m=e['road_width_m'],maximum_height_delta_m=max(r['maximum_height_delta_m']or 0 for r in audits),uncovered_length_m=sum(r['uncovered_length_m']for r in audits)))
 checks['five_full_width_public_profiles_fixed']=all(r['uncovered_length_m']<1e-6 and r['maximum_height_delta_m']<1e-6 for r in public)
 checks['near_approach_widths_never_shrink']=all(r['minimum_full_transverse_width_m']>=p['road_width_m']-1e-8 for p in fieldsdoc['profiles']for r in p.get('width_proof',[]))
 # No retired side piece may intersect the actual wet volume at/below its
 # original transparent water plane, including zero-plan-area vertical banks.
 wet=[]
 for j in range(0,len(scene['surfaces']['water']),3):
  t=scene['surfaces']['water'][j:j+3];wet.append((j//3,[[v[0],v[2]]for v in t],a.common.plane(t)))
 underwater=[]
 for r in report['removed_side_pieces']:
  for wi,wp,plane in wet:
   q=b.planar_clip3(r['vertices_xyz_m'],wp)
   if q:q=b.clip3(q,lambda v:a.common.height(plane,[v[0],v[2]])-v[1])
   if q and side.area3d(q)>1e-8:underwater.append(dict(source_material=r['material'],source_triangle_index=r['triangle_index'],water_triangle_index=wi,area_m2=side.area3d(q)))
 checks['no_submerged_bank_or_bed_piece_removed']=not underwater
 # Actual retained and new side faces are checked in the full walking volume.
 # Contacts wholly on proven external retaining boundaries are curbs, not
 # interior blockers; all other nonzero-area contacts remain fatal.
 owners=[dict(id=t['owner_id'],polygon_xz_m=t['polygon_xz_m'],plane_y_xz_m=t['plane_y_xz_m'])for t in fields]+[dict(id=br['placement_id'],polygon_xz_m=br['traffic_polygon_xz_m'],floor_y_m=br['deck_top_y_m'])for br in bridges];ss=side.SideIndex(out,[r['polygon_xz_m']for r in owners]);contacts=ss.audit(owners)['contacts'];lateral=[r for r in report['boundary_seams']if r['kind']=='nonwalking_lateral_retaining'];fatal=[];boundary=[]
 for r in contacts:
  points=[[v[0],v[2]]for v in r['intersection_vertices_xyz_m']];matches=[]
  for seam in lateral:
   edge=[[v[0],v[2]]for v in seam['edge_xyz_m']]
   if all(g.point_segment_distance(v,*edge)<2e-6 for v in points):matches.append(seam)
  if matches:boundary.append(dict(owner_id=r['owner_id'],material=r['material'],triangle_index=r['triangle_index'],area_m2=r['clear_volume_contact_area_m2']))
  else:fatal.append(r)
 checks['full_walk_volume_free_of_interior_bank_faces']=not fatal
 print('CHECKS',checks,flush=True);print('DECK',[(r['bridge_id'],r['side'],r['uncovered_length_m'],r['maximum_height_delta_m'])for r in deck_edges],flush=True);print('FATAL',len(fatal),'BOUNDARY',len(boundary),'SUBMERGED',len(underwater),flush=True)
 result=dict(schema='riverstone.water_approach_exact_audit.r02',base_scene_sha256=a.SCENE_SHA256,patch_sha256=a.sha(HERE/'surface_patch.json'),field_sha256=a.sha(HERE/'fields.json'),checks=checks,field_coverage=coverage,deck_edges=deck_edges,public_terminals=public,submerged_removal_contacts=underwater,interior_bank_contacts=fatal,allowed_outer_retaining_contacts=boundary,status='PASS'if all(checks.values())else'FAIL',activation=False,limits=['Static exact geometry only; parent canonical-road composition, actual scene/controller and visual review remain required.'])
 s.write('exact_audit.json',result)
if __name__=='__main__':run()
