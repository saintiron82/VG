"""One data-driven roof author for every supported native facility; no asset dispatch.
Reuse common-master primitives and roof interpretation from house_rules.adapter.
Only a bounded ROI is compiled. Full roof masters are source data, not a build.
"""
from __future__ import annotations
import argparse, collections, copy, hashlib, itertools, json, math, resource, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE.parent/'house_rules'))
import adapter as shared
from voxel_character.common import core
from voxel_character.common.render_data import make_render_data
RULES=HERE/'inputs/roof_rules.v1.json'
MAP=HERE.parent/'surface_mapping/material_surface_map.v1.json'
def read(p):return json.loads(Path(p).read_bytes())
def rel(p):return str(Path(p).relative_to(ROOT))
def ref(p):return {'path':rel(p),'sha256':shared.sha(p)}
def write(p,x):shared.write(p,x)
def identity():return core.transform()
def trim_floats(x):
 if isinstance(x,float):return round(x,10)
 if isinstance(x,list):return [trim_floats(y) for y in x]
 if isinstance(x,dict):return {k:trim_floats(v) for k,v in x.items()}
 return x
def instance_transforms(m):
 by={i['id']:i for i in m['instances']};done={};visiting=set()
 def get(k):
  if k in done:return done[k]
  if k in visiting:raise ValueError('instance_cycle')
  visiting.add(k);i=by[k];t=core.transform(i.get('transform'))
  if i.get('parent'):t=core.compose(get(i['parent']),t)
  done[k]=t;visiting.remove(k);return t
 for k in by:get(k)
 return done

def transformed_bounds(shape,t):
 lo,hi=core.shape_bounds(core.prepare_shape(shape,.05));points=[core.apply(t,list(p)) for p in itertools.product(*zip(lo,hi))]
 return {'min':[min(p[j] for p in points) for j in range(3)],'max':[max(p[j] for p in points) for j in range(3)]}
def intersect(a,b):return all(a['max'][j]>b['min'][j]+1e-9 and b['max'][j]>a['min'][j]+1e-9 for j in range(3))
def relevant_cuts(m,c,op,transforms):
 affected=[];proofs=[]
 for ins in (i for i in m['instances'] if i['component']==c['id']):
  cell={'instance':ins['id'],'component':c['id'],'part':op['part'],'material':op.get('material'),'feature':op['id']}
  ob=transformed_bounds(op['shape'],core.compose(transforms[ins['id']],core.transform(op.get('transform'))))
  for scope,cut in [('component',q) for q in c['operations'] if q['action']=='cut']+[('assembly',q) for q in m.get('assembly_cuts',[])]:
   if not core.selector_matches(cut.get('selector',{}),cell):
    proofs.append({'cut':cut['id'],'scope':scope,'instance':ins['id'],'exclusion':'selector_excludes_roof_operation'});continue
   t=core.transform(cut.get('transform'))
   if scope=='component':t=core.compose(transforms[ins['id']],t)
   cb=transformed_bounds(cut['shape'],t)
   if intersect(ob,cb):affected.append({'cut':cut['id'],'scope':scope,'instance':ins['id']})
   else:proofs.append({'cut':cut['id'],'scope':scope,'instance':ins['id'],'exclusion':'strictly_disjoint_transformed_aabb','roof_operation_aabb':ob,'cut_aabb':cb})
 return affected,proofs

