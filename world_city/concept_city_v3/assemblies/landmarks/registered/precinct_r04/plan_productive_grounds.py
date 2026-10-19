"""Finite coherent orchard and kitchen-plot frames; failed frames stay explicit."""
from plan_coverage import *
def main():
 plan=load(HERE/'coverage_plan.json');sites={s['id']:s for s in plan['sites']};obs=plan['reserved_records']+[{'polygon_xz_m':p}for c in plan['compounds']for p in c['available_regions_xz_m']];index=geo._SpatialIndex(32)
 for i,r in enumerate(obs):index.add(i,r['polygon_xz_m'])
 ds=sorted((x*x+z*z,x,z)for x in range(-8,9)for z in range(-8,9));frames=[];failed=[]
 for id,site,kind,c,w,d,yaw in SPEC['productive_frames_requested']:
  site_tri=triangulate(sites[site]['polygon_xz_m']);found=None
  for _,dx,dz in ds:
   center=[c[0]+dx,c[1]+dz];poly=rect(center,w,d,math.radians(yaw));expanded=rect(center,w+1,d+1,math.radians(yaw))
   if abs(sum(geo.intersection_area(expanded,t)for t in site_tri)-geo.polygon_area(expanded))>1e-5:continue
   if any(geo.positive_area_overlap(expanded,obs[i]['polygon_xz_m'],1e-7)for i in index.candidates(expanded)):continue
   if any(geo.positive_area_overlap(expanded,r['polygon_xz_m'],1e-7)for r in frames):continue
   found=(center,poly,dx,dz);break
  if not found:failed.append({'id':id,'site_id':site,'function':kind,'requested_center_xz_m':c,'status':'no_bounded_fit; do_not_count_as_built'});continue
  center,poly,dx,dz=found;frames.append({'id':id,'site_id':site,'function':kind,'center_xz_m':center,'polygon_xz_m':poly,'width_m':w,'depth_m':d,'yaw_degrees':yaw,'finished_floor_y_m':14 if site=='SITE_CLERGY'else 8,'area_m2':w*d,'fit_delta_m':[dx,dz],'boundary':'continuous_native_wall_with_real_gate_pending','working_aisle_m':3})
 write(HERE/'productive_frames.json',{'coverage_plan':ref(HERE/'coverage_plan.json'),'frames':frames,'failed_frames':failed,'fitted_area_m2':sum(f['area_m2']for f in frames),'actual_placed':False,'actual_viewed':False});print('FITTED',[(x['id'],x['fit_delta_m'])for x in frames]);print('FAILED',failed)
if __name__=='__main__':main()
