"""Frozen-candidate replay and locality audit; failures are not repaired here."""
import joint_costume as J
from joint_costume import *
from scipy.sparse.csgraph import connected_components

def operations(ma):return ma['components'][0]['operations']
def mesh_map(v,f,mask_component=None):
 uv=np.c_[v[:,0]/SCALE+F['axis_u'],F['sole_y']-v[:,1]/SCALE];out={}
 for tri in f:
  center=uv[tri].mean(0);x=int(math.floor(center[0]))-F['crop'][0];y=int(math.floor(center[1]))
  if mask_component is not None and 0<=y<mask_component.shape[0] and 0<=x<mask_component.shape[1] and mask_component[y,x]:continue
  vals=sorted([(round(float(uv[i,0]),6),round(float(uv[i,1]),6),round(float(v[i,2]),10)) for i in tri]);key=tuple((q[0],q[1]) for q in vals);out[key]=tuple(q[2] for q in vals)
 return out

def run():
 t=time.monotonic();m,a=load_measurement();ma=gzread(BASE/'generated/costume_master.json.gz');sf=np.load(BASE/'generated/continuous_costume.npz');mm,aa=extract(SOURCE);fresh,v,f,ch,fit,mesh=build(mm,aa,SOURCE);assert ma==fresh and np.array_equal(v,sf['vertices']) and np.array_equal(f,sf['triangles']);reg={};baseops=operations(ma)
 for name,box in [('local_train',A['regression']['front_boundary_patch_xyxy']),('unrelated_face',[315,185,320,190])]:
  src=SOURCE.copy();x0,y0,x1,y1=box;src[y0:y1,x0:x1]=[255,0,0];nm,na=extract(src);nb,nv,nf,nch,nfit,nmesh=build(nm,na,src);diff=a['front_support']^na['front_support'];record={'actual_changed_source_pixels':int(np.any(src!=SOURCE,2).sum()),'fixture_xyxy':box,'fixture_rgb':[255,0,0],'changed_front_mask_pixels':int(diff.sum()),'other_view_geometry_masks_exact':all(np.array_equal(a[k],na[k]) for k in a if (k.startswith('side_') or k.startswith('back_')) and k.endswith(('_support','_charts','_upper_candidate','_lobe_candidate'))),'master_geometry_exact':baseops==operations(nb),'source_geometry_digest':digest(operations(nb)),'source_pixel_sha256':rawsha(src),'source_approval_not_misattributed':nb['extensions']['source_sha256'] is None,'solver_converged':nfit['success'],'body_hair_or_skin_geometry_modified':False}
  if name=='local_train':
   labels,n=ndi.label(a['front_support'],structure=np.ones((3,3),int));affected=set(labels[diff]);affected.discard(0);mask=np.isin(labels,list(affected));old=mesh_map(v,f,mask);new=mesh_map(nv,nf,mask);keys=set(old)|set(new);bad=[k for k in keys if old.get(k)!=new.get(k)];shared=set(old)&set(new);maxdz=max([max(abs(np.array(old[k])-np.array(new[k]))) for k in shared],default=0);record.update({'dependency_domain':'baseline native shared-vertex graph neighborhood, including diagonal-only point adjacency; explicit topology caveat','affected_front_component_pixel_count':int(mask.sum()),'outside_dependency_mesh_triangle_changes':len(bad),'outside_dependency_vertex_depth_difference_max_m':float(maxdz),'outside_dependency_geometry_exact':not bad,'locality_pass':not bad,'point_adjacency_may_not_be_sewn_connection':True})
  else:record['locality_pass']=baseops==operations(nb)
  reg[name]=record
 wrong=SOURCE.copy();wrong[275:624,655:1050]=[255,0,0]
 try:extract(wrong);reject=False;message=None
 except ValueError as e:reject=True;message=str(e)
 gap={}
 for name in ['front','side','back']:
  oc=a[name+'_unmodeled_occluder'];known=a[name+'_upper_candidate']|a[name+'_lobe_candidate'];gap[name]={'actual_occluder_search_eligible_pixels':int(oc.sum()),'actual_unmodeled_occluder_pixels_excluding_known_patches':int((oc&~known).sum()),'known_patch_pixels_retained_inside_occluder_search':int((oc&known).sum()),'front_domain_vs_foreground_conflict_pixels':int((a[name+'_support']&~a[name+'_foreground']).sum())}
 out={'status':'WHOLE_VISIBLE_COSTUME_SOURCE_FAILURE_DIAGNOSTIC__NOT_FULL_CHARACTER','same_source_measurement_to_master_exact':ma==fresh,'stored_source_mesh_exact':bool(np.array_equal(v,sf['vertices']) and np.array_equal(f,sf['triangles'])),'pixel_regression':reg,'contradictory_side_pixels_rejected':reject,'contradiction_message':message,'corrected_occluder_counts':gap,'metadata_erratum':'ownership.omitted_under_occluder_eligible_pixels in initial generator is misnamed/miscomputed after visible-array replacement; it counted protected known-patch pixels. Correct omission counts are in corrected_occluder_counts. Geometry masks and output are unchanged; initial artifact/code preserved.','source_representation_limits':['43 four-connected source domains remain; no pixel/island deletion','Native vertex graph can identify diagonal-only point contacts. Such point adjacency is not confirmed material sewing or a finite cloth/body connection','Unknown large remaining chart uses whole side support conservatively; minimum-curvature/midpoint prior collapsed its actual side projection','Solver reached1800 iteration limit; no convergence or appearance pass claimed','Source master includes only visible costume surfaces, no new body/head/hair/socket geometry'],'elapsed_seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'code_sha256':sha(__file__),'source_solver_sha256':sha(J.__file__),'master_sha256':sha(BASE/'generated/costume_master.json.gz'),'common_compile_performed':False,'GPU_rig_socket_validated':False};write(BASE/'evidence/verification.json',out);print(json.dumps(out));print('new bytes',sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file()))
if __name__=='__main__':run()
