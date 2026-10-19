"""Two original path-only data policies, bounded reusable source-cap/cut adapter."""
from pathlib import Path
import argparse,collections,copy,json,resource,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import source_cap_cut_adapter as adapter
e=adapter.e;b=e.b;a=e.a;R=e.R;P=e.P;read=e.read;save=e.save;sha=e.sha;digest=e.digest
KEYS=['registered_precinct_cemetery_caps_r03','registered_precinct_r06_common_r02_retained_base'];PLAN=H/'source_plan.json';CAT=H/'modules/catalog.json';CACHE=[H.parent/'combined/module_catalog_r03_plus_r04.json',H.parent/'extrusion_support_r01/modules/catalog.json']

def policy(key,master):
 if key==KEYS[0]:site='CLERGY_CEMETERY';names=['burial_aisle:0','gate_walk:0',*[f'burial_row_access_{i}:0'for i in range(9)],'connection:0:0']
 elif key==KEYS[1]:site='PUBLIC_TERRACE_PARK';names=['main_walk:0','cross_walk:0','gate_walk:0','gate_walk:1']
 else:raise ValueError('unapproved_selection')
 assert master['metadata']['source_site_ids']==[site]
 return {'kind':'paving','material':'stone_light','part':'solid','source_components':['landscape'],'operation_ids':[site+':'+n for n in names],'semantic_role':'Explicit original aisle/access/walk operations only, excluding grass owned floor and stone boundary walls','source_site_ids':master['metadata']['source_site_ids'],'semantic_site_metadata_sha256':digest(master['metadata']['source_site_ids']),'geometry_policy':'actual retained source quad intersect exact original selected paint cap union minus every relevant component cut; source operations never synthesized'}

