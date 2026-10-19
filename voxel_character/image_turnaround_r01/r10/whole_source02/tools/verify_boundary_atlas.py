"""Reproduction, input causality, independent-chart scope and coverage failure diagnosis.
No occupancy repair, no unapproved geometry publication or heavy whole compile.
"""
from boundary_atlas import *
import review_surface as view
view.A=A;view.C=C;view.F=F;view.SOURCE=SOURCE

def topology(f,ch):
 result=[]
 for i in range(len(A['charts'])):
  faces=f[ch==i];edges={};n=len(faces)
  for j,t in enumerate(faces):
   for p,q in zip(t,np.roll(t,-1)):edges.setdefault(tuple(sorted([int(p),int(q)])),[]).append(j)
  adj=[set() for _ in faces]
  for ids in edges.values():
   for p in ids:adj[p].update(set(ids)-{p})
  seen=set();counts=[]
  for p in range(n):
   if p in seen:continue
   todo=[p];seen.add(p);count=0
   while todo:
    q=todo.pop();count+=1
    for r in adj[q]:
     if r not in seen:seen.add(r);todo.append(r)
   counts.append(count)
  result.append({'chart':A['charts'][i]['id'],'edge_connected_components':len(counts),'component_triangle_counts':sorted(counts,reverse=True),'nonmanifold_edge_count':sum(len(q)>2 for q in edges.values()),'boundary_edge_count':sum(len(q)==1 for q in edges.values())})
 return result

def geodigest(v,f,ch):return digest({'v':rawsha(v),'f':rawsha(f),'ch':rawsha(ch)})

def run():
 t=time.monotonic();m,a=load();saved=gzread(BASE/'generated/costume_master.json.gz');s=np.load(BASE/'generated/continuous_costume.npz');ma,v,f,ch,pp,rep=build(m,a,SOURCE);baseline=geodigest(v,f,ch);same={'master_canonical_exact':canonical(ma)==canonical(saved),'source_arrays_exact':all(np.array_equal(x,s[k]) for x,k in [(v,'vertices'),(f,'triangles'),(ch,'charts'),(pp,'primary_pixels')])};m2,a2=extract(SOURCE);same['independent_remeasurement_arrays_exact']=all(np.array_equal(a[k],a2[k]) for k in a);same['boundary_records_exact']=m['charts']==m2['charts'];del m2,a2,ma
 union=np.zeros_like(a['front_support'])
 for i in range(len(A['charts'])):union|=a[f'chart_{i}_front']
 render=view.source_render(v,f,saved['materials']);pred=view.project_exact(render,F)
 pv=np.c_[(pp[:,0]-F['axis_u'])*SCALE,(F['sole_y']-pp[:,1])*SCALE,np.zeros(len(pp))];pre=view.project_exact(view.source_render(pv,f,saved['materials']),F)
 coverage={'whole_front_support_pixels':int(a['front_support'].sum()),'annotated_chart_union_pixels':int(union.sum()),'unassigned_measured_pixels_before_geometry':int((a['front_support']&~union).sum()),'missed_assigned_pixels_in_primary_parameter_map':int((union&~pre).sum()),'parameter_map_projection_outside_assigned_chart_union_pixels':int((pre&~union).sum()),'missed_assigned_pixels_after_spatial_boundary_fit':int((union&~pred).sum()),'spatial_projection_outside_assigned_chart_union_pixels':int((pred&~union).sum()),'classification_exterior_conflicts':m['views'],'parameter_projection_note':'Source chart disks may fold over in primary projection. This is not automatically a proven 3D self-intersection; needs constrained parametrization/triangle collision review.'}
 fixtures=[]
 for name,box in [('actual_train_rgb_change',[591,582,601,592]),('unrelated_face_rgb_change',[315,185,320,190])]:
  changed=SOURCE.copy();x0,y0,x1,y1=box;changed[y0:y1,x0:x1]=[255,0,0];mm,aa=extract(changed);mb,vb,fb,cb,pb,rb=build(mm,aa,changed);direct=[]
  for i in range(len(A['charts'])):
   if mm['charts'][i]!=m['charts'][i] or not np.array_equal(aa[f'chart_{i}_front'],a[f'chart_{i}_front']):direct.append(i)
  declared=set(direct)
  if 0 in direct:declared.update(i for i,q in enumerate(A['charts']) if 'side' not in q['views'] and q['hidden_depth_prior']=='nearest_paired')
  # A change to whole side support may influence an explicitly unknown chart only.
  if not np.array_equal(aa['side_support'],a['side_support']):declared.update(i for i,q in enumerate(A['charts']) if 'side' not in q['views'])
  changed_charts=[];escaped=[];nv=len(v)//len(A['charts'])
  for i in range(len(A['charts'])):
   differs=not np.array_equal(v[i*nv:(i+1)*nv],vb[i*nv:(i+1)*nv]) or not np.array_equal(f[ch==i],fb[cb==i])
   if differs:changed_charts.append(i)
   if differs and i not in declared:escaped.append(i)
  fixtures.append({'fixture':name,'actual_pixel_box':box,'actual_changed_pixels':int(np.any(changed!=SOURCE,2).sum()),'measured_front_mask_changed_pixels':int((a['front_support']!=aa['front_support']).sum()),'directly_changed_chart_indices':direct,'declared_dependency_chart_indices':sorted(declared),'actual_geometry_changed_chart_indices':changed_charts,'outside_dependency_changed_chart_indices':escaped,'geometry_changed':geodigest(vb,fb,cb)!=baseline,'outside_dependency_exact':not escaped,'source_pixel_sha256':rawsha(changed)})
  del mm,aa,mb,vb,fb,cb,pb,rb
 rejected={}
 try:build(None,a,SOURCE)
 except ValueError as e:rejected['missing_measurement']=str(e)
 try:
  changed=SOURCE.copy();changed[275:624,655:1050]=[255,0,0];extract(changed)
 except ValueError as e:rejected['contradictory_side_source']=str(e)
 report={'status':'UNAPPROVED_SOURCE; whole costume completeness and chart attachment FAIL','reproduction':same,'pixel_regressions':fixtures,'required_input_rejection':rejected,'coverage_diagnosis':coverage,'source_edge_connectivity':topology(f,ch),'source_chart_count':len(A['charts']),'cross_chart_shared_sewing_constraints':0,'sockets':None,'no_automatic_island_deletion_or_fill':True,'common_compile':'WITHHELD: spatial/coverage failure must be reviewed before whole compile; common master adapter exists','seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'generator_sha256':sha(Path(__file__).with_name('boundary_atlas.py')),'verification_sha256':sha(__file__),'master_sha256':sha(BASE/'generated/costume_master.json.gz'),'source_geometry_sha256':sha(BASE/'generated/continuous_costume.npz')};write(BASE/'evidence/verification.json',report);print(json.dumps(report))
if __name__=='__main__':run()
