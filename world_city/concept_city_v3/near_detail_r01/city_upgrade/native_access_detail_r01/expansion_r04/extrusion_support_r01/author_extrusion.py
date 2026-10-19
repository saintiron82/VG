"""Bounded training access path candidate, exact source cap union per actual quad patch.
Common patch/author/crop and polygon-union helper remain unchanged. Fraction
halfplane oracle is proof-only, not a mesher or a replacement source geometry.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse,collections,copy,itertools,json,resource,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;PARENT=H.parent;sys.path.insert(0,str(PARENT));import author_r04 as b
a=b.a;R=b.R;P=b.P;KEY='registered_training_r09_recovered_coarse';PLAN=H/'source_plan.json';CAT=H/'modules/catalog.json';BASE=PARENT/'combined/module_catalog_r03_plus_r04.json'
read=b.read;sha=b.sha;digest=b.digest;save=b.save

def fp(poly):return [[F(v) for v in p] for p in poly]
def cross(x,y,p):return (y[0]-x[0])*(p[1]-x[1])-(y[1]-x[1])*(p[0]-x[0])
def area(poly):return abs(sum(p[0]*q[1]-p[1]*q[0] for p,q in zip(poly,poly[1:]+poly[:1])))/2 if len(poly)>=3 else F(0)
def signed(poly):return sum(p[0]*q[1]-p[1]*q[0] for p,q in zip(poly,poly[1:]+poly[:1]))
def convex(poly):
 if len(poly)<3 or area(poly)==0 or len({tuple(p) for p in poly})!=len(poly):return False
 direction=1 if signed(poly)>0 else -1
 return all(direction*cross(x,y,p)>=0 for x,y in zip(poly,poly[1:]+poly[:1]) for p in poly)
def clip(poly,x,y,direction,inside):
 if not poly:return []
 out=[];previous=poly[-1];pd=direction*cross(x,y,previous)
 for current in poly:
  cd=direction*cross(x,y,current);pi=pd>=0 if inside else pd<=0;ci=cd>=0 if inside else cd<=0
  if pi!=ci:
   t=pd/(pd-cd);out.append([previous[j]+t*(current[j]-previous[j]) for j in [0,1]])
  if ci:out.append(current)
  previous,pd=current,cd
 return out

def difference(subject,cover):
 current=subject;out=[];direction=1 if signed(cover)>0 else -1
 for x,y in zip(cover,cover[1:]+cover[:1]):
  if not current:break
  part=clip(current,x,y,direction,False)
  if area(part)>0:out.append(part)
  current=clip(current,x,y,direction,True)
 return out

def exact_union(subject,covers):
 remaining=[subject]
 for poly in covers:
  remaining=[piece for part in remaining for piece in difference(part,poly)]
  if len(remaining)>512:raise ValueError('exact_union_fragment_budget')
  if not remaining:return F(0)
 return sum(area(poly) for poly in remaining)

def source_caps(master,rule):
 if master.get('assembly_cuts'):raise ValueError('assembly_cut_unproven')
 if any(op['action']=='cut' for cp in master['components'] for op in cp['operations']):raise ValueError('component_cut_unproven')
 metadata={r['id']:r for r in master['metadata']['owned_floor_regions']};wanted=set(rule['operation_ids']);owners=[]
 for inst,op,tr in a.previous.source_parts(master):
  if op['id'] not in wanted:continue
  if inst['component']!=rule['component'] or op.get('material')!=rule['material'] or op['action']!='paint' or op['part']!='solid' or op['shape']['kind']!='extrusion':raise ValueError('wrong_declared_path_source')
  if metadata[op['id']]['material']!=rule['material']:raise ValueError('source_semantic_metadata_mismatch')
  # This bounded cap projection is exact for signed axis permutations only.
  if any(v not in [-1,0,1] for row in tr['basis'] for v in row):raise ValueError('non_axis_source_cap_projection_unsupported')
  shape=op['shape']
  if b.core.prepare_shape(shape,.5)!=shape:raise ValueError('pitch_dependent_source_shape')
  vertices=[b.core.apply(tr,[*p,shape['z_max']]) for p in shape['polygon']]
  if len({p[1] for p in vertices})!=1 or [tr['basis'][i][2] for i in range(3)]!=[0,1,0]:raise ValueError('nonhorizontal_or_downward_source_cap')
  poly=[[v[0],-v[2]] for v in vertices];rational=fp(poly)
  if not convex(rational) or not a.polygons.is_convex_polygon(poly):raise ValueError('nonconvex_or_malformed_source_polygon')
  owners.append({'instance':inst['id'],'component':inst['component'],'operation':op['id'],'operation_sha256':digest(op),'semantic_metadata_sha256':digest(metadata[op['id']]),'material':op['material'],'part':op['part'],'semantic_key':[inst['id'],inst['component'],op['material'],op['part']],'top_y_m':vertices[0][1],'polygon_uv_m':poly,'polygon_sha256':digest(poly),'bounds_uv_m':[min(v[i] for v in poly) for i in [0,1]]+[max(v[i] for v in poly) for i in [0,1]],'transform':tr})
 if len(owners)!=len(wanted):raise ValueError('missing_selected_source_path')
 return owners

def semantic_proof(rect,plane,owners):
 usable=[o for o in owners if o['top_y_m']==plane and min(o['bounds_uv_m'][2],rect[2])>max(o['bounds_uv_m'][0],rect[0]) and min(o['bounds_uv_m'][3],rect[3])>max(o['bounds_uv_m'][1],rect[1])]
 if len(usable)>32:raise ValueError('local_owner_budget')
 subject=a.polygon(rect);polys=[o['polygon_uv_m'] for o in usable];value=exact_union(fp(subject),[fp(p) for p in polys]);common=a.polygons.uncovered_area_by_union(subject,polys,0)
 return {'supported':value==0 and common==0 and bool(usable),'exact_uncovered_area_ratio':[value.numerator,value.denominator],'common_uncovered_area_m2':common,'owner_operation_ids':[o['operation'] for o in usable],'owner_polygons_sha256':digest(polys),'semantic_key':usable[0]['semantic_key'] if usable else None,'geometric_tolerance_m':0,'method':'unchanged_common_polygon_union_plus_exact_binary64_rational_halfplane_oracle'}

def make_plan():
 idx=read(b.IP);src=idx['common_assets'][KEY];assert sha(R/src['master_path'])==src['master_sha256'] and sha(R/src['render_path'])==src['render_sha256'];master=read(R/src['master_path']);render=read(R/src['render_path']);metadata=master['metadata'];ids=[r['id'] for r in metadata['owned_floor_regions'] if r['material']=='stone_light'];assert len(ids)==55 and all(':door:' in k and ':route:' in k for k in ids)
 rule={'kind':'paving','material':'stone_light','component':'landscape','operation_ids':ids,'source_metadata_field':'owned_floor_regions','source_space_id':metadata['source_space_id'],'scope':'Only explicitly owned door-route stone paths. Earth drill ground, external fine slope and all other operations excluded.','proof_scope':'per actual retained source-quad patch; original face alone does not imply full semantic coverage'};owners=source_caps(master,rule);poses,pdeps=b.poses(idx,[KEY]);faces=[];patches=[];rejected=[];demand={};stats=collections.Counter();coverage=[]
 for gi,g in enumerate(render['groups']):
  if g['material']!=rule['material']:continue
  for qi,q in enumerate(g['quads']):
   try:rect=a.top_rectangle(q)
   except ValueError as e:stats[str(e)]+=1;continue
   stats['eligible_actual_top_quads']+=1;rect_m=[v*P for v in rect];full=semantic_proof(rect_m,q[0][1],owners);f={'group_index':gi,'quad_index':qi,'quad':q,'quad_sha256':digest(q),'rect_uv_integer_cells':rect,'plane_y_m':q[0][1],'full_face_semantic_proof':full,'semantic_ownership_scope':'each emitted placement proves support independently'};facepatches=[]
   for patch in a.previous.patches(rect):
    bounds=patch['low_uv']+patch['high_uv'];proof=semantic_proof(bounds,q[0][1],owners);stats['all_actual_patch_candidates']+=1
    if not proof['supported']:
     stats['unsupported_boundary_patch']+=1;rejected.append({'source_face_ref':[gi,qi],'bounds_uv_m':bounds,'reason':'outside_exact_path_union' if proof['exact_uncovered_area_ratio'][0] else 'common_numeric_disagreement','proof':proof});continue
    trim=patch['trim'];seed=patch['seed'];token='paving_'+str(seed)+'_'+digest(trim)[:12];demand[token]={'id':token,'kind':'paving','seed':seed,'trim':trim}
    facepatches.append({'module_key':token,'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[bounds[0],q[0][1]+.0375,-bounds[1]]},'source_face_ref':[gi,qi],'source_face_sha256':f['quad_sha256'],'bounds_uv_m':bounds,'source_plane_y_m':q[0][1],'source_semantic_proof':proof,'collision_changed':False})
   if facepatches:faces.append(f);patches+=facepatches
   coverage.append({'source_face_ref':[gi,qi],'full_face_semantically_supported':full['supported'],'retained_patches':len(facepatches)})
 assert len(patches)<=800 and len(demand)<=30 and len(owners)==55
 asset={'asset_key':KEY,'source_master_path':src['master_path'],'source_master_sha256':src['master_sha256'],'source_render_path':src['render_path'],'source_render_sha256':src['render_sha256'],'source_pitch_m':src['pitch_m'],'rule':rule,'faces':faces,'placements':patches,'source_polygon_owners':owners,'actual_instances':poses[KEY],'existing_collision_unchanged':True,'source_collision_baseline':b.collision_baseline(idx,src,poses[KEY]),'excluded':dict(stats),'status':'PARTIAL_EXACT_OWNED_PATH_SUPPORT','original_remaining_surfaces_unchanged':True}
 plan={'schema':'riverstone.native_access_detail.plan.v1','revision':'r04_extrusion_support_r01','source_city_index_sha256':sha(b.IP),'assets':[asset],'module_demand':list(demand.values()),'maximum_additional_visual_offset_from_source_m':.0375,'runtime_activation':False,'whole_city_upgrade_complete':False,'source_collision_note':'Additional visual offset from original top; existing original native collider unchanged. No walking route pass claimed.','provenance':{'author':b.ref(Path(__file__)),'r03_guards':b.ref(a.HERE/'author_r03.py'),'common_union':b.ref(Path(a.polygons.__file__)),'common_core':b.ref(Path(b.core.__file__)),'baseline_common_modules':b.ref(BASE),'source_semantic_field':'source metadata.owned_floor_regions by exact operation ID/material; no earth or AABB replacement','exact_numeric_contract':'source binary64 polygon coordinates treated as exact rationals for proof; common helper also must return zero uncovered area','cuts_supported':False,'non_axis_component_transforms_supported':False}}
 audit={'scope':KEY,'statistics':dict(stats),'accepted_actual_faces':len(faces),'accepted_patches':len(patches),'supported_area_m2':sum((p['bounds_uv_m'][2]-p['bounds_uv_m'][0])*(p['bounds_uv_m'][3]-p['bounds_uv_m'][1]) for p in patches),'source_owners':len(owners),'face_coverage':coverage,'rejected_patches':rejected,'generated_outside_source_support_area_m2':0,'whole_asset_complete':False};return plan,audit,pdeps

def build(audit_only=False):
 start=time.perf_counter();plan,audit,pdeps=make_plan();base=read(BASE);known={r['id']:r for r in base['modules']};new=[d for d in plan['module_demand'] if d['id'] not in known];info={'faces':len(plan['assets'][0]['faces']),'placements':len(plan['assets'][0]['placements']),'demand':len(plan['module_demand']),'new_trim_modules':len(new),'supported_area_m2':audit['supported_area_m2'],'rejected_patches':len(audit['rejected_patches'])}
 if audit_only:print(json.dumps(info));return
 frozen={str(p.relative_to(R)):sha(p) for p in [b.IP,BASE,Path(a.polygons.__file__),Path(b.core.__file__),Path(a.edge.__file__),Path(a.common.__file__),a.HERE/'author_r03.py']};frozen.update(pdeps);asset=plan['assets'][0]
 for name in ['master','render']:frozen[asset['source_'+name+'_path']]=asset['source_'+name+'_sha256']
 rows=[];safe=read(b.U/'surface_modules/inputs/safe_offset_rules.v1.json');geom=0
 for d in plan['module_demand']:
  if d['id'] in known:
   row=known[d['id']];assert all(row[k]==d[k] for k in ['kind','seed','trim']);rows.append(copy.deepcopy(row))
   for k in ['master','render']:frozen[row[k+'_path']]=row[k+'_sha256']
  else:
   assert d['trim']!={'width_m':1.0,'height_m':1.0,'offset_m':[0.0,0.0]};spec=copy.deepcopy(safe);spec['trim']=d['trim'];master,c,render,contract,checks=a.edge.compile_exact_crop(spec,d['kind'],d['seed'],boundary_quantum_m=P);mp=CAT.parent/(d['id']+'.master.json');rp=CAT.parent/(d['id']+'.render.json');mb=a.common.payload(master);rb=a.common.payload(render);geom+=len(mb)+len(rb);assert b.output_bytes()+len(mb)+len(rb)<b.LIMIT-1_500_000;a.common.write_exact(mp,mb);a.common.write_exact(rp,rb)
   rows.append({**d,'master_path':str(mp.relative_to(R)),'master_sha256':sha(mp),'render_path':str(rp.relative_to(R)),'render_sha256':sha(rp),'payload_hash':c['payload_hash'],'cells':len(c['cells']),'quads':render['quad_count'],'checks':checks})
 save(PLAN,plan);save(H/'source_application_audit.json',audit);catalog={'schema':base['schema'],'revision':'r04_extrusion_support_r01','source_plan_sha256':sha(PLAN),'modules':rows,'runtime_activation':False,'original_collision_unchanged':True,'source_dependencies':frozen};save(CAT,catalog);assert frozen=={p:sha(R/p) for p in frozen}
 result={'all_pass':True,**info,'new_geometry_bytes':geom,'module_rows_reused':len(rows)-len(new),'original_full_compiles':0,'source_plan':b.ref(PLAN),'module_catalog':b.ref(CAT),'source_application_audit':b.ref(H/'source_application_audit.json'),'source_dependencies':frozen,'all_dependencies_unchanged':True,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'runtime_promoted':False,'new_colliders':0};save(H/'build_report.json',result);assert b.output_bytes()<b.LIMIT;print(json.dumps({k:v for k,v in result.items() if k!='source_dependencies'}))
if __name__=='__main__':
 b.limits();ap=argparse.ArgumentParser();ap.add_argument('--audit-only',action='store_true');build(ap.parse_args().audit_only)
