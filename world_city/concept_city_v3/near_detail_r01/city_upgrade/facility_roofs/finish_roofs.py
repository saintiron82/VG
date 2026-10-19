"""Generic roof finishing, exact-cut retention and layered-compiler input adapter.
No whole asset compilation. Original author remains the shared plane/row grammar.
"""
from __future__ import annotations
import argparse, collections, copy, gzip, itertools, json, math, resource, sys, time
from pathlib import Path
import author_facility_roofs as a
import layered_compile as layers
RULES=a.HERE/'inputs/finish_rules.v2.json'
OUT=a.HERE/'finished'

def disk():return sum(p.stat().st_size for p in a.HERE.rglob('*') if p.is_file())
def limited():
 r=a.read(RULES);resource.setrlimit(resource.RLIMIT_AS,(r['budgets']['memory_limit_bytes'],)*2);return r

def provenance(d,p,role):
 return {'asset_key':d['asset_key'],'source_master_sha256':d['source_master_sha256'],'source_component':p['component'],'source_operations':p.get('source_operations',[p.get('operation',{}).get('id')]),'role':role}

def ridge_component(d,r,j,rules):
 op=r['operation'];lo,hi=op['shape']['min'],op['shape']['max'];width=min(hi[0]-lo[0],hi[2]-lo[2]);length=max(hi[0]-lo[0],hi[2]-lo[2]);height=hi[1]-lo[1];cfg=rules['ridge']
 if height<=cfg['cap_depth_m'] or width<=.1:raise ValueError('ridge_envelope_too_thin')
 t=a.core.transform({'translation':[(hi[0]+lo[0])/2,0,(hi[2]+lo[2])/2]})
 if hi[0]-lo[0]>hi[2]-lo[2]:t['basis']=[[0,0,1],[0,1,0],[-1,0,0]]
 t=a.core.compose(a.core.transform(op.get('transform')),t)
 x0,x1=-width/2,width/2;z0,z1=-length/2,length/2;top=hi[1];bed=top-cfg['cap_depth_m'];mat=op['material'];cid='finished_ridge_%03d'%j
 ops=[a.shared.box(cid+'_continuous_bed',[x0,lo[1],z0],[x1,bed+cfg['bed_overlap_m'],z1],mat)]
 n=math.ceil(length/cfg['cap_run_m']);step=length/n
 for k in range(n):
  start=z0+k*step;end=z0+(k+1)*step;za=start+(cfg['joint_m']/2 if k else 0);zb=end-(cfg['joint_m']/2 if k<n-1 else 0)
  poly=[[x0,bed],[x1,bed],[x1,top-cfg['shoulder_drop_m']],[width/4,top-.02],[0,top],[-width/4,top-.02],[x0,top-cfg['shoulder_drop_m']]]
  ops.append(a.shared.prism(cid+'_cap_%04d'%k,poly,za,zb,mat))
 for q in ops:q['transform']=copy.deepcopy(t);q['metadata']={'source_operation':op['id'],'detail_role':'continuous_ridge_bed' if 'continuous_bed' in q['id'] else 'segmented_ridge_cap'}
 c=a.comp(cid,ops);c['metadata']={'provenance':provenance(d,r,'segmented_ridge_caps'),'original_envelope':copy.deepcopy(op['shape']),'joint_is_recessed_sealed_bed':True}
 return c

