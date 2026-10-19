"""Bounded r03: exact same-semantic box-union ownership for actual source quads.
Uses common polygon-union proof, existing native patches, and common exact crop.
No runtime binding or source edits; r01/r02 remain immutable dependencies.
"""
from pathlib import Path
import argparse,copy,hashlib,itertools,json,math,resource,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;N=HERE.parent;U=N.parent;R=U.parents[3];C=U.parents[1]
sys.path[:0]=[str(N),str(R),str(U/'surface_modules/edge_trims')]
import author_native_access as previous
import author_edge_trims as edge
from world_city.runtime_city.checks import placement as polygons
common=edge.common
P=.0125;LIMIT=5*1024*1024
PLAN=N/'generated/source_plan_r03.json';CAT=N/'generated/modules_r03/catalog_r03.json'
BASE_PLAN=N/'generated/source_plan_r02.json';BASE_CAT=N/'generated/modules_r01/catalog_r02.json'

def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,value):common.write_exact(p,common.payload(value))
def number(v):return type(v) in (int,float) and math.isfinite(v)
def strict_grid(v):
 if not number(v):raise ValueError('nonfinite_or_nonnumeric_coordinate')
 q=round(v/P);canonical=q*P
 # Only binary64 representation noise is accepted. No CAD expansion or half-pitch padding.
 if abs(v-canonical)>8*max(math.ulp(float(v)),math.ulp(float(canonical))):raise ValueError('unsupported_non_microgrid_coordinate')
 return q

def orient(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def intersects(a,b,c,d):
 o=[orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)]
 def on(p,x,y):return min(x[0],y[0])<=p[0]<=max(x[0],y[0]) and min(x[1],y[1])<=p[1]<=max(x[1],y[1])
 return (o[0]*o[1]<0 and o[2]*o[3]<0) or any(v==0 and on(p,x,y) for v,p,x,y in [(o[0],c,a,b),(o[1],d,a,b),(o[2],a,c,d),(o[3],b,c,d)])

def top_rectangle(q):
 if not isinstance(q,(list,tuple)) or len(q)!=4 or any(not isinstance(p,(list,tuple)) or len(p)!=3 or not all(number(v) for v in p) for p in q):raise ValueError('finite_numeric_quad_required')
 cells=[[strict_grid(v) for v in p] for p in q]
 if len({p[1] for p in cells})!=1:raise ValueError('unsupported_nonhorizontal_quad')
 uv=[(p[0],-p[2]) for p in cells]
 if len(set(uv))!=4:raise ValueError('duplicate_or_degenerate_quad')
 if intersects(uv[0],uv[1],uv[2],uv[3]) or intersects(uv[1],uv[2],uv[3],uv[0]):raise ValueError('self_intersecting_quad')
 lo=[min(p[i] for p in uv) for i in (0,1)];hi=[max(p[i] for p in uv) for i in (0,1)]
 if set(uv)!={(x,y) for x in (lo[0],hi[0]) for y in (lo[1],hi[1])}:raise ValueError('unsupported_nonrectangle_quad')
 if any((a[0]!=b[0])+(a[1]!=b[1])!=1 for a,b in zip(uv,uv[1:]+uv[:1])):raise ValueError('invalid_perimeter_edge')
 # The XY/+Z source frame uses u=X,v=-Z: both original triangles must face +Y.
 if orient(uv[0],uv[1],uv[2])<=0 or orient(uv[0],uv[2],uv[3])<=0:raise ValueError('downward_or_inconsistent_triangle_winding')
 return lo+hi

def polygon(rect):
 x0,y0,x1,y1=rect;return [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]

