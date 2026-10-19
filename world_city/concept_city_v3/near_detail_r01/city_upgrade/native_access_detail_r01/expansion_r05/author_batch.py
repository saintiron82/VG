"""Data-selected original walk surfaces. Reuses frozen exact cap/cut adapter.
Sequential immutable batches; no full-source compile or production binding.
"""
from pathlib import Path
import argparse,collections,copy,json,resource,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;N=H.parent;OLD=N/'expansion_r04';sys.path.insert(0,str(OLD/'extrusion_support_r02'));import source_cap_cut_adapter as adapter
e=adapter.e;b=e.b;a=e.a;R=e.R;P=e.P;read=e.read;sha=e.sha;digest=e.digest
LIMIT=40*1024*1024
AUDIT=OLD/'next_source_audit_r01/source_archetypes.json'
CACHE=[OLD/'combined/module_catalog_r03_plus_r04.json',OLD/'extrusion_support_r01/modules/catalog.json',OLD/'extrusion_support_r02/modules/catalog.json']
BATCHES={'first_e7_e1':[7,1],'remaining_e2_e3_e4_e5_e6':[2,3,4,5,6]}

def output_bytes():return sum(p.stat().st_size for p in H.rglob('*')if p.is_file()and not p.is_symlink())
def save(path,value):
 payload=a.common.payload(value);assert output_bytes()+len(payload)<LIMIT,'40MiB combined output budget';a.common.write_exact(path,payload)
def rules():
 return {r['asset_key']:r for r in read(AUDIT)['assets']if r['archetype']=='horizontal_owned_walk_caps_with_foundation_and_gate_cuts'}
def policy(key,master):
 row=rules()[key];rule=copy.deepcopy(row['existing_adapter_audit']['rule_for_review']);actual=[o['id']for c in master['components']for o in c['operations']if o['action']=='paint'and o.get('material')=='stone_dark'and o['id'].startswith('walk_')]
 assert set(actual)==set(rule['operation_ids']) and len(actual)==len(rule['operation_ids']),'walk ownership drift'
 assert all(name.startswith('walk_')for name in rule['operation_ids'])
 return {**rule,'kind':'paving','semantic_role':'Original walk operations only, excluding grass, land_use, joined walls, foundations and other surfaces','source_policy_audit':b.ref(AUDIT),'geometry_policy':'actual original retained top quad AND exact original walk cap union minus all relevant original component cuts'}