def add_eaves(master,d,p,rules):
 cfg=rules['eaves'];pid=p['id'];x0,x1=p['x_min'],p['x_max'];z0,z1=p['z_min'],p['z_max'];s=p['slope'];h=lambda x:s*x+p['intercept'];th=p['vertical_skin_thickness_m'];lower=x0 if s>=0 else x1;sign=1 if s>=0 else -1
 if min(x1-x0,z1-z0)<=2*cfg['fascia_depth_m']:raise ValueError('edge_envelope_too_small')
 # Recess continuous backing so the segments have actual visible side joints.
 under=next(c for c in master['components'] if c['id']==pid+'_underlay')['operations'][0]
 aa=x0+cfg['backing_inset_m'] if sign>0 else x0;bb=x1-cfg['backing_inset_m'] if sign<0 else x1
 under['shape']['polygon']=[[aa,h(aa)-th],[bb,h(bb)-th],[bb,h(bb)-.1],[aa,h(aa)-.1]]
 under['shape']['z_min']=z0+cfg['backing_inset_m'];under['shape']['z_max']=z1-cfg['backing_inset_m']
 ops=[];a0,a1=sorted([lower,lower+sign*cfg['fascia_depth_m']]);n=math.ceil((z1-z0)/cfg['segment_run_m']);step=(z1-z0)/n
 for k in range(n):
  za=z0+k*step+(cfg['joint_m']/2 if k else 0);zb=z0+(k+1)*step-(cfg['joint_m']/2 if k<n-1 else 0)
  ops.append(a.shared.prism(pid+'_eave_segment_%04d'%k,[[a0,h(a0)-th],[a1,h(a1)-th],[a1,h(a1)-cfg['top_recess_m']],[a0,h(a0)-cfg['top_recess_m']]],za,zb,p['material']))
 n=math.ceil((x1-x0)/cfg['segment_run_m']);step=(x1-x0)/n
 for side in (0,1):
  za,zb=(z0,z0+cfg['fascia_depth_m']) if side==0 else (z1-cfg['fascia_depth_m'],z1)
  for k in range(n):
   aa=x0+k*step+(cfg['joint_m']/2 if k else 0);bb=x0+(k+1)*step-(cfg['joint_m']/2 if k<n-1 else 0)
   ops.append(a.shared.prism(pid+'_verge_%d_%04d'%(side,k),[[aa,h(aa)-th],[bb,h(bb)-th],[bb,h(bb)-cfg['top_recess_m']],[aa,h(aa)-cfg['top_recess_m']]],za,zb,p['material']))
 cid=pid+'_finished_edges';c=a.comp(cid,ops);c['metadata']={'provenance':provenance(d,p,'segmented_eave_and_verge'),'actual_fascia_depth_m':cfg['fascia_depth_m'],'source_vertical_thickness_m':th}
 master['components'].append(c)
 for ins in p['component_instances']:a.add_instance(master,cid+'_'+ins['id'],cid,a.core.compose(ins['transform'],p['operation_transform']))

def finish(d,source,rules,covering='roof_tile'):
 master=a.make_near(d,source,a.read(a.RULES),covering)
 master['components']=[c for c in master['components'] if not c['id'].startswith('retained_ridge_')]
 master['instances']=[i for i in master['instances'] if not i['component'].startswith('retained_ridge_')]
 for p in d['planes']:
  if p['component_instances']:add_eaves(master,d,p,rules)
 for j,r in enumerate(d['retained_ridge_boxes']):
  c=ridge_component(d,r,j,rules);master['components'].append(c)
  for ins in r['component_instances']:a.add_instance(master,c['id']+'_'+ins['id'],c['id'],ins['transform'])
 # Derive source identity for every reused row/edge/ridge instance.
 instance_source={};component_source={}
 for p in d['planes']:
  for i in master['instances']:
   if i['component'].startswith(p['id']+'_'):
    ins=next(v for v in sorted(p['component_instances'],key=lambda v:-len(v['id'])) if i['id'].endswith('_'+v['id']))
    instance_source[i['id']]={'component':p['component'],'instance':ins['id'],'part':p['part'],'material':p['material'],'transform':ins['transform']}
    component_source[i['component']]=provenance(d,p,'sloped_roof_and_finished_edges')
 for j,r in enumerate(d['retained_ridge_boxes']):
  for i in master['instances']:
   if i['component']=='finished_ridge_%03d'%j:
    ins=next(v for v in sorted(r['component_instances'],key=lambda v:-len(v['id'])) if i['id'].endswith('_'+v['id']))
    instance_source[i['id']]={'component':r['component'],'instance':ins['id'],'part':r['operation']['part'],'material':r['operation']['material'],'transform':ins['transform']}
    component_source[i['component']]=provenance(d,r,'segmented_ridge_caps')
 for c in master['components']:c.setdefault('metadata',{})['provenance']=component_source[c['id']]
 for i in master['instances']:i['metadata']={'source_identity':instance_source[i['id']]}
 for cid,cuts in d.get('preserved_terminal_component_cuts',{}).items():
  original_instances={s['instance']:s for s in instance_source.values() if s['component']==cid}
  for iid,src in original_instances.items():
   for cut in cuts:
    ids=[ident for ident,v in instance_source.items() if v['component']==cid and v['instance']==iid and a.core.selector_matches(cut.get('selector',{}),{'part':v['part'],'material':v['material']})]
    if not ids:continue
    q=copy.deepcopy(cut);q.pop('part',None);q.pop('action',None);q['id']='retained_cut_%05d'%len(master['assembly_cuts']);q['transform']=a.core.compose(src['transform'],a.core.transform(cut.get('transform')));q['selector']={'instance':ids};q['metadata']={'source_component':cid,'source_instance':iid,'source_cut_id':cut['id'],'source_cut':copy.deepcopy(cut),'exact_terminal_order':True};master['assembly_cuts'].append(q)
 master['metadata'].update({'authoring':'facility_roof_finish_v2','ridge_finish':'segmented_actual_caps_with_recessed_sealed_joints','eaves_finish':'segmented_full_source_thickness_fascia_and_verges','cuts':'exact_terminal_component_cuts_retained_as_identity_scoped_assembly_cuts','runtime_activation':False})
 a.core.validate_master(master,.05);return master

