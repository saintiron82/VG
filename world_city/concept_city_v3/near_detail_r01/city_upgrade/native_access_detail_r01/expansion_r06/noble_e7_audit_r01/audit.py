"""Read-only source and actual-view attribution. No compile, new geometry or binding.
Exact domain is original actual top quads intersect original walk union, minus
all relevant original instance-local cuts. Reuses the frozen cap/cut adapter.
"""
from pathlib import Path
from fractions import Fraction as F
import collections,json,math,resource,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;N=H.parents[1]
sys.path.insert(0,str(N/'expansion_r06/training_partial_crop_r01'));import prepare as p
sys.path.insert(0,str(N/'expansion_r04/extrusion_support_r02'));import source_cap_cut_adapter as ad
e=p.e;a=p.a;R=p.R
PLAN=N/'expansion_r05/first_e7_e1/source_plan.json'
AUDIT=PLAN.parent/'source_application_audit.json'
CAPTURE=N.parent/'evidence/row_mill_noble_actual_r01/noble_e7_after.json'
KEY='registered_precinct_noble_entry_r01_e7_retained_base'

def owned_domain(subject,owner_polys,cut_polys):
 """Disjoint proof-only convex pieces. Not a new source primitive or mesher."""
 remaining=[subject];owned=[]
 for owner in owner_polys:
  for piece in remaining:
   hit=p.intersection(piece,owner)
   if e.area(hit)>0:owned.append(hit)
  remaining=[part for piece in remaining for part in e.difference(piece,owner)]
  assert len(remaining)<512 and len(owned)<512
 before=sum(e.area(s)for s in owned)
 for cut in cut_polys:owned=[part for piece in owned for part in e.difference(piece,cut)]
 return owned,before

def whole_cell_supported(rect,walk,actual_quads,cuts):
 """Reusable conservative input rule for the already tested common crop adapter.
 Both full unions are required; cut intersection is exact and strictly zero.
 """
 subject=p.rectpoly(rect)
 return e.exact_union(subject,walk)==0 and e.exact_union(subject,actual_quads)==0 and all(ad.intersection_area(subject,c)==0 for c in cuts)

def camera_point(x,y,capture):
 camera=capture['camera'];eye=camera['position'];forward=[camera['target'][i]-eye[i]for i in range(3)]
 norm=lambda v:[x/math.sqrt(sum(t*t for t in v))for x in v]
 forward=norm(forward);right=norm(a.previous.cross(forward,[0,1,0]));up=a.previous.cross(right,forward)
 tangent=math.tan(math.radians(camera['fov']/2));tx=(2*(x+.5)/1180-1)*tangent*1180/812;ty=(1-2*(y+.5)/812)*tangent
 direction=[forward[i]+tx*right[i]+ty*up[i]for i in range(3)];t=(10-eye[1])/direction[1]
 return [eye[i]+t*direction[i]for i in range(3)]