def describe(key,a,m,allow_terminal_component_cuts=False):
 transforms=instance_transforms(m);pending=[];raw=[];retained=[];handled=set();cutproofs=[];preserved_cuts={};roofmats={mid for mid,s in a['slots'].items() if any(r.startswith('roof_') for r in s['operation_role_counts'])}
 for c in m['components']:
  selected=[o for o in c['operations'] if o.get('action')=='paint' and o.get('material') in roofmats]
  if not selected:continue
  cuts=[o['id'] for o in c['operations'] if o['action']=='cut']
  for op in selected:
   base={'component':c['id'],'operation':op['id'],'material':op['material'],'part':op['part'],'shape_kind':op['shape']['kind']}
   affected,proofs=relevant_cuts(m,c,op,transforms);cutproofs.extend({'component':c['id'],'operation':op['id'],**q} for q in proofs)
   if affected:
    # Only exact terminal component cuts can be retained in the finishing path.
    # A selector requiring old feature/instance identity is deliberately unsupported.
    co=c['operations'];first_cut=next((j for j,q in enumerate(co) if q['action']=='cut'),len(co))
    eligible=(allow_terminal_component_cuts and all(q['scope']=='component' for q in affected)
      and all(q['action']=='cut' for q in co[first_cut:])
      and all(q['shape']['kind'] in ('box','extrusion') and set(q.get('selector',{}))<= {'part','material'} for q in co[first_cut:]))
    if not eligible:
     pending.append({**base,'reason':'trimmed_or_cut_roof_pending','intersecting_cuts':affected});continue
    preserved_cuts[c['id']]=[copy.deepcopy(q) for q in co[first_cut:]]
   if op['shape']['kind']=='box' and 'ridge' in op['id'].lower():
    retained.append({'component':c['id'],'operation':copy.deepcopy(op)});handled.add((c['id'],op['id']));continue
   try:
    if op['shape']['kind']!='extrusion':raise ValueError('shape_not_sloped_extrusion')
    aa,bb,ya,yb,thick=shared.roof_geometry(op)
    if thick<=.125:raise ValueError('insufficient_original_skin_depth')
    if op['shape']['z_max']<=op['shape']['z_min']:raise ValueError('zero_extrusion_width')
    t=core.transform(op.get('transform'))
   except (ValueError,KeyError,shared.UnsupportedSurface) as e:
    pending.append({**base,'reason':str(e)});continue
   p={'component':c['id'],'source_operations':[op['id']],'material':op['material'],'part':op['part'],'x_min':aa,'x_max':bb,'y_at_x_min':ya,'y_at_x_max':yb,'vertical_skin_thickness_m':thick,'z_min':op['shape']['z_min'],'z_max':op['shape']['z_max'],'operation_transform':t,'slope':(yb-ya)/(bb-aa),'intercept':ya-(yb-ya)/(bb-aa)*aa}
   p['component_instances']=[{'id':i['id'],'transform':transforms[i['id']]} for i in m['instances'] if i['component']==c['id']]
   raw.append(p);handled.add((c['id'],op['id']))
 # Merge only adjacent bands with identical source plane, thickness, extrusion span, material and operation transform.
 buckets=collections.defaultdict(list)
 for p in raw:
  tag={k:p[k] for k in ['component','material','part','slope','intercept','vertical_skin_thickness_m','z_min','z_max','operation_transform']}
  buckets[json.dumps(trim_floats(tag),sort_keys=True)].append(p)
 planes=[]
 for ls in buckets.values():
  ls.sort(key=lambda p:p['x_min']);run=None
  for p in ls:
   if run and abs(run['x_max']-p['x_min'])<1e-8:
    run['x_max']=p['x_max'];run['y_at_x_max']=p['y_at_x_max'];run['source_operations']+=p['source_operations']
   else:
    run=copy.deepcopy(p);planes.append(run)
 for j,p in enumerate(planes):
  p['id']='plane_%03d'%j;p['projected_area_m2']=(p['x_max']-p['x_min'])*(p['z_max']-p['z_min']);p['sloped_area_m2']=p['projected_area_m2']*math.sqrt(1+p['slope']**2)
  p['source_top_corners']=[[x,p['slope']*x+p['intercept'],z] for x,z in [(p['x_min'],p['z_min']),(p['x_max'],p['z_min']),(p['x_max'],p['z_max']),(p['x_min'],p['z_max'])]]
  p['boundary_contract']='Exact source x/z domain and top plane; no outward tile lip. Max source height retained at uphill boundary.'
 # Whole-group suppression is safe only if every source paint operation for that material is represented.
 safe=[];unsafe=[]
 for mat in sorted(roofmats):
  allops=[(c['id'],o['id']) for c in m['components'] for o in c['operations'] if o.get('action')=='paint' and o.get('material')==mat]
  unsupported=[x for x in allops if x not in handled]
  if allops and not unsupported:safe.append(mat)
  else:unsafe.append({'material':mat,'unhandled_operation_refs':unsupported,'action':'Do not suppress whole render group or enable partial replacement behind it; require exact face-ownership mask or complete source roof replacement.'})
 source_instances=[]
 for r in retained:
  r['component_instances']=[{'id':i['id'],'transform':transforms[i['id']]} for i in m['instances'] if i['component']==r['component']]
 return {'schema':'riverstone.facility_roof.planes.v1','asset_key':key,'source_master_path':a['master_path'],'source_master_sha256':a['master_sha256'],'source_render_path':a['render_path'],'source_render_sha256':a['render_sha256'],'source_pitch_m':a['pitch_m'],'planes':planes,'retained_ridge_boxes':retained,'cut_exclusion_proofs':cutproofs,'preserved_terminal_component_cuts':preserved_cuts,'pending':pending,'suppression':{'safe_material_groups_when_full_matching_near_resource_ready':safe,'unsafe_material_groups':unsafe,'exact_quad_masks_emitted':False,'runtime_activation':False,'require_atomic_swap':True,'old_group_removal_includes_all_normals':True,'source_collision_preserved':True},'palette_id_counts':a['palette_id_counts'],'status':'SOURCE_DESCRIPTORS_ONLY'}

