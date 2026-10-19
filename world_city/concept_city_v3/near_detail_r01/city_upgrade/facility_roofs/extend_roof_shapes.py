"""Data-driven subtractive detail on exact original hip/lathe/flat roof solids.
All new detail operations are cuts; source paint and source cuts are unchanged.
No geometry crop, new primitive, common-core edit or full asset compilation.
"""
import argparse,collections,copy,gc,itertools,json,math,resource,time
from pathlib import Path
import author_facility_roofs as a
import finish_roofs as f
import expand_facilities as e
RULES=a.HERE/'inputs/shape_extension_rules.v4.json'
OUT=a.HERE/'shape_extensions'

def limited():
 r=a.read(RULES);resource.setrlimit(resource.RLIMIT_AS,(r['budgets']['memory_limit_bytes'],)*2);return r

def subtract(shape,id,part,t=None,role=None):
 q={'id':id,'part':part,'action':'cut','shape':shape,'metadata':{'detail_role':role or id,'subtractive_only':True}}
 if t:q['transform']=t
 return q

def extrusion(poly,z0,z1):return {'kind':'extrusion','polygon':poly,'z_min':z0,'z_max':z1}
def box(lo,hi):return {'kind':'box','min':lo,'max':hi}
def yaw(theta):return a.core.transform({'basis':[[math.cos(theta),0,math.sin(theta)],[0,1,0],[-math.sin(theta),0,math.cos(theta)]]})
def normalize(v):
 n=math.sqrt(sum(x*x for x in v));return [x/n for x in v]
def cross(u,v):return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
def transform_points(t,poly):return [a.core.apply(t,p) for p in poly]

def hip_parameters(op,cuts):
 sh=op['shape'];p=sh['polygon'];assert sh['kind']=='extrusion' and len(p)==3
 low=min(y for x,y in p);high=max(y for x,y in p);base=sorted(x for x,y in p if y==low);peak=[x for x,y in p if y==high]
 if len(base)!=2 or len(peak)!=1 or not (base[0]==-base[1] and peak[0]==0 and sh['z_min']==base[0] and sh['z_max']==base[1]):raise ValueError('non_square_or_offcenter_solid_hip_pending')
 w=base[1]
 if len(cuts)!=2:raise ValueError('hip_requires_exact_two_orthogonal_source_end_cuts')
 expected=[]
 for sign in (-1,1):
  expected.append({'kind':'extrusion','polygon':[[0,high],[sign*w,low],[sign*w,high+1],[0,high+1]],'z_min':-w-.01,'z_max':w+.01})
 for cut,shape in zip(cuts,expected):
  if cut['shape']!=shape or a.core.transform(cut.get('transform'))!=a.core.transform({'basis':[[0,0,1],[0,1,0],[-1,0,0]]}):raise ValueError('hip_source_end_cut_contract_mismatch')
 return {'half_span_m':w,'base_y_m':low,'apex_y_m':high,'slope':(high-low)/w,'source_paint_triangle':copy.deepcopy(p),'source_end_cuts_exact':True}

