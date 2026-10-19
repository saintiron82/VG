"""Finite old-noble side retirement; preserves all other joint bank rows."""
from normalize_predecessors import *
from finite_collision_clip import cutprism,area3

JOINT_ID='R8_JOINT_61_BOUNDARY_NORTH_EXACT_REBOUND_FINAL_R01'
REVIEW=CITY/'registered_integration/r8/joint_boundary_r06/boundary_review.json'

def rebind(patch,domains):
 inputs=load(OUT/'tail_solve_inputs.json');windows={r['owner_id']:r['window_polygon_xz_m']for r in inputs['owners']if r['owner_id']!='E3'}
 review=load(REVIEW);oldseams={};seam_records=[]
 for s in review['boundary_seams']:
  other=s['other_owner'];oid=other[1].split(':')[0]if isinstance(other,list)and len(other)>1 and other[0]=='accepted_adjacent_owner'else None
  if oid not in windows or s['kind']!='nonwalking_retaining':continue
  e=s['edge_xz_m'];ys=s['owned_y_m'];zs=s['outside_y_m'];v=[[e[0][0],ys[0],e[0][1]],[e[1][0],ys[1],e[1][1]],[e[1][0],zs[1],e[1][1]],[e[0][0],zs[0],e[0][1]]]
  for t in ([v[0],v[1],v[2]],[v[0],v[2],v[3]]):
   if area3(t)>1e-10:oldseams[merger.canonical_sha(t)]=(oid,s)
 candidates=[];ix=geo._SpatialIndex(4)
 for r in domains:
  for oid,w in windows.items():
   q=fg.clip(r['polygon_xz_m'],w)
   if fg.area(q)>1e-12:ix.add(len(candidates),q);candidates.append((oid,q))
 result=copy.deepcopy(patch);ledger=[]
 for material,vs in patch['appended_surfaces'].items():
  out=[]
  for i in range(len(vs)//3):
   t=vs[3*i:3*i+3];h=merger.canonical_sha(t);matched=oldseams.get(h);poly=[[v[0],v[2]]for v in t]
   if not physical_side(t,material):out+=t;continue
   masks=[(oid,q,'new_finite_private_owned_domain')for j in ix.candidates(poly)for oid,q in[candidates[j]]]
   if matched:masks.append((matched[0],windows[matched[0]],'source_bound_old_noble_adjacency'))
   parts=[t];removed=[]
   for oid,mask,reason in masks:
    nxt=[]
    for piece in parts:
     outside,inside=cutprism(piece,mask);nxt+=outside
     if inside and area3(inside)>1e-12:removed.append(dict(owner_id=oid,reason=reason,polygon_xyz_m=inside,area_m2=area3(inside)))
    parts=nxt
   if not removed:out+=t;continue
   replacement=[[q[0],q[k],q[k+1]]for q in parts for k in range(1,len(q)-1)if area3([q[0],q[k],q[k+1]])>1e-12]
   removed_area=sum(r['area_m2']for r in removed);keep=sum(area3(q)for q in replacement);assert abs(area3(t)-removed_area-keep)<max(1e-9,area3(t)*1e-8),(i,area3(t),removed_area,keep)
   out +=[v for q in replacement for v in q];ledger.append(dict(material=material,triangle_index=i,old_triangle_sha256=h,source_triangle=t,retained_triangles=replacement,removed_side_area_m2=removed_area,removed_parts=removed,old_noble_boundary_seam=matched[1]if matched else None))
  result['appended_surfaces'][material]=out
 result['finite_noble_side_replacement']=dict(revision='R02_SIX_CHANGED_TAILS',source_boundary_review=ref(REVIEW),tail_domains=ref(OUT/'tail_solve_inputs.json'),replacement_retaining_patch=ref(OUT/'native_ground_candidate_patch.json'),policy='Only obsolete old-noble side portions in six changed tails or new private owned domains retire. Unaffected original and appended sides including north remain byte-value identical.')
 return result,dict(patch_id=patch['id'],records=ledger,source_boundary_review=ref(REVIEW),replacement_nonwalking_sides=ref(OUT/'native_ground_candidate_patch.json'),summary=dict(retired_appended_rows=len(ledger),removed_side_area_m2=sum(r['removed_side_area_m2']for r in ledger),matched_old_noble_rows=sum(r['old_noble_boundary_seam']is not None for r in ledger)))
