"""Bind sealed noble R02 and final native packs without changing route vectors."""
import collections,copy,hashlib,json,pathlib
import catalog
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3'
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def main():
 prior=H/'route_catalog_61_ready_r05.json';old=read(prior);assert ref(prior)['sha256']=='443c8d56a73dad16ce73a36414f5de846b7c19011da7c7c6bca7725628aad1f6';d=copy.deepcopy(old);assert len(catalog.validate(d))==412
 folder=CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02';handoff=ref(folder/'integration_handoff.json');assert handoff['sha256']=='ba2a8d10d5e2211f20fb2ffdee1bf4b0caeadd868f234e47772947cd683901be';h=read(catalog.source(handoff));routes=read(catalog.source(h['runtime_routes']))['routes'];byowner={r['owner_id']:r for r in routes};contracts={r['owner_id']:r['contract']for r in h['collision_contracts']};changes=[]
 old_pack=d['sources']['noble_native_pack'];d['sources'].update(prior_412_catalog=ref(prior),noble_integration_handoff=handoff,noble_runtime_routes=h['runtime_routes'],noble_native_pack=h['native_pack'],noble_private_route_audit=h['private_static_clearance'])
 for name,r in h.items():
  if isinstance(r,dict)and 'path'in r and 'sha256'in r:catalog.source(r);d['sources']['noble_r02_'+name]=r
 for owner,r in byowner.items():
  d['sources']['noble_physical_top_'+owner]=r['physical_top'];d['sources']['noble_contract_'+owner]=contracts[owner];catalog.source(r['physical_top']);catalog.source(contracts[owner])
 for r in d['routes']:
  if not r['id'].startswith('NOBLE:'):continue
  owner=r['id'].split(':')[1];source=byowner[owner];assert [[p[0],p[2]]for p in r['points_xyz_m']]==source['polyline_xz_m'];before=copy.deepcopy(r)
  r.update(provenance=[handoff,h['runtime_routes'],source['physical_top'],contracts[owner]],resolved_geometry_proof=h['runtime_routes'],native_fine_id=source['native_fine_id'],source_geometry_basis='SEALED_R02_NATIVE_FINE_ENTRY_AND_UNCHANGED_FIXED_PUBLIC_ENDPOINT')
  r['hint_height_policy']='Predecessor Y is a hint only; actual standing Y is resolved from the final authored collision geometry, then bound unchanged to its exact runtime sanitation.'
  if owner=='E1':r['design_exception']='Retained incident public step of 0.057576 m; unchanged-controller pass remains required.'
  if owner=='E2':r['design_exception']='Visible pedestrian steps with continuous collision envelope at most 35%; no cart access claim.'
  if owner=='E5':r['design_exception']='Declared pedestrian approach at most 25%; no cart access claim.'
  assert r['points_xyz_m']==before['points_xyz_m'];changes.append(dict(route_id=r['id'],owner_id=owner,prior_native_fine_id=before['native_fine_id'],current_native_fine_id=r['native_fine_id'],points_xyz_value_unchanged=True,old_provenance=before['provenance'],new_provenance=r['provenance']))
 assert len(changes)==7
 act=d['activation_requirements'];act['native_packs']=[h['native_pack']if p==old_pack else p for p in act['native_packs']];act['collision_contracts']=[contracts['E'+str(i)]for i in range(1,8)]
 binding=read(catalog.source(h['activation_binding']));selected={}
 for key,fragment in [('corrected_835_native_pack','phase02_ownership_correction_r01/resolved_placements_r02.json'),('cemetery_r03_native_pack','cemetery_public_caps_r03/resolved_placements.json')]:
  candidates=[p for p in binding['packs']if p['path'].endswith(fragment)];assert len(candidates)==1;p=candidates[0];pack=read(catalog.source(p));d['sources'][key]=p;act['native_packs'].append(p);selected[key]=p
  if key=='corrected_835_native_pack':assert len(pack['placements'])==835
 for p in binding['evidence']:
  if p['path'].endswith('cemetery_public_caps_r03/integration_handoff.json'):d['sources']['cemetery_r03_handoff']=p;catalog.source(p)
 review_path=CITY/'registered_integration/r8/foundation_margin_binding_r01_61/review.json';review=read(review_path);assert review['source_patch']in act['appended_surface_patches'];act['appended_surface_patches']=[review['replacement_patch']if p==review['source_patch']else p for p in act['appended_surface_patches']];revision=dict(previous=review['source_patch'],current=review['replacement_patch'],review=ref(review_path),contract=review['contract']);act['private_append_revisions']=[revision]
 d['sources'].update(private_top_patch_next18_prior=review['source_patch'],private_top_patch_next18=review['replacement_patch'],foundation_margin_review=ref(review_path),foundation_margin_contract=review['contract'])
 d['source_candidate_accounting']['noble_r02_revision']=dict(prior_catalog=ref(prior),handoff=handoff,changed_route_vectors=0,changed_native_fine_skins=6,retained_E3=True,exact_current_source_bindings=changes,additional_required_native_packs=selected,foundation_margin_revision=revision)
 d['limits']+=h['limits'][:3]+['Seven noble source bindings are updated to sealed R02 while preserving all 412 declared case vectors. Any passed R01/R04 evidence remains specific to its original scene.','The corrected 835-fixture pack, cemetery R03 replacement and exact nonwalking foundation-margin retirement are mandatory actual-scene activation guards.']
 expanded=catalog.validate(d);assert len(expanded)==412;assert [r['id']for r in d['routes']]==[r['id']for r in old['routes']];assert all(a['points_xyz_m']==b['points_xyz_m']for a,b in zip(d['routes'],old['routes']));assert act['finite_public_field']==old['activation_requirements']['finite_public_field'];assert ref(prior)['sha256']=='443c8d56a73dad16ce73a36414f5de846b7c19011da7c7c6bca7725628aad1f6'
 output=H/'route_catalog_61_noble_r06.json';write(output,d);report=dict(status='SOURCE_BOUND_AWAITING_FINAL_AUTHORED_RUNTIME_SCENES',catalog=ref(output),preserved_prior_catalog=ref(prior),expanded_cases=len(expanded),forward_records=len(d['routes']),case_classes=dict(collections.Counter(r['case_class']for r in expanded)),changed_route_vectors=0,noble_source_rebindings=changes,required_native_pack_sets=len(act['native_packs']),required_private_append_sets=len(act['appended_surface_patches']),required_collision_contracts=len(act['collision_contracts']),runtime_launched=False);write(H/'catalog_61_noble_r06_report.json',report);print(json.dumps({k:v for k,v in report.items()if k!='noble_source_rebindings'},indent=2))
if __name__=='__main__':main()