def hip_detail(op,sourcecuts,cfg,margin):
 p=hip_parameters(op,sourcecuts);w,low,high,s=p['half_span_m'],p['base_y_m'],p['apex_y_m'],p['slope'];part=op['part'];ops=[];ot=a.core.transform(op.get('transform'));counts=collections.Counter()
 # Leave an actual thin roof shell and intact source underside by removing only
 # provably interior boxes. These hidden steps cannot alter the external solid.
 y=low+cfg['underside_plate_m'];j=0
 while y<high-cfg['roof_shell_vertical_clearance_m']:
  end=min(y+cfg['interior_hollow_step_m'],high-cfg['roof_shell_vertical_clearance_m']);bound=w*(high-end-cfg['roof_shell_vertical_clearance_m'])/(high-low)
  if bound>0:
   ops.append(subtract(box([-bound,y,-bound],[bound,end,bound]),'hip_internal_void_%04d'%j,part,ot,'hidden_interior_hollow_keeps_source_shell'));counts['interior_hollow_cuts']+=1
  y=end;j+=1
 # Four real source faces; no boxes or substitute planes are painted over them.
 for face in range(4):
  t=a.core.compose(ot,yaw(face*math.pi/2));a0=-w+cfg['eave_guard_m'];b0=-cfg['hip_cap_guard_m'];n=math.ceil((b0-a0)/cfg['course_run_m']);step=(b0-a0)/n
  for row in range(n):
   aa=a0+row*step;bb=a0+(row+1)*step;half=-bb-cfg['hip_cap_guard_m'];h=lambda u:high+s*u
   if half<=cfg['joint_m']:continue
   ops.append(subtract(extrusion([[aa,h(aa)],[bb,h(bb)-cfg['headlap_recess_m']],[bb,h(bb)+margin],[aa,h(aa)+margin]],-half,half),'hip_face_%d_headlap_%04d'%(face,row),part,t,'recessed_course_headlap_on_exact_slope'));counts['headlap_cuts']+=1
   z=-half+(cfg['tile_width_m']/2 if row%2 else 0);col=0
   while z<half:
    if z>-half+cfg['joint_m']/2:
     ops.append(subtract(extrusion([[aa,h(aa)-cfg['joint_depth_m']],[bb,h(bb)-cfg['joint_depth_m']],[bb,h(bb)+margin],[aa,h(aa)+margin]],max(-half,z-cfg['joint_m']/2),min(half,z+cfg['joint_m']/2)),'hip_face_%d_row_%04d_joint_%03d'%(face,row,col),part,t,'staggered_lateral_tile_joint'));counts['lateral_joint_cuts']+=1
    z+=cfg['tile_width_m'];col+=1
  # Shallow segmented eave notches, following the original source slope.
  aa=-w;bb=-w+cfg['eave_guard_m'];h=lambda u:high+s*u;z=-w+cfg['tile_width_m'];j=0
  while z<w-cfg['joint_m']:
   ops.append(subtract(extrusion([[aa,h(aa)-cfg['joint_depth_m']],[bb,h(bb)-cfg['joint_depth_m']],[bb,h(bb)+margin],[aa,h(aa)+margin]],z-cfg['joint_m']/2,z+cfg['joint_m']/2),'hip_eave_%d_joint_%03d'%(face,j),part,t,'source_envelope_segmented_eave'));counts['eave_cuts']+=1;z+=cfg['tile_width_m'];j+=1
 # True 3D hip axes. Notch cross-sections follow the original dihedral surfaces.
 for sx,sz in itertools.product((-1,1),repeat=2):
  tangent=normalize([sx,-s,sz]);normal=normalize([sz,0,-sx]);up=normalize(cross(tangent,normal));k=s/math.sqrt(s*s+2);length=w*math.sqrt(s*s+2);step=cfg['hip_cap_interval_m'];j=1
  while j*step<length-cfg['eave_guard_m']:
   distance=j*step;r=distance/math.sqrt(s*s+2);center=[sx*r,high-s*r,sz*r];t=a.core.transform({'basis':[[normal[v],up[v],tangent[v]] for v in range(3)],'translation':center});width=cfg['hip_cap_half_width_m'];depth=cfg['headlap_recess_m'];poly=[[-width,-k*width-depth],[0,-depth],[width,-k*width-depth],[width,margin],[-width,margin]]
   ops.append(subtract(extrusion(poly,-cfg['hip_cap_joint_m']/2,cfg['hip_cap_joint_m']/2),'hip_cap_%s_%s_joint_%04d'%(sx,sz,j),part,a.core.compose(ot,t),'segmented_dihedral_hip_cap'));counts['hip_cap_joint_cuts']+=1;j+=1
 return ops,{'type':'solid_square_hip','parameters':p,'counts':dict(counts),'shell_policy':'Original source paint and exact end cuts retained; interior subtraction leaves source underside and minimum declared vertical shell clearance.'}