def flatten(master):
 """One identity instance per expanded source instance; transforms remain rigid ops."""
 out={k:copy.deepcopy(v) for k,v in master.items() if k not in ('components','instances','assembly_cuts')};out.update(components=[],instances=[],assembly_cuts=[])
 components={c['id']:c for c in master['components']};transforms=a.instance_transforms(master);mapping={}
 for number,ins in enumerate(master['instances']):
  cid='flat_%05d'%number;iid=cid;mapping[ins['id']]=iid;c=copy.deepcopy(components[ins['component']]);c['id']=cid;c.setdefault('metadata',{})['shared_row_source']={'component':ins['component'],'instance':ins['id'],'resolved_transform':transforms[ins['id']],'instance_metadata':ins.get('metadata',{})}
  for op in c['operations']:
   op['transform']=a.core.compose(transforms[ins['id']],a.core.transform(op.get('transform')))
   op.setdefault('metadata',{})['source_shared_operation']=op['id']
  out['components'].append(c);out['instances'].append({'id':iid,'component':cid})
 for cut in master['assembly_cuts']:
  q=copy.deepcopy(cut)
  if 'instance' in q.get('selector',{}):
   ids=q['selector']['instance'];q['selector']['instance']=[mapping[v] for v in ids] if isinstance(ids,list) else mapping[ids]
  out['assembly_cuts'].append(q)
 out['metadata']['flattened_shared_row_instances']=True;out['metadata']['flattening_contract']='Same ordered operations and resolved proper-rigid transforms; one instance per component; original component/instance/operation provenance retained.'
 a.core.validate_master(out,.05);return out