def union_proof(subject,covers):
 """Exact integer boundary partition + unchanged common finite polygon union.
 Not occupancy sampling: intervals split only at source box/quad boundaries.
 """
 if len(subject)!=4 or any(type(v)!=int for v in subject) or subject[0]>=subject[2] or subject[1]>=subject[3]:raise ValueError('positive_integer_rectangle_required')
 clipped=[]
 for r in covers:
  if len(r)!=4 or any(type(v)!=int for v in r) or r[0]>=r[2] or r[1]>=r[3]:raise ValueError('positive_integer_cover_required')
  a,b,c,d=max(subject[0],r[0]),max(subject[1],r[1]),min(subject[2],r[2]),min(subject[3],r[3])
  if a<c and b<d:clipped.append([a,b,c,d])
 if len(clipped)>128:raise ValueError('owner_union_budget_exceeded')
 xs=sorted({subject[0],subject[2],*[r[i] for r in clipped for i in (0,2)]});ys=sorted({subject[1],subject[3],*[r[i] for r in clipped for i in (1,3)]})
 if (len(xs)-1)*(len(ys)-1)>4096:raise ValueError('owner_partition_budget_exceeded')
 uncovered=0;missing=[]
 for a,c in zip(xs,xs[1:]):
  for b,d in zip(ys,ys[1:]):
   # Integer doubled midpoints are exact on each constant-membership atomic region.
   if not any(2*r[0]<=a+c<=2*r[2] and 2*r[1]<=b+d<=2*r[3] for r in clipped):uncovered+=(c-a)*(d-b);missing.append([a,b,c,d])
 common_uncovered=polygons.uncovered_area_by_union(polygon(subject),[polygon(r) for r in clipped],0)
 if common_uncovered!=uncovered:raise ValueError('common_union_and_integer_partition_disagree')
 area=(subject[2]-subject[0])*(subject[3]-subject[1]);covered=area-uncovered
 return {'supported':uncovered==0 and bool(clipped),'subject_uv_integer_cells':subject,'clipped_owner_rectangles':clipped,'subject_area_cells2':area,'union_covered_area_cells2':covered,'uncovered_area_cells2':uncovered,'uncovered_rectangles':missing,'source_owner_overlap_cells2':sum((r[2]-r[0])*(r[3]-r[1]) for r in clipped)-covered,'common_uncovered_area_cells2':common_uncovered,'boundary_partition_cells':(len(xs)-1)*(len(ys)-1),'geometric_tolerance_m':0.0,'method':'unchanged_common_polygon_union_plus_exact_integer_boundary_partition'}

def source_boxes(master,rule):
 if master.get('assembly_cuts'):raise ValueError('unsupported_assembly_cut_ownership')
 result=[]
 for inst,op,tr in previous.source_parts(master):
  if inst['component'] not in rule['source_components']:continue
  if op.get('action')!='paint' or op.get('material')!=rule['material'] or op.get('shape',{}).get('kind')!='box':raise ValueError('unsupported_semantic_source_operation')
  if tr['basis']!=[[1,0,0],[0,1,0],[0,0,1]]:raise ValueError('unsupported_rotated_source_component_box')
  s=op['shape'];lo=[s['min'][i]+tr['translation'][i] for i in range(3)];hi=[s['max'][i]+tr['translation'][i] for i in range(3)]
  l=[strict_grid(v) for v in lo];h=[strict_grid(v) for v in hi]
  if any(a>=b for a,b in zip(l,h)):raise ValueError('nonpositive_source_box')
  result.append({'instance':inst['id'],'component':inst['component'],'operation':op['id'],'material':op['material'],'part':op.get('part',''),'min':lo,'max':hi,'operation_sha256':digest(op),'top_y_integer_cells':h[1],'rect_uv_integer_cells':[l[0],-h[2],h[0],-l[2]],'semantic_key':[inst['id'],inst['component'],op['material'],op.get('part','')]})
 return result

def ownership(rect,y,boxes):
 groups={}
 for box in boxes:
  if box['top_y_integer_cells']==y:groups.setdefault(tuple(box['semantic_key']),[]).append(box)
 matches=[]
 for semantics,owners in groups.items():
  usable=[b for b in owners if min(rect[2],b['rect_uv_integer_cells'][2])>max(rect[0],b['rect_uv_integer_cells'][0]) and min(rect[3],b['rect_uv_integer_cells'][3])>max(rect[1],b['rect_uv_integer_cells'][1])]
  proof=union_proof(rect,[b['rect_uv_integer_cells'] for b in usable])
  if proof['supported']:matches.append({'semantic_key':list(semantics),'owners':usable,'proof':proof})
 if len(matches)!=1:raise ValueError('no_unique_complete_same_semantic_owner_union')
 return matches[0]