def make_plan():
 idx=read(b.IP);posemap,pdeps=b.poses(idx,KEYS);assets=[];dem={};rejected=[];summaries=[]
 for key in KEYS:
  src=idx['common_assets'][key];assert sha(R/src['master_path'])==src['master_sha256'] and sha(R/src['render_path'])==src['render_sha256'];m=read(R/src['master_path']);r=read(R/src['render_path']);rule=policy(key,m);owners,cuts=adapter.source_contract(m,rule,src['pitch_m']);faces=[];placements=[];stats=collections.Counter();area=0
  for gi,g in enumerate(r['groups']):
   if g['material']!=rule['material']:continue
   for qi,q in enumerate(g['quads']):
    try:rect=a.top_rectangle(q)
    except ValueError as ex:stats[str(ex)]+=1;continue
    stats['eligible_original_top_quads']+=1;fp=[]
    for patch in a.previous.patches(rect):
     bounds=patch['low_uv']+patch['high_uv'];proof=adapter.patch_proof(bounds,q[0][1],owners,cuts);stats['all_actual_patch_candidates']+=1
     if not proof['supported']:
      code='outside_exact_semantic_path_union' if not proof['source_cap_union']['supported'] else 'original_gate_cut_overlap';stats[code]+=1;rejected.append({'asset_key':key,'source_face_ref':[gi,qi],'bounds_uv_m':bounds,'source_plane_y_m':q[0][1],'reason':code,'proof':proof});continue
     token='paving_'+str(patch['seed'])+'_'+digest(patch['trim'])[:12];dem[token]={'id':token,'kind':'paving','seed':patch['seed'],'trim':patch['trim']};area+=(bounds[2]-bounds[0])*(bounds[3]-bounds[1])
     fp.append({'module_key':token,'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[bounds[0],q[0][1]+.0375,-bounds[1]]},'source_face_ref':[gi,qi],'source_face_sha256':digest(q),'bounds_uv_m':bounds,'source_plane_y_m':q[0][1],'source_semantic_cut_proof':proof,'collision_changed':False})
    if fp:faces.append({'group_index':gi,'quad_index':qi,'quad':q,'quad_sha256':digest(q),'rect_uv_integer_cells':rect,'plane_y_m':q[0][1],'semantic_ownership_scope':'per emitted patch only'});placements+=fp
  assert placements
  assets.append({'asset_key':key,'source_master_path':src['master_path'],'source_master_sha256':src['master_sha256'],'source_render_path':src['render_path'],'source_render_sha256':src['render_sha256'],'source_pitch_m':src['pitch_m'],'rule':rule,'source_polygon_owners':owners,'source_component_cuts':cuts,'faces':faces,'placements':placements,'excluded':dict(stats),'actual_instances':posemap[key],'existing_collision_unchanged':True,'source_collision_baseline':b.collision_baseline(idx,src,posemap[key]),'status':'PARTIAL_EXACT_ORIGINAL_PATH_AND_CUT_SUPPORT'})
  summaries.append({'asset_key':key,'owners':len(owners),'cuts':len(cuts),'faces':len(faces),'placements':len(placements),'supported_area_m2':area,'excluded':dict(stats)})
 assert sum(len(a['placements'])for a in assets)<=1800
 plan={'schema':'riverstone.native_access_detail.plan.v1','revision':'r04_extrusion_support_r02','source_city_index_sha256':sha(b.IP),'assets':assets,'module_demand':list(dem.values()),'maximum_additional_visual_offset_from_source_m':.0375,'runtime_activation':False,'whole_city_upgrade_complete':False,'source_collision_note':'Original native source mesh collider retained. No new floor/collider/walking pass.','provenance':{'author':b.ref(Path(__file__)),'generic_cap_cut_adapter':b.ref(Path(adapter.__file__)),'exact_union_oracle':b.ref(Path(e.__file__)),'common_polygon_union':b.ref(Path(a.polygons.__file__)),'r03_quad_and_integer_support_guard':b.ref(a.HERE/'author_r03.py'),'cuts':'closed cap-to-additional-offset height interval, exact projected convex cut polygon overlap must be zero','source_geometry_modified':False}}
 return plan,{'assets':summaries,'rejected_patches':rejected,'whole_assets_complete':False},pdeps

def build(audit_only=False):
 start=time.perf_counter();plan,audit,pdeps=make_plan();known={}
 for cp in CACHE:
  for row in read(cp)['modules']:
   if row['id'] in known:assert known[row['id']]==row
   known[row['id']]=row
 missing=[d for d in plan['module_demand'] if d['id']not in known];info={'assets':audit['assets'],'module_demand':len(plan['module_demand']),'missing_cached_modules':len(missing)}
 if audit_only:print(json.dumps(info));return
 assert len(missing)<=2,'At most two additional <=1m quarter trim keys in this bounded revision'
 rows=[];frozen={str(p.relative_to(R)):sha(p)for p in [b.IP,*CACHE,Path(adapter.__file__),Path(e.__file__),Path(a.polygons.__file__),Path(a.edge.__file__),Path(a.common.__file__),Path(b.core.__file__),a.HERE/'author_r03.py']};frozen.update(pdeps)
 for asset in plan['assets']:
  for k in ['master','render']:frozen[asset['source_'+k+'_path']]=asset['source_'+k+'_sha256']
 new_bytes=0;safe=read(b.U/'surface_modules/inputs/safe_offset_rules.v1.json')
 for d in missing:
  assert d['trim']!={'width_m':1.0,'height_m':1.0,'offset_m':[0.0,0.0]};spec=copy.deepcopy(safe);spec['trim']=d['trim'];master,c,render,contract,checks=a.edge.compile_exact_crop(spec,d['kind'],d['seed'],boundary_quantum_m=P)
  mp=CAT.parent/(d['id']+'.master.json');rp=CAT.parent/(d['id']+'.render.json');mb=a.common.payload(master);rb=a.common.payload(render);new_bytes+=len(mb)+len(rb);assert b.output_bytes()+len(mb)+len(rb)<b.LIMIT-1_000_000;a.common.write_exact(mp,mb);a.common.write_exact(rp,rb)
  known[d['id']]={**d,'master_path':str(mp.relative_to(R)),'master_sha256':sha(mp),'render_path':str(rp.relative_to(R)),'render_sha256':sha(rp),'payload_hash':c['payload_hash'],'cells':len(c['cells']),'quads':render['quad_count'],'checks':checks}
 for d in plan['module_demand']:
  row=known[d['id']];assert all(row[k]==d[k] for k in ['kind','seed','trim']);rows.append(copy.deepcopy(row))
  for k in ['master','render']:frozen[row[k+'_path']]=row[k+'_sha256'];assert sha(R/row[k+'_path'])==row[k+'_sha256']
 save(PLAN,plan);save(H/'source_application_audit.json',audit);save(CAT,{'schema':read(CACHE[0])['schema'],'revision':'r04_extrusion_support_r02','source_plan_sha256':sha(PLAN),'modules':rows,'source_dependencies':frozen,'runtime_activation':False,'original_collision_unchanged':True});assert frozen=={p:sha(R/p)for p in frozen};assert b.output_bytes()<b.LIMIT
 result={'all_pass':True,**info,'modules_exactly_reused':len(rows)-len(missing),'new_modules_compiled':len(missing),'new_geometry_bytes':new_bytes,'source_plan':b.ref(PLAN),'module_catalog':b.ref(CAT),'source_application_audit':b.ref(H/'source_application_audit.json'),'source_dependencies':frozen,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'production_binding_changed':False,'source_geometry_changed':False,'new_colliders':0};save(H/'build_report.json',result);assert b.output_bytes()<b.LIMIT;print(json.dumps({k:v for k,v in result.items()if k!='source_dependencies'}))
if __name__=='__main__':
 b.limits();ap=argparse.ArgumentParser();ap.add_argument('--audit-only',action='store_true');build(ap.parse_args().audit_only)
