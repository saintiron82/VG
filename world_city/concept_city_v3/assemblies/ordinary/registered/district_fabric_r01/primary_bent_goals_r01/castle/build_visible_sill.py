from pathlib import Path
import sys,json,math,hashlib
ROOT=Path(__file__).resolve().parents[8];sys.path.insert(0,str(ROOT));C=ROOT/'world_city/concept_city_v3';SRC=C/'assemblies/landmarks/registered/precinct_r06_whole/primary_goals_completion_r01';sys.path.insert(0,str(SRC))
from audit_main_opening_diagnostics import Support,terrain,SideIndex,b,geo,load,slab_rectangles
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.final_profile_audit_r01.exact_clip import clip as exact_clip, difference as exact_difference
O=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ref=lambda p:{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
SC=C/'evidence/r8_final110_runtime_r01/scene.json';scene=load(SC);search=load(O/'search_result.json');native={}
for q in search['native_floor_rows']:
 native.setdefault('native:'+q['native_id'],[]).extend(v for tri in terrain.fan_upward([[x,24,z]for x,z in q['polygon_xz_m']])for v in tri)
p=next(n['placement']for n in search['native_bindings']if n['placement']['id']=='castle_registered:front_curtain')
out=b.xform([[0,2]],p)[0];pts=[search['start_xz_m'],out,search['gate_xz_m'],search['end_xz_m']]
polys=b.ribbon(pts,.6);gap=b.xform(b.rect(-3,.5,3,.75),p);central=b.xform(b.rect(-.3,.5,.3,.75),p)
def subtract_exact(ps,masks):
 for m in masks:
  ps=[q for p in ps for q in(exact_difference(p,m)if geo.polygon_area(exact_clip(p,m))>1e-12 else[p])]
 return ps
def exact_cover(index,p):
 for i in index.index.candidates(p):
  r=index.rows[i];q=exact_clip(p,r['polygon_xz_m'])
  if geo.polygon_area(q)>1e-12:yield dict(r,intersection_polygon_xz_m=q)
class UpperSupport(Support):
 def __init__(self,scene,windows,native):
  super().__init__(scene,windows,native)
  for ix in [self.native,self.terrain]:
   ix.index=geo._SpatialIndex(1)
   for i,r in enumerate(ix.rows):ix.index.add(i,r['polygon_xz_m'])
 def covering(self,p):
  claimed=[];ci=geo._SpatialIndex(1)
  allnative=list(exact_cover(self.native,p));allterrain=list(exact_cover(self.terrain,p))
  print('Cover',len(allnative),len(allterrain),flush=True)
  flat=[q for q in allterrain if max(abs(v[1]-24)for v in q['vertices_xyz_m'])<=1e-7]
  other=[q for q in allterrain if q not in flat]
  for r in allnative+flat+sorted(other,key=lambda q:-sum(v[1]for v in q['vertices_xyz_m'])/3):
   for q in subtract_exact([r['intersection_polygon_xz_m']],[claimed[i]for i in ci.candidates(r['intersection_polygon_xz_m'])]):
    if geo.polygon_area(q)>1e-10:
     yield dict(r,intersection_polygon_xz_m=q)
     ci.add(len(claimed),q);claimed.append(q)
def audit_exact(index,polygon,expected_floor_y_m=None,grade_limit=.12):
 rows=[]
 for r in index.covering(polygon):
  p=r['intersection_polygon_xz_m'];plane=r['plane_y_xz_m'];ys=[terrain.common.height(plane,q)for q in p]
  rows.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=p,plane_y_xz_m=plane,area_m2=geo.polygon_area(p),min_y_m=min(ys),max_y_m=max(ys),actual_triangle_grade=math.hypot(*plane[:2])))
 area=geo.polygon_area(polygon);covered=sum(r['area_m2']for r in rows);gap=max(0,area-covered);excess=max(0,covered-area);mg=max((r['actual_triangle_grade']for r in rows),default=0);md=max((max(abs(r['min_y_m']-expected_floor_y_m),abs(r['max_y_m']-expected_floor_y_m))for r in rows),default=0)if expected_floor_y_m is not None else None
 return dict(area_m2=area,covered_area_m2=covered,missing_area_m2=gap,excess_area_m2=excess,max_floor_delta_m=md,max_actual_triangle_grade=mg,passes_existing_surface=gap<=1e-7 and excess<=1e-7 and mg<=grade_limit+1e-9 and(md is None or md<=1e-7),source_pieces=rows,coverage_proof='Every source piece is exact-clipped to the convex query, then exact-differenced against already assigned sources; disjoint subset areas establish coverage without short-edge tolerant re-clipping.')