def gzwrite(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('wb') as raw:
  with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as stream:stream.write((json.dumps(data,separators=(',',':'),allow_nan=False)+'\n').encode())

def structure(master,d,require_layered=True):
 checks=collections.Counter();plans={p['id']:p for p in d['planes']};ridges={(r['component'],r['operation']['id']):r for r in d['retained_ridge_boxes']};fail=[]
 from validate_facility_roofs import shape_vertices
 for c in master['components']:
  orig=c['metadata']['shared_row_source'];prov=c['metadata']['provenance'];identity=orig.get('instance_metadata',{}).get('source_identity',{});role=prov['role']
  for op in c['operations']:
   t=a.core.transform(op.get('transform'))
   if role=='segmented_ridge_caps':
    r=ridges[(prov['source_component'],prov['source_operations'][0])];src=r['operation'];base=a.core.compose(identity['transform'],a.core.transform(src.get('transform')));lo,hi=src['shape']['min'],src['shape']['max']
    for v in shape_vertices(op):
     q=a.core.inverse(base,a.core.apply(t,v))
     if any(q[j]<lo[j]-1e-7 or q[j]>hi[j]+1e-7 for j in range(3)):fail.append(['ridge_vertex_outside_source',c['id'],op['id']])
    checks['ridge_prisms_within_original_box']+=1
   else:
    pid='_'.join(orig['component'].split('_')[:2]);p=plans[pid];base=a.core.compose(identity['transform'],p['operation_transform'])
    for v in shape_vertices(op):
     x,y,z=a.core.inverse(base,a.core.apply(t,v));h=p['slope']*x+p['intercept'];e=1e-7
     if not(p['x_min']-e<=x<=p['x_max']+e and p['z_min']-e<=z<=p['z_max']+e and h-p['vertical_skin_thickness_m']-e<=y<=h+e):fail.append(['plane_vertex_outside_source',c['id'],op['id']])
    checks['roof_prisms_within_original_plane_solid']+=1
  checks['single_instance_components']+=1
 compiler_pending=[]
 try:
  layers.SpatialSource(master,.05);checks['existing_layered_spatial_source_accepts']=1
 except a.shared.UnsupportedSurface as exc:
  if require_layered:raise
  compiler_pending.append(str(exc));checks['existing_layered_spatial_source_pending']=1
 if a.shared.sha(a.ROOT/d['source_master_path'])!=d['source_master_sha256'] or a.shared.sha(a.ROOT/d['source_render_path'])!=d['source_render_sha256']:fail.append(['original_changed'])
 return {'checks':dict(checks),'failures':fail,'compiler_pending':compiler_pending,'status':'PASS_STRUCTURE_ONLY' if not fail else 'FAIL'}

def build():
 rules=limited();mapping=a.read(a.MAP);old=a.read(a.HERE/'catalog.json');support=[];descriptors={}
 for record in old['assets']:
  key=record['asset_key'];item=mapping['assets'][key];source=a.read(a.ROOT/item['master_path']);d=a.describe(key,item,source,allow_terminal_component_cuts=True);descriptors[key]=d
  before=a.read(a.ROOT/record['descriptor']['path']);support.append({'asset_key':key,'supported_planes':len(d['planes']),'previous_supported_planes':len(before['planes']),'pending':d['pending'],'retained_terminal_cut_components':list(d['preserved_terminal_component_cuts']),'safe_material_groups':d['suppression']['safe_material_groups_when_full_matching_near_resource_ready'],'replacement_allowed':False})
 catalog=[]
 for key in rules['targets']:
  d=descriptors[key];source=a.read(a.ROOT/d['source_master_path'])
  if d['pending'] or d['suppression']['unsafe_material_groups']:raise ValueError('target_not_fully_supported:'+key)
  near=finish(d,source,rules);flat=flatten(near);check=structure(flat,d)
  if check['failures']:raise ValueError(check['failures'][:10])
  mp=OUT/(key+'.finished.master.json.gz');gzwrite(mp,flat);dp=OUT/(key+'.finished.planes.json');a.write(dp,d)
  record={'asset_key':key,'emitted_master_path':a.rel(mp),'emitted_master_sha256':a.shared.sha(mp),'source_master_path':d['source_master_path'],'source_sha256':d['source_master_sha256'],'source_render_path':d['source_render_path'],'source_render_sha256':d['source_render_sha256'],'descriptor':a.ref(dp),'covering':'roof_tile','replacement_allowed':False,'source_authoring_complete_for_all_roof_groups':True,'whole_group_material_ids':d['suppression']['safe_material_groups_when_full_matching_near_resource_ready'],'structure_validation':check,'components':len(flat['components']),'operations':sum(len(c['operations']) for c in flat['components']),'compressed_bytes':mp.stat().st_size,'uncompiled':True}
  catalog.append(record);print(json.dumps({'asset':key,'operations':record['operations'],'gzip_bytes':record['compressed_bytes'],'structure':check['status']}),flush=True)
 descriptor_bundle=OUT/'shape_support_descriptors.v2.json.gz';gzwrite(descriptor_bundle,{'schema':'riverstone.facility_roof.support_descriptors.v2','assets':descriptors,'runtime_activation':False})
 a.write(OUT/'shape_support_catalog.json',{'schema':'riverstone.facility_roof.shape_support.v2','assets':support,'descriptors':a.ref(descriptor_bundle),'old_pending_operations':sum(len(a.read(a.ROOT/r['descriptor']['path'])['pending']) for r in old['assets']),'new_pending_operations':sum(len(r['pending']) for r in support),'runtime_activation':False,'source_only':True,'geometry_status':'Exact cut-preserving descriptors; only the two selected targets have finished full source masters. Hip join-cap finish remains pending.'})
 a.write(OUT/'layered_compile_catalog.json',{'schema':'riverstone.facility_roof.layered_input_catalog.v2','assets':catalog,'rules':a.ref(RULES),'author':a.ref(Path(__file__)),'common_plane_author':a.ref(Path(a.__file__)),'layered_compile':a.ref(Path(layers.__file__)),'compile_command_template':'python house_rules/layered_compile.py ASSET_KEY --catalog facility_roofs/finished/layered_compile_catalog.json --output-dir <parent-approved-output>','full_compile_performed':False,'runtime_activation':False})
 old_contracts={r['asset_key']:r for r in a.read(a.HERE/'replacement_contracts.json')['assets']};contracts=[]
 for rec in catalog:
  contract=copy.deepcopy(old_contracts[rec['asset_key']]);contract['finished_source_master']={k:rec[k] for k in ['emitted_master_path','emitted_master_sha256']};contract['source_authoring_complete_for_all_roof_groups']=True;contract['current_blocker']='Full matching roof chunks, atomic runtime swap, whole-roof intersections and in-engine visual acceptance are not yet verified.'
  for g in contract['render_groups']:
   for ref in g['represented_roof_operations']:
    if ref['role'].startswith('unchanged_source_ridge_box'):ref['role']='segmented_actual_ridge_caps_and_continuous_recessed_bed_within_original_box'
  contracts.append(contract)
 a.write(OUT/'replacement_contracts.v2.json',{'schema':'riverstone.facility_roof.finished_replacement_contracts.v2','assets':contracts,'runtime_active':False,'replacement_allowed':False,'partial_roi_never_authorizes_whole_group_suppression':True,'untargeted_assets':'Use original replacement_contracts.json, plus v2 shape-support descriptors for authoring only.'})
 if disk()>rules['budgets']['total_bytes_limit']:raise ValueError('additional_disk_budget_exceeded')
 print(json.dumps({'old_pending':sum(len(a.read(a.ROOT/r['descriptor']['path'])['pending']) for r in old['assets']),'new_pending':sum(len(r['pending']) for r in support),'disk_bytes':disk(),'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}))

def original_roof_only(d,source):
 """Exact original roof operations for small-ROI containment comparisons."""
 materials=set(d['suppression']['safe_material_groups_when_full_matching_near_resource_ready'])
 m=a.new_master(source['id']+'__original_roof_reference',source['materials'])
 for c in source['components']:
  if not any(o.get('material') in materials and o['action']=='paint' for o in c['operations']):continue
  q=copy.deepcopy(c);q['operations']=[o for o in q['operations'] if o['action']=='cut' or o.get('material') in materials];m['components'].append(q)
 ids={c['id'] for c in m['components']};t=a.instance_transforms(source)
 for i in source['instances']:
  if i['component'] in ids:m['instances'].append({'id':i['id'],'component':i['component'],'transform':t[i['id']]})
 return flatten(m)

def bounds(points,pad=.025):return ([min(p[j] for p in points)-pad for j in range(3)],[max(p[j] for p in points)+pad for j in range(3)])

def small_rois():
 rules=limited();cat=a.read(OUT/'layered_compile_catalog.json');reports=[]
 for record in cat['assets']:
  d=a.read(a.ROOT/record['descriptor']['path']);source=a.read(a.ROOT/d['source_master_path']);master=layers.load_master(a.ROOT/record['emitted_master_path']);near=layers.SpatialSource(master,.05);old=layers.SpatialSource(original_roof_only(d,source),.05);p=d['planes'][0];t=a.core.compose(p['component_instances'][0]['transform'],p['operation_transform']);h=lambda x:p['slope']*x+p['intercept'];aa,bb=(p['x_min'],min(p['x_min']+1,p['x_max'])) if p['slope']>=0 else (max(p['x_min'],p['x_max']-1),p['x_max']);zz=p['z_min'];points=[a.core.apply(t,[x,y,z]) for x in [aa,bb] for y in [h(x)-p['vertical_skin_thickness_m'],h(x)] for z in [zz,min(zz+1,p['z_max'])]]
  cases=[('eave_verge_tile_overlap',bounds(points))]
  r=d['retained_ridge_boxes'][0];op=r['operation'];lo,hi=op['shape']['min'],op['shape']['max'];rhi=hi.copy();axis=2 if hi[2]-lo[2]>=hi[0]-lo[0] else 0;rhi[axis]=min(hi[axis],lo[axis]+1);t=a.core.compose(r['component_instances'][0]['transform'],a.core.transform(op.get('transform')));cases.append(('segmented_ridge_caps',bounds([a.core.apply(t,list(v)) for v in itertools.product(*zip(lo,rhi))])))
  for name,(low,high) in cases:
   start=time.perf_counter();cropped=near.crop(low,high);reference=old.crop(low,high);opts={'max_candidate_cells':rules['budgets']['roi_candidate_cells'],'max_output_cells':rules['budgets']['roi_output_cells']};compiled=a.core.compile_master(cropped,{'pitch':.05},**opts);original=a.core.compile_master(reference,{'pitch':.05},**opts);cells={tuple(c[:3]) for c in compiled['cells']};oldcells={tuple(c[:3]) for c in original['cells']};outside=cells-oldcells
   # A center sample inside an original source solid must remain inside that solid.
   if outside:raise ValueError(['roi_cells_outside_original_solid',record['asset_key'],name,len(outside)])
   render=a.make_render_data(compiled);base=OUT/'roi'/(record['asset_key']+'.'+name);a.write(base.with_suffix(base.suffix+'.master.json'),cropped);a.write(base.with_suffix(base.suffix+'.render.json'),render)
   report={'asset_key':record['asset_key'],'case':name,'status':'PASS_SMALL_ROI' if compiled['valid'] else 'FAIL','bounds_m':[low,high],'near_cells':len(cells),'original_cells':len(oldcells),'outside_original_cells':len(outside),'quads':render['quad_count'],'near_candidate_cells':compiled['candidate_cells'],'reference_candidate_cells':original['candidate_cells'],'actual_3d_geometry':True,'source_master_preserved':a.shared.sha(a.ROOT/d['source_master_path'])==d['source_master_sha256'],'whole_asset_compile':False,'runtime_activation':False,'visual_approval':False,'seconds':time.perf_counter()-start};reports.append(report);print(json.dumps(report),flush=True)
 a.write(OUT/'roi_validation.json',{'schema':'riverstone.facility_roof.finish_roi_validation.v2','reports':reports,'status':'PASS_SMALL_ROIS' if all(r['status']=='PASS_SMALL_ROI' for r in reports) else 'FAIL','max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'artifact_bytes':disk(),'full_compile_performed':False})

def hip_roi():
 rules=limited();mapping=a.read(a.MAP);support=a.read(OUT/'shape_support_catalog.json')
 record=min((r for r in support['assets'] if r['retained_terminal_cut_components'] and not r['pending']),key=lambda r:(r['supported_planes'],r['asset_key']))
 key=record['asset_key'];item=mapping['assets'][key];source=a.read(a.ROOT/item['master_path']);d=a.describe(key,item,source,allow_terminal_component_cuts=True);m=finish(d,source,rules);flat=flatten(m);check=structure(flat,d)
 if check['failures']:raise ValueError(check['failures'][:8])
 p=next(p for p in d['planes'] if p['component'] in d['preserved_terminal_component_cuts']);cut=d['preserved_terminal_component_cuts'][p['component']][0];ins=p['component_instances'][0];base=a.core.compose(ins['transform'],p['operation_transform']);ct=a.core.compose(ins['transform'],a.core.transform(cut.get('transform')));shape=a.core.prepare_shape(cut['shape'],.05);x=(p['x_min']+p['x_max'])/2;h=p['slope']*x+p['intercept'];last=None;center=None
 for k in range(101):
  z=p['z_min']+(p['z_max']-p['z_min'])*k/100;point=a.core.apply(base,[x,h-.2,z]);inside=a.core.contains(shape,a.core.inverse(ct,point),epsilon=1e-9)
  if last is not None and last[1]!=inside:center=(last[0]+z)/2;break
  last=(z,inside)
 if center is None:raise ValueError('hip_roi_cut_transition_not_found')
 points=[a.core.apply(base,[xx,p['slope']*xx+p['intercept']-depth,zz]) for xx in [x-.4,x+.4] for depth in [0,p['vertical_skin_thickness_m']] for zz in [center-.4,center+.4]];low,high=bounds(points)
 near=layers.SpatialSource(flat,.05).crop(low,high);old=layers.SpatialSource(original_roof_only(d,source),.05).crop(low,high);uncut=copy.deepcopy(near);uncut['assembly_cuts']=[];opts={'max_candidate_cells':rules['budgets']['roi_candidate_cells'],'max_output_cells':rules['budgets']['roi_output_cells']}
 result=a.core.compile_master(near,{'pitch':.05},**opts);reference=a.core.compile_master(old,{'pitch':.05},**opts);untrimmed=a.core.compile_master(uncut,{'pitch':.05},**opts);cells={tuple(c[:3]) for c in result['cells']};original={tuple(c[:3]) for c in reference['cells']};before={tuple(c[:3]) for c in untrimmed['cells']};outside=cells-original;removed=before-cells
 if outside or not removed or not cells:raise ValueError(['hip_roi_cut_semantics_failed',len(outside),len(removed),len(cells)])
 path=OUT/'roi'/(key+'.exact_hip_cut');a.write(path.with_suffix(path.suffix+'.master.json'),near);a.write(path.with_suffix(path.suffix+'.render.json'),a.make_render_data(result));report={'schema':'riverstone.facility_roof.hip_cut_roi.v2','asset_key':key,'status':'PASS_SMALL_ROI_EXACT_CUT','bounds_m':[low,high],'source_cut':cut,'source_cut_transform_world':ct,'retained_assembly_cuts':len(near['assembly_cuts']),'cells':len(cells),'cells_removed_by_exact_original_cut':len(removed),'outside_original_roof_cells':len(outside),'candidate_cells':result['candidate_cells'],'reference_candidate_cells':reference['candidate_cells'],'structure':check,'source_master_sha256':a.shared.sha(a.ROOT/item['master_path']),'source_unchanged':a.shared.sha(a.ROOT/item['master_path'])==item['master_sha256'],'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'full_asset_compile':False,'runtime_activation':False,'fine_hip_join_caps':'pending_visual_finish','author':a.ref(Path(__file__))};a.write(OUT/'hip_cut_roi_validation.json',report);print(json.dumps({k:report[k] for k in ['asset_key','status','cells','cells_removed_by_exact_original_cut','outside_original_roof_cells','candidate_cells','max_rss_bytes']}))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['build','roi','hip-roi']);args=parser.parse_args();{'build':build,'roi':small_rois,'hip-roi':hip_roi}[args.command]()
