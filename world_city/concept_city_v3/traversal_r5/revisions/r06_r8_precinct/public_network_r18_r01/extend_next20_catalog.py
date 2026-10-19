"""Bind the released next20 without modifying the 372-case predecessor."""
import collections,hashlib,json,math,pathlib,sys
H=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
sys.path.insert(0,str(H))
import catalog
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def write(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
 base=H/'route_catalog_ready_r04.json';before=ref(base)
 assert before['sha256']=='88fb03035d971f379efa773cfad6c6f0677e7d9c172ba3e384608e17e6918de2'
 d=read(base);prior=read(base);assert len(catalog.validate(d))==372
 folder=ROOT/'world_city/concept_city_v3/registered_topography/revisions/r17_district_batches/coherent_batch20_r01'
 path=folder/'route_handoff_ready_r02.json';handoff=read(path)
 assert ref(path)['sha256']=='8f862c26b2e1d83878edc8c77d8809857b1eb4bbc139c85dbb1ed231b4b6fdce'
 assert len(handoff['entries'])==20 and not handoff['failures']
 cp=folder/'ready_subset_contract_r01.json';contract=read(cp);packpath=catalog.source(contract['native_pack']);pack=read(packpath)
 assert set(pack['accepted_holding_ids'])==set(handoff['accepted_holding_ids'])==set(contract['accepted_holding_ids'])
 assert not {r.get('holding_id')for r in d['routes']}&set(handoff['accepted_holding_ids'])
 candidates=read(catalog.source(d['sources']['ordinary_entry_candidates']))
 byholding={r['holding_id']:r for r in candidates['entries']};coverage={r['id']:r for r in d['coverage']['ordinary_entries']}
 for row in handoff['entries']:
  pts=row['polyline_xyz_m'];assert not row['errors'];assert all(math.dist(p,q)>1e-8 for p,q in zip(pts,pts[1:]))
  holding=row['holding_id'];owners=sorted({r['owner_id']for r in row['exact_plane_segments']});assert owners
  d['routes'].append(dict(id=row['id'],case_class='ordinary_entry',points_xyz_m=pts,source_road_ids=[row['public_road_id'],row['id']],test_scope='Exact released next20 public-to-court chain through finite source planes, both directions. Retained public step events are explicit. No interior or cart claim.',provenance=[ref(path),handoff['terrain_handoff'],ref(packpath),ref(cp)],resolved_geometry_proof=ref(path),bidirectional=True,holding_id=holding,entry_id=row['id'],source_width_m=row['width_m'],source_plane_owner_ids=owners,source_waypoints_preserved=True,source_maximum_centerline_grade=row['maximum_centerline_grade'],inherited_public_steps=row['inherited_public_steps']))
  cid=byholding[holding]['id'];assert coverage[cid]['status']=='held';coverage[cid].clear();coverage[cid].update(id=cid,holding_id=holding,status='accepted',route_ids=[row['id']],activation_condition='Exact sealed next20 native pack and top/physical-owner field must appear in the same joint integrated scene.')
 d['sources'].update(prior_372_catalog=before,ready_entries_next20=ref(path),ready_native_pack_next20=ref(packpath),ready_contract_next20=ref(cp),ready_freeze_next20=ref(folder/'ready_subset_freeze_r01.json'),private_top_patch_next20=contract['top_patch'])
 d['activation_requirements']['native_packs'].append(ref(packpath));d['activation_requirements']['appended_surface_patches'].append(contract['top_patch'])
 d['source_candidate_accounting']['private_holding_batches'].update(next20=ref(path),private_holdings=61,accepted_entry_roots=83,held_candidates=17,inherited_public_steps_next20=contract['inherited_public_steps'])
 d['limits']=[v.replace('The ready 41 holding entries plus 22 sealed B15 roots are accepted; 37 ordinary candidates remain held.','The ready 61 holding entries plus 22 sealed B15 roots are accepted; 17 ordinary candidates remain held.')for v in d['limits']]
 d['limits']+=['The next20 routes preserve three source-declared retained public height steps. Actual collision support and traversal remain pending on the joint scene.','All 96 next20 door branches remain source references; this extension admits only its 40 public-entry directions.']
 assert d['routes'][:len(prior['routes'])]==prior['routes'];assert ref(base)==before
 expanded=catalog.validate(d);assert len(expanded)==412
 out=H/'route_catalog_61_ready_r05.json';write(out,d)
 report=dict(status='SOURCE_BOUND_AWAITING_EXACT_JOINT_SCENE',catalog=ref(out),preserved_predecessor=before,unchanged_previous_route_records=len(prior['routes']),forward_records=len(d['routes']),expanded_cases=len(expanded),case_classes=dict(collections.Counter(r['case_class']for r in expanded)),accepted_entry_roots=83,held_candidates=17,new20_source=ref(path),native_pack_sets=len(d['activation_requirements']['native_packs']),private_top_patch_sets=len(d['activation_requirements']['appended_surface_patches']),inherited_public_steps=contract['inherited_public_steps'],runtime_launched=False)
 write(H/'catalog_61_binding_report.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
