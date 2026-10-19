"""Rebind finite original retirements and predecessor appended tops atomically.

Every invocation accepts an explicit integration binding. It never edits its
inputs. Shared old removals remain owned by predecessors; only the noble-domain
difference is removed by the noble patch. Predecessor appended tops are clipped
only in the exact final noble-owned top domains, with their original planes.
"""
from pathlib import Path
import sys,json,copy,argparse,collections,math,time
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE))
from resolve_pack import *
from world_city.concept_city_v3.registered_integration.r8 import compose_finite_patches as compose
from world_city.concept_city_v3.registered_integration.r6 import merge_patches as merger
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import physical_side
OUT=Path(__file__).resolve().parent

def source_row(scene,r):return scene['surfaces'][r['material']][3*r['triangle_index']:3*r['triangle_index']+3]
def removal(scene,r):
 tri=source_row(scene,r);n,L,d,project,unproject=compose.project_frame(tri);poly=[project(p)for p in tri];keep=[];changed=[]
 for t in r['replacement_triangles_xyz_m']:
  if max(abs(compose.dot(n,v)-d)/L for v in t)<=1e-8:keep.append([project(v)for v in t])
  else:changed.append(t)
 return fg.subtract([poly],keep),changed,(n,project,unproject,poly)
def fan_plane(polys,frame):
 n,project,unproject,original=frame;out=[]
 for poly in polys:
  v=[unproject(p)for p in poly]
  for i in range(1,len(v)-1):
   t=[v[0],v[i],v[i+1]];normal=compose.cross(compose.sub(t[1],t[0]),compose.sub(t[2],t[0]));dot=compose.dot(n,normal)
   if dot<0:t=[t[0],t[2],t[1]]
   if dot:out.append(t)
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binding',required=True);ap.add_argument('--output',required=True);ap.add_argument('--noble-patch');ap.add_argument('--public-records',default=str(CITY/'registered_topography/revisions/public_corridors_r18/finite_field_candidate_r07_native_bound.json'));ap.add_argument('--noble-id',default='R8_NOBLE_SEVEN_FINE_ENTRY_R01');args=ap.parse_args();dest=Path(args.output).resolve();assert dest.is_relative_to(OUT);dest.mkdir(exist_ok=True,parents=True);assert not(dest/'READY_SEAL.json').exists();started=time.monotonic()
 bindingpath=Path(args.binding).resolve();binding=load(bindingpath);scene=load(ROOT/binding['base_scene']['path']);patches=[]
 for r in binding['patches']:
  assert sha(ROOT/r['path'])==r['sha256'],r
  patches.append(load(ROOT/r['path']))
 ni=next(i for i,p in enumerate(patches)if p['id']==args.noble_id);original=copy.deepcopy(patches[ni]);noble=load(Path(args.noble_patch).resolve())if args.noble_patch else copy.deepcopy(original);assert noble['id']==args.noble_id
 publicpath=Path(args.public_records).resolve();public=load(publicpath)['records'];pi=geo._SpatialIndex(8)
 for i,r in enumerate(public):pi.add(i,r['polygon_xz_m'])
 # Public is authoritative. The native revision must likewise remove its
 # genuine public overreach before this normalization may be activated.
 nclip=[]
 for material,verts in noble['appended_surfaces'].items():
  out=[]
  for ti in range(0,len(verts),3):
   t=verts[ti:ti+3];poly=[[v[0],v[2]]for v in t]
   if physical_side(t,material)or terrain.normal_y(t)<=0 or fg.area(poly)<=1e-12:out+=t;continue
   masks=[public[j]['polygon_xz_m']for j in pi.candidates(poly)if fg.clip(poly,public[j]['polygon_xz_m'])];parts=fg.subtract([poly],masks)
   delta=fg.area(poly)-sum(fg.area(q)for q in parts)
   if delta>1e-10:
    pl=terrain.common.plane(t);replacement=[]
    for q in parts:replacement.extend(terrain.fan_upward([[x,terrain.common.height(pl,[x,z]),z]for x,z in q]))
    out +=[v for tr in replacement for v in tr];nclip.append(dict(material=material,triangle_index=ti//3,removed_public_projection_m2=delta,source_triangle=t,retained_triangles=replacement))
   else:out+=t
  noble['appended_surfaces'][material]=out
 domains=[];di=geo._SpatialIndex(8)
 for material,verts in noble['appended_surfaces'].items():
  for ti in range(0,len(verts),3):
   t=verts[ti:ti+3];poly=[[v[0],v[2]]for v in t]
   if physical_side(t,material)or terrain.normal_y(t)<=0 or fg.area(poly)<=1e-12:continue
   di.add(len(domains),poly);domains.append(dict(material=material,polygon_xz_m=poly,plane_y_xz_m=terrain.common.plane(t),source_triangle_index=ti//3))
 allprior=collections.defaultdict(list)
 for i,p in enumerate(patches):
  if i==ni:continue
  for r in p['surface_edits']:allprior[(r['material'],r['triangle_index'])].append((i,p['id'],r))
 edits=[];retirement=[];needed=set()
 for r in noble['surface_edits']:
  key=r['material'],r['triangle_index'];oldremoved,changed,frame=removal(scene,r);assert not changed,('Noble changed original replacement requires explicit ownership',key)
  masks=[];priorowners=[]
  for i,pid,pr in allprior[key]:
   removed,_,_=removal(scene,pr);masks+=removed;priorowners.append(pid)
  exclusive=fg.subtract(oldremoved,masks);oldarea=sum(fg.area(p)for p in oldremoved);newarea=sum(fg.area(p)for p in exclusive)
  if oldarea-newarea>1e-9:
   needed.update(priorowners);retirement.append(dict(material=key[0],triangle_index=key[1],prior_patch_ids=priorowners,original_noble_removal_area=oldarea,exclusive_noble_removal_area=newarea,delegated_removal_area=oldarea-newarea,exclusive_removed_polygons_source_frame=exclusive))
   if newarea>1e-12:
    keep=fg.subtract([frame[3]],exclusive);edits.append(dict(r,replacement_triangles_xyz_m=fan_plane(keep,frame)))
  else:edits.append(r)
 noble['surface_edits']=edits
 priorclips=[];sideclips=[];changedpatches={}
 for i,p in enumerate(patches):
  if i==ni:continue
  q=copy.deepcopy(p);ledger=[]
  for material,verts in p['appended_surfaces'].items():
   out=[]
   for ti in range(0,len(verts),3):
    t=verts[ti:ti+3];poly=[[v[0],v[2]]for v in t]
    if physical_side(t,material)or terrain.normal_y(t)<=0 or fg.area(poly)<=1e-12:out+=t;continue
    masks=[domains[j]['polygon_xz_m']for j in di.candidates(poly)if fg.clip(poly,domains[j]['polygon_xz_m'])];parts=fg.subtract([poly],masks);delta=fg.area(poly)-sum(fg.area(v)for v in parts)
    if delta>1e-9:
     pl=terrain.common.plane(t);replacement=[]
     for part in parts:replacement.extend(terrain.fan_upward([[x,terrain.common.height(pl,[x,z]),z]for x,z in part]))
     out +=[v for tr in replacement for v in tr];ledger.append(dict(material=material,triangle_index=ti//3,old_triangle_sha256=merger.canonical_sha(t),removed_projection_area_m2=delta,source_triangle=t,retained_triangles=replacement))
    else:out+=t
   q['appended_surfaces'][material]=out
  if ledger:
   q['finite_noble_top_normalization']=dict(original_patch=binding['patches'][i],noble_original_patch=binding['patches'][ni],policy='Only actual noble finite top domains take appended-top ownership; original source retirement unchanged')
   changedpatches[i]=q;needed.add(q['id']);priorclips.append(dict(patch_id=q['id'],original_patch=binding['patches'][i],removed_projection_area_m2=sum(r['removed_projection_area_m2']for r in ledger),records=ledger));print('prior clipped',q['id'],len(ledger),sum(r['removed_projection_area_m2']for r in ledger),flush=True)
  if p['id']=='R8_JOINT_61_BOUNDARY_NORTH_EXACT_REBOUND_FINAL_R01':
   from rebind_joint_sides import rebind as rebind_sides
   q,sl=rebind_sides(q,domains);changedpatches[i]=q;needed.add(q['id']);sideclips.append(sl);print('prior sides clipped',sl['summary'],flush=True)
 # All predecessor requirements must be rebound to the exact final wrapper
 # content. Reject dependency cycles rather than guessing a hash order.
 final=copy.deepcopy(patches)
 for i,p in changedpatches.items():final[i]=p
 # Parent-authorized exact logical replacement, preserving the original failed
 # input and both source references. No original/source geometry changes here.
 old_joint='R8_JOINT_61_HOLDING_PUBLIC_BOUNDARY_CLOSURE';new_joint='R8_JOINT_61_BOUNDARY_NORTH_EXACT_REBOUND_FINAL_R01';aliases=[]
 if new_joint in {p['id']for p in final}:
  for i,p in enumerate(final):
   if old_joint in p.get('requires_patch_ids',[])or old_joint in p.get('requires_patch_canonical_sha256',{}):
    aliases.append(dict(patch_id=p['id'],source_patch=binding['patches'][i],old_required_patch_id=old_joint,new_required_patch_id=new_joint,old_required_canonical_sha256=p.get('requires_patch_canonical_sha256',{}).get(old_joint),replacement_source_patch=next(binding['patches'][j]for j,q in enumerate(patches)if q['id']==new_joint)))
    p['requires_patch_ids']=[new_joint if x==old_joint else x for x in p.get('requires_patch_ids',[])]
    p['requires_patch_canonical_sha256']={new_joint if k==old_joint else k:v for k,v in p.get('requires_patch_canonical_sha256',{}).items()}
 byid={p['id']:i for i,p in enumerate(final)};done=set();active=set()
 def rebind(i):
  if i in done:return
  assert i not in active,('dependency cycle',final[i]['id']);active.add(i);p=final[i]
  for pid in p.get('requires_patch_canonical_sha256',{}):
   j=byid[pid];assert j!=ni,('predecessor depends on noble',pid);rebind(j);p['requires_patch_canonical_sha256'][pid]=merger.canonical_sha(final[j])
  active.remove(i);done.add(i)
 for i in range(len(final)):
  if i!=ni:rebind(i)
 noble['requires_patch_ids']=sorted(set(noble.get('requires_patch_ids',[]))|needed);noble['requires_patch_canonical_sha256']={pid:merger.canonical_sha(final[byid[pid]])for pid in noble['requires_patch_ids']};noble['finite_retirement_normalization']=dict(integration_binding=ref(bindingpath),original_noble_patch=binding['patches'][ni],public_records=ref(publicpath),source_original_retirement_delegated_to_prior_owners=True,prior_appended_tops_rebound=True,activation_requires_atomic_new_native_and_collision=True);final[ni]=noble
 def write(name,obj):p=dest/name;p.write_text(json.dumps(obj,indent=2)+'\n');return ref(p)
 outbinding=copy.deepcopy(binding)
 for i,p in enumerate(final):
  if p!=patches[i]:outbinding['patches'][i]=write('noble_surface_patch.json'if i==ni else f'predecessor_{i:02d}.json',p)
 for row in priorclips:
  j=byid[row['patch_id']];row['source_patch']=binding['patches'][j];row['replacement_patch']=outbinding['patches'][j];row['source_rows']=[dict(material=r['material'],appended_triangle_index=r['triangle_index'],old_triangle_sha256=r['old_triangle_sha256'])for r in row['records']];row['added_nonwalking_side_triangles']=[]
 for row in sideclips:
  j=byid[row['patch_id']];row['source_patch']=binding['patches'][j];row['replacement_patch']=outbinding['patches'][j];row['source_rows']=[dict(material=r['material'],appended_triangle_index=r['triangle_index'],old_triangle_sha256=r['old_triangle_sha256'])for r in row['records']];row['added_nonwalking_side_triangles']=[]
  row['bound_new_nonwalking_side_triangles']=dict(patch=outbinding['patches'][ni],material='bank',triangles=noble['appended_surfaces'].get('bank',[]),canonical_sha256=merger.canonical_sha(noble['appended_surfaces'].get('bank',[])))
 proof=dict(schema='riverstone.noble.finite_predecessor_normalization.v1',integration_binding=ref(bindingpath),public_records=ref(publicpath),noble_original=binding['patches'][ni],normalized_noble=outbinding['patches'][ni],delegated_original_retirements=retirement,noble_public_top_retirements=nclip,prior_appended_top_clips=priorclips,owned_top_domains=domains,summary=dict(original_rows=len(original['surface_edits']),normalized_rows=len(noble['surface_edits']),delegated_rows=len(retirement),delegated_source_projection_area=sum(r['delegated_removal_area']for r in retirement),predecessors_clipped=len(priorclips),prior_appended_projection_removed_m2=sum(r['removed_projection_area_m2']for r in priorclips),public_projection_removed_m2=sum(r['removed_public_projection_m2']for r in nclip),seconds=time.monotonic()-started),activation=False)
 proof['prior_appended_side_clips']=sideclips;proof['authorized_prerequisite_aliases']=aliases
 proof['summary']['predecessor_side_rows_clipped']=sum(len(r['records'])for r in sideclips)
 write('normalization_audit.json',proof);write('binding.json',outbinding);print(proof['summary'],flush=True)
if __name__=='__main__':main()
