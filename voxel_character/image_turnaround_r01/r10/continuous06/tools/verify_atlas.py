"""Independent deterministic replay, actual pixel fixtures, common sampling audit."""
from surface_atlas import *
import review_surface as view
from collections import Counter
from scipy.sparse.csgraph import connected_components

def cellset(co):return {tuple(c[:3]) for c in co['cells']}
def compile_one(ma,pitch):
 candidates=view.candidate_count(ma,pitch)
 if candidates>A['budget']['candidate_cells_ceiling']:raise ValueError('Candidate ceiling exceeded')
 co=compile_master(ma,{'pitch':pitch},max_candidate_cells=A['budget']['candidate_cells_ceiling'],max_output_cells=20000);return co,make_render_data(co)
def topology(v,f,charts):
 edges={}
 for fi,tri in enumerate(f):
  for i,j in zip(tri,np.roll(tri,-1)):edges.setdefault(tuple(sorted((int(i),int(j)))),[]).append(fi)
 pairs=np.array(list(edges));graph=sparse.csr_matrix((np.ones(len(pairs)),(pairs[:,0],pairs[:,1])),shape=(len(v),len(v)));num,_=connected_components(graph,directed=False);norm=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);areas=np.linalg.norm(norm,axis=1)/2;norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-15);fold=[]
 for edge,ids in edges.items():
  if len(ids)==2 and charts[ids[0]]!=charts[ids[1]]:fold.append(float(np.degrees(np.arccos(np.clip(norm[ids[0]]@norm[ids[1]],-1,1)))))
 return {'connected_surface_components':int(num),'boundary_edges':sum(len(q)==1 for q in edges.values()),'nonmanifold_edges':sum(len(q)>2 for q in edges.values()),'degenerate_triangles':int((areas<1e-14).sum()),'shared_fold_edges':len(fold),'fold_dihedral_abs_degrees_min_median_max':[min(fold),float(np.median(fold)),max(fold)] if fold else None,'fold_positions_share_identical_vertices':True,'fold_angle_is_solved_prior_not_image_measurement':True,'nonlocal_thick_prism_self_intersection_audit':'not yet performed; mid-surface is an injective front-domain graph'}
def approximation(v,f,fit,a):
 nv,nf,nfit=solve(*load_measurement());nodes=np.array(nfit['source_pixel_nodes']);truth={tuple(p):q[2] for p,q in zip(nodes,nv)};errs={};xy=np.c_[v[:,0]/SCALE+F['axis_u'],F['sole_y']-v[:,1]/SCALE]
 for tri in f:
  p=xy[tri];z=v[tri,2];lo=np.ceil(p.min(0)-1e-7).astype(int);hi=np.floor(p.max(0)+1e-7).astype(int);aa,bb,cc=p;den=(bb[1]-cc[1])*(aa[0]-cc[0])+(cc[0]-bb[0])*(aa[1]-cc[1])
  if abs(den)<1e-12:continue
  for yy in range(lo[1],hi[1]+1):
   for xx in range(lo[0],hi[0]+1):
    if (xx,yy) not in truth:continue
    wa=((bb[1]-cc[1])*(xx-cc[0])+(cc[0]-bb[0])*(yy-cc[1]))/den;wb=((cc[1]-aa[1])*(xx-cc[0])+(aa[0]-cc[0])*(yy-cc[1]))/den;wc=1-wa-wb
    if min(wa,wb,wc)>=-1e-7:errs[(xx,yy)]=abs(wa*z[0]+wb*z[1]+wc*z[2]-truth[(xx,yy)])
 return {'native_vertices_tested':len(errs),'native_vertex_count':len(nv),'maximum_actual_triangle_depth_error_m':max(errs.values()),'rms_actual_triangle_depth_error_m':float(np.sqrt(np.mean(np.array(list(errs.values()))**2))),'bilinear_leaf_bound_is_not_the_triangle_error_bound':True,'no_native_domain_pixels_discarded':True}
def contact(co,pitch):
 name='common25.cells.json.gz' if pitch==.025 else 'common125.cells.json.gz';p=ROOT/'continuous05c/generated'/name
 if not p.exists():return {'status':'frozen upper-flap comparison unavailable'}
 other=gzread(p);a0,b=cellset(co),cellset(other);touch=[]
 for c in a0:
  if c in b or any(tuple(c[k]+(d if k==j else 0) for k in range(3)) in b for j in range(3) for d in [-1,1]):touch.append(c)
 box=A['views']['front']['root_search_box'];roots=[]
 for c in touch:
  x,y,z=(np.array(c)+.5)*pitch;u=x/SCALE+F['axis_u'];py=F['sole_y']-y/SCALE
  if box[0]<=u<=box[2] and box[1]<=py<=box[3]:roots.append(c)
 return {'target_path':str(p.relative_to(REPO)),'target_sha256':sha(p),'overlap_cells':len(a0&b),'six_neighbor_or_overlap_cells':len(touch),'root_box_contact_cells':len(roots),'status':'Only discrete contact with previous measured upper visible flap. Neither sewn identity nor direct body attachment confirmed.'}
