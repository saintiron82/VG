"""Bounded common compile, causal regression, context contact and camera residuals."""
from review_surface import *
from core import contains,inverse

def compile_one(ma,pitch=.025):
 count=candidate_count(ma,pitch)
 if count>A['budget']['candidate_cells_ceiling']:raise ValueError('Preflight candidate budget exceeded')
 co=compile_master(ma,{'pitch':pitch},max_candidate_cells=A['budget']['candidate_cells_ceiling'],max_output_cells=20000);return co,make_render_data(co)
def cells(co):return {tuple(q[:3]) for q in co['cells']}
def operations(ma):return {o['id']:o for o in ma['components'][0]['operations']}
def contact(a,b,pitch,root_ymin):
 aa,bb=cells(a),cells(b);touch=[]
 for p in aa:
  if p in bb or any(tuple(p[k]+(d if k==j else 0) for k in range(3)) in bb for j in range(3) for d in [-1,1]):touch.append(p)
 root=[p for p in touch if (p[1]+.5)*pitch>=root_ymin]
 return {'overlap_cells':len(aa&bb),'six_neighbor_or_overlap_cells':len(touch),'root_local_contact_cells':len(root),'root_ymin_m':root_ymin,'contact_cells':touch}

def parent_validation(ma,v,f):
 p=ROOT/'full01/generated/volume_master_v03.json.gz';vol=gzread(p);parent=copy.deepcopy(vol);parent['components'][0]['operations']=[o for o in parent['components'][0]['operations'] if o['part']=='torso_closed'];parent['constraints']=[{'id':'nonempty','kind':'nonempty','minimum_cells':1}]
 # Existing parent is an earlier failed coarse character body, not an approved attachment target.
 rootbox=A['views']['front']['root_search_box'];uv=np.c_[v[:,0]/SCALE+F['axis_u'],F['sole_y']-v[:,1]/SCALE];inroot=(uv[:,0]>=rootbox[0])&(uv[:,0]<=rootbox[2])&(uv[:,1]>=rootbox[1])&(uv[:,1]<=rootbox[3]);rootnodes=v[inroot];inside=0
 for pt in rootnodes:
  if any(contains(prepare_shape(o['shape'],.025),inverse(transform(o.get('transform')),pt.tolist()),epsilon=1e-10) for o in parent['components'][0]['operations']):inside+=1
 pc=compile_master(parent,{'pitch':.025},max_candidate_cells=120000,max_output_cells=20000)
 return pc,{'parent_path':str(p.relative_to(REPO)),'parent_sha256':sha(p),'part':'torso_closed','status':'unchanged full01 measured coarse context, not anatomical/art approval','observed_root_status':'glove/bouquet/waist root unknown in image; no newly fabricated connector','root_surface_vertices_tested':len(rootnodes),'root_mid_surface_vertices_inside_parent':inside,'negative_vertex_test_does_not_prove_full_prism_disjoint':True},(F['sole_y']-rootbox[3])*SCALE

def geometry_delta(a,b):
 aa=operations(a);bb=operations(b);changed=[key for key in set(aa)|set(bb) if aa.get(key)!=bb.get(key)];return {'changed_operation_count':len(changed),'changed_parts':sorted({(aa.get(k) or bb[k])['part'] for k in changed}),'ids_digest':digest(sorted(changed))}

