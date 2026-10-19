"""Remove only sub-tolerance triangles that disappear/reverse in runtime float32."""
from build_candidate import *
def main():
 p=read(H/'surface_patch.json');removed=[]
 def good(t,kind,material,index):
  a=np.asarray(t,dtype=np.float32);n=np.cross(a[1]-a[0],a[2]-a[0]);d=np.asarray(t,dtype=np.float64);normal=np.cross(d[1]-d[0],d[2]-d[0])
  ok=float(np.dot(n,n))>0 and float(np.dot(n,normal))>0
  if not ok:
   ar=area3(t);assert ar<1e-5,(kind,material,index,ar);removed.append(dict(kind=kind,material=material,index=index,triangle_xyz_m=t,area_3d_m2=ar))
  return ok
 for m,vs in p['appended_surfaces'].items():p['appended_surfaces'][m]=[v for i in range(0,len(vs),3)if good(vs[i:i+3],'append',m,i//3)for v in vs[i:i+3]]
 for e in p['surface_edits']:e['replacement_triangles_xyz_m']=[t for k,t in enumerate(e['replacement_triangles_xyz_m'])if good(t,'outside_source_fragment',e['material'],[e['triangle_index'],k])]
 assert sum(r['area_3d_m2']for r in removed)<1e-5
 p['summary']['float32_degenerate_skips']+=len(removed);p['summary']['appended_triangles']=sum(len(v)//3 for v in p['appended_surfaces'].values());p['summary']['float32_filter_area_m2']=sum(r['area_3d_m2']for r in removed)
 write('surface_patch.json',p);write('float32_filter_report.json',dict(status='PASS_BOUNDED_FLOAT32_SLIVER_FILTER',removed=removed,total_removed_area_m2=sum(r['area_3d_m2']for r in removed),maximum_triangle_area_limit_m2=1e-5,total_area_limit_m2=1e-5))
 print(len(removed),sum(r['area_3d_m2']for r in removed))
if __name__=='__main__':main()
