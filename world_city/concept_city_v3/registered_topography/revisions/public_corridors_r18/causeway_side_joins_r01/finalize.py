"""Immutable producer-row retirement and explicit actual native-apron closure."""
import json,copy,math,collections,time
from .author import *
from ...r17_district_batches.side_clearance import area3d

def wall(row,owner):
 u,v=row['edge_xz_m'];ys=row['owned_y_m'];zs=row['outside_y_m'];poly=owner['polygon_xz_m'];sgn=1 if g.signed_area(poly)>0 else -1;dx,dz=v[0]-u[0],v[1]-u[1];n=[sgn*dz,-sgn*dx];n=n if sum(ys)>sum(zs)else[-x for x in n];vs=[[u[0],ys[0],u[1]],[v[0],ys[1],v[1]],[v[0],zs[1],v[1]],[u[0],zs[0],u[1]]];out=[]
 for t in [[vs[0],vs[1],vs[2]],[vs[0],vs[2],vs[3]]]:
  if area3d(t)<=0:continue
  a1=[t[1][k]-t[0][k]for k in range(3)];b1=[t[2][k]-t[0][k]for k in range(3)];nn=[a1[1]*b1[2]-a1[2]*b1[1],a1[0]*b1[1]-a1[1]*b1[0]]
  if nn[0]*n[0]+nn[1]*n[1]<0:t=[t[0],t[2],t[1]]
  out.append(t)
 return out

def interval(u,v,p):
 sign=1 if g.signed_area(p)>0 else-1;lo=0.;hi=1.
 for a,b in zip(p,p[1:]+p[:1]):
  f=lambda q:sign*((b[0]-a[0])*(q[1]-a[1])-(b[1]-a[1])*(q[0]-a[0]));fu,fv=f(u),f(v)
  if fu<0 and fv<0:return None
  if fu<0:lo=max(lo,fu/(fu-fv))
  elif fv<0:hi=min(hi,fu/(fu-fv))
 return [lo,hi]if hi>lo else None