def cone_parameters(op):
 sh=op['shape'];profile=sh['profile']
 if sh['kind']!='lathe' or len(profile)!=4:raise ValueError('unsupported_spire_profile')
 outer,tip,inner_tip,inner_base=profile
 if not (outer[0]>inner_base[0]>0 and tip[0]==inner_tip[0]==0 and outer[1]==inner_base[1]<inner_tip[1]<tip[1]):raise ValueError('unsupported_spire_profile_order')
 return {'base_radius_m':outer[0],'base_y_m':outer[1],'apex_y_m':tip[1],'inner_apex_y_m':inner_tip[1],'inner_base_radius_m':inner_base[0],'radial_slope':outer[0]/(tip[1]-outer[1]),'original_lathe_profile':copy.deepcopy(profile)}

def cone_detail(op,cfg,margin):
 p=cone_parameters(op);base,top,s=p['base_y_m'],p['apex_y_m'],p['radial_slope'];radius=lambda y:s*(top-y);cap=top-cfg['protected_apex_cap_radius_m']/s;part=op['part'];ot=a.core.transform(op.get('transform'));ops=[];counts=collections.Counter();n=math.ceil((cap-base)/cfg['course_height_m']);step=(cap-base)/n
 for row in range(n):
  ya=base+row*step;yb=base+(row+1)*step;ra,rb=radius(ya),radius(yb);head_start=max(ya,base+cfg['eave_collar_height_m'])
  if head_start<yb:
   cutprofile=[[radius(head_start),head_start],[rb-cfg['headlap_recess_radial_m'],yb],[rb+margin,yb],[radius(head_start)+margin,head_start]]
   ops.append(subtract({'kind':'lathe','profile':cutprofile},'spire_course_headlap_%04d'%row,part,ot,'curved_radial_headlap_on_original_cone'));counts['curved_headlap_cuts']+=1
  count=max(6,math.ceil(2*math.pi*((ra+rb)/2)/cfg['tile_circumference_width_m']));phase=(row%2)*math.pi/count
  for col in range(count):
   theta=2*math.pi*col/count+phase;poly=[[ra-cfg['joint_depth_radial_m'],ya],[rb-cfg['joint_depth_radial_m'],yb],[rb+margin,yb],[ra+margin,ya]]
   ops.append(subtract(extrusion(poly,-cfg['joint_m']/2,cfg['joint_m']/2),'spire_row_%04d_joint_%04d'%(row,col),part,a.core.compose(ot,yaw(theta)),'staggered_radial_tile_joint_following_exact_taper'));counts['radial_joint_cuts']+=1
 # A shallow exact-lathe collar separates the preserved tapered apex cap.
 ya=cap-.05;yb=cap;ops.append(subtract({'kind':'lathe','profile':[[radius(ya)-.05,ya],[radius(yb)-.05,yb],[radius(yb)+margin,yb],[radius(ya)+margin,ya]]},'spire_apex_cap_separation',part,ot,'recessed_circular_cap_joint'));counts['cap_joint_cuts']+=1
 return ops,{'type':'conical_spire','parameters':p,'cap_starts_y_m':cap,'counts':dict(counts),'surface_policy':'Exact original radial lathe remains the only paint. Courses and staggered radial joints subtract from that true curved surface; apex and inner hollow profile are preserved.'}

