"""Rebind the approved finite tread-envelope contract to final R02 native cells."""
from pathlib import Path
import sys,json,copy,time,importlib.util,math,argparse
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent;OLD=OUT.with_name('noble_entry_batch_r01')
spec=importlib.util.spec_from_file_location('oldcollision',OLD/'author_collision.py');old=importlib.util.module_from_spec(spec);sys.path.insert(0,str(OLD));spec.loader.exec_module(old)
normal,area3,tris=old.normal,old.area3,old.tris
sys.path.insert(0,str(OUT))
from finite_collision_clip import clip3,cutprism
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg

def write(name,obj):p=OUT/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(obj,indent=2)+'\n');return ref(p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--owners',default='E1,E2,E3,E4,E5,E6,E7');args=ap.parse_args();started=time.monotonic();pack=load(OUT/'resolved_native_candidate.json');audit=load(OUT/'physical_profile_audit.json');contracts=[];audits=[];routes=copy.deepcopy(load(OLD/'runtime_routes.json'))
 for owner in pack['owners']:
  eid=owner['owner_id']
  if eid not in args.owners.split(','):continue
  p=next(p for p in pack['placements']if p['owner_id']==eid and p['role']=='fine_access');row=next(r for r in audit['owners']if r['owner_id']==eid);physical=load(ROOT/row['physical_top']['path'])['top_pieces'];oldcontract=load(OLD/f'contracts/{eid}_collision_contract.json')
  if eid=='E3':
   contracts.append(dict(owner_id=eid,contract=ref(OLD/f'contracts/{eid}_collision_contract.json')));audits.append(dict(owner_id=eid,status='EXACT_R01_UNCHANGED',source_contract=ref(OLD/f'contracts/{eid}_collision_contract.json')));continue
  window=next(r for r in pack['native_revision_ledger']if r['owner_id']==eid)['window_polygon_xz_m'];corridor=load(ROOT/row['physical_top']['path'])['corridor_polygons_xz_m'];ci=geo._SpatialIndex(4)
  for i,q in enumerate(corridor):ci.add(i,q)
  native=load(ROOT/p['cache']['path']);pose=p['position_m'];tops=row['actual_native_upward_faces'];ui=geo._SpatialIndex(4);fi=geo._SpatialIndex(2)
  for i,r in enumerate(tops):ui.add(i,r['polygon_xz_m'])
  for i,r in enumerate(physical):fi.add(i,r['polygon_xz_m'])
  def owns(q):return any(geo.point_in_convex_polygon(q,tops[j]['polygon_xz_m'],1e-8)for j in ui.candidates([q]))
  low=min(v[1]+pose[1]for g in native['groups']for q in g['quads']for v in q)-.001;retained=[];ledger=[];lips=[];sourcearea=keptarea=removedarea=0.;preserved=0
  for gi,g in enumerate(native['groups']):
   for qi,local in enumerate(g['quads']):
    q=[[v[k]+pose[k]for k in range(3)]for v in local];n=normal(q);A=area3(q);sourcearea+=A;up=n[1]>1e-9;vertical=abs(n[1])<1e-9;mid=np.mean(q,axis=0);nn=np.array([n[0],n[2]]);nn=nn/np.linalg.norm(nn)if np.linalg.norm(nn)>1e-9 else nn;internal=vertical and owns((mid[[0,2]]+nn*.0001).tolist())and owns((mid[[0,2]]-nn*.0001).tolist());px=[[v[0],v[2]]for v in q];box=b.rect(min(v[0]for v in px)-1e-7,min(v[1]for v in px)-1e-7,max(v[0]for v in px)+1e-7,max(v[1]for v in px)+1e-7);pieces=[q];kind='preserved_exterior'
    if up:
     kind='continuous_walking_top';remaining=fg.subtract([px],[physical[ix]['polygon_xz_m']for ix in fi.candidates(box)]);pieces=[[[x,q[0][1],z]for x,z in poly]for poly in remaining]
    elif internal:
     kind='continuous_walking_riser'
     for ix in ci.candidates(box):
      nxt=[]
      for piece in pieces:
       outside,inside=cutprism(piece,corridor[ix]);nxt+=outside
       if inside:
        bottom=clip3(inside,lambda v:low-v[1])
        if bottom:nxt.append(bottom)
      pieces=nxt
    elif vertical:
     untouched,within=cutprism(q,window);pieces=[within]if within else[]
     for ix in fi.candidates(box):
      nxt=[];field=physical[ix];pl=field['plane_y_xz_m']
      for piece in pieces:
       outside,inside=cutprism(piece,field['polygon_xz_m']);nxt+=outside
       if inside:
        below=clip3(inside,lambda v:terrain.common.height(pl,[v[0],v[2]])-v[1]);above=clip3(inside,lambda v:v[1]-terrain.common.height(pl,[v[0],v[2]]))
        if below:nxt.append(below)
        if above and area3(above)>1e-10:
         height=max(v[1]-terrain.common.height(pl,[v[0],v[2]])for v in above);assert height<=.1500001,(eid,'exterior tread exceeds envelope',height);lips.append(dict(group_index=gi,quad_index=qi,removed_polygon_xyz_m=above,maximum_above_physical_floor_m=height,plane_y_xz_m=pl));kind='finite_walking_cap_lip'
      pieces=nxt
     pieces=untouched+pieces
    kept=sum(area3(v)for v in pieces);removed=A-kept;assert removed>=-1e-7,(eid,gi,qi,kind,A,kept,q,pieces);keptarea+=kept;removedarea+=removed
    if kind=='preserved_exterior':preserved+=1;assert abs(kept-A)<1e-8
    if removed>1e-8:ledger.append(dict(group_index=gi,quad_index=qi,kind=kind,source_quad_xyz_m=q,retained_polygons_xyz_m=pieces,removed_area_m2=removed))
    for piece in pieces:retained+=tris(piece)
  proxy=[]
  for r in physical:
   q=[[x,terrain.common.height(r['plane_y_xz_m'],[x,z]),z]for x,z in r['polygon_xz_m']];proxy +=[[t[0],t[2],t[1]]for t in terrain.fan_upward(q)if float(np.linalg.norm(normal(t)))>1e-11]
  risers=[[t[0],t[2],t[1]]for t in row.get('native_proxy_riser_triangles_xyz_m',[])if area3(t)>1e-12];combined=retained+proxy+risers;assert abs(sourcearea-keptarea-removedarea)<1e-6;mesh=write(f'geometry/{eid}_collision_world.json',dict(schema='riverstone.finite_native_collision_replacement.v1',triangles=combined,winding='direct Godot clockwise',retained_native_triangles=len(retained),walking_proxy_triangles=len(proxy),explicit_private_riser_triangles=len(risers)));contract=copy.deepcopy(oldcontract);contract.update(id='R8_NOBLE_SEVEN_FINE_WALKING_R02:'+eid,native_source=p['cache'],native_placement_id=p['id'],logical_collider_id_preserved=p['id'],disable_native_mesh_collider_ids=[p['id']],replacement_transform=dict(position_m=pose,yaw_rad=p['yaw_rad'],scale=[1,1,1]),replacement_world_mesh=mesh,add_triangles_world_xyz_m=combined,retained_native_triangle_count=len(retained),walking_triangle_count=len(proxy),explicit_private_riser_triangle_count=len(risers),explicit_private_riser_source=ref(OUT/'physical_profile_audit.json'),walking_projected_area_m2=sum(geo.polygon_area(r['polygon_xz_m'])for r in physical),maximum_visual_above_collision_m=row['summary']['max_native_above_physical_m'],maximum_collision_above_visual_m=row['summary']['max_physical_above_native_m'],max_grade=max(math.hypot(*r['plane_y_xz_m'][:2])for r in physical),visual_native_asset_unchanged=False,visible_native_tail_reauthored=True,native_retained_base_unchanged=True,native_side_guards_bottom_and_nonwalking_exterior_preserved=True,public_walking_end_cap_collision_lips=lips,removed_native_face_ledger=ledger,physical_top=row['physical_top'],source_profile=ref(OUT/'physical_profile_audit.json'),superseded_source_contract=ref(OLD/f'contracts/{eid}_collision_contract.json'),runtime_ready=False);contract['explicit_private_grade_limit']=row['private_grade_limit'];assert contract['max_grade']<=row['private_grade_limit']+1e-7;cr=write(f'contracts/{eid}_collision_contract.json',contract);contracts.append(dict(owner_id=eid,contract=cr));audits.append(dict(owner_id=eid,source_area_m2=sourcearea,retained_area_m2=keptarea,removed_area_m2=removedarea,area_partition_error_m2=sourcearea-keptarea-removedarea,preserved_exterior_faces=preserved,retained_triangles=len(retained),proxy_triangles=len(proxy),explicit_private_riser_triangles=len(risers),max_grade=contract['max_grade']));route=next(r for r in routes['routes']if r['owner_id']==eid);route['native_fine_id']=p['id'];route['physical_top']=row['physical_top'];route['private_sampling_collar_source']=ref(OUT/'private_collars.json');print(eid,'collision',len(retained),len(proxy),flush=True)
 write('collision_contracts.json',dict(schema='riverstone.collision_contract_bundle.v1',id='R8_NOBLE_SEVEN_FINE_WALKING_R02',contracts=contracts));write('collision_audit.json',dict(owners=audits,seconds=time.monotonic()-started,runtime_ready=False));write('runtime_routes.json',routes)
if __name__=='__main__':main()