def main():
 start=time.monotonic();bp=C/'registered_integration/r8/final_exterior_candidate_r01/noble_cap_bridge_binding.json';b=json.loads(bp.read_bytes());patches=[]
 for r in b['patches']:
  p=ROOT/r['path'];assert sha(p)==r['sha256'];patches.append(json.loads(p.read_bytes()))
 tops=json.loads((D/'current_top_replacements.json').read_bytes());bd=json.loads((D/'boundary_candidate.json').read_bytes());prof=json.loads((D/'profile_candidate.json').read_bytes());owners=prof['records'];byid={r['id']:r for r in owners};extra=[]
 for e in bd['unknown_exterior_segments']:
  u,v=e['edge_xz_m'];owner=byid[e['owner_id']];road=next(r for r in s.survey['interfaces']if r['id']==owner['road_id']);parts=[]
  for q in road['actual_native_support_quads_in_window']:
   vs=q['world_quad_xyz_m'];p=[[v[0],v[2]]for v in vs];ny=(vs[1][2]-vs[0][2])*(vs[2][0]-vs[0][0])-(vs[1][0]-vs[0][0])*(vs[2][2]-vs[0][2])
   if ny<=0:continue
   span=interval(u,v,p)
   if span:parts.append((span,q))
  knots=sorted({0.,1.,*(t for span,q in parts for t in span)});missing=[]
  for lo,hi in zip(knots,knots[1:]):
   if (hi-lo)*math.dist(u,v)<1e-9:continue
   choices=[q for (a,b),q in parts if a<=(lo+hi)/2<=b]
   if not choices:missing.append([lo,hi]);continue
   q=max(choices,key=lambda r:r['world_quad_xyz_m'][0][1]);edge=[[u[k]+t*(v[k]-u[k])for k in(0,1)]for t in[lo,hi]];ys=[s.val(owner['plane_y_xz_m'],p)for p in edge];y=q['world_quad_xyz_m'][0][1];assert min(ys)>=y-1e-9
   extra.append(dict(owner_id=e['owner_id'],edge_xz_m=edge,owned_y_m=ys,outside_y_m=[y,y],kind='nonwalking_retaining',other_owner=['actual_native_bearing_top',q['instance'],q['group_index'],q['quad_index']],native_quad_xyz_m=q['world_quad_xyz_m'],native_cache=q['cache'],reason='Vertical structural fill above actual bearing apron; no walking-floor attribution outside named road.'))
  assert not missing,(e,missing)
 seams=[r for r in bd['boundary_seams']if r['kind']=='nonwalking_retaining']+extra;newbanks=[t for r in seams for t in wall(r,byid[r['owner_id']])]
 target={};targets=[]
 for r in tops['rows']+bd['side_surface_edits']:
  key=(r['material'],r['source_triangle_sha256']);new=r['replacement_triangles_xyz_m'];
  if key in target:assert target[key]==new
  target[key]=new;targets.append(r)
 remaining=set(target);maps=[];final=copy.deepcopy(patches)
 def match(t,material):
  # Exact source-hash matching. Bounds only skip distant triangles.
  if max(v[0]for v in t)<99 or min(v[0]for v in t)>134 or max(v[2]for v in t)<381 or min(v[2]for v in t)>397:return None
  k=(material,a.canonical_sha(t));return k if k in target else None
 for pi,p in enumerate(patches):
  for m,flat in p.get('appended_surfaces',{}).items():
   out=[]
   for i in range(0,len(flat),3):
    t=flat[i:i+3];k=match(t,m)
    if k is None:out+=t;continue
    remaining.discard(k);maps.append(dict(patch_index=pi,producer_id=p['id'],location='appended_surfaces',material=m,source_triangle_index=i//3,source_triangle_sha256=k[1],source_triangle_xyz_m=t,replacement_triangles_xyz_m=target[k]));out.extend(v for tr in target[k]for v in tr)
   final[pi]['appended_surfaces'][m]=out
  for ei,r in enumerate(p['surface_edits']):
   out=[]
   for ti,t in enumerate(r['replacement_triangles_xyz_m']):
    k=match(t,r['material'])
    if k is None:out.append(t);continue
    remaining.discard(k);maps.append(dict(patch_index=pi,producer_id=p['id'],location='surface_edits',source_edit_array_index=ei,original_source_triangle_index=r['triangle_index'],material=r['material'],replacement_triangle_index=ti,source_triangle_sha256=k[1],source_triangle_xyz_m=t,replacement_triangles_xyz_m=target[k]));out+=target[k]
   final[pi]['surface_edits'][ei]['replacement_triangles_xyz_m']=out
 print('producer matches',len(maps),'unmatched',len(remaining),flush=True)
 baseedits=[];base=json.loads((ROOT/b['base_scene']['path']).read_bytes());existing={(r['material'],r['triangle_index'])for p in patches for r in p['surface_edits']}
 for m in {k[0]for k in remaining}:
  flat=base['surfaces'][m]
  for i in range(0,len(flat),3):
   t=flat[i:i+3];k=match(t,m)
   if k not in remaining:continue
   assert(m,i//3)not in existing
   baseedits.append(dict(material=m,triangle_index=i//3,source_triangle_sha256=k[1],replacement_triangles_xyz_m=target[k]));remaining.remove(k);maps.append(dict(location='original_untouched_base',material=m,source_triangle_index=i//3,source_triangle_sha256=k[1],source_triangle_xyz_m=t,replacement_triangles_xyz_m=target[k]))
 assert not remaining,remaining
 geometry_changed=[i for i,(p,q)in enumerate(zip(patches,final))if p!=q]
 for i in geometry_changed:final[i]['causeway_side_join_retirement']=dict(source=b['patches'][i],survey=ref(s.S),source_scene=tops['source_scene'],scope='Exact diagnosed finite road/top and side rows within two 4 m approach ribbons.')
 local=dict(schema='riverstone.frozen_scene_patch.v1',id='R18_TWO_CAUSEWAY_SIDE_JOINS_R01',status='SOURCE_READY_ACTUAL_REPLAY_PENDING',base_scene_sha256=b['base_scene']['sha256'],source_surface_hashes={m:a.canonical_sha(base['surfaces'][m])for m in {r['material']for r in baseedits}},surface_edits=baseedits,appended_surfaces=dict(road=[v for r in owners for t in r['triangles_xyz_m']for v in t],bank=[v for t in newbanks for v in t]),removed_foundation_proxy_ids=[],source_references=[ref(bp),ref(s.S),ref(D/'profile_candidate.json'),ref(D/'current_top_replacements.json'),ref(D/'boundary_candidate.json')],requires_patch_canonical_sha256={final[i]['id']:None for i in geometry_changed})
 final.append(local);ids={x['id']:i for i,x in enumerate(final)};done=set()
 def rebind(i,active=()):
  if i in done:return
  assert i not in active
  for pid in final[i].get('requires_patch_canonical_sha256',{}):rebind(ids[pid],active+(i,));final[i]['requires_patch_canonical_sha256'][pid]=merger.canonical_sha(final[ids[pid]])
  done.add(i)
 for i in range(len(final)):rebind(i)
 outb=copy.deepcopy(b);replacements=[]
 for i,p in enumerate(final):
  if i<len(patches)and p==patches[i]:continue
  dest=D/f'producer_{i:02d}.json';rr=dump(dest,p)
  if i<len(patches):outb['patches'][i]=rr
  else:outb['patches'].append(rr)
  replacements.append(dict(patch_index=i,producer_id=p['id'],reference=rr,canonical_sha256=merger.canonical_sha(p),geometry_changed=i in geometry_changed or i==len(patches)))
 outb['causeway_side_join_repair']=dict(survey=ref(s.S),profile=ref(D/'profile_candidate.json'),status='REQUIRES_EXACT_COMPOSED_SCENE_RUNTIME');dump(D/'activation_binding.json',outb)
 dump(D/'producer_row_retirement_ledger.json',dict(source_binding=ref(bp),source_scene=tops['source_scene'],rows=maps,target_scene_row_count=len(targets),target_hash_count=len(target),geometry_changed_producer_indexes=geometry_changed,new_original_base_edit_count=len(baseedits),new_road_triangles=sum(len(r['triangles_xyz_m'])for r in owners),new_retaining_triangles=len(newbanks),producer_replacements=replacements))
 dump(D/'native_apron_side_closure.json',dict(source=ref(s.S),original_unknown_count=len(bd['unknown_exterior_segments']),closed_intervals=extra,unresolved_intervals=[],new_retaining_triangles_xyz_m=newbanks))
 print('final',geometry_changed,'base edits',len(baseedits),'tops',len(local['appended_surfaces']['road'])//3,'banks',len(newbanks),'sec',time.monotonic()-start,flush=True)

if __name__=='__main__':main()
