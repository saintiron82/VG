"""Twelve conservative source-supported crops, using the unchanged common pipeline.
Run only after the shared sampling slot is released. No production binding.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse,collections,copy,json,math,os,resource,subprocess,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import prepare as p
a=p.a;b=p.b;e=p.e;R=p.R;P=p.P

def limit():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
 resource.setrlimit(resource.RLIMIT_CPU,(60,)*2)
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def compile_conservative_crop(spec,seed,allowed_runs,cut_rectangles):
 """Generic mask -> ordinary assembly cuts. No occupancy filtering or mesher."""
 allowed=p.expand(allowed_runs);cuts=p.expand(cut_rectangles)
 assert not allowed.intersection(cuts) and allowed|cuts=={(x,y)for x in range(80)for y in range(80)}
 assert sum((r[2]-r[0])*(r[3]-r[1])for r in cut_rectangles)==len(cuts),'cut interiors overlap'
 master,contract=a.edge.author_exact_crop(spec,'paving',seed,boundary_quantum_m=P)
 original_components=copy.deepcopy(master['components']);mask_hash=p.digest(allowed_runs)
 master['id']+='_safe_cells_'+mask_hash[:12]
 master['extensions']['shared_surface']['source_support_mask_sha256']=mask_hash
 master['extensions']['shared_surface']['source_support_policy']='Entire exported cell footprint inside exact allowed source union; standard common assembly cuts only.'
 for i,r in enumerate(cut_rectangles):
  cut=a.common.box('source_footprint_crop_%03d'%i,[r[0]*P,r[1]*P,-.0375],[r[2]*P,r[3]*P,.0125],None,action='cut')
  master['assembly_cuts'].append({'id':cut['id'],'shape':cut['shape'],'selector':{}})
 assert master['components']==original_components
 ox,oy=spec['trim']['offset_m'];w=spec['trim']['width_m'];h=spec['trim']['height_m']
 bounds={'min':[round(ox/P),round(oy/P),-3],'max':[round((ox+w)/P),round((oy+h)/P),0]}
 compiled=a.common.compile_master(master,{'pitch':P},cell_bounds=bounds,max_candidate_cells=spec['budgets']['max_candidate_cells_per_module'],max_output_cells=spec['budgets']['max_output_cells_per_module'])
 xy={(r[0],r[1])for r in compiled['cells']}
 assert xy==allowed,'Common compiled footprint must exactly equal the proved mask, including joint backing'
 frame=dict(compiled,grid_origin=[-ox,-oy,0]);render=a.common.make_render_data(frame)
 render['provenance'].update({'source_compile_grid_origin':[0,0,0],'evaluation_scope':compiled['evaluation_scope'],'global_constraints_evaluated':False,'master_to_render_translation_m':[-ox,-oy,0],'source_support_mask_sha256':mask_hash})
 contract['module_id']=master['id'];contract['render_file']=master['id']+'.render.json'
 contract['collision']['reference_prisms']=[{'min':[r[0]*P-ox,r[1]*P-oy,-.1],'max':[r[2]*P-ox,r[3]*P-oy,0]}for r in allowed_runs]
 checks=a.common.validate_geometry(spec,frame,render,contract)
 return master,compiled,render,checks

def exterior_proof(compiled,render):
 """Independently expand common greedy quads into exact occupancy boundary faces."""
 cells={tuple(r[:3])for r in compiled['cells']};expected=set()
 for cell in cells:
  for axis in range(3):
   for sign in [-1,1]:
    other=list(cell);other[axis]+=sign
    if tuple(other)in cells:continue
    plane=cell[axis]+(sign>0);axes=[j for j in range(3)if j!=axis];expected.add((axis,sign,plane,cell[axes[0]],cell[axes[1]]))
 actual=set();wrong=zero=0;triangles=0
 for group in render['groups']:
  for q in group['quads']:
   ints=[[round((v[i]-render['grid_origin'][i])/P)for i in range(3)]for v in q]
   assert all(v[i]==render['grid_origin'][i]+k[i]*P for v,k in zip(q,ints)for i in range(3))
   u=[ints[1][i]-ints[0][i]for i in range(3)];v=[ints[2][i]-ints[0][i]for i in range(3)];n=a.previous.cross(u,v);nonzero=[i for i in range(3)if n[i]];assert len(nonzero)==1;axis=nonzero[0];sign=1 if n[axis]>0 else -1;plane=ints[0][axis];axes=[i for i in range(3)if i!=axis]
   for x in range(min(v[axes[0]]for v in ints),max(v[axes[0]]for v in ints)):
    for y in range(min(v[axes[1]]for v in ints),max(v[axes[1]]for v in ints)):
     face=(axis,sign,plane,x,y);assert face not in actual;actual.add(face)
   for order in [[0,2,1],[0,3,2]]:
    tri=[q[i]for i in order];u=[tri[1][i]-tri[0][i]for i in range(3)];v=[tri[2][i]-tri[0][i]for i in range(3)];c=a.previous.cross(u,v);triangles+=1;zero+=not any(c);wrong+=sum(c[i]*n[i]for i in range(3))>=0
 assert actual==expected and zero==wrong==0
 return {'all_pass':True,'exposed_unit_faces':len(expected),'missing_exterior_faces':0,'duplicate_exterior_faces':0,'internal_faces_emitted':0,'wrong_clockwise_triangles':0,'degenerate_triangles':0,'closed_occupancy_boundary':True,'triangles_before_common_back_omission':triangles}

def source_proof(item,old,owners,actual):
 polys=[e.fp(o['polygon_uv_m'])for o in owners if o['operation']in item['source_owner_operation_ids']];quad=e.fp([[v[0],-v[2]]for v in item['source_quad']]);outside=F(0)
 tested=0;maximum_roundtrip=0
 # Each full row run is the union of consecutive exported cell footprints.
 # Exact run coverage therefore proves every constituent compiled cell.
 for x,y,z,w in item['allowed_cell_runs_xy']:
  first=p.cell_rect(item,x,y);last=p.cell_rect(item,z-1,w-1);rect=[*first[:2],*last[2:]];poly=p.rectpoly(rect)
  assert e.exact_union(poly,polys)==0 and e.exact_union(poly,[quad])==0
  assert a.polygons.uncovered_area_by_union([[float(v)for v in q]for q in poly],[[[float(v)for v in q]for q in s]for s in polys],0)==0
  assert all(not p.intersects(rect,r['bounds_uv_m'])for r in old)
  for position,yaw in [(actual['position_m'],actual.get('yaw_rad',0)),([-213.5,14.1,-321.75],.37),([-213.5,14.1,-321.75],-2.194336547087899),([-213.5,14.1,-321.75],math.pi/2)]:
   for u,v in poly:
    local=[float(u),0,-float(v)];world=a.polygons.transform_point_m(local,position,yaw);back=a.polygons.inverse_transform_point_m(world,position,yaw);error=max(abs(back[i]-local[i])for i in range(3));assert error<1e-12;maximum_roundtrip=max(maximum_roundtrip,error);tested+=1
 assert item['source_plane_y_m']==0
 return {'all_pass':True,'whole_footprint_cells_proven':item['allowed_horizontal_cells'],'whole_row_runs_replayed':len(item['allowed_cell_runs_xy']),'actual_quad_union_uncovered_area_m2':0,'walk_union_uncovered_area_m2':0,'previous_detail_overlap_area_m2':0,'support_tolerance_m':0,'actual_and_rotated_negative_position_corners':tested,'maximum_roundtrip_error_m':maximum_roundtrip,'rotated_support_argument':'Same proper rigid owner transform maps the proved footprint and source region; roundtrip diagnostic does not enlarge the exact local support.'}

def fixtures():
 cases=[]
 def check(name,condition):assert condition,name;cases.append({'name':name,'pass':True})
 # A centroid inside a diagonal source polygon does not license its corners.
 triangle=e.fp([[0,0],[1,0],[0,1]])
 check('centroid_inside_but_footprint_crosses_diagonal_rejected',p.point_in([F(2,5),F(2,5)],triangle) and not p.safe_cell([F(1,5),F(1,5),F(3,5),F(3,5)],[triangle])[0])
 left=e.fp([[0,0],[.5,0],[.5,1],[0,1]]);right=e.fp([[.5,0],[1,0],[1,1],[.5,1]])
 check('shared_seam_whole_footprint_accepted',p.safe_cell([F(1,4),F(1,4),F(3,4),F(3,4)],[left,right])[0])
 notch=[e.fp([[0,0],[1,0],[1,.4],[0,.4]]),e.fp([[0,0],[.4,0],[.4,1],[0,1]])]
 check('concave_missing_corner_rejected',not p.safe_cell([F(0),F(0),F(1),F(1)],notch)[0])
 ring=[e.fp(p.rectpoly(r))for r in [[0,0,1,.4],[0,.6,1,1],[0,.4,.4,.6],[.6,.4,1,.6]]]
 check('internal_hole_rejected_even_when_four_corners_inside',all(any(p.point_in(q,s)for s in ring)for q in e.fp([[0,0],[1,0],[1,1],[0,1]])) and not p.safe_cell([F(0),F(0),F(1),F(1)],ring)[0])
 delta=F(1,10**12);narrow=[[[F(0),F(0)],[1-delta,F(0)],[1-delta,F(1)],[F(0),F(1)]]]
 check('sub_epsilon_positive_outside_is_rejected',not p.safe_cell([F(0),F(0),F(1),F(1)],narrow)[0])
 negative=e.fp([[-2,-2],[-1,-2],[-1,-1],[-2,-1]])
 check('negative_coordinates_supported',p.safe_cell([F(-2),F(-2),F(-1),F(-1)],[negative])[0])
 check('empty_original_support_rejected',not p.safe_cell([F(0),F(0),F(1),F(1)],[])[0])
 for name,basis in [('reflection',[[-1,0,0],[0,1,0],[0,0,1]]),('shear',[[1,.1,0],[0,1,0],[0,0,1]])]:
  rejected=False
  try:a.common.validate_placement([0,0,0],basis)
  except ValueError:rejected=True
  check(name+'_placement_rejected',rejected)
 return {'all_pass':True,'tests':len(cases),'results':cases}

def build(expected):
 start=time.monotonic();limit();data=p.read(H/'prepared_inputs.json');assert p.sha(H/'prepared_inputs.json')==expected;assert data['status']=='SOURCE_PREPARED_NO_SAMPLING';assert data['author']==p.ref(H/'prepare.py');deps=data['source_dependencies'];assert all(p.sha(R/k)==v for k,v in deps.items())
 remaining=60-data['summary']['elapsed_seconds'];assert remaining>0;deadline=start+remaining
 def budget():assert time.monotonic()<deadline,'Combined source preparation plus generation exceeded 60 seconds'
 oldplan=p.read(p.E/'source_plan.json');asset=oldplan['assets'][0];master=p.read(R/asset['source_master_path']);owners=e.source_caps(master,asset['rule']);safe=p.read(b.U/'surface_modules/inputs/safe_offset_rules.v1.json');modules=[];placements=[];reports=[];bytes_written=0;allcells=set()
 p.save(H/'validation/fixtures.json',fixtures())
 for item in data['selected_patches']:
  budget();source=source_proof(item,asset['placements'],owners,asset['actual_instances'][0]['instance']);spec=copy.deepcopy(safe);spec['trim']=item['trim'];m,c,r,checks=compile_conservative_crop(spec,item['seed'],item['allowed_cell_runs_xy'],item['common_cut_rectangles_xy']);closed=exterior_proof(c,r);token=item['id'];mp=H/'modules'/(token+'.master.json');rp=H/'modules'/(token+'.render.json');mb=a.common.payload(m);rb=a.common.payload(r);bytes_written+=len(mb)+len(rb);assert bytes_written<=8*1024*1024;a.common.write_exact(mp,mb);a.common.write_exact(rp,rb)
  for x,y in {(v[0],v[1])for v in c['cells']}:
   coord=(item['grid_xy_m'][0]*80+x,item['grid_xy_m'][1]*80+y);assert coord not in allcells;allcells.add(coord)
  modules.append({'id':token,'kind':'paving','seed':item['seed'],'trim':item['trim'],'master_path':str(mp.relative_to(R)),'master_sha256':p.sha(mp),'render_path':str(rp.relative_to(R)),'render_sha256':p.sha(rp),'payload_hash':c['payload_hash'],'cells':len(c['cells']),'quads':r['quad_count'],'source_support_mask_sha256':p.digest(item['allowed_cell_runs_xy']),'checks':checks})
  placements.append({'module_key':token,'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[item['bounds_uv_m'][0],.0375,-item['bounds_uv_m'][1]]},'bounds_uv_m':item['bounds_uv_m'],'source_plane_y_m':0,'source_face_ref':item['source_face_ref'],'source_face_sha256':item['source_face_sha256'],'source_support_mask_sha256':p.digest(item['allowed_cell_runs_xy']),'partial_footprint':True,'source_proof_ref':{'prepared_inputs':p.ref(H/'prepared_inputs.json'),'patch_id':token},'collision_changed':False})
  reports.append({'id':token,'source':source,'boundary':closed,'compiled_cells':len(c['cells']),'horizontal_footprint_cells':len({(r[0],r[1])for r in c['cells']}),'quads':r['quad_count'],'geometry_bytes':len(mb)+len(rb)});print(json.dumps({'id':token,'elapsed_seconds':time.monotonic()-start,'new_geometry_bytes':bytes_written}),flush=True)
 budget();selected={k:copy.deepcopy(asset[k])for k in ['asset_key','source_master_path','source_master_sha256','source_render_path','source_render_sha256','source_pitch_m','rule','actual_instances','existing_collision_unchanged','source_collision_baseline']};selected.update({'placements':placements,'status':'PARTIAL_BOUNDARY_CROP_PROOF_CANDIDATE','original_remaining_surfaces_unchanged':True,'full_source_proof':p.ref(H/'prepared_inputs.json')})
 plan={'schema':oldplan['schema'],'revision':'r06_training_partial_crop_12_r01','source_city_index_sha256':oldplan['source_city_index_sha256'],'assets':[selected],'maximum_additional_visual_offset_from_source_m':.0375,'runtime_activation':False,'provenance':{'author':p.ref(Path(__file__)),'source_preparation':p.ref(H/'prepared_inputs.json'),'usage':'Proof-only 12 additions, disjoint from existing 347.25m2. Any full training revision must replace/repartition the old plan, not stack overlapping patches.'}}
 pp=H/'source_plan.json';cp=H/'modules/catalog.json';p.save(pp,plan);p.save(cp,{'schema':'riverstone.native_access_detail.module_catalog.v1','revision':'r06_training_partial_crop_12_r01','source_plan_sha256':p.sha(pp),'modules':modules,'source_dependencies':deps,'original_collision_unchanged':True,'runtime_activation':False})
 # Use unchanged shared Godot mesh helper tests, without a production World.
 env={**os.environ,'REPO_ROOT':str(R),'SOURCE_PLAN':str(pp),'MODULE_CATALOG':str(cp),'OUTPUT_REPORT':str(H/'validation/godot_mesh_report.json'),'XDG_DATA_HOME':str(H/'xdg_data'),'XDG_CACHE_HOME':str(H/'xdg_cache'),'XDG_CONFIG_HOME':str(H/'xdg_config')}
 with (H/'validation/godot_mesh.log').open('w')as log:proc=subprocess.run(['godot','--headless','--path',str(H/'mesh_validation'),'--script','res://verify.gd'],env=env,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=max(.1,deadline-time.monotonic()),preexec_fn=limit)
 assert proc.returncode==0 and p.read(H/'validation/godot_mesh_report.json')['all_pass'];budget();assert all(p.sha(R/k)==v for k,v in deps.items())
 result={'all_pass':True,'source_preparation':p.ref(H/'prepared_inputs.json'),'source_plan':p.ref(pp),'module_catalog':p.ref(cp),'modules':reports,'new_geometry_bytes':bytes_written,'source_preparation_seconds':data['summary']['elapsed_seconds'],'generation_verification_seconds':time.monotonic()-start,'combined_unit_seconds':data['summary']['elapsed_seconds']+time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'godot_peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'address_space_limit_bytes':256*1024*1024,'source_dependencies_unchanged':True,'original_nonroof_or_source_groups_changed':False,'existing_detail_overlap_area_m2':0,'duplicate_footprint_cells':0,'entire_result_cell_footprints_inside_original_support':True,'occupancy_post_filter_used':False,'new_colliders':0,'runtime_bound':False,'area_accounting':data['summary']};p.save(H/'validation/build_report.json',result);print(json.dumps({k:v for k,v in result.items()if k not in ['modules','area_accounting']}),flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prepared-sha256',required=True);args=ap.parse_args()
 try:build(args.prepared_sha256)
 except Exception as ex:
  p.save(H/'validation/build_failure.json',{'all_pass':False,'type':type(ex).__name__,'message':str(ex),'candidate_not_promoted':True});raise