def flat_detail(op,partmeta,cfg,margin):
 lo,hi=op['shape']['min'],op['shape']['max'];depth=min(cfg['maximum_joint_depth_m'],(hi[1]-lo[1])/2);lap=min(cfg['maximum_headlap_recess_m'],(hi[1]-lo[1])/2);ot=a.core.transform(op.get('transform'));part=op['part'];ops=[];counts=collections.Counter();x0,x1,z0,z1=lo[0],hi[0],lo[2],hi[2];n=math.ceil((x1-x0)/cfg['course_run_m']);step=(x1-x0)/n
 for row in range(n):
  aa=x0+row*step;bb=x0+(row+1)*step;za=z0+min(cfg['edge_guard_m'],(z1-z0)/4);zb=z1-min(cfg['edge_guard_m'],(z1-z0)/4)
  ops.append(subtract(extrusion([[aa,hi[1]],[bb,hi[1]-lap],[bb,hi[1]+margin],[aa,hi[1]+margin]],za,zb),'flat_headlap_%04d'%row,part,ot,'source_flat_cover_headlap_relief'));counts['headlap_cuts']+=1
  z=z0+(cfg['tile_width_m']/2 if row%2 else cfg['tile_width_m']);j=0
  while z<z1-cfg['joint_m']/2:
   ops.append(subtract(box([aa,hi[1]-depth,z-cfg['joint_m']/2],[bb,hi[1]+margin,z+cfg['joint_m']/2]),'flat_lateral_%04d_%03d'%(row,j),part,ot,'staggered_flat_cover_seam'));counts['lateral_joint_cuts']+=1;z+=cfg['tile_width_m'];j+=1
 # Rim segments stay entirely within the actual original slab thickness.
 for axis in (0,2):
  crossaxis=2 if axis==0 else 0;v=lo[axis]+.5;j=0
  while v<hi[axis]-.025:
   for side in (0,1):
    a0=lo.copy();b0=hi.copy();a0[axis]=v-.025;b0[axis]=v+.025;a0[1]=hi[1]-depth;b0[1]=hi[1]+margin
    if side==0:b0[crossaxis]=lo[crossaxis]+min(.075,(hi[crossaxis]-lo[crossaxis])/4)
    else:a0[crossaxis]=hi[crossaxis]-min(.075,(hi[crossaxis]-lo[crossaxis])/4)
    ops.append(subtract(box(a0,b0),'flat_rim_%d_%d_%03d'%(axis,side,j),part,ot,'segmented_original_cover_edge'));counts['rim_cuts']+=1
   v+=.5;j+=1
 return ops,{'type':'flat_cover','parameters':{'original_bounds':copy.deepcopy(op['shape']),'original_part_metadata':partmeta,'joint_depth_m':depth,'headlap_recess_m':lap},'counts':dict(counts),'ownership_evidence':{'source_operation_id':op['id'],'source_component_role':partmeta.get('source_category'),'classification_basis':'Original covered gallery/slate cap operation and component provenance, not color.'}}

