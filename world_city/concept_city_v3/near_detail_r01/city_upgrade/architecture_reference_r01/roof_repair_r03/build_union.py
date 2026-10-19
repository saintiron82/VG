"""Reuses exact r02 fine union; restores only original occupied descendants."""
from author_roof_r03 import *
def main():
 t=time.monotonic();plan=read(H/'plan.json');assert plan['source_dependencies']==pins();a=np.load(OLD/'upper_union_arrays.npz');arr=a['materials'];names=a['material_names'].tolist();lo=a['origin_cell_xyz'];assert lo.tolist()==[-200,300,-164];ids={n:i for i,n in enumerate(names)}
 original=np.load(F/'foundation_arrays.npz');occ=original['occupancy'];mats=original['materials'];legacy=read(OLD/'roof_patch.master.json.gz');slope=legacy['metadata']['measured_gable_slope'];ridge=legacy['metadata']['original_max_y'];X=(np.arange(400)-200+.5)*P;labels=np.zeros(arr.shape,np.uint8);restored=0
 for iy in range(4,148):
  row=np.full((400,328),-1,np.int16);row[8:392,4:324]=np.where(occ[(iy+300)//4],mats[(iy+300)//4],-1).repeat(4,0).repeat(4,1)
  mask=(arr[iy]<0)&(row>=0)&((iy+300+.5)*P<ridge-slope*np.abs(X)[:,None]-.1875)
  arr[iy][mask]=row[mask];labels[iy][mask]=1;restored+=int(mask.sum())
 cleared=0
 for b in plan['edge_blocks']:
  y,x=b['source_yx'];zs=b['original_z_cells'];sl=(slice(y*4-300,(y+1)*4-300),slice(x*4+8,(x+1)*4+8),slice(zs[0]*4+4,(zs[-1]+1)*4+4));block=arr[sl]
  assert np.all(block==mats[y,x,zs[0]]),'Original pale block changed before source replacement'
  cleared+=int((block>=0).sum());arr[sl]=-1;labels[sl]=2
 c=read(R/read(H/'compile.json')['delta']['path']);shadow={};edge_count=shadow_added=shadow_support_replaced=shadow_blocked=0
 for x,y,z,instance,part,material,feature in c['cells']:
  iy,ix,iz=y-300,x+200,z+164;old=int(arr[iy,ix,iz])
  if part=='foreground_resampled_gable_edge':
   assert labels[iy,ix,iz]==2 and old<0,'Edge source outside exact cleared original footprint'
   arr[iy,ix,iz]=ids[material];edge_count+=1
  else:
   assert part=='observed_shadow_tile_extensions';shadow[(x,y,z)]=feature
   if old>=0 and (old<15 or old>=21):shadow_blocked+=1;continue
   assert labels[iy,ix,iz]!=2,'Observed extension must not override facade foreground ownership'
   shadow_added+=int(old<0);shadow_support_replaced+=int(old>=0);arr[iy,ix,iz]=ids[material];labels[iy,ix,iz]=3
 overlap_parts={}
 for ch in read(OLD/'compile.json')['chunks']:
  cc=read(R/ch['compiled']['path'])
  for x,y,z,instance,part,material,feature in cc['cells']:
   if (x,y,z)in shadow:
    overlap_parts[part]=overlap_parts.get(part,0)+1
    assert part=='thin_roof_support','New tile overlaps an existing measured region or chimney'
  del cc;gc.collect()
 topy=np.full((400,328),-1,np.int16);topclass=np.zeros((400,328),np.uint8);topmat=np.full((400,328),-1,np.int16)
 for iy in range(4,148):
  mask=arr[iy]>=0;topy[mask]=iy+300;topclass[mask]=labels[iy][mask];topmat[mask]=arr[iy][mask]
 restored_top=int((topclass==1).sum());assert restored_top==0,'Restored original interior is exposed as roof top or chimney blade'
 rest_exposed={};dirs=[(0,1,'+Y'),(0,-1,'-Y'),(1,1,'+X'),(1,-1,'-X'),(2,1,'+Z'),(2,-1,'-Z')]
 for axis,sign,name in dirs:
  count=0
  for iy in range(4,148):
   rm=(labels[iy]==1)&(arr[iy]>=0)
   if axis==0:empty=(arr[iy+sign]<0) if 0<=iy+sign<148 else np.ones(rm.shape,bool)
   else:
    empty=np.ones(rm.shape,bool)
    if axis==1:
     if sign>0:empty[:-1]=arr[iy,1:]<0
     else:empty[1:]=arr[iy,:-1]<0
    else:
     if sign>0:empty[:,:-1]=arr[iy,:,1:]<0
     else:empty[:,1:]=arr[iy,:,:-1]<0
   count+=int((rm&empty).sum())
  rest_exposed[name]=count
 np.savez_compressed(H/'upper_union_arrays.npz',materials=arr,origin_cell_xyz=lo,pitch_m=P,material_names=np.asarray(names),join_y_m=JOIN)
 np.savez_compressed(H/'delta_ownership_arrays.npz',delta_class=labels,top_first_hit_delta_class=topclass,top_first_hit_material=topmat)
 prior=np.load(OLD/'upper_union_arrays.npz')['materials'];outside_changes=0
 for iy in range(148):outside_changes+=int(((arr[iy]!=prior[iy])&(labels[iy]==0)).sum())
 lower_halo_changes=int((arr[:4]!=prior[:4]).sum());assert outside_changes==lower_halo_changes==0
 beforeproj=np.array([(row>=0).any(1)for row in prior]);afterproj=np.array([(row>=0).any(1)for row in arr]);Ys=(np.arange(148)+300+.5)*P;plane=ridge-slope*np.abs(X);band=(Ys[:,None]>=plane[None,:]-.65)&(Ys[:,None]<=plane[None,:]+.125)&(Ys[:,None]>=JOIN)&(np.abs(X)[None,:]>.25)&(np.abs(X)[None,:]<6)
 def gaps(pr):return ~pr&np.maximum.accumulate(pr,axis=0)&np.maximum.accumulate(pr[::-1],axis=0)[::-1]&band
 beforegap=gaps(beforeproj);aftergap=gaps(afterproj);remaining=int(aftergap.sum());closed=int((beforegap&~aftergap).sum());new=int((aftergap&~beforegap).sum())
 report={'schema':'riverstone.roof_source_delta.union.v1','status':'PASS_EXACT_SOURCE_DELTA','source':ref(OLD/'upper_union_arrays.npz'),'union':ref(H/'upper_union_arrays.npz'),'delta_masks':ref(H/'delta_ownership_arrays.npz'),'restored_original_occupied_fine_cells':restored,'restored_volume_template_m3':restored*P**3,'restoration_outside_original_bounds':0,'restored_above_backing_bottom':0,'restored_top_first_hits':restored_top,'restored_exposed_unit_faces':rest_exposed,'restored_exposed_faces_qualification':'Below existing support; +Y faces may be hidden cavities. TOP first-hit test is authoritative for vertical roof visibility. Side/underside retained source remains diagnostic.','edge_original_fine_cells_cleared':cleared,'edge_foreground_fine_cells_inserted':edge_count,'edge_background_fine_cells_removed':cleared-edge_count,'observed_tile_delta_fine_cells_added':shadow_added,'observed_tile_delta_support_cells_replaced':shadow_support_replaced,'observed_tile_delta_blocked_by_retained_source':shadow_blocked,'r02_overlap_parts':overlap_parts,'unchanged_outside_delta_masks':outside_changes==0,'lower_join_halo_exact':lower_halo_changes==0,'gable_projected_gap_before_cells':int(beforegap.sum()),'gable_projected_gap_after_cells':remaining,'gable_gap_closed_cells':closed,'gable_new_gap_cells':new,'gable_remaining_gap_area_template_m2':remaining*P*P,'gable_original_gap_area_template_m2':int(beforegap.sum())*P*P,'no_new_sampling':True,'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'all_source_pins_unchanged':plan['source_dependencies']==pins()}
 assert report['all_source_pins_unchanged'];write('union_validation.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(384*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(45,)*2);main()
