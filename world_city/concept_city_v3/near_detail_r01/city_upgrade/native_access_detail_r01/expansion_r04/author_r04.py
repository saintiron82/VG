"""Bounded original-face native access audit and four static bridge candidates.
Reuse frozen r03 ownership/quad guards, existing common author/crop/mesh helpers.
No scene, source, production catalog, collider, or previous revision writes.
"""
from pathlib import Path
import argparse,collections,copy,itertools,json,math,resource,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;N=H.parent;U=N.parent
sys.path.insert(0,str(N/'r03'));import author_r03 as a
R=a.R;C=a.C;P=a.P;core=a.previous.source_parts.__globals__['core']
IP=C/'playable_detail_r01/generated/tile_r01/index.json';CV=U/'coverage/type_coverage.json'
PLAN=H/'source_plan_r04.json';CAT=H/'modules/catalog_r04.json';LEDGER=H/'scope_ledger.json'
LIMIT=10_000_000;AS=256*1024*1024;CPU=90
KEYS=['registered_water_crossing_east_radial','registered_water_crossing_east_wall_service','registered_water_crossing_north_back_lane','v3_waterworks_stone_road_bridge_bay']
read=a.read;sha=a.sha;digest=a.digest;save=a.save

def limits():
 resource.setrlimit(resource.RLIMIT_AS,(AS,AS));resource.setrlimit(resource.RLIMIT_CPU,(CPU,CPU))

def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def output_bytes():return sum(p.stat().st_size for p in H.rglob('*') if p.is_file())
def rule_for(key):
 if key not in KEYS:raise ValueError('unapproved_asset_selection')
 return {'kind':'paving' if key.startswith('v3_') else 'planks','material':'stone' if key.startswith('v3_') else 'timber','source_components':['arch' if key.startswith('v3_') else 'deck'],'semantic':'static_bridge_retained_original_deck_top_only','cuts':'conservative_transformed_source_bounds_disjoint_from_actual_top_quad_required','boundary_quantum_m':P,'allow_paint_box_only':True}