def build(revision):
 assert revision in BATCHES;dest=H/revision;assert not dest.exists(),'immutable output revision already exists';dest.mkdir();start=time.monotonic();idx=read(b.IP);keys=[f'registered_precinct_noble_entry_r01_e{i}_retained_base'for i in BATCHES[revision]];posemap,pdeps=b.poses(idx,keys);assets=[];demand={};rejected=[];summaries=[];unsupported=[]
 for key in keys:
  src=idx['common_assets'][key];prior=rules()[key]
  for field in ['master','render']:assert src[field+'_path']==prior['source_'+field]['path'] and src[field+'_sha256']==prior['source_'+field]['sha256'] and sha(R/src[field+'_path'])==src[field+'_sha256']
  master=read(R/src['master_path']);render=read(R/src['render_path']);rule=policy(key,master)
  try:owners,cuts=adapter.source_contract(master,rule,src['pitch_m'])
  except ValueError as ex:unsupported.append({'asset_key':key,'status':'UNSUPPORTED','reason':str(ex)});continue
  assert len({tuple(o['semantic_key'])for o in owners})==1
  faces=[];placements=[];stats=collections.Counter();area=0
  for gi,g in enumerate(render['groups']):
   if g['material']!=rule['material']:continue
   for qi,q in enumerate(g['quads']):
    try:rect=a.top_rectangle(q)
    except ValueError as ex:stats[str(ex)]+=1;continue
    stats['eligible_original_top_quads']+=1;fp=[]
    for patch in a.previous.patches(rect):
     bounds=patch['low_uv']+patch['high_uv'];proof=adapter.patch_proof(bounds,q[0][1],owners,cuts);stats['all_actual_patch_candidates']+=1
     if not proof['supported']:
      code='outside_exact_walk_union'if not proof['source_cap_union']['supported']else 'original_foundation_or_gate_cut_overlap';stats[code]+=1;rejected.append({'asset_key':key,'source_face_ref':[gi,qi],'bounds_uv_m':bounds,'source_plane_y_m':q[0][1],'reason':code,'proof':proof});continue
     token='paving_'+str(patch['seed'])+'_'+digest(patch['trim'])[:12];demand[token]={'id':token,'kind':'paving','seed':patch['seed'],'trim':patch['trim']};area+=(bounds[2]-bounds[0])*(bounds[3]-bounds[1]);fp.append({'module_key':token,'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[bounds[0],q[0][1]+.0375,-bounds[1]]},'source_face_ref':[gi,qi],'source_face_sha256':digest(q),'bounds_uv_m':bounds,'source_plane_y_m':q[0][1],'source_semantic_cut_proof':proof,'collision_changed':False})
    if fp:faces.append({'group_index':gi,'quad_index':qi,'quad':q,'quad_sha256':digest(q),'rect_uv_integer_cells':rect,'plane_y_m':q[0][1],'semantic_ownership_scope':'per emitted patch only'});placements+=fp
  if not placements:unsupported.append({'asset_key':key,'status':'UNSUPPORTED','reason':'NO_EXACT_WALK_QUAD_PATCHES'});continue
  assets.append({'asset_key':key,'source_master_path':src['master_path'],'source_master_sha256':src['master_sha256'],'source_render_path':src['render_path'],'source_render_sha256':src['render_sha256'],'source_pitch_m':src['pitch_m'],'rule':rule,'source_polygon_owners':owners,'source_component_cuts':cuts,'faces':faces,'placements':placements,'excluded':dict(stats),'actual_instances':posemap[key],'existing_collision_unchanged':True,'source_collision_baseline':b.collision_baseline(idx,src,posemap[key]),'status':'PARTIAL_EXACT_ORIGINAL_WALK_AND_CUT_SUPPORT'})
  summaries.append({'asset_key':key,'owners':len(owners),'cuts':len(cuts),'faces':len(faces),'placements':len(placements),'supported_area_m2':area,'excluded':dict(stats)})
  print(json.dumps({'source_plan_asset':key,**summaries[-1]}),flush=True)
 plan={'schema':'riverstone.native_access_detail.plan.v1','revision':'r05_'+revision,'source_city_index_sha256':sha(b.IP),'assets':assets,'module_demand':list(demand.values()),'maximum_additional_visual_offset_from_source_m':.0375,'runtime_activation':False,'whole_city_upgrade_complete':False,'source_collision_note':'Original native mesh support unchanged. Visual detail only; no new floor/collider/walking claim.','provenance':{'author':b.ref(Path(__file__)),'generic_cap_cut_adapter':b.ref(Path(adapter.__file__)),'exact_union_oracle':b.ref(Path(e.__file__)),'source_policy_audit':b.ref(AUDIT),'source_geometry_modified':False}}
 known={};caches=CACHE+([H/'first_e7_e1/modules/catalog.json']if revision!='first_e7_e1'else [])
 for cp in caches:
  for row in read(cp)['modules']:
   if row['id']in known:assert known[row['id']]==row
   known[row['id']]=row
 missing=[d for d in demand.values()if d['id']not in known];assert len(missing)<=16,'bounded small crop module budget';rows=[];new_bytes=0;safe=read(b.U/'surface_modules/inputs/safe_offset_rules.v1.json')
 frozen={str(p.relative_to(R)):sha(p)for p in [b.IP,AUDIT,*caches,Path(__file__),Path(adapter.__file__),Path(e.__file__),Path(a.polygons.__file__),Path(a.edge.__file__),Path(a.common.__file__),Path(b.core.__file__),a.HERE/'author_r03.py']};frozen.update(pdeps)
 for asset in assets:
  for k in ['master','render']:frozen[asset['source_'+k+'_path']]=asset['source_'+k+'_sha256']
 for d in missing:
  assert d['trim']!={'width_m':1.0,'height_m':1.0,'offset_m':[0.0,0.0]},'full-source module compilation not authorized';spec=copy.deepcopy(safe);spec['trim']=d['trim'];m,c,r,contract,checks=a.edge.compile_exact_crop(spec,d['kind'],d['seed'],boundary_quantum_m=P);mp=dest/'modules'/(d['id']+'.master.json');rp=dest/'modules'/(d['id']+'.render.json');mb=a.common.payload(m);rb=a.common.payload(r);new_bytes+=len(mb)+len(rb);assert new_bytes<=8*1024*1024 and output_bytes()+len(mb)+len(rb)<LIMIT-2*1024*1024;a.common.write_exact(mp,mb);a.common.write_exact(rp,rb);known[d['id']]={**d,'master_path':str(mp.relative_to(R)),'master_sha256':sha(mp),'render_path':str(rp.relative_to(R)),'render_sha256':sha(rp),'payload_hash':c['payload_hash'],'cells':len(c['cells']),'quads':r['quad_count'],'checks':checks}
 for d in demand.values():
  row=known[d['id']];assert all(row[k]==d[k]for k in ['kind','seed','trim']);rows.append(copy.deepcopy(row))
  for k in ['master','render']:frozen[row[k+'_path']]=row[k+'_sha256'];assert sha(R/row[k+'_path'])==row[k+'_sha256']
 save(dest/'source_plan.json',plan);save(dest/'source_application_audit.json',{'assets':summaries,'rejected_patches':rejected,'unsupported':unsupported,'whole_assets_complete':False});save(dest/'modules/catalog.json',{'schema':read(CACHE[0])['schema'],'revision':'r05_'+revision,'source_plan_sha256':sha(dest/'source_plan.json'),'modules':rows,'source_dependencies':frozen,'runtime_activation':False,'original_collision_unchanged':True});assert frozen=={p:sha(R/p)for p in frozen}
 report={'all_pass':True,'assets':summaries,'unsupported':unsupported,'module_demand':len(rows),'modules_exactly_reused':len(rows)-len(missing),'new_modules_compiled':len(missing),'new_geometry_bytes':new_bytes,'source_dependencies':frozen,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'production_binding_changed':False,'source_geometry_changed':False,'new_colliders':0};save(dest/'build_report.json',report);print(json.dumps({k:v for k,v in report.items()if k!='source_dependencies'}),flush=True)
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(120,)*2);ap=argparse.ArgumentParser();ap.add_argument('--revision',required=True,choices=list(BATCHES));build(ap.parse_args().revision)