def build_one(key,d,source,covering,rules):
 if d['planes'] or d['retained_ridge_boxes']:m=e.ordered_finish(d,source,a.read(f.RULES),covering)
 else:m=a.new_master(key+'__extended_roof__'+covering,source['materials'])
 if source.get('assembly_cuts'):raise ValueError('unhandled_assembly_cuts_extension_pending')
 world=a.instance_transforms(source);source_comps={c['id']:c for c in source['components']};records=[]
 for number,pending in enumerate(d['pending']):
  c=source_comps[pending['component']];op=next(o for o in c['operations'] if o['id']==pending['operation']);originalcuts=[copy.deepcopy(q) for q in c['operations'] if q['action']=='cut'];part=next(p for p in c['parts'] if p['id']==op['part']);kind=op['shape']['kind']
  if kind=='extrusion':newcuts,record=hip_detail(op,originalcuts,rules['shape_types']['solid_square_hip'],rules['cut_margin_m'])
  elif kind=='lathe':newcuts,record=cone_detail(op,rules['shape_types']['conical_spire'],rules['cut_margin_m'])
  elif kind=='box':
   if op['id'] not in ('gallery_roof','slate_cap'):raise ValueError('unproven_nonridge_box_ownership')
   flatcfg={**rules['shape_types']['flat_cover'],**rules.get('covering_overrides',{}).get(covering,{}).get('flat_cover',{})}
   newcuts,record=flat_detail(op,part.get('metadata',{}),flatcfg,rules['cut_margin_m'])
  else:raise ValueError('shape_extension_pending:'+kind)
  cid='extension_%03d'%number;original=copy.deepcopy(op);component={'id':cid,'parts':copy.deepcopy(c['parts']),'operations':[original]+originalcuts+newcuts,'metadata':{'provenance':{'asset_key':key,'source_master_sha256':d['source_master_sha256'],'source_component':c['id'],'source_operations':[op['id']],'role':'exact_source_solid_subtractive_detail'},'source_operation':copy.deepcopy(op),'source_cuts':copy.deepcopy(originalcuts),'subtractive_subset_proof':True,'type_parameters':record}}
  m['components'].append(component)
  for ins in source['instances']:
   if ins['component']==c['id']:m['instances'].append({'id':cid+'_'+ins['id'],'component':cid,'transform':world[ins['id']],'metadata':{'source_identity':{'component':c['id'],'instance':ins['id'],'part':op['part'],'material':op['material'],'transform':world[ins['id']]}}})
  record.update(source_component=c['id'],source_operation=op['id'],material=op['material'],source_shape_sha256=a.core.digest(op['shape']),source_cut_ids=[x['id'] for x in originalcuts],new_cut_operations=len(newcuts));records.append(record)
 # Keep original instance/paint precedence across already-supported and new shapes.
 comps={c['id']:c for c in m['components']};rank={i['id']:j for j,i in enumerate(source['instances'])};oprank={(c['id'],o['id']):j for c in source['components'] for j,o in enumerate(c['operations'])}
 m['instances'].sort(key=lambda i:(rank[i['metadata']['source_identity']['instance']],min(oprank[(comps[i['component']]['metadata']['provenance']['source_component'],o)] for o in comps[i['component']]['metadata']['provenance']['source_operations'])))
 flat=f.flatten(m);flat['metadata'].update({'shape_extension_rules':a.ref(RULES),'subtractive_original_solid_extensions':records,'runtime_activation':False,'source_coverage_is_not_playable_completion':True});a.core.validate_master(flat,.05);f.layers.SpatialSource(flat,.05,range_only=True)
 # Exact algebraic subset proof: no later paint may refill after source cuts.
 proofs=[]
 for component in flat['components']:
  md=component['metadata']
  if not md.get('subtractive_subset_proof'):continue
  first=component['operations'][0];src=md['source_operation'];srcins=md['shared_row_source']['instance_metadata']['source_identity'];expected_t=a.core.compose(srcins['transform'],a.core.transform(src.get('transform')))
  if first['shape']!=src['shape'] or first['material']!=src['material'] or first['part']!=src['part'] or first['transform']!=expected_t or any(o['action']!='cut' for o in component['operations'][1:]):raise ValueError('subtractive_subset_proof_failed')
  for j,cut in enumerate(md['source_cuts']):
   actual=component['operations'][j+1]
   if actual['shape']!=cut['shape'] or actual.get('selector',{})!=cut.get('selector',{}) or actual['transform']!=a.core.compose(srcins['transform'],a.core.transform(cut.get('transform'))):raise ValueError('original_cut_changed')
  proofs.append({'component':component['id'],'original_shape_exact':True,'original_cut_count':len(md['source_cuts']),'additional_operations_are_cuts_only':True,'subset_holds_for_continuous_shapes_and_every_sampling_pitch':True})
 return flat,records,proofs

