"""Bounded exact upper-envelope proof; immutable base and existing sill sidecar."""
from pathlib import Path
import sys,json,math,hashlib,time
import numpy as np
O=Path(__file__).resolve().parent;ROOT=next(p for p in O.parents if (p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));C=ROOT/'world_city/concept_city_v3'
sys.path.insert(0,str(C/'assemblies/landmarks/registered/precinct_r06_whole/primary_goals_completion_r01'))
from audit_main_opening_diagnostics import terrain,SideIndex,b,geo,load,slab_rectangles
sys.path.insert(0,str(O.parent/'abbey'))
from upper_surface_support import Support,exact_subtract
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.final_profile_audit_r01.exact_clip import clip
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:dict(path=str(p.relative_to(ROOT)),sha256=SHA(p));write=lambda n,d:(O/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def area(p):return geo.polygon_area(p)if len(p)>=3 else 0.
def circle(p,n=32):
 r=.3/math.cos(math.pi/n);return[[p[0]+r*math.cos(2*math.pi*j/n),p[1]+r*math.sin(2*math.pi*j/n)]for j in range(n)]
def audit(index,poly,datum=None):
 rows=[]
 for r in index.covering(poly):
  q=r['intersection_polygon_xz_m'];plane=r['plane_y_xz_m'];ys=[terrain.common.height(plane,p)for p in q]
  rows.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=q,plane_y_xz_m=plane,area_m2=area(q),min_y_m=min(ys),max_y_m=max(ys),actual_triangle_grade=math.hypot(*plane[:2])))
 ar=area(poly);covered=sum(x['area_m2']for x in rows);gap=max(0,ar-covered);excess=max(0,covered-ar);mg=max((r['actual_triangle_grade']for r in rows),default=0);md=max((max(abs(r['min_y_m']-datum),abs(r['max_y_m']-datum))for r in rows),default=0)if datum is not None else None
 return dict(area_m2=ar,covered_area_m2=covered,missing_area_m2=gap,excess_area_m2=excess,max_actual_triangle_grade=mg,max_floor_delta_m=md,passes_existing_surface=gap<=1e-7 and excess<=1e-7 and mg<=.120000001 and(md is None or md<=1e-7),source_pieces=rows)
