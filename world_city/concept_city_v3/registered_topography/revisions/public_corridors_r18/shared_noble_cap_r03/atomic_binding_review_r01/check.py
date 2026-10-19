import json,hashlib,pathlib
from world_city.concept_city_v3.registered_integration.r6.merge_patches import canonical_sha
C=pathlib.Path('world_city/concept_city_v3')
R=C/'registered_topography/revisions/public_corridors_r18'
G=C/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_cap_route_repair_r01'
D=R/'shared_noble_cap_r03/atomic_binding_review_r01'
def load(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
b=load(G/'activation_binding.json'); old=load(R/'runtime_local_remnants_r02/activation_binding.json')
assert sha(G/'activation_binding.json')=='663b251d9bb21f79cc34edd6cec419e262b3b57ce3894abc83054003c601a768'
verified=[]; failures=[]
def refs(x):
 if isinstance(x,dict):
  if isinstance(x.get('path'),str) and isinstance(x.get('sha256'),str):
   p=pathlib.Path(x['path']); actual=sha(p) if p.exists() else None
   if actual!=x['sha256']:failures.append(dict(reference=x,actual=actual))
   verified.append(x)
  for v in x.values():refs(v)
 elif isinstance(x,list):
  for v in x:refs(v)
refs(b)
p=[load(r['path']) for r in b['patches']]; before=[load(r['path']) for r in old['patches']]
byid={x['id']:canonical_sha(x) for x in p}; assert len(byid)==len(p)
deps=[]
for x in p:
 for ident,digest in x.get('requires_patch_canonical_sha256',{}).items():
  assert byid[ident]==digest,(x['id'],ident,digest,byid.get(ident))
  deps.append(dict(producer=x['id'],dependency=ident,canonical_sha256=digest))
assert b['patches'][16]['sha256']=='1ae311aa8696b19710e45defb87d9dc255a8bfad6cf54a61eb682f4de85dafc5'
assert byid[p[16]['id']]=='635bdc148e6025145919d4e5bd09eca11bf1bc340ab65f6d49fb8ea8afc0f866'
checks={}
for i in [11,14]:
 for k in ['surface_edits','appended_surfaces','source_surface_hashes','base_scene_sha256','removed_foundation_proxy_ids']:
  assert p[i].get(k)==before[i].get(k),(i,k)
checks['dependent_11_14_geometry_exact']=True
for k in ['surface_edits','source_surface_hashes','base_scene_sha256','removed_foundation_proxy_ids']:
 assert p[15].get(k)==before[15].get(k),k
assert p[15]['appended_surfaces']['road']==before[15]['appended_surfaces']['road']
checks['public_15_source_retirements_and_48052_road_triangles_exact']=True
assert p[16]['surface_edits']==before[16]['surface_edits']
checks['shared_16_source_retirements_exact']=True
for i in set(range(len(before)))-{11,14,15,16,22}:
 assert b['patches'][i]==old['patches'][i],i
checks['other_18_producer_references_exact']=True
for k in ('packs','collision_contracts'):
 if k in old:assert b.get(k)==old[k],k
checks['native_pack_and_collision_contract_binding_exact']=True
checks['all_file_hashes_pass']=not failures
assert not failures,failures
out=dict(status='PASS_BOUNDED_ATOMIC_BINDING_PARITY',binding=ref(G/'activation_binding.json'),prior_binding=ref(R/'runtime_local_remnants_r02/activation_binding.json'),checked_reference_count=len(verified),patch_count=len(p),dependencies=deps,checks=checks,verified_inputs=verified,limits=['The northern graded transition and E1/E2 cap changes still require final composed-scene unchanged-controller replay.','The prior eight-direction road-remnant removal-only regression remains exact separate evidence; this review proves source composition parity.'])
(D/'review.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(status=out['status'],checks=checks,dependencies=len(deps),references=len(verified),report=ref(D/'review.json')),indent=2))
