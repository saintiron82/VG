"""Bounded R14 physical-height screening of proposed range dimensions."""
from plan import *
import time,resource
from world_city.concept_city_v3.registered_topography.revisions.r14_precinct_merchant import author as terrain

def main():
 start=time.monotonic();d=load(HERE/'remaining_land_plan.json');out=[]
 for b in d['range_parcels']:
  p=b['building_envelope_xz_m'];cx,cz=b['center_xz_m'];pts=p+[[(a[0]+q[0])/2,(a[1]+q[1])/2]for a,q in zip(p,p[1:]+p[:1])]+[[cx,cz]];samples=[]
  for x,z in pts:
   o=terrain.owner_at(x,z);y=terrain.land_height_at(x,z);samples.append({'xz_m':[x,z],'ground_y_m':y,'owner_kind':o['kind'],'owner_id':o.get('owner_id'),'render_land':o.get('render_land',True)})
  ys=[s['ground_y_m']for s in samples];span=max(ys)-min(ys);status='terraced_or_split_native_range_required'if span>1.5 else'finite_platform_and_threshold_profile_required';out.append({'parcel_id':b['id'],'zone_id':b['zone_id'],'ground_y_min_sampled_m':min(ys),'ground_y_max_sampled_m':max(ys),'sampled_height_span_m':span,'floor_y_m':None,'status':status,'samples':samples,'support_policy':'Do not set the whole holding to the maximum sample. Select bounded native modules and stepped floor/platform sections after terrain owner review.'})
 result={'schema':'riverstone.remaining_land.terrain_screen.v1','plan':ref(HERE/'remaining_land_plan.json'),'terrain_api':ref(Path(terrain.__file__)),'terrain_freeze':ref(CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json'),'status':'Nine-point screening of native-dimension range envelopes. Not a full surface/support, excavation or accessible-slope proof.','ranges':out,'summary':{'range_parcels':len(out),'point_samples':sum(len(q['samples'])for q in out),'requiring_terraced_or_split_design':sum(q['sampled_height_span_m']>1.5 for q in out),'largest_sampled_span_m':max(q['sampled_height_span_m']for q in out),'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'limits':['R14 is sealed and supplies finite precinct/merchant owners; source screening binds its exact author and contract.','No source floor or terrain grade has been modified.','The point sample can miss a narrow grade seam; the next accepted parcel needs finite ownership and full-width entrance tests.']};write(HERE/'terrain_screen.json',result);print(result['summary'])
if __name__=='__main__':main()
