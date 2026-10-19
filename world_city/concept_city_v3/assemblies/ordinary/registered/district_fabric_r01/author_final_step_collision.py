"""Existing noble-style finite collision envelope for the one native step skin."""
from . import geometry as g
from .rebind_coherent_datums import require
from world_city.concept_city_v3.assemblies.landmarks.registered.precinct_r06_whole.residual_completion_r01.noble_entry_batch_r02.finite_collision_clip import clip3,cutprism,area3
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_integration.r8.runtime_precision import zero_mask
from world_city.concept_city_v3.registered_integration.r8.runtime_contracts import append_collision_contracts
import math,time
OUT=g.HERE/'final_pedestrian_step_skins_r01/collision_r01'
HANDOFF=g.HERE/'final_pedestrian_step_skins_r01/native_step_handoff.json'
SHA='3ff5084861d7907f91b5b50d6e0bf66d8a8fdbd4b49ba6198c301535e1d91480'
def normal(q):return g.np.cross(g.np.subtract(q[1],q[0]),g.np.subtract(q[2],q[0]))
def tris(q):return [[q[0],q[i+1],q[i]]for i in range(1,len(q)-1)if area3([q[0],q[i+1],q[i]])>1e-12]
def run():
 start=time.monotonic();assert g.ref(HANDOFF)['sha256']==SHA;h=g.load(HANDOFF);p=h['placements'][0];ass=h['assets'][p['asset_key']];assert p['yaw_rad']==0 and p['scale']==[1,1,1];cp=g.ROOT/ass['render_path'];assert g.ref(cp)['sha256']==ass['render_sha256'];native=g.load(cp);pose=p['position_m'];physical=h['physical_collision_triangles'];tops=h['native_top_sections'];corridor=h['physical_collision_domain_polygons_xz_m'];fi=g.geo._SpatialIndex(2);ui=g.geo._SpatialIndex(2);ci=g.geo._SpatialIndex(2)
 for i,r in enumerate(physical):fi.add(i,r['polygon_xz_m'])
 for i,r in enumerate(tops):ui.add(i,r['polygon_xz_m'])
 for i,q in enumerate(corridor):ci.add(i,q)
 def owns(q):return any(g.geo.point_in_convex_polygon(q,tops[j]['polygon_xz_m'],1e-8)for j in ui.candidates([q]))
 low=pose[1]+native['bounds']['min'][1]-.001;retained=[];ledger=[];lips=[];sourcearea=keptarea=removedarea=0.;preserved=0;bottoms=0
 for gi,group in enumerate(native['groups']):
  for qi,local in enumerate(group['quads']):
   q=[[v[k]+pose[k]for k in range(3)]for v in local];n=normal(q);A=area3(q);sourcearea+=A;up=n[1]>1e-9;vertical=abs(n[1])<1e-9;mid=g.np.mean(q,axis=0);nn=g.np.array([n[0],n[2]]);nn=nn/g.np.linalg.norm(nn)if g.np.linalg.norm(nn)>1e-9 else nn;internal=vertical and owns((mid[[0,2]]+nn*.0001).tolist())and owns((mid[[0,2]]-nn*.0001).tolist());px=[[v[0],v[2]]for v in q];box=g.rect(min(v[0]for v in px)-1e-7,min(v[1]for v in px)-1e-7,max(v[0]for v in px)+1e-7,max(v[1]for v in px)+1e-7);pieces=[q];kind='preserved_bottom'if n[1]<-1e-9 else'preserved_nonwalking_exterior'
   if up:
    kind='continuous_walking_top';remaining=fg.subtract([px],[physical[ix]['polygon_xz_m']for ix in fi.candidates(box)]);pieces=[[[x,q[0][1],z]for x,z in poly]for poly in remaining]
   elif internal:
    kind='continuous_internal_walking_riser'
    for ix in ci.candidates(box):
     nxt=[]
     for piece in pieces:
      outside,inside=cutprism(piece,corridor[ix]);nxt+=outside
      if inside:
       bottom=clip3(inside,lambda v:low-v[1])
       if bottom:nxt.append(bottom)
     pieces=nxt
   elif vertical:
    for ix in fi.candidates(box):
     nxt=[];field=physical[ix];pl=field['plane_y_xz_m']
     for piece in pieces:
      outside,inside=cutprism(piece,field['polygon_xz_m']);nxt+=outside
      if inside:
       below=clip3(inside,lambda v:a.common.height(pl,[v[0],v[2]])-v[1]);above=clip3(inside,lambda v:v[1]-a.common.height(pl,[v[0],v[2]]))
       if below:nxt.append(below)
       if above and area3(above)>1e-10:
        height=max(v[1]-a.common.height(pl,[v[0],v[2]])for v in above);assert height<=.1500001,('exterior lip',height);lips.append(dict(group_index=gi,quad_index=qi,removed_polygon_xyz_m=above,maximum_above_physical_floor_m=height,plane_y_xz_m=pl));kind='finite_walking_cap_lip'
     pieces=nxt
   kept=sum(area3(v)for v in pieces);removed=A-kept;assert removed>=-1e-7,(gi,qi,kind,A,kept);keptarea+=kept;removedarea+=removed
   if kind.startswith('preserved'):
    preserved+=1;assert abs(kept-A)<1e-8
    if kind=='preserved_bottom':bottoms+=1
   if removed>1e-8:ledger.append(dict(group_index=gi,quad_index=qi,kind=kind,source_quad_xyz_m=q,retained_polygons_xyz_m=pieces,removed_area_m2=removed))
   for piece in pieces:retained+=tris(piece)
 proxy=[]
 for r in physical:
  q=r['vertices_xyz_m'];proxy.append([q[0],q[2],q[1]]if normal(q)[1]>0 else q)
 combined=retained+proxy;assert abs(sourcearea-keptarea-removedarea)<1e-6
 _,runtime,cross,zero=zero_mask([v for t in combined for v in t]);keep=g.np.flatnonzero(~zero).tolist();drop=g.np.flatnonzero(zero).tolist();normalized=[combined[i]for i in keep];precision=[dict(source_triangle_index=i,source_triangle_xyz_m=combined[i],float32_vertices_xyz_m=runtime[i].tolist(),float32_cross_xyz=cross[i].tolist(),original_area3_m2=area3(combined[i]))for i in drop];assert all(normal(t)[1]<-1e-12 for t in proxy)
 OUT.mkdir(exist_ok=True);g.write(OUT/'source_collision_world.json',dict(triangles=combined,winding='direct Godot clockwise',retained_native_triangles=len(retained),walking_proxy_triangles=len(proxy)));g.write(OUT/'collision_world.json',dict(triangles=normalized,winding='direct Godot clockwise',source=g.ref(OUT/'source_collision_world.json'),precision_policy='Only exact zero float32 cross products are removed; every nonzero runtime triangle retains its source vertices.'));g.write(OUT/'runtime_precision_ledger.json',dict(source=g.ref(OUT/'source_collision_world.json'),runtime=g.ref(OUT/'collision_world.json'),removed=precision,predicate='Exact float32 cross product equals zero in all three components. No geometric area/width cutoff.',nonzero_source_triangles_unchanged=True))
 contract=dict(schema='riverstone.explicit_stair_collision_contract.v1',id='R8_ORDINARY_FINAL_B001_C003_FINE_STEPS',status='SOURCE_BOUND_FINITE_ENVELOPE_RUNTIME_REPLAY_PENDING',native_source=g.ref(cp),native_placement_id=p['id'],logical_collider_id_preserved=p['id'],disable_native_mesh_collider_ids=[p['id']],replacement_transform=dict(position_m=pose,yaw_rad=0.,scale=[1,1,1]),replacement_world_mesh=g.ref(OUT/'collision_world.json'),add_triangles_world_xyz_m=normalized,retained_native_triangle_count=sum(i<len(retained)for i in keep),walking_triangle_count=sum(i>=len(retained)for i in keep),walking_projected_area_m2=sum(g.geo.polygon_area(r['polygon_xz_m'])for r in physical),physical_envelope_band_width_m=2.,verified_walking_width_m=1.5,source_clear_width_m=2.,maximum_visual_above_collision_m=h['summary']['maximum_visible_above_physical_m'],maximum_collision_above_visual_m=h['summary']['maximum_physical_above_visible_m'],max_grade=max(r['gradient']for r in physical),explicit_private_grade_limit=.25,cart_access_claim=False,visual_native_asset_unchanged=True,native_side_guards_bottom_and_nonwalking_exterior_preserved=True,visible_native_end_faces_unchanged=True,public_walking_end_cap_collision_lips=lips,removed_native_face_ledger=ledger,physical_top=g.ref(HANDOFF),source_profile=h['selected_profile'],approved_pattern=g.ref(g.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02/author_collision.py'),exact_runtime_precision_normalization=g.ref(OUT/'runtime_precision_ledger.json'),runtime_ready=False)
 assert contract['max_grade']<=.2500001;g.write(OUT/'collision_contract.json',contract)
 # Exercise the unmodified integration contract loader against its exact cache.
 scene=dict(common_instances=[p],common_assets=h['assets']);loaded=append_collision_contracts(scene,[contract]);assert len(loaded['collision_contracts'])==1
 checks=dict(one_native_collider_disabled=contract['disable_native_mesh_collider_ids']==[p['id']],cache_bytes_unchanged=g.ref(cp)['sha256']==ass['render_sha256'],source_native_faces_partitioned=abs(sourcearea-keptarea-removedarea)<1e-6,bottom_faces_preserved=bottoms>0,continuous_top_exact_selected_field=len(proxy)==len(physical),all_runtime_triangles_nonzero=not g.np.any(zero_mask([v for t in normalized for v in t])[3]),direct_clockwise_proxy=True,existing_runtime_loader_accepts=True,approved_grade_limit_preserved=contract['max_grade']<=.2500001)
 audit=dict(schema='riverstone.final_step.finite_collision_audit.v1',native_handoff=g.ref(HANDOFF),contract=g.ref(OUT/'collision_contract.json'),checks=checks,passed=all(checks.values()),source_native_face_area_m2=sourcearea,retained_native_face_area_m2=keptarea,removed_walking_face_area_m2=removedarea,partition_error_m2=sourcearea-keptarea-removedarea,preserved_native_face_count=preserved,preserved_bottom_face_count=bottoms,removed_face_records=len(ledger),bounded_end_cap_lips=len(lips),exact_float32_zero_triangles_removed=len(drop),retained_native_triangles=contract['retained_native_triangle_count'],continuous_walking_triangles=contract['walking_triangle_count'],runtime_ready=False,author=g.ref(__file__),seconds=time.monotonic()-start);g.write(OUT/'audit.json',audit);g.write(OUT/'handoff.json',dict(collision_contract=g.ref(OUT/'collision_contract.json'),audit=g.ref(OUT/'audit.json'),native_step_handoff=g.ref(HANDOFF),frozen_native_source=g.ref(g.HERE/'final24_source_addendum_r01/atomic_source_addendum.json'),activation='Bind alongside the matching final23 native/terrain release. Runtime replay remains required.',new_compilations=0));print(audit,flush=True);print(g.ref(OUT/'handoff.json'),flush=True)
if __name__=='__main__':run()