def main():
 started=time.monotonic();SC=C/'evidence/r8_final110_runtime_r01/scene.json';scene=load(SC);assert SHA(SC)=='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
 patch=load(O/'surface_patch.json');assert SHA(O/'surface_patch.json')=='b230ba1592cb285382996907ec39ba0b0d127765acc434285b1557de6bb7d1d3';scene['surfaces'].setdefault('ground_stone',[]).extend(patch['appended_surfaces']['ground_stone'])
 old=load(O/'search_result.json');p=next(n['placement']for n in old['native_bindings']if n['placement']['id']=='castle_registered:front_curtain');pts=[old['start_xz_m'],b.xform([[0,2]],p)[0],old['gate_xz_m'],old['end_xz_m']]
 threshold=[-298.58587663222653,-238.73298525158293];polys=[]
 for i,(a,c)in enumerate(zip(pts,pts[1:])):
  parts=np.linspace(a,c,max(2,math.ceil(math.dist(a,c)/2)+1)).tolist()
  polys.extend(dict(id=f'SEG:{i}:{j}',kind='finite_segment_strip',polygon_xz_m=q)for j,q in enumerate(b.ribbon(parts,.6)))
 polys.extend([dict(id='THRESHOLD_WITNESS',kind='standing_to_actual_door_threshold',polygon_xz_m=b.ribbon([pts[-1],threshold],.6)[0]),dict(id='THRESHOLD_CAP',kind='circumscribed_32gon',polygon_xz_m=circle(threshold))]);polys.extend(dict(id=f'CAP:{i}',kind='circumscribed_32gon',polygon_xz_m=circle(q))for i,q in enumerate(pts));wins=[r['polygon_xz_m']for r in polys]
 native={};bindings=[];meshes={};refs=[]
 for pl in scene['common_instances']:
  a=scene['common_assets'][pl['asset_key']];mesh=meshes.setdefault(a['render_path'],None);bb=a.get('bounds')
  if bb is None:
   if mesh is None:mesh=meshes[a['render_path']]=load(ROOT/a['render_path'])
   bb=mesh['bounds']
  py=pl['position_m'][1]
  if bb['max'][1]+py<23 or bb['min'][1]+py>26.2:continue
  wp=b.xform(b.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),pl)
  if not any(area(clip(w,wp))>1e-8 for w in wins):continue
  if mesh is None:mesh=meshes[a['render_path']]=load(ROOT/a['render_path'])
  assert SHA(ROOT/a['render_path'])==a['render_sha256'];assert SHA(ROOT/a['master_path'])==a['master_sha256']
  bindings.append(dict(placement=pl,asset=a,world_bounds_xz_m=wp));vs=[]
  for gi,g in enumerate(mesh['groups']):
   for qi,q in enumerate(g['quads']):
    if max(v[1]for v in q)-min(v[1]for v in q)>1e-8 or abs(q[0][1]+py-24)>1e-7:continue
    ny=(q[1][2]-q[0][2])*(q[2][0]-q[0][0])-(q[1][0]-q[0][0])*(q[2][2]-q[0][2])
    if ny<=0:continue
    world=b.xform([[v[0],v[2]]for v in q],pl)
    for tr in terrain.fan_upward([[x,24,z]for x,z in world]):
     refs.append(dict(native_id=pl['id'],triangle_index=len(vs)//3,group_index=gi,quad_index=qi,source_quad_sha256=terrain.canonical_sha(q),local_source_quad_xyz_m=q,world_triangle_xyz_m=tr));vs.extend(tr)
  if vs:native['native:'+pl['id']]=vs
 print('Native',len(bindings),'tube parts',len(polys),time.monotonic()-started,flush=True)
 ix=Support(scene,wins,native);side=SideIndex(scene,wins);checks=[];owners=[];contacts=[];slabs={}
 for part in polys:
  r=audit(ix,part['polygon_xz_m']);checks.append(dict(**part,**r));fmin=min(x['min_y_m']for x in r['source_pieces']);fmax=max(x['max_y_m']for x in r['source_pieces'])
  for j,x in enumerate(r['source_pieces']):
   owners.append(dict(id=part['id']+':'+str(j),polygon_xz_m=x['polygon_xz_m'],plane_y_xz_m=x['plane_y_xz_m']))
   for bn in bindings:
    if area(clip(x['polygon_xz_m'],bn['world_bounds_xz_m']))<=1e-8:continue
    pl=bn['placement'];a=bn['asset'];lo=fmin-pl['position_m'][1]+.01;hi=fmax-pl['position_m'][1]+2.2;key=(pl['id'],round(lo,9),round(hi,9))
    if key not in slabs:slabs[key]=[b.xform(q,pl)for q in slab_rectangles(meshes[a['render_path']],lo,hi)]
    for k,q in enumerate(slabs[key]):
     ar=area(clip(x['polygon_xz_m'],q))
     if ar>1e-8:contacts.append(dict(part_id=part['id'],native_id=pl['id'],body_piece=k,area_m2=ar))
  print(part['id'],r['passes_existing_surface'],len(r['source_pieces']),time.monotonic()-started,flush=True)
 banks=side.audit(owners);higher=[]
 for owner in owners:
  for index in[ix.terrain,ix.native]:
   for rr in index.covering(owner['polygon_xz_m']):
    q=rr['intersection_polygon_xz_m']
    if area(q)<=1e-8:continue
    delta=max(terrain.common.height(rr['plane_y_xz_m'],v)-terrain.common.height(owner['plane_y_xz_m'],v)for v in q)
    if delta>1e-7:higher.append(dict(owner=owner['id'],other_material=rr['material'],other_triangle_index=rr['triangle_index'],max_above_m=delta,polygon_xz_m=q))
 boxes=[]
 for box in scene['boxes']:
  x,y,z=box['position_m'];w,h,l=box['size_m'];bp=b.xform(b.rect(-w/2,-l/2,w/2,l/2),box)
  if not any(area(clip(wp,bp))>1e-8 for wp in wins):continue
  for owner in owners:
   q=clip(owner['polygon_xz_m'],bp)
   if area(q)<=1e-8:continue
   ys=[terrain.common.height(owner['plane_y_xz_m'],v)for v in q]
   if y+h/2>min(ys)+.01+1e-8 and y-h/2<max(ys)+2.2-1e-8:boxes.append(dict(box_id=box['id'],owner=owner['id'],polygon_xz_m=q))
 sampled=[]
 for a,c in zip(pts,pts[1:]):
  for q in np.linspace(a,c,max(2,math.ceil(math.dist(a,c))+1)).tolist()[:-1]:
   candidates=[]
   for index in[ix.terrain,ix.native]:
    for j in index.index.candidates(circle(q)):
     rr=index.rows[j]
     if geo.point_in_convex_polygon(q,rr['polygon_xz_m'],1e-8):candidates.append((terrain.common.height(rr['plane_y_xz_m'],q),rr))
   y,r=max(candidates,key=lambda x:x[0]);sampled.append(dict(point_xyz_m=[q[0],y,q[1]],material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256']))
 sampled.append(dict(point_xyz_m=[pts[-1][0],24,pts[-1][1]],kind='actual_source_door_exterior'))
 passed=all(c['passes_existing_surface']for c in checks)and not contacts and not banks['contacts']and not higher and not boxes
 summary=dict(status='FINITE_SOURCE_PASS_RUNTIME_PENDING'if passed else'HOLD',passed=passed,parts=len(checks),native_contacts=len(contacts),bank_contacts=len(banks['contacts']),higher_source_contacts=len(higher),box_contacts=len(boxes),missing_area_m2=sum(c['missing_area_m2']for c in checks),max_triangle_grade=max(c['max_actual_triangle_grade']for c in checks),route_length_m=sum(math.dist(a,c)for a,c in zip(pts,pts[1:])),seconds=time.monotonic()-started)
 proof=dict(schema='riverstone.castle_bent_route_finite_proof.v1',scene=ref(SC),visible_patch=ref(O/'surface_patch.json'),collision_addendum=ref(O/'sill_collision_addendum.json'),upper_envelope_helper=ref(O.parent/'abbey/upper_surface_support.py'),summary=summary,polyline_xyz_m=[[q[0],24,q[1]]for q in pts],width_m=.6,capsule_radius_m=.3,headroom_m=2.2,floor_contact_allowance_m=.01,threshold_world_xyz_m=[threshold[0],24,threshold[1]],support_selection='Exact pointwise upper envelope; source-only overlap selection. No geometry changes beyond separately bound 1.5 m2 sill.',support_checks=checks,native_bindings=bindings,native_floor_source_refs=refs,native_contacts=contacts,terrain_side_check=banks,higher_source_contacts=higher,explicit_box_clearance=dict(total_scene_boxes=len(scene['boxes']),contacts=boxes),source_selection_diagnostic=ref(O/'patch_acceptance.json'),limitations=['Source finite geometry proof; unchanged-controller goal replay is pending.'])
 write('final_branch_proof.json',proof);write('final_branch_summary.json',dict(proof=ref(O/'final_branch_proof.json'),**summary));write('surface_snapped_profile.json',dict(scene=ref(SC),visible_patch=ref(O/'surface_patch.json'),proof=ref(O/'final_branch_proof.json'),points=sampled));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