def main():
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
 plan=p.read(PLAN);asset=next(r for r in plan['assets']if r['asset_key']==KEY);audit=p.read(AUDIT);capture=p.read(CAPTURE);config=p.read(R/'world_city/concept_city_v3/playable_detail_r01/native_access_catalog.json');source=p.read(R/asset['source_render_path']);master=p.read(R/asset['source_master_path']);owners,cuts=ad.source_contract(master,asset['rule'],asset['source_pitch_m']);assert owners==asset['source_polygon_owners'] and cuts==asset['source_component_cuts'];assert p.sha(R/asset['source_render_path'])==asset['source_render_sha256'] and p.sha(R/asset['source_master_path'])==asset['source_master_sha256']
 accepted={tuple(r['bounds_uv_m']):r for r in asset['placements']};rejected={tuple(r['bounds_uv_m']):r for r in audit['rejected_patches']if r['asset_key']==KEY};pose=asset['actual_instances'][0]['instance'];observer=capture['observer'];rows=[];totals=collections.defaultdict(F);counts=collections.Counter();grid=collections.defaultdict(list)
 for gi,g in enumerate(source['groups']):
  if g['material']!=asset['rule']['material']:continue
  for qi,q in enumerate(g['quads']):
   try:rect=a.top_rectangle(q)
   except ValueError:continue
   assert q[0][1]==0
   for patch in a.previous.patches(rect):
    r=patch['low_uv']+patch['high_uv'];subject=e.fp(p.rectpoly(r));local=[o for o in owners if p.intersects(r,o['bounds_uv_m'])];local_cuts=[c for c in cuts if not(c['y_interval_m'][1]<0 or c['y_interval_m'][0]>.0375)];domain,before=owned_domain(subject,[e.fp(o['polygon_uv_m'])for o in local],[e.fp(c['polygon_uv_m'])for c in local_cuts]);area=e.area(subject);safe=sum(e.area(s)for s in domain);key=tuple(r);has=key in accepted;assert has !=(key in rejected)
    center_local=[(r[0]+r[2])/2,.0375,-(r[1]+r[3])/2];center=a.polygons.transform_point_m(center_local,pose['position_m'],pose.get('yaw_rad',0));distance=math.dist(center,observer);near=distance<=config['radius_m'];state='accepted'if has else rejected[key]['reason'];counts[state]+=1;counts[state+'/within_radius'if near else state+'/outside_radius']+=1
    values={'actual_source_quad_area_m2':area,'outside_source_walk_union_m2':area-before,'original_cut_inside_walk_m2':before-safe,'allowed_source_domain_m2':safe,'existing_detail_area_m2':area if has else F(0),'potential_partial_recovery_before_microgrid_loss_m2':F(0)if has else safe}
    for name,value in values.items():totals[name]+=value;totals[('center_within_radius/'if near else 'center_outside_radius/')+name]+=value
    assert not has or safe==area
    entry={'bounds_uv_m':r,'source_face_ref':[gi,qi],'classification':state,'within_runtime_radius':near,'center_distance_m':distance,**{k:float(v)for k,v in values.items()},'owner_operation_ids':[o['operation']for o in local]};rows.append(entry);grid[tuple(patch['grid_xy'])].append((r,domain,has))
 assert len(rows)==631 and counts['accepted']==170
 # Repartition can combine multiple original quad fragments in one metre-grid
 # module, but it does not change the exact source domain or allow cut fill.
 gridrows=[]
 for xy,pieces in sorted(grid.items()):
  safe=sum(e.area(poly)for r,domain,has in pieces for poly in domain)
  if safe==0:continue
  center=a.polygons.transform_point_m([xy[0]+.5,.0375,-xy[1]-.5],pose['position_m'],pose.get('yaw_rad',0));gridrows.append({'grid_xy':list(xy),'original_quad_fragments':len(pieces),'existing_accepted_fragments':sum(has for r,domain,has in pieces),'exact_safe_domain_area_m2':float(safe),'potential_module_center_within_radius':math.dist(center,observer)<=8})
 diagnostic=[]
 for pixel in [[460,660],[360,510],[920,473],[900,595],[220,600],[540,450]]:
  world=camera_point(*pixel,capture);local=a.polygons.inverse_transform_point_m(world,pose['position_m'],pose.get('yaw_rad',0));uv=[local[0],-local[2]];point=list(map(F,uv));hits=[r for r in rows if r['bounds_uv_m'][0]<=uv[0]<=r['bounds_uv_m'][2]and r['bounds_uv_m'][1]<=uv[1]<=r['bounds_uv_m'][3]]
  diagnostic.append({'image_pixel_xy':pixel,'source_plane_world_y_m':10,'world_point_m':world,'local_uv_m':uv,'distance_to_observer_m':math.dist(world,observer),'before_fade_start':math.dist(world,observer)<config['fade_start_m'],'exact_source_walk_owners_at_point':[o['operation']for o in owners if p.point_in(point,e.fp(o['polygon_uv_m']))],'exact_source_cuts_at_point':[c['operation']for c in cuts if p.point_in(point,e.fp(c['polygon_uv_m']))],'actual_source_patch_hits':hits,'camera_reconstruction_scope':'Original fixed capture camera, vertical FOV and 1180x812 viewport; plane projection is diagnostic, not a source-support raycast or a walking test.'})
 # Tiny fixtures on the generalized whole-cell rule; no shape compilation.
 rect=e.fp(p.rectpoly([0,0,1,1]));q=[e.fp(p.rectpoly(r))for r in [[0,0,.5,1],[.5,0,1,1]]];hole=e.fp(p.rectpoly([.4,.4,.6,.6]))
 tests={'multi_quad_union_seam_supported':whole_cell_supported(list(map(F,[0,0,1,1])),[rect],q,[]),'original_cut_hole_rejected':not whole_cell_supported(list(map(F,[0,0,1,1])),[rect],q,[hole]),'missing_actual_quad_rejected':not whole_cell_supported(list(map(F,[0,0,1,1])),[rect],q[:1],[]),'walk_union_gap_rejected':not whole_cell_supported(list(map(F,[0,0,1,1])),q[:1],[rect],[])};assert all(tests.values())
 report={'schema':'riverstone.native_access.source_gap_diagnosis.v1','all_pass':True,'asset_key':KEY,'source_plan':p.ref(PLAN),'source_audit':p.ref(AUDIT),'capture':p.ref(CAPTURE),'capture_image':p.ref(CAPTURE.with_suffix('.png')),'runtime_config_observed':p.ref(R/'world_city/concept_city_v3/playable_detail_r01/native_access_catalog.json'),'runtime_helper_observed':p.ref(R/'world_city/concept_city_v3/playable_detail_r01/CityWorldAccessDetail.gd'),'author':p.ref(Path(__file__)),'source_master':p.ref(R/asset['source_master_path']),'source_render':p.ref(R/asset['source_render_path']),'actual_runtime_stats':capture['world']['native_access'],'runtime_radius_m':config['radius_m'],'runtime_fade_m':[config['fade_start_m'],config['fade_end_m']],'counts':dict(counts),'areas':{k:float(v)for k,v in totals.items()},'area_scope':'Exact original per-quad fragments. Radius subsets use unchanged runtime module-center selection, not exact circular clipping. No source domain expanded.','potential_consistent_grid_modules':len(gridrows),'potential_grid_modules_center_within_radius':sum(r['potential_module_center_within_radius']for r in gridrows),'grid_repartition_area_is_not_recovery':True,'patches':rows,'consistent_grid_demands':gridrows,'image_gap_diagnostics':diagnostic,'generalized_partial_crop_rule_tests':tests,'partial_crop_input_contract':{'actual_support':'same-plane original top-quad union','semantic_support':'same semantic-key original walk cap union','cuts':'all relevant original instance-local component cuts, with exact positive area forbidden','cell_acceptance':'whole exported cell footprint, not center','authoring':'same 1m anchor/seed phase, unsafe cells removed by existing common assembly cuts','mesher':'unchanged common core and greedy render export','replacement':'single whole-training/estate revision replacing original detail row; no overlapping stacked additions','unsupported':['changed source SHA','mixed semantics','dynamic support','nonhorizontal or malformed original faces','unsupported source caps or unproven assembly cuts']},'new_geometry_bytes':0,'compile_or_sampling_performed':False,'production_binding_changed':False,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 p.save(H/'diagnosis.json',report);print(json.dumps({k:v for k,v in report.items()if k not in ['patches','consistent_grid_demands','image_gap_diagnostics']}))
if __name__=='__main__':main()
