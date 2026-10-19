"""Require exact nonzero noble contracts, preserving every route and native ref."""
import copy,hashlib,json,pathlib
import numpy as np
import catalog
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3'
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def canonical(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def main():
 prior=H.parent/'public_network_r18_r01/route_catalog_61_noble_r06.json';old=read(prior);assert ref(prior)['sha256']=='4a1b30bd3e77f9d21f9cd356ab732040713b744641e800830feee4fded47236d';d=copy.deepcopy(old)
 folder=CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02/runtime_precision_r01';handoff=ref(folder/'integration_handoff.json');assert handoff['sha256']=='112f623a11a73234c9b456e8e9db4b55a51356558c1a3ceb69d938bd4d1bc022';h=read(catalog.source(handoff));mapping={};proofs=[]
 for row in h['exact_source_index_retirements']:
  owner=row['owner_id'];source=read(catalog.source(row['source_contract']));current=read(catalog.source(row['replacement_contract']));ledger=read(catalog.source(row['removal_ledger']));tri=source['add_triangles_world_xyz_m'];q=np.asarray(tri,dtype=np.float32);cross=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);assert np.all(np.isfinite(q))and np.all(np.isfinite(cross));zero=np.all(cross==np.float32(0),axis=1);keep=np.flatnonzero(~zero).tolist();drop=np.flatnonzero(zero).tolist();assert ledger['retained_source_triangle_indices']==keep;assert current['add_triangles_world_xyz_m']==[tri[i]for i in keep];assert canonical(current['add_triangles_world_xyz_m'])==ledger['retained_triangles_canonical_sha256'];assert len(drop)==row['removed_triangle_count'];assert source['id']==current['id'];assert source['disable_native_mesh_collider_ids']==current['disable_native_mesh_collider_ids'];assert ledger['source_preserved']and ledger['retained_double_vertices_and_order_unchanged'];assert ledger['source_contract']==row['source_contract'];catalog.source(ledger['implementation'])
  mapping[json.dumps(row['source_contract'],sort_keys=True)]=row['replacement_contract'];d['sources']['noble_authored_contract_'+owner]=row['source_contract'];d['sources']['noble_contract_'+owner]=row['replacement_contract'];d['sources']['noble_contract_retirement_'+owner]=row['removal_ledger'];proofs.append(dict(owner_id=owner,source=row['source_contract'],current=row['replacement_contract'],ledger=row['removal_ledger'],source_triangles=len(tri),retained=len(keep),removed=len(drop),nonzero_vertices_and_order_exact=True))
 def update(r):return mapping.get(json.dumps(r,sort_keys=True),r)
 for route in d['routes']:
  if not route['id'].startswith('NOBLE:'):continue
  route['provenance']=[update(r)for r in route['provenance']]+[handoff]
 d['activation_requirements']['collision_contracts']=[update(r)for r in d['activation_requirements']['collision_contracts']]
 d['sources'].update(prior_noble_r06_catalog=ref(prior),normalized_contract_handoff=handoff,normalized_contract_activation=h['activation_binding'],normalized_contract_bundle=h['collision_contract_bundle'],normalized_contract_tests=h['tests'])
 d['source_candidate_accounting']['noble_contract_precision_revision']=dict(handoff=handoff,proofs=proofs,removed_total=sum(r['removed']for r in proofs),changed_native_geometry=0,changed_route_vectors=0)
 d['limits'].append('Six noble contract sources now retire exactly 647 zero-float32 triangles with immutable per-source index ledgers. Every nonzero contract triangle, all route vectors, native geometry and E3 remain exact; actual runtime pass is still required.')
 assert len(proofs)==6 and sum(r['removed']for r in proofs)==647;assert all(a['points_xyz_m']==b['points_xyz_m']for a,b in zip(d['routes'],old['routes']));assert d['activation_requirements']['native_packs']==old['activation_requirements']['native_packs'];assert d['activation_requirements']['appended_surface_patches']==old['activation_requirements']['appended_surface_patches'];assert d['activation_requirements']['finite_public_field']==old['activation_requirements']['finite_public_field'];assert d['coverage']==old['coverage'];expanded=catalog.validate(d);assert len(expanded)==412
 out=H/'route_catalog_61_contracts_r07.json';write(out,d);report=dict(status='SOURCE_BOUND_AWAITING_NORMALIZED_CONTRACT_SCENE',catalog=ref(out),prior_catalog=ref(prior),cases=len(expanded),proofs=proofs,changed_route_vectors=0,changed_native_packs=0,changed_terrain_requirements=0,runtime_launched=False);write(H/'contract_binding_report.json',report);print(json.dumps(dict(catalog=ref(out),cases=len(expanded),removed_total=647),indent=2))
if __name__=='__main__':main()