def plan():
 policy=read(N/'source_policy.json');ip=C/'playable_r01/generated/tile_r01/index.json';index=read(ip);old=read(BASE_PLAN);assert sha(ip)==policy['source_city_index_sha256']==old['source_city_index_sha256']
 out=copy.deepcopy(old);out['revision']='r03';out['assets']=[];demand={d['id']:d for d in old['module_demand']};changes=[]
 for prior in old['assets']:
  key=prior['asset_key'];rule=policy['assets'][key];src=index['common_assets'][key];assert sha(R/src['master_path'])==src['master_sha256']==prior['source_master_sha256'];assert sha(R/src['render_path'])==src['render_sha256']==prior['source_render_sha256']
  master=read(R/src['master_path']);render=read(R/src['render_path']);boxes=source_boxes(master,rule);faces=[];placements=[];excluded={};prior_refs={(f['group_index'],f['quad_index']) for f in prior['faces']}
  for gi,g in enumerate(render['groups']):
   if g['material']!=rule['material']:continue
   for qi,q in enumerate(g['quads']):
    try:rect=top_rectangle(q);own=ownership(rect,strict_grid(q[0][1]),boxes)
    except ValueError as e:excluded[str(e)]=excluded.get(str(e),0)+1;continue
    f={'group_index':gi,'quad_index':qi,'quad_sha256':digest(q),'quad':q,'rect_uv_integer_cells':rect,'plane_y_m':q[0][1],'operation_owners':own['owners'],'semantic_owner_union':own['proof'],'semantic_key':own['semantic_key']};faces.append(f)
    for patch in previous.patches(rect):
     trim=patch['trim'];kind=rule['kind'];seed=patch['seed'];token=kind+'_'+str(seed)+'_'+digest(trim)[:12];demand[token]={'id':token,'kind':kind,'seed':seed,'trim':trim}
     tr={'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[patch['low_uv'][0],q[0][1]+policy['maximum_visual_offset_m'],-patch['low_uv'][1]]}
     placements.append({'module_key':token,'transform':tr,'source_face_ref':[gi,qi],'source_face_sha256':f['quad_sha256'],'bounds_uv_m':patch['low_uv']+patch['high_uv'],'source_plane_y_m':q[0][1],'collision_changed':False})
  lookup={(f['group_index'],f['quad_index']):f for f in faces};assert prior_refs<=set(lookup),'r03 must preserve every existing selected face'
  previous_placements=[p for p in placements if tuple(p['source_face_ref']) in prior_refs];assert previous_placements==prior['placements'],'r02 placements must remain exactly identical'
  a=copy.deepcopy(prior);a.update(faces=faces,placements=placements,excluded=excluded);out['assets'].append(a)
  changes.append({'asset_key':key,'previous_faces':len(prior['faces']),'faces':len(faces),'previous_placements':len(prior['placements']),'placements':len(placements),'previous_placements_sha256':digest(prior['placements']),'preserved_placements_sha256':digest(previous_placements),'new_faces':[f for ref,f in lookup.items() if ref not in prior_refs]})
 out['module_demand']=list(demand.values());out['r03_provenance']={'parent_plan_path':str(BASE_PLAN.relative_to(R)),'parent_plan_sha256':sha(BASE_PLAN),'parent_module_catalog_path':str(BASE_CAT.relative_to(R)),'parent_module_catalog_sha256':sha(BASE_CAT),'author_path':str(Path(__file__).relative_to(R)),'author_sha256':sha(Path(__file__)),'source_shape_policy':'same semantic instance/component/material/part and exact coplanar box tops only; no cuts or rotated component boxes','union_helper':str(Path(polygons.__file__).relative_to(R)),'union_helper_sha256':sha(Path(polygons.__file__)),'numeric_grid_policy':'declared .0125m source grid with <=8 binary64 ULP representation normalization, never half-pitch or CAD expansion','source_geometry_changed':False,'runtime_catalog_changed':False}
 return out,changes

def build():
 start=time.perf_counter();out,changes=plan();base=read(BASE_CAT);previous_modules={m['id']:m for m in base['modules']};new_demands=[d for d in out['module_demand'] if d['id'] not in previous_modules]
 assert len(previous_modules)==75 and len(new_demands)<=30,'bounded incremental module scope exceeded'
 frozen_paths=[BASE_PLAN,BASE_CAT,N/'generated/source_plan.json',N/'generated/modules_r01/catalog.json',N/'author_native_access.py',N/'source_policy.json',R/'voxel_character/common/core.py',R/'voxel_character/common/render_data.py',Path(edge.__file__),Path(common.__file__),Path(polygons.__file__),C/'playable_detail_r01/native_access_catalog.json']
 frozen_paths.extend(R/m[k] for m in base['modules'] for k in ['master_path','render_path'])
 frozen={str(p.relative_to(R)):sha(p) for p in frozen_paths}
 for m in base['modules']:
  assert sha(R/m['master_path'])==m['master_sha256'] and sha(R/m['render_path'])==m['render_sha256']
 safe_path=U/'surface_modules/inputs/safe_offset_rules.v1.json';safe=read(safe_path);rows=copy.deepcopy(base['modules']);new_bytes=0;compiled_count=0;shared_reused=0
 shared_dir=U/'surface_modules/generated_safe';shared_manifest_path=shared_dir/'manifest.json';shared=read(shared_manifest_path);frozen[str(safe_path.relative_to(R))]=sha(safe_path);frozen[str(shared_manifest_path.relative_to(R))]=sha(shared_manifest_path)
 for d in new_demands:
  spec=copy.deepcopy(safe);spec['trim']=d['trim'];mp=CAT.parent/(d['id']+'.master.json')
  if d['trim']=={'width_m':1.0,'height_m':1.0,'offset_m':[0.0,0.0]}:
   # Existing exact full 1m common render: materialize only its deterministic master,
   # verify the published master digest, and reuse render bytes without compiling.
   candidates=[r for r in shared['modules'] if r['kind']==d['kind'] and r['seed']==d['seed']];assert len(candidates)==1
   prior=candidates[0];master,_=common.author(spec,d['kind'],d['seed']);assert common.digest(master)==prior['master_hash']
   name=prior['placement_contract']['render_file'];rp=shared_dir/name;assert sha(rp)==prior['files'][name]['sha256'];frozen[str(rp.relative_to(R))]=sha(rp)
   mb=common.payload(master);common.write_exact(mp,mb);new_bytes+=len(mb);shared_reused+=1
   rows.append({**d,'render_path':str(rp.relative_to(R)),'render_sha256':sha(rp),'master_path':str(mp.relative_to(R)),'master_sha256':sha(mp),'payload_hash':prior['payload_hash'],'cells':prior['cells'],'quads':prior['quads'],'checks':prior['checks'],'reuse_existing_common_render':True})
  else:
   master,c,render,contract,checks=edge.compile_exact_crop(spec,d['kind'],d['seed'],boundary_quantum_m=P)
   rp=CAT.parent/(d['id']+'.render.json');rb=common.payload(render);mb=common.payload(master);new_bytes+=len(rb)+len(mb);assert new_bytes<LIMIT
   common.write_exact(rp,rb);common.write_exact(mp,mb);compiled_count+=1
   rows.append({**d,'render_path':str(rp.relative_to(R)),'render_sha256':sha(rp),'master_path':str(mp.relative_to(R)),'master_sha256':sha(mp),'payload_hash':c['payload_hash'],'cells':len(c['cells']),'quads':render['quad_count'],'checks':checks})
 save(PLAN,out);catalog=copy.deepcopy(base);catalog.update(source_plan_sha256=sha(PLAN),modules=rows,revision='r03',source_dependencies=frozen,runtime_activation=False,original_collision_unchanged=True);catalog['incremental_reuse']={'previous_catalog_sha256':sha(BASE_CAT),'existing_modules_reused_byte_identical':75,'new_modules':len(new_demands),'new_trim_modules_compiled':compiled_count,'additional_existing_common_renders_reused':shared_reused,'new_geometry_bytes':new_bytes};save(CAT,catalog)
 assert frozen=={p:sha(R/p) for p in frozen},'immutable dependencies changed during r03 build'
 report={'all_pass':True,'changes':changes,'reused_modules':75,'new_modules':len(new_demands),'new_trim_modules_compiled':compiled_count,'additional_existing_common_renders_reused':shared_reused,'total_modules':len(rows),'new_geometry_bytes':new_bytes,'source_plan_path':str(PLAN.relative_to(R)),'source_plan_sha256':sha(PLAN),'module_catalog_path':str(CAT.relative_to(R)),'module_catalog_sha256':sha(CAT),'source_dependencies':frozen,'all_previous_dependencies_unchanged':True,'runtime_catalog_unchanged':True,'seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 save(HERE/'build_report.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['changes','source_dependencies']}));return report
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--audit-only',action='store_true');args=ap.parse_args()
 if args.audit_only:
  p,changes=plan();base=read(BASE_CAT);ids={m['id'] for m in base['modules']};print(json.dumps({'assets':[{k:v for k,v in c.items() if k!='new_faces'} for c in changes],'new_modules':[d for d in p['module_demand'] if d['id'] not in ids]},indent=2))
 else:build()
