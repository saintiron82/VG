"""Read-only original source classification; no sampling, module generation or binding."""
from pathlib import Path
import sys,json,collections,hashlib,resource,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;H=HERE.parent;R=next(p for p in H.parents if(p/'voxel_character/common/core.py').is_file());sys.path.insert(0,str(H/'extrusion_support_r02'));import source_cap_cut_adapter as adapter

def ref(p):return {'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def load(p):return json.loads(p.read_bytes())
def audit():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(90,)*2);start=time.monotonic()
 ledger=load(H/'scope_ledger.json');exclude={'registered_training_r09_recovered_coarse','registered_precinct_cemetery_caps_r03','registered_precinct_r06_common_r02_retained_base'};rows=[]
 for a in ledger['assets']:
  if a['category']!='native_paving_access'or a['status']=='EXISTING_R03'or a['asset_key']in exclude:continue
  for f in ['source_master','source_render']:assert ref(R/a[f]['path'])==a[f]
  m=load(R/a['source_master']['path']);counts=collections.Counter();walk=[];k=a['asset_key'];cuts=[]
  for ins,op,tr in adapter.a.previous.source_parts(m):
   if op['action']=='cut':cuts.append(op);continue
   if op['action']!='paint':continue
   n=[tr['basis'][i][2]for i in range(3)];axis=all(v in [-1,0,1]for row in tr['basis']for v in row);horizontal=n in ([0,1,0],[0,-1,0]);counts['paint']+=1
   counts['signed_axis_horizontal_cap'if axis and horizontal else 'yaw_horizontal_cap'if horizontal else 'other_extrusion_orientation']+=1
   if op['id'].startswith('walk_')and op['material']=='stone_dark':walk.append(op['id'])
  details={'status':'NO_EXISTING_CAP_ADAPTER_SUPPORT_CLAIM'}
  if walk:
   rule={'operation_ids':walk,'source_components':['infrastructure'],'material':'stone_dark','part':'solid'}
   try:
    owners,sourcecuts=adapter.source_contract(m,rule,a['source_pitch_m']);details={'status':'EXISTING_SOURCE_CAP_CONTRACT_PASS','rule_for_review':rule,'walk_owners':len(owners),'cut_count':len(sourcecuts),'top_y_values':sorted(set(o['top_y_m']for o in owners)),'owner_contract_sha256':adapter.e.digest(owners),'cut_contract_sha256':adapter.e.digest(sourcecuts),'actual_quad_patch_support_not_yet_proven':True,'private_boundary_scope':'existing walk operations only; grass, land_use areas, foundation voids and joined walls excluded'}
   except ValueError as err:details={'status':'UNSUPPORTED','reason':str(err)}
   group='horizontal_owned_walk_caps_with_foundation_and_gate_cuts';rank=1
  elif 'noble_entry'in k or 'common_r02_fine'in k:group='rigid_triangle_profile_skins_with_original_proxy';rank=2 if 'common_r02'in k or '_e3_'in k else 4
  elif 'training'in k:group='sloped_wedge_sides_with_instance_local_vertical_cuts';rank=3
  else:group='dense_public_private_step_profile';rank=5
  rows.append({'asset_key':k,'archetype':group,'priority_band':rank,'source_master':a['source_master'],'source_render':a['source_render'],'source_pitch_m':a['source_pitch_m'],'actual_placement_count':a['actual_placement_count'],'original_collision_kind':a['collision_baseline']['kind'],'source_paint_orientation_counts':dict(counts),'component_cut_count':len(cuts),'assembly_cut_count':len(m.get('assembly_cuts',[])),'actual_horizontal_quad_inventory':[{'material':f['material'],'quads':f['strict_horizontal_rectangles'],'area_m2':f['strict_horizontal_area_m2'],'scope':'inventory upper bound only; not authorized patch area'}for f in a['actual_retained_face_inventory']],'existing_adapter_audit':details,'current_status':'AUDIT_ONLY_NO_NEW_CANDIDATE','new_geometry_bytes':0})
 assert len(rows)==17
 groups=[{'archetype':g,'asset_keys':[r['asset_key']for r in rows if r['archetype']==g]}for g in sorted({r['archetype']for r in rows})]
 return {'schema':'riverstone.native_access_detail.remaining_source_audit.v1','source_ledger':ref(H/'scope_ledger.json'),'author':ref(Path(__file__)),'reused_cap_adapter':ref(Path(adapter.__file__)),'all_source_hashes_match':True,'remaining_types':17,'archetypes':groups,'assets':rows,'recommended_first_candidate':'registered_precinct_noble_entry_r01_e7_retained_base','first_candidate_scope':'Only its 31 original stone_dark walk operations, 4 original foundation/gate cuts, exact actual top-quad/union overlap; no land_use, wall or grass region. Existing adapter already accepts source contract. No modules or placements generated yet.','next_profile_exemplar':'registered_precinct_r06_common_r02_fine_access: 40 yaw-horizontal source caps first; 234 other tilted profiles remain separate and unsupported until exact source-side/visible-quad ownership proof. Existing continuous proxy never supplies visual support.','alternative_small_profile_exemplar':'registered_precinct_noble_entry_r01_e3_fine_access: 34 paints / 14 cuts, including 4 yaw-horizontal caps; preserve private/public boundary provenance.','new_geometry_bytes':0,'production_binding_changed':False,'sampling_or_compile_performed':False,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':{'address_space_bytes':256*1024*1024,'cpu_seconds':90},'stop_condition':'Source grouping and bounded next exemplar selected; request slots/disk coordination before any expensive sampling or module compile.'}
if __name__=='__main__':
 d=audit();p=HERE/'source_archetypes.json'
 if p.exists():raise SystemExit('Audit is immutable: choose a new revision to rerun')
 p.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n');print(json.dumps({'path':ref(p),'groups':[(g['archetype'],len(g['asset_keys']))for g in d['archetypes']],'seconds':d['elapsed_seconds'],'rss_kib':d['peak_rss_kib']}))