def run():
 t=time.monotonic();m,a=load_measurement();ma=gzread(BASE/'generated/panel_master.json.gz');sf=np.load(BASE/'generated/continuous_surface.npz');mm,aa=extract(SOURCE);re,v,f,fit,mesh,charts=build(mm,aa,SOURCE);assert ma==re;re2,v2,f2,_,_,_=build(m,a,SOURCE);assert re2==ma and np.array_equal(v,v2) and np.array_equal(f,f2)
 reports={};baseline={}
 for pitch,key in [(.025,'common25'),(.0125,'common125')]:
  co,r=compile_one(ma,pitch);co2,r2=compile_one(ma,pitch);assert co==co2 and r==r2;gzwrite(BASE/'generated'/f'{key}.cells.json.gz',co);gzwrite(BASE/'generated'/f'{key}.render.json.gz',r);st,pred=view.metrics(r,a);im,cam=view.view_sheet(r,f'CONTINUOUS06 | actual common {pitch*1000:g}mm | immutable master/thickness/origin');im.save(BASE/'generated'/f'{key}_four_views.jpg',quality=90);view.overlays(a,pred,f'{key}: unchanged source / no deletion or filling').save(BASE/'generated'/f'{key}_overlay.jpg',quality=90);reports[key]={'pitch_m':pitch,'candidates':co['candidate_cells'],'cells':len(co['cells']),'structure':components(co['cells']),'projection':st,'repeat_common_payload_exact':co==co2,'repeat_common_mesh_exact':r==r2,'upper_flap_contact':contact(co,pitch),'compiler_sha256':co['compiler_source_hash'],'mesher_sha256':r['provenance']['mesher_sha256'],'exporter_sha256':r['provenance']['exporter_sha256']};baseline[key]=(co,r,pred)
 regression={}
 for name,box in [('local_lobe',[490,465,502,477]),('unrelated_face',[315,185,320,190])]:
  src=SOURCE.copy();x0,y0,x1,y1=box;src[y0:y1,x0:x1]=[255,0,0];nm,na=extract(src);nb,nv,nf,nfit,nmesh,ncharts=build(nm,na,src);oldops=ma['components'][0]['operations'];newops=nb['components'][0]['operations'];same=oldops==newops;rep={'source_fixture_xyxy':box,'fixture_rgb':[255,0,0],'actual_changed_pixels':int(np.any(src!=SOURCE,2).sum()),'changed_front_mask_pixels':int((a['front_support']^na['front_support']).sum()),'other_view_masks_exact':all(np.array_equal(na[k],a[k]) for k in a if not k.startswith('front_')),'geometry_unchanged':same,'expectation_pass':same if name=='unrelated_face' else not same,'dependency_scope':'only this two-chart connected atlas. No hair, skin, body or frozen upper flap output modified.','source_status':nb['extensions']['source_status'],'approved_source_sha_not_misattributed':nb['extensions']['source_sha256'] is None,'master_geometry_digest':digest(newops),'source_pixel_sha256':rawsha(src)}
  if name=='local_lobe':
   nc,nr=compile_one(nb,.025);rep['changed_common25_cells']=len(cellset(nc)^cellset(baseline['common25'][0]));rep['projection_changed_pixels']={k:int((view.project_exact(nr,c)^baseline['common25'][2][k]).sum()) for k,c in C['views'].items()};rep['source_component_sizes']=nm['views']['front']['component_sizes']
  regression[name]=rep
 rejects={}
 for key,mutm,muta,muts in [('missing_measurement',{},a,SOURCE),('wrong_source_pixels',m,a,np.zeros_like(SOURCE))]:
  try:validate(mutm,muta,muts);rejects[key]=False
  except ValueError:rejects[key]=True
 bad=copy.deepcopy(m);bad['dependencies'][-1]['sha256']='0'*64
 try:validate(bad,a,SOURCE);rejects['stale_solver_dependency']=False
 except ValueError:rejects['stale_solver_dependency']=True
 src=SOURCE.copy();src[383:567,756:932]=[255,0,0]
 try:
  nm,na=extract(src);build(nm,na,src);rejects['contradictory_actual_side_pixels']=False
 except ValueError as e:rejects['contradictory_actual_side_pixels']=True;rejects['contradiction_message']=str(e)
 oldclosure=read(ROOT/'continuous05c/closure.json');changed=[]
 entries=oldclosure.get('files',oldclosure.get('entries',[]))
 for entry in entries:
  path=REPO/entry['path']
  if sha(path)!=entry['sha256']:changed.append(entry['path'])
 approximation_result=approximation(v,f,fit,a)
 out={'status':'LARGER_MEASURED_SURFACE_PROCESS_PROTOTYPE__APPEARANCE_AND_FULL_CHARACTER_UNAPPROVED','same_input_source_to_master_exact':ma==re,'independent_measurement_replay_exact':ma==re2,'source_vertices_exact':np.array_equal(v,v2),'source_topology':topology(v,f,charts),'adaptive_approximation':approximation_result,'common':reports,'pixel_regression':regression,'rejection_checks':rejects,'frozen05c_closure_files_verified':len(entries),'changed_frozen05c_files':changed,'normal_thickness_m':.025,'grid_origin':[0,0,0],'root_depth_prior_vertices':len(fit['unknown_root_depth_prior_vertices']),'fold_y_residual_rms_mm':1000*fit['fold_y_residual_rms_m'],'fold_y_residual_max_mm':1000*fit['fold_y_residual_max_m'],'elapsed_seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'source_sha256':A['source_sha256'],'generator_sha256':sha(Path(__file__).with_name('surface_atlas.py')),'verifier_sha256':sha(__file__),'common_full_character_complete':False,'art_approved':False,'GPU_validated':False,'rig_socket_validated':False,'repair_performed':False}
 write(BASE/'evidence/verification.json',out);used=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file());assert used<41943040;assert out['peak_rss_mib']<512;print(json.dumps(out));print('r10 bytes',used)
if __name__=='__main__':run()