def new_master(id,materials):
 return {'schema':core.SCHEMA,'id':id,'revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':copy.deepcopy(materials),'components':[],'instances':[],'assembly_cuts':[],'constraints':[],'metadata':{'authoring':'facility_roof_shared_descriptor_adapter','near_pitch_m':.05,'runtime_activation':False,'roof_only':True,'whole_city_complete':False}}
def comp(name,ops):return {'id':name,'parts':[{'id':'solid','pivot':[0,0,0],'metadata':{'source_category':'near_roof_surface','dynamic':False}}],'operations':ops}
def add_instance(m,name,cid,t):m['instances'].append({'id':name,'component':cid,'transform':t})
def add_plane(m,p,r,covering):
 """Emit shared row components + rigid row instances, avoiding full tile duplication."""
 a,b,z0,z1=p['x_min'],p['x_max'],p['z_min'],p['z_max'];s=p['slope'];h=lambda x:s*x+p['intercept'];th=p['vertical_skin_thickness_m'];pid=p['id'];mat=p['material'];counts={'row_instances':0,'tile_operations':0,'underlays':1,'plane_instances':len(p['component_instances'])}
 under=shared.prism(pid+'_underlay',[[a,h(a)-th],[b,h(b)-th],[b,h(b)-r['underlay_recess_m']],[a,h(a)-r['underlay_recess_m']]],z0,z1,mat)
 m['components'].append(comp(pid+'_underlay',[under]))
 for ins in p['component_instances']:
  t=core.compose(ins['transform'],p['operation_transform']);add_instance(m,pid+'_underlay_'+ins['id'],pid+'_underlay',t)
 n=max(1,math.ceil((b-a)/r['tile_run_m']));step=(b-a)/n;cache={}
 for row in range(n):
  start=a+row*step;x0=start;x1=start+step
  if s>0:x1=min(b,x1+r['course_overlap_m'])
  else:x0=max(a,x0-r['course_overlap_m'])
  # No tile vertex exceeds the original source top plane, including outer eaves/ridge.
  drop0=0 if s>0 or abs(x0-a)<1e-8 else r['uphill_recess_m']
  drop1=0 if s<0 or abs(x1-b)<1e-8 else r['uphill_recess_m']
  sig=(round(x0-start,10),round(x1-start,10),row%2,drop0,drop1)
  if sig not in cache:
   name=pid+'_row_%d'%len(cache);cache[sig]=name;ops=[];z=z0-(r['tile_width_m']*.5 if row%2 else 0);col=0
   while z<z1-1e-9:
    za,zb=max(z0,z+r['lateral_joint_m']/2),min(z1,z+r['tile_width_m']-r['lateral_joint_m']/2)
    if zb>za+1e-9:
     u,v=x0-start,x1-start
     ops.append(shared.prism(name+'_tile_%04d'%col,[[u,s*u-r['tile_bed_depth_m']],[v,s*v-r['tile_bed_depth_m']],[v,s*v-drop1],[u,s*u-drop0]],za,zb,mat))
    z+=r['tile_width_m'];col+=1
   m['components'].append(comp(name,ops));counts['tile_operations']+=len(ops)
  for ins in p['component_instances']:
   t=core.compose(core.compose(ins['transform'],p['operation_transform']),core.transform({'translation':[start,h(start),0]}))
   add_instance(m,pid+'_course_%04d_'%row+ins['id'],cache[sig],t);counts['row_instances']+=1
 return counts

