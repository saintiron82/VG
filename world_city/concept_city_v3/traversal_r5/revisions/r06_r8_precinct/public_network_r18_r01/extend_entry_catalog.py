"""Add the sealed next18 routes without modifying the initial 23-only catalog."""
import collections,hashlib,json,math,pathlib,sys
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(H));import catalog
T=ROOT/'world_city/concept_city_v3/registered_topography/revisions/r17_district_batches'
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def write(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
 base=H/'route_catalog.json';d=read(base);folder=T/'coherent_batch18_r01';path=folder/'route_handoff_ready_r03.json';handoff=read(path);assert ref(path)['sha256']=='b50f81248c20efbc84f424274dfdee0b06a6c679a32feb42ef6dfb45a575d2ec';assert len(handoff['entries'])==18 and not handoff['failures']
 contract_path=folder/'ready_subset_contract_r01.json';contract=read(contract_path);pack_path=catalog.source(contract['native_pack']);pack=read(pack_path);assert set(pack['accepted_holding_ids'])==set(handoff['accepted_holding_ids'])
 current={r.get('holding_id')for r in d['routes']if r.get('holding_id')};assert not current&set(handoff['accepted_holding_ids']);candidates=read(catalog.source(d['sources']['ordinary_entry_candidates']));candidatebyholding={r['holding_id']:r for r in candidates['entries']};coverage={r['id']:r for r in d['coverage']['ordinary_entries']};exceptions={r['holding_id']:r for r in contract['local_grade_exceptions']}
 for row in handoff['entries']:
  pts=row['polyline_xyz_m'];assert all(math.dist(p,q)>1e-8 for p,q in zip(pts,pts[1:]));holding=row['holding_id'];exception=exceptions.get(holding)
  route=dict(id=row['id'],case_class='ordinary_entry',points_xyz_m=pts,source_road_ids=[row['public_road_id'],row['id']],test_scope='Exact released next18 public-to-gate chain through finite source planes, both directions; no interior or cart claim.',provenance=[ref(path),handoff['terrain_handoff'],ref(pack_path),ref(contract_path)],resolved_geometry_proof=ref(path),bidirectional=True,holding_id=holding,entry_id=row['id'],source_width_m=row['width_m'],source_plane_owner_ids=row['source_plane_owner_ids'],source_waypoints_preserved=True,source_maximum_centerline_grade=row['maximum_centerline_grade'])
  if exception:route['explicit_design_grade_exception']=exception
  d['routes'].append(route);cid=candidatebyholding[holding]['id'];assert coverage[cid]['status']=='held';coverage[cid].clear();coverage[cid].update(id=cid,holding_id=holding,status='accepted',route_ids=[row['id']],activation_condition='Exact sealed next18 native pack and top/physical-owner field must appear in the joint integrated scene.')
 d['sources'].update(prior_23_catalog=ref(base),ready_entries_next18=ref(path),ready_native_pack_next18=ref(pack_path),ready_contract_next18=ref(contract_path),ready_freeze_next18=ref(folder/'ready_subset_freeze_r01.json'))
 d['activation_requirements']['native_packs'].append(ref(pack_path));d['source_candidate_accounting']['private_holding_batches']=dict(first23=d['sources']['ready_entries'],next18=ref(path),private_holdings=41,fixed_b15_entry_roots=22,accepted_entry_roots=63,held_candidates=37,explicit_local_grade_exceptions=contract['local_grade_exceptions'])
 first_contract_path=T/'contour_bulk_r01/ready_subset_contract_r01.json';first_contract=read(first_contract_path)
 d['sources'].update(ready_contract_first23=ref(first_contract_path),private_top_patch_first23=first_contract['top_patch'],private_top_patch_next18=contract['top_patch'])
 d['activation_requirements']['appended_surface_patches']=[first_contract['top_patch'],contract['top_patch']]
 d['limits']=[v.replace('Only the ready 23 holding entries plus the sealed 22 B15 entries are accepted; the other 55 candidates are held.','The ready 41 holding entries plus 22 sealed B15 roots are accepted; 37 ordinary candidates remain held.')for v in d['limits']]+['BLOCK_010:R8_C006 includes the declared local 15% service-ramp design exception. A capsule result will not imply cart suitability or erase the design exception.']
 expanded=catalog.validate(d);out=H/'route_catalog_41_holdings_r02.json';write(out,d);write(H/'catalog_41_binding_report.json',dict(status='SOURCE_BOUND_AWAITING_EXACT_JOINT_SCENE',catalog=ref(out),forward_records=len(d['routes']),expanded_cases=len(expanded),case_classes=dict(collections.Counter(r['case_class']for r in expanded)),accepted_entry_roots=63,held_candidates=37,new18_source=ref(path),native_pack_sets=len(d['activation_requirements']['native_packs']),explicit_local_grade_exceptions=contract['local_grade_exceptions']));print(json.dumps(read(H/'catalog_41_binding_report.json'),indent=2))
if __name__=='__main__':main()