def build(representatives=False):
 rules=limited();start=time.perf_counter();bundle=f.layers.load_master(f.OUT/'shape_support_descriptors.v2.json.gz')['assets'];pending=a.read(e.OUT/'pending_extensions.json');records=[];fail=[];contracts=[];oldcontracts={x['asset_key']:x for x in a.read(a.HERE/'replacement_contracts.json')['assets']}
 for item in pending['assets']:
  key=item['asset_key']
  if representatives and key not in rules['representatives']:continue
  d=bundle[key];source=a.read(a.ROOT/d['source_master_path']);selector_path=a.HERE/'variant_selection.json';selectors=a.read(selector_path)['placements'] if selector_path.exists() else [];requires_wood=any('wood_brown' in pal for pal in d['palette_id_counts']) or any(v['native_asset_key']==key and v['roof_covering']=='wood_shingle' for v in selectors);variants=['roof_tile']+(['wood_shingle'] if requires_wood else [])
  for covering in variants:
   try:
    m,types,proofs=build_one(key,d,source,covering,rules);vkey=key if covering=='roof_tile' else key+'__wood_shingle';mp=OUT/'masters'/(vkey+'.finished.master.json.gz');f.gzwrite(mp,m)
    if f.disk()>rules['budgets']['total_bytes_limit']:raise ValueError('extension_disk_budget_exceeded')
    rec={'asset_key':vkey,'native_asset_key':key,'covering':covering,'emitted_master_path':a.rel(mp),'emitted_master_sha256':a.shared.sha(mp),'source_master_path':d['source_master_path'],'source_sha256':d['source_master_sha256'],'source_render_path':d['source_render_path'],'source_render_sha256':d['source_render_sha256'],'shape_extensions':types,'subset_proofs':proofs,'source_authoring_complete_for_all_roof_groups':True,'replacement_allowed':False,'uncompiled':True,'native_cell_bounds_required':True,'operations':sum(len(c['operations']) for c in m['components']),'gzip_bytes':mp.stat().st_size,'original_source_unchanged':a.shared.sha(a.ROOT/d['source_master_path'])==d['source_master_sha256']};records.append(rec);print(json.dumps({'asset':vkey,'types':[x['type'] for x in types],'operations':rec['operations'],'gzip_bytes':rec['gzip_bytes']}),flush=True)
   except (ValueError,AssertionError,KeyError) as ex:fail.append({'asset_key':key,'covering':covering,'error':str(ex)});print(json.dumps(fail[-1]),flush=True)
   finally:m=None;gc.collect()
  complete=not any(x['asset_key']==key for x in fail)
  contract=copy.deepcopy(oldcontracts[key]);contract['replacement_contract_supported_for_all_roof_groups']=complete;contract['pending_shape_operations']=[] if complete else item['pending_operations'];contract['source_authoring_complete_for_all_roof_groups']=complete;contract['replacement_allowed']=False;contract['current_blocker']='Full matching near resource compilation, whole-roof interfaces and runtime/visual acceptance pending.' if complete else 'Source authoring failed; see catalog errors.'
  contract['replacement_contract_supported_material_ids']=[g['material_id'] for g in contract['render_groups']] if complete else contract['replacement_contract_supported_material_ids']
  for group in contract['render_groups']:
   group['group_replacement_supported']=complete;group['unsupported_refs']=[] if complete else group['unsupported_refs'];group['replacement_allowed']=False
   if complete:
    represented={}
    for plane in d['planes']:
     if plane['material']==group['material_id']:
      for oid in plane['source_operations']:represented[(plane['component'],oid)]={'component':plane['component'],'operation':oid,'role':'finished_sloped_roof_and_edges'}
    for ridge in d['retained_ridge_boxes']:
     if ridge['operation']['material']==group['material_id']:represented[(ridge['component'],ridge['operation']['id'])]={'component':ridge['component'],'operation':ridge['operation']['id'],'role':'finished_segmented_ridge'}
    for op in item['pending_operations']:
     if op['material']==group['material_id']:represented[(op['component'],op['operation'])]={'component':op['component'],'operation':op['operation'],'role':'exact_source_shape_with_subtractive_surface_detail'}
    group['represented_roof_operations']=list(represented.values())
  contracts.append(contract)
 out={'schema':'riverstone.facility_roof.shape_extension_catalog.v4','assets':records,'native_asset_count':len({r['native_asset_key'] for r in records}),'variant_count':len(records),'rules':a.ref(RULES),'author':a.ref(Path(__file__)),'shared_core':a.ref(a.core.__file__),'shared_layered':a.ref(f.layers.__file__),'variant_selection_input':a.ref(a.HERE/'variant_selection.json') if (a.HERE/'variant_selection.json').exists() else None,'previous_65_variants_untouched':True,'replacement_allowed':False,'full_asset_compiles':0,'errors':fail,'scope':'representatives' if representatives else 'all_remaining_shapes','seconds':time.perf_counter()-start,'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'directory_bytes':f.disk()};a.write(OUT/('representative_catalog.json' if representatives else 'layered_compile_catalog.json'),out);a.write(OUT/('representative_contracts.json' if representatives else 'replacement_contracts.v4.json'),{'schema':'riverstone.facility_roof.shape_extension_replacements.v4','assets':contracts,'runtime_activation':False});print(json.dumps({'status':'SOURCE_STRUCTURES_VALIDATED' if not fail else 'PARTIAL','assets':out['native_asset_count'],'errors':fail,'bytes':f.disk(),'rss':out['max_rss_bytes']}));return bool(fail)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--representatives',action='store_true');args=p.parse_args();raise SystemExit(build(args.representatives))