def make_near(d,source,rules,covering='roof_tile',only_planes=None):
 master=new_master(d['asset_key']+'__near_roof__'+covering,source['materials']);counts=collections.Counter()
 for p in d['planes'] if only_planes is None else only_planes:
  if not p['component_instances']:continue
  counts.update(add_plane(master,p,rules['coverings'][covering],covering))
 if only_planes is None:
  for j,ret in enumerate(d['retained_ridge_boxes']):
   op=copy.deepcopy(ret['operation']);op['part']='solid';cid='retained_ridge_%03d'%j;master['components'].append(comp(cid,[op]))
   for ins in ret['component_instances']:add_instance(master,cid+'_'+ins['id'],cid,ins['transform'])
   counts['retained_ridge_boxes']+=1
 if master['components']:core.validate_master(master,rules['near_pitch_m'])
 master['metadata'].update({'source_master_sha256':d['source_master_sha256'],'covering':covering,'preserve_original_semantic_materials':True,'height_policy':'all new top vertices <= exact original plane; high boundary unchanged','source_descriptor_schema':d['schema'],'counts':dict(counts),'full_compilation':'NOT_RUN_PENDING_BUDGETED_CHUNK_STREAMING'})
 return master

def inventory():
 rules=read(RULES);resource.setrlimit(resource.RLIMIT_AS,(rules['budgets']['memory_limit_bytes'],)*2);mapping=read(MAP);catalog=[];excluded=[];totalbytes=0
 for key,a in mapping['assets'].items():
  if not a['used'] or not a['roof_silhouette_status'].startswith('PENDING'):continue
  if any(key.startswith(p) for p in rules['exclude_asset_prefixes']):excluded.append({'asset_key':key,'owner':'house_rules','reason':'explicit_house_family_scope'});continue
  src=ROOT/a['master_path'];source=read(src)
  if shared.sha(src)!=a['master_sha256']:raise ValueError('source_hash_changed:'+key)
  d=describe(key,a,source);dp=HERE/'descriptors'/(key+'.planes.json');write(dp,d)
  record={'asset_key':key,'descriptor':ref(dp),'plane_count':len(d['planes']),'pending_operation_count':len(d['pending']),'safe_suppression_material_groups':d['suppression']['safe_material_groups_when_full_matching_near_resource_ready'],'variants':[]}
  if d['planes']:
   variants=['roof_tile']+(['wood_shingle'] if any('wood_brown' in pal for pal in a['palette_id_counts']) else [])
   for covering in variants:
    near=make_near(d,source,rules,covering);np=HERE/'masters'/(key+'.'+covering+'.master.json');data=json.dumps(near,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n'
    used=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
    if used+len(data.encode())>rules['budgets']['max_artifact_bytes']-2000000:
     record['variants'].append({'covering':covering,'status':'PENDING_DISK_BUDGET','estimated_master_bytes':len(data.encode())});continue
    write(np,near);record['variants'].append({'covering':covering,'status':'AUTHORED_STRUCTURE_VALIDATED_NOT_FULLY_COMPILED','master':ref(np),'bytes':np.stat().st_size,'component_count':len(near['components']),'instance_count':len(near['instances']),'counts':near['metadata']['counts']})
  record['status']='PENDING_UNSUPPORTED_GEOMETRY' if not d['planes'] else 'PARTIAL_SUPPORTED_PLANES_WITH_PENDING' if d['pending'] else 'SUPPORTED_SOURCE_AUTHORING_ONLY'
  catalog.append(record)
 out={'schema':'riverstone.facility_roof.catalog.v1','rules':ref(RULES),'mapping':ref(MAP),'shared_adapter':ref(HERE.parent/'house_rules/adapter.py'),'source_unchanged':True,'runtime_activation':False,'asset_count':len(catalog),'excluded_house_asset_count':len(excluded),'excluded_house_assets':excluded,'assets':catalog,'limits':rules['budgets'],'completion':'Source authoring and bounded ROI only; full roof sampling/chunking, visual review and runtime suppression swap remain pending.'}
 write(HERE/'catalog.json',out);return out

def roi(asset,plane_id,covering):
 rules=read(RULES);resource.setrlimit(resource.RLIMIT_AS,(rules['budgets']['memory_limit_bytes'],)*2)
 d=read(HERE/'descriptors'/(asset+'.planes.json'));source=read(ROOT/d['source_master_path']);p=copy.deepcopy(next(p for p in d['planes'] if p['id']==plane_id))
 # Fixed minimum-corner 1m x 1m projected ROI retains exact source plane and transform.
 p['x_max']=min(p['x_max'],p['x_min']+1);p['z_max']=min(p['z_max'],p['z_min']+1);p['y_at_x_max']=p['slope']*p['x_max']+p['intercept'];p['id']='roi_'+plane_id;p['component_instances']=p['component_instances'][:1]
 near=make_near(d,source,rules,covering,[p]);np=HERE/'roi'/(asset+'.'+plane_id+'.'+covering+'.master.json');write(np,near)
 t=time.perf_counter();c=core.compile_master(near,{'pitch':rules['near_pitch_m']},max_candidate_cells=rules['budgets']['roi_max_candidate_cells'],max_output_cells=rules['budgets']['roi_max_output_cells']);rd=make_render_data(c);rp=np.with_name(np.name.replace('.master.json','.render.json'));write(rp,rd)
 report={'schema':'riverstone.facility_roof.roi_validation.v1','status':'PASS' if c['valid'] else 'FAIL','asset_key':asset,'plane_id':plane_id,'covering':covering,'scope':'1m x 1m projected original-plane ROI; NOT a full building or full roof compile','source_master':ref(ROOT/d['source_master_path']),'roi_master':ref(np),'roi_render':ref(rp),'pitch_m':rules['near_pitch_m'],'candidate_cells':c['candidate_cells'],'cells':len(c['cells']),'quads':rd['quad_count'],'seconds':time.perf_counter()-t,'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'source_plane':p,'source_unchanged':shared.sha(ROOT/d['source_master_path'])==d['source_master_sha256'],'runtime_activation':False,'whole_asset_compile':False,'visual_approval':False,'shared_compiler_source':ref(Path(core.__file__))}
 write(np.with_name(np.name.replace('.master.json','.validation.json')),report);print(json.dumps({k:report[k] for k in ['status','asset_key','plane_id','covering','candidate_cells','cells','quads','seconds','max_rss_bytes']}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['inventory','roi']);p.add_argument('--asset',default='registered_cathedral_nave_aisles_transept');p.add_argument('--plane',default='plane_000');p.add_argument('--covering',choices=['roof_tile','wood_shingle'],default='roof_tile');args=p.parse_args()
 if args.command=='inventory':
  c=inventory();print(json.dumps({'assets':c['asset_count'],'house_excluded':c['excluded_house_asset_count'],'planes':sum(a['plane_count'] for a in c['assets']),'variants':sum(len(a['variants']) for a in c['assets']),'bytes':sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())}))
 else:roi(args.asset,args.plane,args.covering)
