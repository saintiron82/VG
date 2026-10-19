from pathlib import Path
import sys,json,math,hashlib
ROOT=Path(__file__).resolve().parents[8];sys.path.insert(0,str(ROOT));C=ROOT/'world_city/concept_city_v3';SRC=C/'assemblies/landmarks/registered/precinct_r06_whole/primary_goals_completion_r01';sys.path.insert(0,str(SRC))
from audit_main_opening_diagnostics import Support,terrain,SideIndex,b,geo,load,slab_rectangles
O=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ref=lambda p:{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
SC=C/'evidence/r8_final110_runtime_r01/scene.json';scene=load(SC);search=load(O/'search_result.json');native={}
for q in search['native_floor_rows']:
 native.setdefault('native:'+q['native_id'],[]).extend(v for tri in terrain.fan_upward([[x,24,z]for x,z in q['polygon_xz_m']])for v in tri)
p=next(n['placement']for n in search['native_bindings']if n['placement']['id']=='castle_registered:front_curtain')
out=b.xform([[0,2]],p)[0];pts=[search['start_xz_m'],out,search['gate_xz_m'],search['end_xz_m']]
polys=b.ribbon(pts,.6);gap=b.xform(b.rect(-3,.5,3,.75),p);central=b.xform(b.rect(-.3,.5,.3,.75),p)
class UpperSupport(Support):
 def covering(self,p):
  claimed=[]
  allnative=list(self.native.covering(p));allterrain=list(self.terrain.covering(p))
  flat=[q for q in allterrain if max(abs(v[1]-24)for v in q['vertices_xyz_m'])<=1e-7]
  other=[q for q in allterrain if q not in flat]
  for r in allnative+flat+sorted(other,key=lambda q:-sum(v[1]for v in q['vertices_xyz_m'])/3):
   for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
    if geo.polygon_area(q)>1e-10:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)
ix=UpperSupport(scene,polys+[gap],native);side=SideIndex(scene,polys)
checks=[terrain.audit_polygon(ix,q,None,grade_limit=.12)for q in polys]
contacts=[]
for i,w in enumerate(polys):
 for q in search['native_body_rows']:
  ar=geo.intersection_area(w,q['polygon_xz_m'])
  if ar>1e-8:contacts.append({'ribbon_index':i,'native_id':q['native_id'],'area_m2':ar})
owners=[dict(id=f'CASTLE_BENT:{i}:{j}',polygon_xz_m=q['polygon_xz_m'],plane_y_xz_m=q['plane_y_xz_m'])for i,r in enumerate(checks)for j,q in enumerate(r['source_pieces'])]
sides=side.audit(owners)
full=terrain.audit_polygon(ix,gap,24);center=terrain.audit_polygon(ix,central,24)
# Adjacent support planes, exact finite polygon strips on both sides of the missing sill.
inside=b.xform(b.rect(-3,.25,3,.5),p);outside=b.xform(b.rect(-3,.75,3,1),p)
insidecheck=terrain.audit_polygon(ix,inside,24);outsidecheck=terrain.audit_polygon(ix,outside,24)
row={'schema':'riverstone.primary_bent_castle_branch_source_review.v1','scene':ref(SC),'status':'HELD_EXACT_GATE_SILL_SUPPORT_GAP','route_points_xz_m':pts,'route_width_m':.6,'route_ribbon_polygons_xz_m':polys,'support_checks':checks,'native_contacts':contacts,'retained_side_check':sides,'native_bindings':search['native_bindings'],'support_summary':{'missing_area_sum_m2':sum(x['missing_area_m2']for x in checks),'native_contacts':len(contacts),'retained_side_contacts':len(sides['contacts']),'max_triangle_gradient':max(x['max_actual_triangle_grade']for x in checks)},'gate_sill':{'native_id':p['id'],'pose':p,'full_opening_missing_polygon_xz_m':gap,'full_opening_audit':full,'central_capsule_missing_polygon_xz_m':central,'central_capsule_audit':center,'inside_adjacent_audit':insidecheck,'outside_adjacent_audit':outsidecheck,'cache_top_local_z_end_m':.5,'terrain_local_z_start_m':.75,'required_same_plane_y_m':24,'proposed_minimum_remedy':'Restore only central0.6m-wide sill rectangle localX[-.3,.3],Z[.5,.75] atY24; full6m opening sill is1.5m2. Do not change gate/wall/native/cache or controller. This artifact does not authorize or apply terrain.'},'limits':['Exact source surfaces and native solid sections; sampled search only selected the route.','The small gap prevents supported unchanged-controller extraction as an accepted chain until explicitly repaired. No geometry changed.']}
(O/'branch_review_upper_support_r02.json').write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps({'summary':row['support_summary'],'full_gap':{k:full[k]for k in ['area_m2','covered_area_m2','missing_area_m2']},'center_gap':{k:center[k]for k in ['area_m2','covered_area_m2','missing_area_m2']},'inside_pass':insidecheck['passes_existing_surface'],'outside_pass':outsidecheck['passes_existing_surface']},indent=2))