def run():
 t=time.monotonic();m,a=load_measurement();ma=gzread(BASE/'generated/panel_master.json.gz');mm,aa=extract(SOURCE);fresh,v,f,fit=build(mm,aa,SOURCE);re,rv,rf,rfit=build(m,a,SOURCE);assert ma==fresh==re and np.array_equal(v,rv) and np.array_equal(f,rf)
 co,r=compile_one(ma);co2,r2=compile_one(ma);assert co==co2 and r==r2;gzwrite(BASE/'generated/common25.cells.json.gz',co);gzwrite(BASE/'generated/common25.render.json.gz',r);stats,pred=metrics(r,a);view,cam=view_sheet(r,'CONTINUOUS05: actual common25mm | no filling, deletion, new connector or increased thickness');view.save(BASE/'generated/common25_four_views.jpg',quality=90);overlays(a,pred,'COMMON25mm FIXED GRID').save(BASE/'generated/common25_overlay.jpg',quality=92)
 pc,pcinfo,rooty=parent_validation(ma,v,f);pcinfo.update(contact(co,pc,.025,rooty));struct=components(co['cells']);gzwrite(BASE/'evidence/parent_contact.json.gz',pcinfo)
 regression={}
 for name,box in [('front_boundary',A['regression']['front_boundary_patch_xyxy']),('unrelated_face',[315,185,320,190])]:
  mutant=SOURCE.copy();xa,ya,xb,yb=box;mutant[ya:yb,xa:xb]=A['regression']['fixture_rgb'];nm,na=extract(mutant);nb,nv,nf,nfit=build(nm,na,mutant);delta=geometry_delta(ma,nb);out={'pixel_recipe_xyxy':box,'pixel_recipe_rgb':A['regression']['fixture_rgb'],'source_pixel_digest':rawsha(mutant),'actual_changed_pixels':int(np.any(mutant!=SOURCE,2).sum()),'front_mask_changed_pixels':int((a['front_support']^na['front_support']).sum()),'other_views_measurement_arrays_exact':all(np.array_equal(aa[k],na[k]) for k in aa if not k.startswith('front_')),'approved_input_not_falsely_claimed':nb['extensions']['source_sha256'] is None and nb['extensions']['source_status']=='TEST_ONLY_pixel_mutation',**delta,'geometry_unchanged_expected':name=='unrelated_face','geometry_expectation_pass':bool(delta['changed_operation_count']==0) if name=='unrelated_face' else bool(delta['changed_operation_count']>0),'locality_scope':'one annotated front flap; global minimum-curvature solve may propagate inside this patch, never outside it'}
  if name=='front_boundary':
   nc,nr=compile_one(nb);out['voxel_occupancy_symmetric_difference']=len(cells(co)^cells(nc));out['projection_changed_pixels']={name:int((pred[name]^project_exact(nr,vw)).sum()) for name,vw in C['views'].items()};gzwrite(BASE/'evidence/mutant_geometry_digest.json.gz',{'master_geometry_digest':digest(operations(nb)),'input_pixel_sha256':rawsha(mutant),'surface_triangle_count':len(nf),'source_mask_digest':nm['arrays_digest'],'compiled_payload_digest':nc['payload_hash'],'not_approved_asset':True})
  regression[name]=out
 rejects={}
 try:build({},a,SOURCE);rejects['missing_measurement']=False
 except ValueError:rejects['missing_measurement']=True
 bad=copy.deepcopy(m);bad['dependencies'][0]['sha256']='0'*64
 try:build(bad,a,SOURCE);rejects['stale_annotation_dependency']=False
 except ValueError:rejects['stale_annotation_dependency']=True
 bad=SOURCE.copy();bad[0,0]=[0,0,0]
 try:build(m,a,bad);rejects['wrong_pixel_hash']=False
 except ValueError:rejects['wrong_pixel_hash']=True
 bad=copy.deepcopy(a);bad['side_support']=np.zeros_like(bad['side_support']);bm=copy.deepcopy(m);bm['arrays_digest']=digest({k:rawsha(v) for k,v in bad.items()})
 try:build(bm,bad,SOURCE);rejects['contradictory_empty_side_support']=False
 except ValueError as ex:rejects['contradictory_empty_side_support']=True;rejects['contradiction_message']=str(ex)
 yaw=[]
 for angle in A['surface_prior']['side_camera_yaw_hypotheses_deg']:
  vv,ff,fitangle=solve_surface(m,a,angle);sr=source_render(vv,ff,ma['materials']);st,_=metrics(sr,a);yaw.append({'yaw_hypothesis_deg':angle,'solver_success':fitangle['solver_success'],'depth_extent_m':fitangle['depth_extent_m'],'vertex_displacement_from75_max_m':float(np.max(np.linalg.norm(vv-v,axis=1))),'source_projection_under_fixed75_evaluator':st,'evaluation_note':'Geometry generated with each angle. Fixed75 projection is a sensitivity diagnostic, not a camera-calibrated fit score.'})
 report={'status':'MEASURED_SURFACE_PROCESS_PROTOTYPE__GEOMETRY_AND_APPEARANCE_NOT_APPROVED','source_sha256':A['source_sha256'],'source_pixel_digest':m['source_pixel_sha256'],'master_sha256':sha(BASE/'generated/panel_master.json.gz'),'measurement_sha256':sha(BASE/'evidence/measurements.json.gz'),'same_input_master_exact':ma==fresh,'independent_saved_measurement_replay_exact':ma==re,'same_source_surface_vertices_exact':np.array_equal(v,rv),'same_common_compile_exact':co==co2,'same_common_mesh_exact':r==r2,'numeric_rounding_m':1e-10,'pitch_m':.025,'grid_origin':[0,0,0],'normal_thickness_m':A['surface_prior']['normal_representation_thickness_m'],'actual_candidates':co['candidate_cells'],'cells':len(co['cells']),'quads':r['quad_count'],'compiler_sha256':co['compiler_source_hash'],'mesher_sha256':r['provenance']['mesher_sha256'],'exporter_sha256':r['provenance']['exporter_sha256'],'source_components':int(ndi.label(a['front_support'])[1]),'voxel_structure':struct,'parent_contact':pcinfo,'projection':stats,'pixel_regression':regression,'rejection_checks':rejects,'camera_sensitivity':yaw,'runtime_seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'whole_character_complete':False,'complete_panel_reconstruction':False,'appearance_validated':False,'GPU_validated':False,'rig_socket_validated':False,'repair_performed':False}
 write(BASE/'evidence/verification25.json',report);write(BASE/'evidence/CPU_provenance.json',{'CPU_renderer_sha256':sha(CPU_SOURCE),'evaluator_sha256':sha(Path(__file__).with_name('review_surface.py')),'verifier_sha256':sha(__file__),'common_render_sha256':sha(BASE/'generated/common25.render.json.gz'),'camera':cam,'source_geometry_sha256':sha(BASE/'generated/continuous_surface.npz'),'images':[{'path':str(p.relative_to(REPO)),'sha256':sha(p)} for p in sorted((BASE/'generated').glob('*.jpg'))],'GPU':False})
 used=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file());assert used<A['budget']['r10_total_bytes_ceiling'];assert report['peak_rss_mib']<=A['budget']['peak_rss_mib_ceiling'];print(json.dumps({k:report[k] for k in ['cells','actual_candidates','source_components','voxel_structure','parent_contact','projection','pixel_regression','rejection_checks','runtime_seconds','peak_rss_mib']}));print('r10 bytes',used)
if __name__=='__main__':run()