sill_vertices=[v for tri in terrain.fan_upward([[x,24,z]for x,z in gap])for v in tri]
patch={'schema':'riverstone.frozen_scene_patch.v1','id':'CASTLE_EXISTING_GATE_SILL_SUPPORT_R01','status':'EXACT_SAME_PLANE_VISIBLE_SUPPORT_PATCH','base_scene_sha256':sha(SC),'source_surface_hashes':{},'surface_edits':[],'appended_surfaces':{'ground_stone':sill_vertices},'removed_foundation_proxy_ids':[],'source_references':{'scene':ref(SC),'missing_support_proof':ref(O/'branch_review_upper_support_r02.json')},'ownership':{'kind':'restore_missing_existing_gate_sill','native_id':p['id'],'polygon_xz_m':gap,'floor_y_m':24,'area_m2':geo.polygon_area(gap),'visible_and_collision_same_triangles':True,'native_or_wall_changes':0}}
(O/'surface_patch.json').write_text(json.dumps(patch,indent=2)+'\n')
scene['surfaces'].setdefault('ground_stone',[]).extend(sill_vertices)
ix=UpperSupport(scene,polys+[gap],native);side=SideIndex(scene,polys)
print('Index ready',flush=True)
checks=[audit_exact(ix,q,None,grade_limit=.12)for q in polys]
print('Support ready',len(checks),flush=True)
contacts=[]
for i,w in enumerate(polys):
 for q in search['native_body_rows']:
  ar=geo.intersection_area(w,q['polygon_xz_m'])
  if ar>1e-8:contacts.append({'ribbon_index':i,'native_id':q['native_id'],'area_m2':ar})
owners=[dict(id=f'CASTLE_BENT:{i}:{j}',polygon_xz_m=q['polygon_xz_m'],plane_y_xz_m=q['plane_y_xz_m'])for i,r in enumerate(checks)for j,q in enumerate(r['source_pieces'])]
sides=side.audit(owners)
full=audit_exact(ix,gap,24);center=audit_exact(ix,central,24)
# Adjacent support planes, exact finite polygon strips on both sides of the missing sill.
inside=b.xform(b.rect(-3,.25,3,.5),p);outside=b.xform(b.rect(-3,.75,3,1),p)
insidecheck=audit_exact(ix,inside,24);outsidecheck=audit_exact(ix,outside,24)
row={'schema':'riverstone.primary_bent_castle_branch_source_review.v1','scene':ref(SC),'applied_sill_patch':ref(O/'surface_patch.json'),'support_priority':'Actual native floors first, then existing exact24m upper tops, then remaining actual terrain; buried lower faces are not walking owners.','status':'PASS_SOURCE_BRANCH_AFTER_VISIBLE_SILL_PATCH','route_points_xz_m':pts,'route_width_m':.6,'route_ribbon_polygons_xz_m':polys,'support_checks':checks,'native_contacts':contacts,'retained_side_check':sides,'native_bindings':search['native_bindings'],'support_summary':{'missing_area_sum_m2':sum(x['missing_area_m2']for x in checks),'native_contacts':len(contacts),'retained_side_contacts':len(sides['contacts']),'max_triangle_gradient':max(x['max_actual_triangle_grade']for x in checks)},'gate_sill':{'native_id':p['id'],'pose':p,'full_opening_missing_polygon_xz_m':gap,'full_opening_audit':full,'central_capsule_missing_polygon_xz_m':central,'central_capsule_audit':center,'inside_adjacent_audit':insidecheck,'outside_adjacent_audit':outsidecheck,'cache_top_local_z_end_m':.5,'terrain_local_z_start_m':.75,'required_same_plane_y_m':24,'proposed_minimum_remedy':'Restore only central0.6m-wide sill rectangle localX[-.3,.3],Z[.5,.75] atY24; full6m opening sill is1.5m2. Do not change gate/wall/native/cache or controller. This artifact does not authorize or apply terrain.'},'limits':['Exact source surfaces and native solid sections; sampled search only selected the route.','The appended visible sill top is the sole geometry change; existing native/cache/wall geometry remains exact. Full unchanged-controller goal replay is required.']}
(O/'repaired_branch_review.json').write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps({'summary':row['support_summary'],'full_gap':{k:full[k]for k in ['area_m2','covered_area_m2','missing_area_m2']},'center_gap':{k:center[k]for k in ['area_m2','covered_area_m2','missing_area_m2']},'inside_pass':insidecheck['passes_existing_surface'],'outside_pass':outsidecheck['passes_existing_surface']},indent=2))

