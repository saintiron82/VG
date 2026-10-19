"""Immutable final vector inventory, before final atomic source binding exists."""
import pathlib,json,hashlib,copy,collections,math,numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';REV=H.parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:dict(path=str(p.relative_to(ROOT)),sha256=sha(p));read=lambda p:json.loads(p.read_bytes())
def write(p,v):
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def expanded(r):return [r['id'],r['id']+'_REVERSE']if r.get('bidirectional')else[r['id']]
def offset_chain(ps,offset):
 p=np.asarray(ps,dtype=float);u=np.diff(p,axis=0);u=u/np.linalg.norm(u,axis=1)[:,None];norm=np.column_stack((-u[:,1],u[:,0]));out=[]
 for i,q in enumerate(p):
  v=norm[0]if i==0 else norm[-1]if i==len(p)-1 else (norm[i-1]+norm[i])/(1+np.dot(norm[i-1],norm[i]));out.append((q+offset*v).tolist())
 return out

def main():
 oldp=REV/'public_network_r18_authored_r02/route_catalog_61_contracts_r07.json';old=read(oldp);d=copy.deepcopy(old);d['status']='PENDING_FINAL_ATOMIC_ACTIVATION_BINDING';d['sources']['original_412_catalog']=ref(oldp);d['sources']['original_412_result']=ref(REV/'public_network_r18_runtime_r01/evidence/public_network_replay.json');retp=REV/'pending_extensions_r01/north_negative_retirement_r01.json';ret=read(retp);rid=ret['case_id'];d['routes']=[r for r in d['routes']if r['id']!=rid];assert len(old['routes'])-len(d['routes'])==1;d['sources']['north_negative_retirement']=ref(retp)
 finalp=CITY/'registered_topography/revisions/r17_district_batches/coherent_final24_r02/route_handoff_ready_r05.json';f=read(finalp);d['sources']['ready_entries_final23']=ref(finalp);d['sources']['final23_inner_entry_handoff']=f['inner_entry_chain_handoff'];known={r['id']for r in d['routes']};added=[]
 for q in f['entries']:
  assert q['id']not in known;row=dict(id=q['id'],case_class='ordinary_entry',points_xyz_m=q['polyline_xyz_m'],source_road_ids=[q['public_road_id'],q['id']],test_scope='Exact released public-to-inner-court chain, including the explicitly authored compact-core inner continuation where present; both directions.',provenance=[ref(finalp),f['terrain_handoff'],f['inner_entry_chain_handoff']],resolved_geometry_proof=ref(finalp),bidirectional=True,holding_id=q['holding_id'],entry_id=q['id'],source_width_m=q['width_m'],source_plane_owner_ids=sorted({s['owner_id']for s in q['exact_plane_segments']}),source_grade_and_step_disclosures=dict(maximum_centerline_grade=q['maximum_centerline_grade'],inherited_public_steps=q['inherited_public_steps'],existing_public_top_overlaps=q['existing_public_top_overlaps']));d['routes'].append(row);added.append(q['id']);matches=[r for r in d['coverage']['ordinary_entries']if r.get('holding_id')==q['holding_id']]
  if matches:
   assert len(matches)==1;matches[0].update(status='accepted',route_ids=[q['id']],activation_condition='Final23 native/top/physical-owner and exact replacement ledgers must be activated atomically.');matches[0].pop('reason',None);matches[0].pop('source',None)
  else:
   cid=q['holding_id']+':EXACT_PUBLIC_RESERVATION';d['coverage']['ordinary_entries'].append(dict(id=cid,holding_id=q['holding_id'],status='accepted',route_ids=[q['id']],source=ref(finalp),activation_condition='Compact-core source addition, exact final23 native/top ownership activation required.'));d['coverage']['required_ordinary_entries_ids'].append(cid)
 for q in f['superseded_protected_domains']:
  rows=[r for r in d['coverage']['ordinary_entries']if r.get('holding_id')==q['holding_id']];assert len(rows)==1;rows[0].update(status='retired',route_ids=[],reason=q['status']+'; preserve actual '+q['retained_owner_id']+' without activating the cancelled ordinary holding.',source=ref(finalp))
 protected=[]
 for name in ['abbey_gate_extension_r01.json','cloister_extension_r01.json']:
  path=REV/'pending_extensions_r01'/name;q=read(path);d['sources'][name.removesuffix('.json')]=ref(path)
  for r in q['routes']:d['routes'].append(r);protected.append(r['id'])
 trainp=CITY/'assemblies/landmarks/registered/precinct_r06_whole/final_acceptance_r01/training_entry_runtime_handoff.json';t=read(trainp);d['sources']['required_training_entry']=ref(trainp);d['routes'].append(dict(id=t['id'],case_class='precinct_entry',points_xyz_m=[[x,18.,z]for x,z in t['polyline_xz_m']],source_road_ids=['CASTLE_APPROACH',t['named_public_segment_id']],source_width_m=2,bidirectional=True,bridge_state='ROAD_OPEN',test_scope='Complete retained training entrance, through existing native stair/approach to the exact named public landing; both directions.',provenance=[ref(trainp),t['source_audit'],t['static_walk_tests']],resolved_geometry_proof=ref(trainp),hint_height_policy='Y18 is only a floor-selection hint; all actual standing heights must be resolved from the final scene.',source_alias='RETAINED_TRAINING_ENTRY_R01'));protected.append(t['id'])
 width=[]
 for folder,prefix,road in [('fixed_bridge_candidate_r02','FIXED_BRIDGE_LANE_','MAIN_BRIDGE'),('port_bridge_candidate_r04','PORT_TIE_LANE_','PORT_BRIDGE_TIE')]:
  path=REV/folder/'prepared_runtime.json';p=read(path);d['sources'][folder+'_width_vectors']=ref(path)
  for r in p['routes']:
   if not r['id'].startswith(prefix)or r['id'].endswith('_REVERSE'):continue
   rr=dict(id=r['id'],case_class='bridge_approach',points_xyz_m=r['points'],source_road_ids=[road],bidirectional=True,bridge_state='ROAD_OPEN',test_scope='Preserved actual focused width-probe vector; final combined-scene both-direction regression.',provenance=[ref(path)],resolved_geometry_proof=ref(path));d['routes'].append(rr);width.append(rr['id'])
 sidep=CITY/'registered_topography/revisions/public_corridors_r18/causeway_side_joins_r01/integration_handoff.json';surveyp=CITY/'assemblies/waterworks/registered_bridge/side_joins_r01/north_side_interfaces.json';survey=read(surveyp);d['sources']['causeway_side_joins']=ref(sidep);d['sources']['causeway_side_survey']=ref(surveyp);widthprovenance=[]
 for face in survey['interfaces']:
  for off in[-1.5,1.5]:
   points=offset_chain(face['source_polyline_tail_xz_m'],off);rr=dict(id=face['id']+':NATIVE_JOIN_LANE_'+str(off),case_class='bridge_approach',points_xyz_m=[[x,2.,z]for x,z in points],source_road_ids=[face['id']],bidirectional=True,bridge_state='ROAD_OPEN',test_scope='Bounded offset lane through the exact authored four-metre road-to-native join, with a 0.3 m capsule radius; final-scene probe.',source_width_m=4.,probe_center_offset_m=off,provenance=[ref(sidep),ref(surveyp),ref(H/'build_vectors.py')],resolved_geometry_proof=ref(sidep),hint_height_policy='Actual final scene replaces Y2 floor hints.');d['routes'].append(rr);width.append(rr['id']);widthprovenance.append(dict(id=rr['id'],source_road=face['id'],source_tail_xz_m=face['source_polyline_tail_xz_m'],offset_m=off,output_chain_xz_m=points,algorithm='Exact consecutive-segment offset intersections; no source geometry changes.'))
 originalids={x for r in old['routes']for x in expanded(r)};finalids=[x for r in d['routes']for x in expanded(r)];assert len(finalids)==len(set(finalids))==481;assert originalids-set(finalids)=={rid};assert len(added)==23 and len(protected)==4 and len(width)==8
 # Old route rows are value-identical, not reconstructed from older plan axes.
 current={r['id']:r for r in d['routes']};assert all(current[r['id']]==r for r in old['routes']if r['id']!=rid)
 duplicate_knots=[dict(id=r['id'],index=i,distance_m=math.dist(p,q))for r in d['routes']for i,(p,q)in enumerate(zip(r['points_xyz_m'],r['points_xyz_m'][1:]))if math.dist(p,q)<1e-8]
 protected12=['NOBLE:E1:registered_r1:service_gate','NOBLE:E2:registered_r1:service_gate']+protected
 d['vector_accounting']=dict(original_cases=412,retired_expectations=[dict(id=rid,source=ref(retp))],new_final23_directions=46,new_protected_directions=8,new_width_directions=16,total_cases=481,original_vectors_value_identical=True,ordinary_entry_roots=106,protected_required_12_directions=[x for i in protected12 for x in expanded(current[i])],protected_preserved_original_4_directions=[x for i in protected12[:2]for x in expanded(current[i])],protected_new_8_directions=[x for i in protected for x in expanded(current[i])],new_route_ids=added+protected+width,duplicate_or_near_duplicate_knots=duplicate_knots)
 d['pending_final_activation']=['Final23 ownership corrections and source-plane precision ledger','Atomic final public/private top and side replacement ledgers','Selected port guard native replacement and source-cell compatibility','Final authored/runtime scene hashes and exact-zero runtime ledger','Exact-world local-origin collider extraction parity and combined 481-case replay']
 d['limits'].append('This vector-only immutable catalog is not launchable until its final atomic activation requirements are rebound and verified. Previous focused passes are not summed as a final result.');write(H/'route_vectors_r01.json',d);write(H/'width_probe_provenance.json',widthprovenance);write(H/'vector_accounting.json',d['vector_accounting']);print(json.dumps(dict(catalog=ref(H/'route_vectors_r01.json'),cases=481,ordinary_roots=106,duplicate_knots=duplicate_knots[:6],classes=dict(collections.Counter(r['case_class']for r in d['routes'])))))
if __name__=='__main__':main()
