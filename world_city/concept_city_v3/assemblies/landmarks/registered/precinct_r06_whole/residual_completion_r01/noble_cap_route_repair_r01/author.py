"""Finite old-cap ground correction within already solved noble private tails."""
from pathlib import Path
import sys,json,time,math,copy
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];N=OUT.parent/'noble_entry_batch_r02';sys.path.insert(0,str(BASE));sys.path.insert(0,str(N))
from resolve_pack import *
from finite_collision_clip import area3,cutprism,clip3
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.coherent_b15_r01.compose_cluster import interfaces
from world_city.concept_city_v3.registered_integration.r8 import compose_finite_patches as compose
from world_city.concept_city_v3.registered_integration.r6 import merge_patches as merger
OUT=Path(__file__).resolve().parent;N=OUT.parent/'noble_entry_batch_r02';R18=CITY/'registered_topography/revisions/public_corridors_r18';NORTH=R18/'north_junction_transition_r01'

def write(n,d):p=OUT/n;p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n');return ref(p)
def lift(q,p):return[[v[0],terrain.common.height(p,v),v[1]]for v in q]
def fan(p):return[[p[0],p[i],p[i+1]]for i in range(1,len(p)-1)if area3([p[0],p[i],p[i+1]])>1e-12]
def tri_sha(t):return merger.canonical_sha(t)
def xz(t):return[[v[0],v[2]]for v in t]
def main():
 start=time.monotonic();cap_path=R18/'public_top_r03_native_bound/physical_owners.json';caps=[r for r in load(cap_path)['owners']if r['kind']=='nonwalking_private_cap_remainder'];profile_path=N/'physical_profile_audit.json';profiles={r['owner_id']:r for r in load(profile_path)['owners']};owners=[];cap_remainders=[];cap_rows=[]
 for cap in caps:
  eid=cap['id'].split(':')[0];claimed=[]
  for fi,f in enumerate(profiles[eid]['private_field_pieces']):
   pp=fg.clip(cap['polygon_xz_m'],f['polygon_xz_m'])
   if fg.area(pp)<=1e-12:continue
   for q in fg.subtract([pp],claimed):
    if fg.area(q)<=1e-12:continue
    claimed.append(q);owners.append(dict(id='R03_CAP_APPROACH:'+str(len(owners)),owner_id=eid,cap_id=cap['id'],polygon_xz_m=q,plane_y_xz_m=f['plane_y_xz_m'],old_plane_y_xz_m=cap['plane_y_xz_m'],selected_profile_piece_index=fi,material='ground_stone',action='field',kind='selected_private_tail_floor'))
  rem=fg.subtract([cap['polygon_xz_m']],claimed);cap_remainders +=[dict(cap,polygon_xz_m=q)for q in rem if fg.area(q)>1e-12];cap_rows.append(dict(cap=cap,new_owner_ids=[r['id']for r in owners if r['cap_id']==cap['id']],old_area_m2=fg.area(cap['polygon_xz_m']),new_area_m2=sum(fg.area(q)for q in claimed),retained_old_area_m2=sum(fg.area(q)for q in rem),retained_polygons_xz_m=rem))
 oi=geo._SpatialIndex(1)
 for i,r in enumerate(owners):oi.add(i,r['polygon_xz_m'])
 # New fields must not overlap any actually emitted fine top, collar or public floor.
 native=load(N/'native_ground_candidate_audit.json');existing=native['new_native_upward_faces']+native['private_sampling_collars']+load(R18/'finite_field_candidate_r07_native_bound.json')['records'];existing_ix=geo._SpatialIndex(2)
 for i,r in enumerate(existing):existing_ix.add(i,r['polygon_xz_m'])
 conflicts=[]
 for o in owners:
  for j in existing_ix.candidates(o['polygon_xz_m']):
   ar=fg.area(fg.clip(o['polygon_xz_m'],existing[j]['polygon_xz_m']))
   if ar>1e-8:conflicts.append(dict(new_owner=o['id'],existing_owner=existing[j].get('id'),area_m2=ar))
 assert not conflicts,conflicts[:4]
 print('owners',len(owners),'area',sum(fg.area(o['polygon_xz_m'])for o in owners),flush=True)
 source_paths={15:R18/'runtime_local_remnants_r02/producer_15.json',16:R18/'runtime_local_remnants_r02/producer_16.json',22:NORTH/'producer_22.json'};sources={i:load(p)for i,p in source_paths.items()};top=copy.deepcopy(sources[15]);oldvs=top['appended_surfaces']['ground_stone'];newvs=[];top_rows=[]
 for ti in range(len(oldvs)//3):
  t=oldvs[ti*3:ti*3+3];q=xz(t)
  if not oi.candidates(q)or fg.area(q)<=1e-12:newvs+=t;continue
  pl=[0,0,t[0][1]]if max(v[1]for v in t)-min(v[1]for v in t)<1e-10 else terrain.common.plane(t);masks=[owners[j]['polygon_xz_m']for j in oi.candidates(q)if max(abs(terrain.common.height(pl,v)-terrain.common.height(owners[j]['old_plane_y_xz_m'],v))for v in owners[j]['polygon_xz_m'])<1e-6];out=fg.subtract([q],masks);before=fg.area(q);after=sum(fg.area(p)for p in out)
  if before-after>1e-12:
   repl=[tr for p in out for tr in terrain.fan_upward(lift(p,pl))];top_rows.append(dict(material='ground_stone',appended_triangle_index=ti,source_triangle_sha256=tri_sha(t),source_triangle_xyz_m=t,replacement_triangles_xyz_m=repl,removed_projection_area_m2=before-after));newvs +=[v for tr in repl for v in tr]
  else:newvs+=t
 top['appended_surfaces']['ground_stone']=newvs;top['finite_noble_cap_repair']=dict(source_patch=ref(source_paths[15]),physical_owner_source=ref(cap_path),selected_profile_source=ref(profile_path),policy='Only obsolete cap-top fractions inside existing selected private-tail domains retired; new floor supplied by separate finite patch. All R18 road tops exact.')
 top_ref=write('public_cap_top_wrapper.json',top)
 # Three-dimensional clipping retains every side portion below the new floor
 # and outside the exact changed cap prism. No XZ area test discards a wall.
 side_requests=[];remaining_sides=[];retired_sides=[]
 for pi in (16,22):
  patch=sources[pi];vs=patch['appended_surfaces'].get('bank',[]);rows=[];outvs=[]
  for ti in range(len(vs)//3):
   t=vs[3*ti:3*ti+3];remaining=[t];removed=[]
   for j in oi.candidates(xz(t)):
    o=owners[j];nextparts=[]
    for pp in remaining:
     outside,inside=cutprism(pp,o['polygon_xz_m']);nextparts+=outside
     if not inside:continue
     below=clip3(inside,lambda v:terrain.common.height(o['plane_y_xz_m'],[v[0],v[2]])-v[1]);above=clip3(inside,lambda v:terrain.common.height(o['plane_y_xz_m'],[v[0],v[2]])-v[1],False);nextparts+=([below]if below else[])
     if above:
      cut=clip3(above,lambda v:terrain.common.height(o['old_plane_y_xz_m'],[v[0],v[2]])-v[1]);over=clip3(above,lambda v:terrain.common.height(o['old_plane_y_xz_m'],[v[0],v[2]])-v[1],False)
      if over:nextparts.append(over)
      if cut:removed.append(dict(owner_id=o['id'],polygon_xyz_m=cut))
    remaining=nextparts
   ar=sum(area3(r['polygon_xyz_m'])for r in removed)
   if ar>1e-10:
    repl=[tr for pp in remaining for tr in fan(pp)];before=area3(t);after=sum(area3(tr)for tr in repl);assert abs(before-after-ar)<1e-6,(pi,ti,before,after,ar)
    rows.append(dict(material='bank',appended_triangle_index=ti,source_triangle_sha256=tri_sha(t),source_triangle_xyz_m=t,replacement_triangles_xyz_m=repl,retired_polygons=removed,retired_area3_m2=ar));outvs +=[v for tr in repl for v in tr];retired_sides+=rows[-1:]
   else:outvs+=t
  for i in range(0,len(outvs),3):remaining_sides.append(dict(patch_index=pi,triangle=outvs[i:i+3]))
  side_requests.append(dict(binding_patch_index=pi,source_patch=ref(source_paths[pi]),source_patch_id=patch['id'],source_bank_array_sha256=tri_sha(vs),source_rows=rows))
  if pi==22:
   wrapper=copy.deepcopy(patch);wrapper['appended_surfaces']['bank']=outvs;wrapper['finite_cap_side_rebind']=dict(source_patch=ref(source_paths[pi]),policy='Exact changed cap prisms only; below-profile and outside-domain side portions retained.');write('cap_side_wrapper.json',wrapper)
  print('side rows',pi,len(rows),'area',sum(r['retired_area3_m2']for r in rows),flush=True)
 # Exact neighboring physical floors, with native upper faces before terrain.
 contexts=native['new_native_upward_faces']+native['retained_base_upward_faces']+native['private_sampling_collars']+load(R18/'finite_field_candidate_r07_native_bound.json')['records']+cap_remainders
 class Context:pass
 ix=Context();ix.rows=[];ix.index=geo._SpatialIndex(2)
 for r in contexts:
  candidates=oi.candidates(r['polygon_xz_m'])
  if not candidates:continue
  if not any(fg.area(fg.clip(r['polygon_xz_m'],b.rect(min(v[0]for v in o['polygon_xz_m'])-.02,min(v[1]for v in o['polygon_xz_m'])-.02,max(v[0]for v in o['polygon_xz_m'])+.02,max(v[1]for v in o['polygon_xz_m'])+.02)))>1e-12 for o in [owners[i]for i in candidates]):continue
  rr=dict(r,material='physical_neighbor:'+r.get('id','native'),triangle_index=len(ix.rows));ix.index.add(len(ix.rows),rr['polygon_xz_m']);ix.rows.append(rr)
 closure=interfaces({'surfaces':{}},ix,owners);print('seams',len(closure['boundary_seams']),'unknown',len(closure['unknown_exterior_segments']),flush=True)
 # Native side solids already visibly close many small terrain/tread joins.
 native_sides=[]
 for p in load(N/'resolved_native_candidate.json')['placements']:
  if p['owner_id']not in ('E1','E2'):continue
  for gi,g in enumerate(load(ROOT/p['cache']['path'])['groups']):
   for qi,q in enumerate(g['quads']):
    if abs(terrain.normal_y(q[:3]))>1e-8:continue
    x=b.xform([[v[0],v[2]]for v in q],p);qq=[[x[k][0],v[1]+p['position_m'][1],x[k][1]]for k,v in enumerate(q)];native_sides.append(dict(native_id=p['id'],group_index=gi,quad_index=qi,triangle=qq))
 side_context=remaining_sides+native_sides;si=geo._SpatialIndex(1)
 for i,r in enumerate(side_context):si.add(i,xz(r['triangle']))
 newbanks=[];bank_proof=[]
 for tr in closure['appended_retaining_triangles_xyz_m']:
  n,L,d,project,unproject=compose.project_frame(tr);poly=[project(v)for v in tr];masks=[];covered=[]
  for j in si.candidates(xz(tr)):
   rr=side_context[j];q=rr['triangle']
   if max(abs(compose.dot(n,v)-d)/L for v in q)>1e-8:continue
   pp=[project(v)for v in q];hit=fg.clip(poly,pp)
   if fg.area(hit)>1e-12:masks.append(pp);covered.append({k:v for k,v in rr.items()if k!='triangle'})
  rem=fg.subtract([poly],masks);added=[]
  for q in rem:
   vv=[unproject(v)for v in q]
   for t in fan(vv):
    if compose.dot(n,compose.cross(compose.sub(t[1],t[0]),compose.sub(t[2],t[0])))<0:t=[t[0],t[2],t[1]]
    added.append(t)
  newbanks+=added;bank_proof.append(dict(desired_triangle_xyz_m=tr,existing_side_coverage=covered,added_triangles_xyz_m=added))
 fields=[v for o in owners for tr in terrain.fan_upward(lift(o['polygon_xz_m'],o['plane_y_xz_m']))for v in tr];patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R8_NOBLE_E1_E2_CAP_APPROACH_FIELDS_R03',status='SOURCE_CANDIDATE_REQUIRES_EXACT_SHARED_WRAPPER',base_scene_sha256=terrain.SCENE_SHA256,source_surface_hashes={},surface_edits=[],appended_surfaces={'ground_stone':fields,'bank':[v for tr in newbanks for v in tr]},removed_foundation_proxy_ids=[],source_references=[ref(profile_path),ref(cap_path),top_ref],runtime_ready=False)
 write('finite_surface_patch.json',patch);write('physical_owners.json',dict(owners=owners,retained_old_cap_pieces=cap_remainders,source_profile=ref(profile_path),old_cap_source=ref(cap_path)));write('top_retirement_request.json',dict(source_patch=ref(source_paths[15]),replacement_patch=top_ref,source_rows=top_rows));write('side_retirement_requests.json',dict(requests=side_requests,shared_joint_policy='Verifier composes only these exact indexed/hash-bound appended-bank replacements into its latest joint copy; original source-edit rows and north append additions must remain untouched.'))
 write('boundary_review.json',dict(context_rows=ix.rows,boundary_seams=closure['boundary_seams'],unknown_exterior_segments=closure['unknown_exterior_segments'],new_side_proof=bank_proof));write('author_report.json',dict(cap_rows=cap_rows,old_total_area_m2=sum(r['old_area_m2']for r in cap_rows),new_floor_area_m2=sum(fg.area(o['polygon_xz_m'])for o in owners),retained_cap_area_m2=sum(fg.area(o['polygon_xz_m'])for o in cap_remainders),source_top_rows=len(top_rows),source_top_retired_area_m2=sum(r['removed_projection_area_m2']for r in top_rows),side_retired_rows=len(retired_sides),side_retired_area_m2=sum(r['retired_area3_m2']for r in retired_sides),new_bank_triangles=len(newbanks),new_bank_area_m2=sum(area3(t)for t in newbanks),unknown_edges=len(closure['unknown_exterior_segments']),existing_floor_conflicts=conflicts,seconds=time.monotonic()-start));print('DONE',load(OUT/'author_report.json')|{'cap_rows':'omitted'},flush=True)
if __name__=='__main__':main()
