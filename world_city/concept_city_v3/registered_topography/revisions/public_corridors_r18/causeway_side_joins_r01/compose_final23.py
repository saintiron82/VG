"""Compose two immutable exact old-row ledgers and close canonical dependencies.
No geometry lookup is used to locate an altered generated triangle.
"""
import pathlib,json,hashlib,copy,collections,math
import numpy as np
D=pathlib.Path(__file__).resolve().parent
ROOT=D.parents[5]
C=ROOT/'world_city/concept_city_v3'
OUT=D/'final23_joined_r01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def can(j):return hashlib.sha256(json.dumps(j,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def read(r):
 p=ROOT/r['path'];assert sha(p)==r['sha256'],r;return json.loads(p.read_bytes())
def put(name,j):
 p=OUT/name;p.write_text(json.dumps(j,separators=(',',':'),allow_nan=False)+'\n');return ref(p)
def key(r):return(r['patch_index'],r['material'],r['source_triangle_index'])
def flat_apply(flat,rows):
 out=[];touched=set()
 for i in range(0,len(flat),3):
  t=flat[i:i+3];r=rows.get(i//3)
  if r is None:out+=t;continue
  assert can(t)==r['source_triangle_sha256']and t==r['source_triangle_xyz_m']
  out.extend(v for tr in r['replacement_triangles_xyz_m']for v in tr);touched.add(i//3)
 assert touched==set(rows)
 return out

def main():
 assert not OUT.exists();OUT.mkdir()
 cr=dict(path='world_city/concept_city_v3/registered_integration/r8/final_exterior_candidate_r01/noble_cap_bridge_binding.json',sha256='c9476a7251e2977bb7bed77590bf80ebe2bc580ccccd3a2960cd080946af3f90')
 fr=dict(path='world_city/concept_city_v3/registered_integration/r8/final_exterior_candidate_r01/final23_activation_r01/activation_binding.json',sha256='b9001c9946e9d0efd0208f5eb97ea43d9cd3dffd82dc0ba791cfe592baf02b7d')
 cb=read(cr);fb=read(fr);common=[read(r)for r in cb['patches']];current=[read(r)for r in fb['patches']];final=copy.deepcopy(current)
 lr=ref(D/'producer_row_retirement_ledger.json');local=read(lr)
 ar=ref(C/'registered_topography/revisions/r17_district_batches/coherent_final24_r02/generated_bank_source_ledger_r01.json');other=read(ar)
 assert local['source_binding']==cr and other['source_main_binding']==cr
 ores=[dict(patch_index=r['producer_index'],material=r['appended_material'],source_triangle_index=r['appended_triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],source_triangle_xyz_m=r['source_vertices_xyz_m'],replacement_triangles_xyz_m=r['replacement_triangles_xyz_m'])for r in other['rows']]
 lres=[r for r in local['rows']if r['location']=='appended_surfaces'];ok={key(r):r for r in ores};lk={key(r):r for r in lres}
 assert len(ok)==len(ores)and len(lk)==len(lres)
 shared=set(ok)&set(lk);assert not shared,shared
 checks=[];changed=[]
 for pi,m in sorted({(r['patch_index'],r['material'])for r in ores+lres}):
  flat=common[pi]['appended_surfaces'][m];om={r['source_triangle_index']:r for r in ores if r['patch_index']==pi and r['material']==m};lm={r['source_triangle_index']:r for r in lres if r['patch_index']==pi and r['material']==m}
  final23_only=flat_apply(flat,om)
  assert current[pi]['appended_surfaces'][m]==final23_only,(pi,m,'final23 source mismatch')
  joined=flat_apply(flat,dict(om,**{})|lm);final[pi]['appended_surfaces'][m]=joined
  checks.append(dict(producer_index=pi,material=m,old_array_sha256=can(flat),final23_only_array_sha256=can(final23_only),combined_array_sha256=can(joined),final23_row_count=len(om),side_join_row_count=len(lm),shared_source_rows=[]))
  if lm:changed.append(pi)
 # Existing source edit arrays preserve all original keys and unaffected retained fans.
 byedit=collections.defaultdict(dict)
 for r in local['rows']:
  if r['location']=='surface_edits':byedit[r['patch_index'],r['source_edit_array_index']][r['replacement_triangle_index']]=r
 for (pi,ei),rr in byedit.items():
  old=common[pi]['surface_edits'][ei];assert current[pi]['surface_edits'][ei]==old
  out=[]
  for ti,t in enumerate(old['replacement_triangles_xyz_m']):
   r=rr.get(ti)
   if r is None:out.append(t);continue
   assert can(t)==r['source_triangle_sha256']and t==r['source_triangle_xyz_m'];out+=r['replacement_triangles_xyz_m']
  final[pi]['surface_edits'][ei]['replacement_triangles_xyz_m']=out;changed.append(pi)
 # Original untouched base rows are already isolated in the explicit local patch.
 localpatch=json.loads((D/'producer_24.json').read_bytes());assert localpatch['id']=='R18_TWO_CAUSEWAY_SIDE_JOINS_R01'
 existing={(r['material'],r['triangle_index'])for p in current for r in p['surface_edits']}
 own={(r['material'],r['triangle_index'])for r in localpatch['surface_edits']};assert not(existing&own)
 final.append(localpatch)
 for i in sorted(set(changed)):
  final[i]['causeway_side_join_composition']=dict(common_source=cb['patches'][i],prior_final23_source=fb['patches'][i],side_join_ledger=lr,final23_ledger=ar,policy='Exact disjoint original array indices and triangle hashes; apply both ledgers once.')
 # Verify the old dependency graph before changing any hashes.
 original_by={p['id']:can(p)for p in current}
 for p in current:
  for pid,h in p.get('requires_patch_canonical_sha256',{}).items():assert original_by[pid]==h,(p['id'],pid)
 ids={p['id']:i for i,p in enumerate(final)};assert len(ids)==len(final);done=set();depchanges=[]
 def bind(i,stack=()):
  if i in done:return
  assert i not in stack
  for pid,was in list(final[i].get('requires_patch_canonical_sha256',{}).items()):
   j=ids[pid];bind(j,stack+(i,));now=can(final[j]);final[i]['requires_patch_canonical_sha256'][pid]=now
   if was!=now:depchanges.append(dict(producer=final[i]['id'],dependency=pid,before=was,after=now))
  done.add(i)
 for i in range(len(final)):bind(i)
 replacements=[];outb=copy.deepcopy(fb)
 for i,p in enumerate(final):
  if i<len(current)and p==current[i]:continue
  r=put(f'producer_{i:02d}.json',p);replacements.append(dict(producer_index=i,producer_id=p['id'],reference=r,canonical_sha256=can(p),geometry_changed=i in changed or i==len(current)))
  if i<len(current):outb['patches'][i]=r
  else:outb['patches'].append(r)
 for p in final:
  for pid,h in p.get('requires_patch_canonical_sha256',{}).items():assert h==can(final[ids[pid]])
 # Every original retained top replacement is tested in actual float32 arithmetic.
 tested=0;maxgrade=0
 for r in local['rows']:
  if r['material']=='bank':continue
  for t in r['replacement_triangles_xyz_m']:
   q=np.array(t,dtype=np.float32);n=np.cross(q[1]-q[0],q[2]-q[0]);assert n[1]>0,(r,n);tested+=1;maxgrade=max(maxgrade,math.hypot(float(n[0]),float(n[2]))/float(n[1]))
 assert outb['packs']==fb['packs']and outb['collision_contracts']==fb['collision_contracts']and outb['review_cameras']==fb['review_cameras']
 review=put('composition_review.json',dict(status='PASS_EXACT_SOURCE_COMPOSITION_RUNTIME_PENDING',source_binding=fr,common_source_binding=cr,local_ledger=lr,final23_ledger=ar,rows=checks,source_row_overlap_count=0,base_source_index_overlap_count=0,retained_top_float32=dict(triangle_count=tested,nonpositive_count=0,maximum_grade=maxgrade),dependency_updates=depchanges,replacements=replacements,counts=dict(patches=len(final),native_packs=len(outb['packs']),collision_contracts=len(outb['collision_contracts'])),policy='All prior packs, contracts, cameras and unrelated producer geometry preserved. Exact final23-only arrays reconstructed before combined row emission.'))
 outb['evidence']+=[ref(D/'source_tests.json'),ref(D/'free_collinear_normalization.json'),lr,ref(D/'profile_candidate.json'),ref(D/'native_apron_side_closure.json'),review]
 outb['causeway_side_join_repair']=dict(profile=ref(D/'profile_candidate.json'),source_tests=ref(D/'source_tests.json'),composition=review,status='EXACT_COMPOSED_SCENE_REPLAY_REQUIRED')
 outb['source_stage']='Final23 and bounded two causeway side grades composed from exact disjoint old source rows. Port repair, final composed-scene traversal and images remain pending.'
 rr=put('activation_binding.json',outb);print(json.dumps(dict(binding=rr,review=review,patches=len(final),changed=sorted(set(changed)),retained_float32=tested),indent=2),flush=True)
if __name__=='__main__':main()