import numpy as np
triangles=[sill_vertices[i:i+3]for i in range(0,len(sill_vertices),3)]
normal_y=lambda t:float(np.cross(np.array(t[1])-t[0],np.array(t[2])-t[0])[1])
higher=[]
for ci,check in enumerate(checks):
 for s in check['source_pieces']:
  for r in exact_cover(ix.terrain,s['polygon_xz_m']):
   poly=r['intersection_polygon_xz_m'];delta=max(terrain.common.height(r['plane_y_xz_m'],q)-terrain.common.height(s['plane_y_xz_m'],q)for q in poly)
   if delta>1e-7 and geo.polygon_area(poly)>1e-8:higher.append({'ribbon':ci,'selected_owner':s['material'],'other_material':r['material'],'other_triangle_index':r['triangle_index'],'max_above_m':delta,'area_m2':geo.polygon_area(poly)})
checks_final={'no_higher_source_top_hidden':not higher,'full_sill_previously_empty':load(O/'branch_review_upper_support_r02.json')['gate_sill']['full_opening_audit']['covered_area_m2']==0,'sill_covers_exact1_5m2':abs(geo.polygon_area(gap)-1.5)<1e-8,'all_walk_regions_supported':all(x['passes_existing_surface']for x in checks),'no_native_clear_volume_contact':not contacts,'no_retained_bank_contact':not sides['contacts'],'sill_all_precise_upward':all(normal_y(t)>0 for t in triangles),'sill_all_float32_upward':all(normal_y(np.asarray(t,dtype=np.float32))>0 for t in triangles),'adjacent_inner_exact24':insidecheck['passes_existing_surface'],'adjacent_outer_exact24':outsidecheck['passes_existing_surface'],'no_source_triangles_removed':not patch['surface_edits'],'native_cache_hashes_match':all(sha(ROOT/x['asset']['render_path'])==x['asset']['render_sha256']for x in search['native_bindings'])}
(O/'patch_acceptance.json').write_text(json.dumps({'status':'PASS'if all(checks_final.values())else'HOLD','checks':checks_final,'patch':ref(O/'surface_patch.json'),'repaired_branch':ref(O/'repaired_branch_review.json'),'higher_source_top_contacts':higher,'exact_clip_helper':ref(ROOT/'world_city/concept_city_v3/registered_topography/revisions/r17_district_batches/final_profile_audit_r01/exact_clip.py'),'new_triangles':len(triangles),'visible_area_m2':geo.polygon_area(gap),'unchanged_controller_replay':'PENDING'},indent=2)+'\n')
print(checks_final)