def source_owners_and_cuts(master,rule,pitch):
 """Generic fail-closed box ownership; cuts can only be excluded analytically.
 Bounds are used solely for a negative cut/quad intersection proof, NEVER support.
 Actual support still requires an original retained quad AND exact paint-top union.
 """
 if master.get('assembly_cuts'):raise ValueError('unsupported_assembly_cut_ownership')
 boxes=[];cuts=[];components={c['id']:c for c in master['components']}
 for inst,op,tr in a.previous.source_parts(master):
  if inst['component'] not in rule['source_components']:continue
  part=next(p for p in components[inst['component']]['parts'] if p['id']==op['part'])
  if part.get('dynamic') or part.get('metadata',{}).get('dynamic'):raise ValueError('dynamic_part_excluded')
  shape=op['shape']
  if core.prepare_shape(shape,pitch)!=shape:raise ValueError('pitch_dependent_shape_expansion_unsupported')
  if op['action']=='cut':
   lo,hi=core.shape_bounds(shape);points=[core.apply(tr,p) for p in itertools.product(*zip(lo,hi))]
   cuts.append({'instance':inst['id'],'component':inst['component'],'part':op['part'],'operation':op['id'],'operation_sha256':digest(op),'shape_sha256':digest(shape),'transform':tr,'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)],'bounds_method':'unchanged_common_core.shape_bounds_and_apply_to_8_bound_corners'})
   continue
  if op['action']!='paint' or op.get('material')!=rule['material'] or shape['kind']!='box':raise ValueError('unsupported_semantic_paint_operation')
  if tr['basis']!=core.IDENTITY:raise ValueError('unsupported_rotated_source_paint_box')
  lo=[shape['min'][i]+tr['translation'][i] for i in range(3)];hi=[shape['max'][i]+tr['translation'][i] for i in range(3)]
  l=[a.strict_grid(v) for v in lo];h=[a.strict_grid(v) for v in hi]
  if any(x>=y for x,y in zip(l,h)):raise ValueError('nonpositive_source_box')
  boxes.append({'instance':inst['id'],'component':inst['component'],'operation':op['id'],'material':op['material'],'part':op['part'],'min':lo,'max':hi,'operation_sha256':digest(op),'top_y_integer_cells':h[1],'rect_uv_integer_cells':[l[0],-h[2],h[0],-l[2]],'semantic_key':[inst['id'],inst['component'],op['material'],op['part']]})
 if not boxes:raise ValueError('no_selected_box_paint')
 return boxes,cuts

def cut_exclusion(quad,cuts):
 low=[min(p[i] for p in quad) for i in range(3)];high=[max(p[i] for p in quad) for i in range(3)];proof=[]
 for cut in cuts:
  separators=[]
  for axis in range(3):
   if cut['max'][axis]<low[axis]:separators.append({'axis':axis,'cut_side':'below','positive_gap_m':low[axis]-cut['max'][axis]})
   if cut['min'][axis]>high[axis]:separators.append({'axis':axis,'cut_side':'above','positive_gap_m':cut['min'][axis]-high[axis]})
  if not separators:raise ValueError('cut_intersects_or_touches_quad_bound_unsupported')
  proof.append({'cut':cut,'separating_intervals':separators,'strict_disjoint':True,'geometric_tolerance_m':0.0})
 return proof

def poses(index,keys):
 rows={k:[] for k in keys};deps={}
 for tile_id,tile in sorted(index['tiles'].items()):
  path=R/tile['instances_path'];data=read(path)
  for item in data.get('common_instances',[]):
   if item['asset_key'] in rows:
    assert sha(path)==tile['instances_sha256'];deps[str(path.relative_to(R))]=sha(path)
    rows[item['asset_key']].append({'owner_tile':tile_id,'source_instances':ref(path),'instance':item,'instance_sha256':digest(item)})
 return rows,deps

def collision_baseline(index,src,instances):
 ids={p['instance']['id'] for p in instances};matches=[]
 for c in index['collision_contracts']:
  source=c.get('native_source',c.get('source_native_render',{}));declared={c.get('native_placement_id'),c.get('visual_owner'),*c.get('disable_native_mesh_collider_ids',[]),*c.get('keep_native_mesh_collider_ids',[])}
  if not(ids&declared or source.get('sha256')==src['render_sha256']):continue
  matches.append({'id':c['id'],'indexed_contract_sha256':digest(c),'native_placement_id':c.get('native_placement_id'),'source_render_identity_matches':source.get('sha256')==src['render_sha256'],'declared_geometry_refs':{k:v for k,v in c.items() if isinstance(v,dict) and 'path' in v and 'sha256' in v},'declared_limits':{k:v for k,v in c.items() if k.startswith('maximum_') and type(v) in (int,float)},'representation_kind':c.get('representation_kind',c.get('schema','explicit_contract'))})
 disabled=sorted(ids&set(index['disabled_native_collider_ids']));disabled_instances=sorted(ids&set(index.get('disabled_native_instance_ids',[])))
 return {'kind':'explicit_continuous_or_replacement_proxy' if matches else 'original_native_mesh','contracts':matches,'disabled_native_collider_ids':disabled,'disabled_native_instance_ids':disabled_instances,'collision_changed':False,'maximum_additional_visual_offset_from_source_m':.0375,'proxy_difference_is_not_zero_when_existing_contract_present':bool(matches),'new_floor_or_collider':False,'walking_route_validated_in_r04':False}

def candidate(key,index,instances):
 src=index['common_assets'][key];rule=rule_for(key);mp=R/src['master_path'];rp=R/src['render_path'];assert sha(mp)==src['master_sha256'] and sha(rp)==src['render_sha256']
 master=read(mp);render=read(rp);boxes,cuts=source_owners_and_cuts(master,rule,src['pitch_m']);faces=[];placements=[];excluded=collections.Counter();demand={}
 for gi,g in enumerate(render['groups']):
  if g['material']!=rule['material']:continue
  for qi,q in enumerate(g['quads']):
   try:rect=a.top_rectangle(q);own=a.ownership(rect,a.strict_grid(q[0][1]),boxes);cutproof=cut_exclusion(q,cuts)
   except ValueError as e:excluded[str(e)]+=1;continue
   f={'group_index':gi,'quad_index':qi,'quad_sha256':digest(q),'quad':q,'rect_uv_integer_cells':rect,'plane_y_m':q[0][1],'operation_owners':own['owners'],'semantic_owner_union':own['proof'],'semantic_key':own['semantic_key'],'cut_exclusion_proofs':cutproof};faces.append(f)
   for p in a.previous.patches(rect):
    trim=p['trim'];token=rule['kind']+'_'+str(p['seed'])+'_'+digest(trim)[:12];demand[token]={'id':token,'kind':rule['kind'],'seed':p['seed'],'trim':trim}
    placements.append({'module_key':token,'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[p['low_uv'][0],q[0][1]+.0375,-p['low_uv'][1]]},'source_face_ref':[gi,qi],'source_face_sha256':f['quad_sha256'],'bounds_uv_m':p['low_uv']+p['high_uv'],'source_plane_y_m':q[0][1],'collision_changed':False})
 assert faces and placements
 return {'asset_key':key,'source_master_path':src['master_path'],'source_master_sha256':src['master_sha256'],'source_render_path':src['render_path'],'source_render_sha256':src['render_sha256'],'source_pitch_m':src['pitch_m'],'rule':rule,'faces':faces,'placements':placements,'excluded':dict(excluded),'actual_instances':instances,'existing_collision_unchanged':True,'source_collision_baseline':collision_baseline(index,src,instances)},demand

def source_summary(master):
 counts=collections.Counter();examples={};transforms=collections.Counter();cuts=0;sourceids=[]
 for ins,op,tr in a.previous.source_parts(master):
  kind=op['shape']['kind'];signature='|'.join([ins['component'],op['action'],op.get('material',''),op.get('part',''),kind]);counts[signature]+=1
  if len(examples.setdefault(signature,[]))<3:examples[signature].append({'operation':op['id'],'operation_sha256':digest(op)})
  basis=tr['basis'];normal=[basis[i][2] for i in range(3)]
  mode='identity' if basis==core.IDENTITY else ('horizontal_extrusion_cap' if normal[0]==0 and abs(normal[1])==1 and normal[2]==0 else 'sloped_or_nonhorizontal_extrusion_or_other_rigid_operation')
  transforms[mode]+=1;cuts+=op['action']=='cut';sourceids.append([ins['id'],op['id'],digest(op),digest(tr)])
 md=master.get('metadata',{});ext=master.get('extensions',{});interesting={}
 for k,v in md.items():
  if any(word in k for word in ['boundary','floor','surface','span','profile','source','origin','owner','step','riser','gate']):
   interesting[k]={'sha256':digest(v),'count':len(v),'sample':v[0].get('operation_id',v[0].get('id')) if v and isinstance(v[0],dict) else None} if isinstance(v,list) else {'sha256':digest(v),'value':v if not isinstance(v,dict) else {s:t for s,t in v.items() if type(t) in (str,int,float,bool)}}
 return {'operation_signature_counts':dict(counts),'operation_examples':examples,'operation_sequence_sha256':digest(sourceids),'operation_transform_classes':dict(transforms),'component_cut_count':cuts,'assembly_cut_count':len(master.get('assembly_cuts',[])),'source_metadata_keys':sorted(md),'semantic_metadata_evidence':interesting,'source_extension_evidence':{k:ext[k] for k in ['actual_placed','part_kind','network','datum','limits'] if k in ext}}

def face_summary(render):
 result=[]
 for gi,g in enumerate(render['groups']):
  accepted=[];reasons=collections.Counter();area=0;sloped=0
  for qi,q in enumerate(g['quads']):
   try:r=a.top_rectangle(q);accepted.append([qi,digest(q)]);area+=(r[2]-r[0])*(r[3]-r[1])*P*P
   except ValueError as e:
    reasons[str(e)]+=1
    if len(q)==4 and all(len(p)==3 for p in q):
     n=a.previous.cross([q[1][i]-q[0][i] for i in range(3)],[q[2][i]-q[0][i] for i in range(3)])
     if n[1]>0 and (n[0]!=0 or n[2]!=0):sloped+=1
  result.append({'group_index':gi,'material':g['material'],'quads':len(g['quads']),'group_geometry_sha256':digest(g['quads']),'strict_horizontal_rectangles':len(accepted),'strict_top_refs_sha256':digest(accepted),'strict_horizontal_area_m2':area,'sloped_upward_quads':sloped,'rejected_by_frozen_guard':dict(reasons),'semantic_ownership_not_inferred_from_face_count':True})
 return result

def audit(index,posemap):
 coverage=read(CV);rows=[]
 for category in ['native_paving_access','small_bridges']:
  group=next(t for t in coverage['types'] if t['category']==category)
  for key in group['asset_keys']:
   src=index['common_assets'][key];assert sha(R/src['master_path'])==src['master_sha256'] and sha(R/src['render_path'])==src['render_sha256'];m=read(R/src['master_path']);r=read(R/src['render_path']);s=source_summary(m);collision=collision_baseline(index,src,posemap[key]);metadata=m.get('metadata',{});reasons=[]
   if key in KEYS:status='SUPPORTED_CANDIDATE_R04';next_step='Bind reviewed candidate plan/catalog after independent scene/active-budget review.'
   elif key in ['registered_phase02_estate_two_flight_stair','registered_water_crossing_market_north']:status='EXISTING_R03';next_step='Reuse immutable r03 source support proof and modules.'
   else:
    status='UNSUPPORTED_THIS_ADAPTER';reasons=['EXACT_ACTUAL_QUAD_TO_SOURCE_EXTRUSION_OWNER_UNPROVEN']
    if s['component_cut_count'] or s['assembly_cut_count']:reasons.append('SOURCE_CUT_OWNERSHIP_AND_VISIBLE_FACE_SUBTRACTION_REQUIRED')
    if metadata.get('boundary_regions_xz_m') or metadata.get('source_spans'):reasons.append('OWNED_FLOOR_ACCESS_AND_BOUNDARY_WALL_TOPS_MUST_BE_SEPARATED')
    if collision['contracts']:reasons.append('CONTINUOUS_PROXY_IS_NOT_VISUAL_SUPPORT_OR_NEW_FLOOR')
    if 'r1_source_surface_provenance' in metadata or 'source_surface' in metadata:reasons.append('DECLARED_PROFILE_SURFACES_REQUIRE_RIGID_LOCAL_FACE_AND_CUT_BINDING')
    next_step='Use operation-ID and source-profile semantics to prove each actual top quad inside the exact transformed paint region minus all selector/part-relevant cuts; preserve private boundaries/retained walls. Otherwise keep original. No AABB fill or source compile in r04.'
   rows.append({'asset_key':key,'category':category,'status':status,'reason_codes':reasons,'source_master':ref(R/src['master_path']),'source_render':ref(R/src['render_path']),'source_pitch_m':src['pitch_m'],'actual_placement_count':len(posemap[key]),'actual_instances':posemap[key],'source_operations':s,'actual_retained_face_inventory':face_summary(r),'collision_baseline':collision,'next_step':next_step,'new_geometry_generated':key in KEYS})
 return {'schema':'riverstone.native_access_detail.scope_audit.v1','revision':'expansion_r04','source_city_index':ref(IP),'coverage_input':ref(CV),'count_contract':'21 native paving/access assets plus all 5 small bridges; one bridge and one stair already r03, four additional bridges selected','assets':rows,'explicit_exclusions':['Moving drawbridge/state components','Main-bridge static approaches outside requested native21+small4 scope','New collider/floor, original source/full compilation, production binding','Earth/grass/private property surfaces cannot become paving from material or AABB inference alone'],'summary':dict(collections.Counter(r['status'] for r in rows))}

def make_plan():
 index=read(IP);assert sha(IP)==read(N/'source_policy.json')['source_city_index_sha256']
 coverage=read(CV);allkeys=[k for t in coverage['types'] if t['category'] in ['native_paving_access','small_bridges'] for k in t['asset_keys']];posemap,pdeps=poses(index,allkeys);assert len(allkeys)==26 and all(len(posemap[k])==1 for k in allkeys)
 assets=[];demand={}
 for key in KEYS:
  row,d=candidate(key,index,posemap[key]);assets.append(row);demand.update(d)
 plan={'schema':'riverstone.native_access_detail.plan.v1','revision':'expansion_r04','source_city_index_sha256':sha(IP),'assets':assets,'module_demand':list(demand.values()),'maximum_additional_visual_offset_from_source_m':.0375,'runtime_activation':False,'whole_city_upgrade_complete':False,'r04_provenance':{'author':ref(Path(__file__)),'frozen_r03_guards':ref(N/'r03/author_r03.py'),'original_patch_rule':ref(N/'author_native_access.py'),'common_core':ref(Path(core.__file__)),'common_union':ref(Path(a.polygons.__file__)),'existing_r03_plan':ref(a.PLAN),'existing_r03_catalog':ref(a.CAT),'support_rule':'actual retained top quad AND same-semantic exact box-top union; every cut strictly disjoint, no bounds-as-support','source_geometry_changed':False,'collision_changed':False}}
 return plan,audit(index,posemap),pdeps

def build(audit_only=False):
 start=time.perf_counter();plan,ledger,pdeps=make_plan();base=read(a.CAT);known={m['id']:m for m in base['modules']};new=[d for d in plan['module_demand'] if d['id'] not in known]
 audit_info={'assets':[{'key':x['asset_key'],'faces':len(x['faces']),'placements':len(x['placements'])} for x in plan['assets']],'demand':len(plan['module_demand']),'existing_r03_reuse':len(plan['module_demand'])-len(new),'new_trim_demands':len(new),'ledger_summary':ledger['summary']}
 if audit_only:print(json.dumps(audit_info));return
 assert len(new)<=64 and len(plan['assets'])==4 and sum(len(x['placements']) for x in plan['assets'])<=500
 frozen={str(p.relative_to(R)):sha(p) for p in [IP,CV,N/'source_policy.json',a.PLAN,a.CAT,N/'r03/author_r03.py',N/'author_native_access.py',Path(core.__file__),Path(a.edge.__file__),Path(a.common.__file__),Path(a.polygons.__file__),C/'playable_detail_r01/native_access_catalog.json']};frozen.update(pdeps)
 for row in ledger['assets']:
  for name in ['source_master','source_render']:frozen[row[name]['path']]=row[name]['sha256']
 rows=[];safe=read(U/'surface_modules/inputs/safe_offset_rules.v1.json');geom=compiled=0
 for d in plan['module_demand']:
  if d['id'] in known:
   m=known[d['id']];assert m['kind']==d['kind'] and m['seed']==d['seed'] and m['trim']==d['trim'];assert sha(R/m['master_path'])==m['master_sha256'] and sha(R/m['render_path'])==m['render_sha256'];rows.append(copy.deepcopy(m))
   for k in ['master','render']:frozen[m[k+'_path']]=m[k+'_sha256']
  else:
   assert d['trim']!={'width_m':1.0,'height_m':1.0,'offset_m':[0.0,0.0]},'A full module should use published cache, never compile here'
   spec=copy.deepcopy(safe);spec['trim']=d['trim'];master,c,render,contract,checks=a.edge.compile_exact_crop(spec,d['kind'],d['seed'],boundary_quantum_m=P)
   mp=CAT.parent/(d['id']+'.master.json');rp=CAT.parent/(d['id']+'.render.json');mb=a.common.payload(master);rb=a.common.payload(render);geom+=len(mb)+len(rb);assert output_bytes()+len(mb)+len(rb)<LIMIT-2_000_000
   a.common.write_exact(mp,mb);a.common.write_exact(rp,rb);compiled+=1
   rows.append({**d,'master_path':str(mp.relative_to(R)),'master_sha256':sha(mp),'render_path':str(rp.relative_to(R)),'render_sha256':sha(rp),'payload_hash':c['payload_hash'],'cells':len(c['cells']),'quads':render['quad_count'],'checks':checks})
 save(PLAN,plan);save(LEDGER,ledger);cat=copy.deepcopy(base);cat.update(revision='expansion_r04',source_plan_sha256=sha(PLAN),modules=rows,source_dependencies=frozen,runtime_activation=False,original_collision_unchanged=True);cat['incremental_reuse']={'referenced_existing_module_rows':len(rows)-compiled,'compiled_new_trim_rows':compiled,'compiled_full_original_assets':0,'new_geometry_bytes':geom};save(CAT,cat)
 assert frozen=={p:sha(R/p) for p in frozen},'source/runtime/previous dependency changed during build'
 report={'all_pass':True,**audit_info,'new_trim_modules_compiled':compiled,'new_geometry_bytes':geom,'source_plan':ref(PLAN),'module_catalog':ref(CAT),'scope_ledger':ref(LEDGER),'frozen_dependencies':frozen,'all_dependencies_unchanged':True,'runtime_activation':False,'new_colliders':0,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'enforced_limits':{'address_space_bytes':AS,'cpu_seconds':CPU,'total_output_bytes':LIMIT},'output_bytes_before_report':output_bytes()};save(H/'build_report.json',report);assert output_bytes()<LIMIT
 print(json.dumps({k:v for k,v in report.items() if k!='frozen_dependencies'}))
if __name__=='__main__':
 limits();ap=argparse.ArgumentParser();ap.add_argument('--audit-only',action='store_true');build(ap.parse_args().audit_only)
