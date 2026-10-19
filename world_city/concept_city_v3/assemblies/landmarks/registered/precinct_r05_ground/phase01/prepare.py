"""Finite productive holding selection and terrain-relative native preflight."""
import sys,json,math,hashlib,collections
from pathlib import Path
import numpy as np
from scipy import ndimage
HERE=Path(__file__).resolve().parent;REG=HERE.parents[1];ROOT=HERE.parents[6];CITY=ROOT/'world_city/concept_city_v3';PLAN=REG/'remaining_land_r01'
sys.path[:0]=[str(ROOT),str(REG/'precinct_r04')]
from plan_coverage import geo,load,ref,write,world,circle
from world_city.concept_city_v3.registered_topography.revisions.r14_precinct_merchant import author as terrain
from world_city.concept_city_v3.review_geometry import DomainCut
IDS={'C_CHAPTER_GARDEN:1':'chapter_kitchen_and_herbs','C_SOUTH_ORCHARD:1':'cathedral_food_orchard','A_WEST_BOUNDARY:1':'abbey_nursery_orchard','A_EAST_GUEST_GARDEN:1':'infirmary_medicinal_garden','A_SOUTH_KITCHEN_PLOTS:1':'abbey_kitchen_vegetables','B03_ESTATE_GARDEN_LINKS:1':'estate_productive_orchard'}
P=.5

def rect(x0,z0,x1,z1):return[[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def grid_for(parts,margin=3):
 pts=[p for poly in parts for p in poly];x0=math.floor(min(p[0]for p in pts)/P)*P-margin;z0=math.floor(min(p[1]for p in pts)/P)*P-margin;x1=math.ceil(max(p[0]for p in pts)/P)*P+margin;z1=math.ceil(max(p[1]for p in pts)/P)*P+margin;m=np.zeros((round((z1-z0)/P),round((x1-x0)/P)),bool)
 for poly in parts:
  a,b,c,d=min(p[0]for p in poly),min(p[1]for p in poly),max(p[0]for p in poly),max(p[1]for p in poly);assert abs(geo.polygon_area(poly)-(c-a)*(d-b))<1e-6;m[round((b-z0)/P):round((d-z0)/P),round((a-x0)/P):round((c-x0)/P)]=True
 return m,x0,z0

def cellrects(m,x0,z0):
 rows={z:np.flatnonzero(m[z]).tolist()for z in range(m.shape[0])};active={};out=[]
 for z in range(m.shape[0]+1):
  xs=rows.get(z,[]);runs=[]
  if xs:
   a=prev=xs[0]
   for x in xs[1:]:
    if x!=prev+1:runs.append((a,prev+1));a=x
    prev=x
   runs.append((a,prev+1))
  nxt={}
  for run in runs:nxt[run]=active.pop(run,[run[0],z,run[1],z+1]);nxt[run][3]=z+1
  out.extend(active.values());active=nxt
 return[rect(x0+a*P,z0+b*P,x0+c*P,z0+d*P)for a,b,c,d in out]
def inside(m,x0,z0,p):
 x,z=math.floor((p[0]-x0)/P),math.floor((p[1]-z0)/P);return 0<=z<m.shape[0]and 0<=x<m.shape[1]and bool(m[z,x])
def contained(m,x0,z0,poly):
 # Exact candidate rectangles on the same 0.5m source grid.
 xx=[p[0]for p in poly];zz=[p[1]for p in poly];a=math.floor((min(xx)-x0)/P+1e-8);b=math.floor((min(zz)-z0)/P+1e-8);c=math.ceil((max(xx)-x0)/P-1e-8);d=math.ceil((max(zz)-z0)/P-1e-8)
 return 0<=a<c<=m.shape[1]and 0<=b<d<=m.shape[0]and bool(m[b:d,a:c].all())
def sample(poly):
 xs=[p[0]for p in poly];zs=[p[1]for p in poly];pts=poly+[[sum(xs)/len(xs),sum(zs)/len(zs)]];ys=[terrain.land_height_at(*p)for p in pts];return{'points_xz_m':pts,'heights_m':ys,'min_m':min(ys),'max_m':max(ys)}
def main():
 plan=load(PLAN/'remaining_land_plan.json');access=load(PLAN/'access_review.json');r15p=CITY/'registered_topography/revisions/r15_merchant_local_patch/source_contract.json';r15=load(r15p);reserved=[r['polygon_xz_m']for r in r15['patch_masks']];
 for r in r15.get('retained_lower_grounds',[]):
  reserved+=r.get('polygons_xz_m',[])if isinstance(r,dict)else []
 idx=geo._SpatialIndex(16)
 for i,p in enumerate(reserved):idx.add(i,p)
 old=load(REG/'precinct_r04/resolved_placements.json');props=[a for a in old['assets']if 'fabric_r3'in a['id']];holdings=[];allhits=[]
 for zone in plan['zones']:
  for h in zone['contiguous_holdings']:
   if h['id']not in IDS:continue
   parts=h['polygon_parts_xz_m'];route=next(c for c in access['connections']if c['holding_id']==h['id']);assert route['status']=='plan_grid_connected_profile_unresolved';hits=[geo.intersection_area(p,reserved[i])for p in parts for i in idx.candidates(p)];total=sum(x for x in hits if x>1e-7);assert total<1e-6,(h['id'],total)
   m,x0,z0=grid_for(parts);erode=ndimage.distance_transform_edt(m)*P;wall=m&~ndimage.binary_erosion(m);polyline=route['polyline_xz_m'];gatecut=[geo.road_ribbon(a,b,4)for a,b in zip(polyline,polyline[1:])if math.dist(a,b)>1e-7]+[circle(p,2,16)for p in polyline];pathcut=[geo.road_ribbon(a,b,2)for a,b in zip(polyline,polyline[1:])if math.dist(a,b)>1e-7]+[circle(p,1,16)for p in polyline]
   for iz,ix in np.argwhere(wall):
    p=rect(x0+ix*P,z0+iz*P,x0+(ix+1)*P,z0+(iz+1)*P)
    if any(geo.positive_area_overlap(p,q,0)for q in gatecut):wall[iz,ix]=False
   walls=cellrects(wall,x0,z0);spans=[]
   for i,p in enumerate(walls):
    # Slice long rectangles to <=4m so each finite terrain-bearing step is bounded.
    xs=[v[0]for v in p];zs=[v[1]for v in p];axis=0 if max(xs)-min(xs)>=max(zs)-min(zs)else 1;lo=min(xs)if axis==0 else min(zs);hi=max(xs)if axis==0 else max(zs);n=max(1,math.ceil((hi-lo)/4))
    for k in range(n):
     a=lo+(hi-lo)*k/n;b=lo+(hi-lo)*(k+1)/n;q=rect(a,min(zs),b,max(zs))if axis==0 else rect(min(xs),a,max(xs),b);he=sample(q);spans.append({'id':h['id']+':boundary:'+str(len(spans)),'polygon_xz_m':q,'underlying_profile':he,'top_y_m':math.floor(he['min_m']*4)/4+1.25,'bottom_y_m':math.floor(he['min_m']*4)/4-.75,'max_visible_height_m':math.floor(he['min_m']*4)/4+1.25-he['min_m'],'terrain_range_m':he['max_m']-he['min_m']})
   # Source route exit gives the actual wall opening; gate dimensions are checked later.
   line=[]
   for a,b in zip(polyline,polyline[1:]):
    for i in range(max(1,math.ceil(math.dist(a,b)/.25))):t=i/max(1,math.ceil(math.dist(a,b)/.25));line.append([a[j]+t*(b[j]-a[j])for j in(0,1)])
   line.append(polyline[-1]);exitidx=next((i for i,p in enumerate(line)if not inside(m,x0,z0,p)),len(line)-1);gatecenter=line[max(0,exitidx-8)];target=line[min(len(line)-1,exitidx)];vec=[target[j]-gatecenter[j]for j in(0,1)];L=math.hypot(*vec);direction=[v/L for v in vec]if L else[0,1]
   plantations=[];productive=[];kind='tree'if'orchar'in IDS[h['id']]else'bed';spacing=(10,10)if kind=='tree'else(9,6);bounds=[min(p[0]for poly in parts for p in poly),min(p[1]for poly in parts for p in poly),max(p[0]for poly in parts for p in poly),max(p[1]for poly in parts for p in poly)]
   for z in np.arange(math.ceil((bounds[1]+6)/spacing[1])*spacing[1],bounds[3]-5,spacing[1]):
    for x in np.arange(math.ceil((bounds[0]+6)/spacing[0])*spacing[0],bounds[2]-5,spacing[0]):
     clear=rect(float(x)-4.5,float(z)-4.5,float(x)+4.5,float(z)+4.5)if kind=='tree'else rect(float(x)-4,float(z)-2.5,float(x)+4,float(z)+2.5)
     if not contained(m,x0,z0,clear)or any(geo.positive_area_overlap(clear,p,0)for p in pathcut):continue
     fp=rect(float(x)-4,float(z)-4,float(x)+4,float(z)+3)if kind=='tree'else rect(float(x)-3,float(z)-1.5,float(x)+3,float(z)+1.5);he=sample(fp)
     # Flat beds have finite native bearing; do not conceal a cliff with the prop.
     if kind=='bed'and he['max_m']-he['min_m']>.2:continue
     plantations.append({'id':h['id']+':'+kind+':'+str(len(plantations)),'kind':kind,'position_m':[float(x),he['max_m'],float(z)],'yaw_rad':0,'scale':[1,1,1],'footprint_xz_m':fp,'support_samples':he,'native_bottom_y_m':he['max_m']-(1 if kind=='tree'else.5),'support_status':'finite vertex/center sample; independent full-footprint terrain review pending'})
     productive.append(fp if kind=='bed'else rect(float(x)-4.5,float(z)-4.5,float(x)+4.5,float(z)+4.5))
   # Material regions are finite ground ownership only, following current terrain.
   ground={'holding_regions_xz_m':parts,'default_material':'ground_grass'if kind=='tree'else'ground_earth','productive_regions_xz_m':productive,'productive_material':'ground_earth','service_ribbon_polygons_xz_m':pathcut,'service_material':'ground_earth','terrain_profile':'inherit exact frozen R5/R14 surface; no blanket flat floor'}
   holdings.append({**h,'site_id':zone['site_id'],'function':IDS[h['id']],'source_zone_function':zone['function'],'boundary_spans':spans,'boundary_policy':'Continuous native union of0.5m inside-edge cells, with4m source access breaks; open gate leaves staged separately.','source_access':route,'opening_center_xz_m':target,'gate_setback_center_xz_m':gatecenter,'gate_direction_outward_xz':direction,'plantings':plantations,'ground_program':ground,'terrain_min_m':min(s['underlying_profile']['min_m']for s in spans),'terrain_max_m':max(s['underlying_profile']['max_m']for s in spans),'r15_reserved_overlap_m2':total,'status':'bounded native source pending compilation and terrain/access adoption'})
 refs=[PLAN/'remaining_land_plan.json',PLAN/'access_review.json',PLAN/'freeze_manifest.json',r15p,CITY/'registered_topography/revisions/r14_precinct_merchant/author.py',CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json',CITY/'evidence/visual_registered_common_r5/bridge_scene.json'];result={'schema':'riverstone.productive_ground.phase01.v1','sources':[ref(p)for p in refs],'holdings':holdings,'reused_prop_assets':props,'summary':{'holding_count':len(holdings),'meaningful_program_area_m2':sum(h['area_m2']for h in holdings),'planting_instances':sum(len(h['plantings'])for h in holdings),'wall_spans':sum(len(h['boundary_spans'])for h in holdings),'r15_reserved_overlap_m2':sum(h['r15_reserved_overlap_m2']for h in holdings)},'unresolved_original_access_gaps':11,'unresolved_original_stepped_range_parcels':7,'new_range_buildings':0,'actual_viewed':False,'terrain_activated':False,'limits':['Six source-plan holdings only; other54holdings remain source plan.','Source access centerlines are clear in2D only. Ground profile and public joins are not automatically approved.','R15 merchant public collars have no final extent yet; no nearby activation until cross-pack check.','No concept roof-pixel segmentation or historical agricultural capacity claim.']};write(HERE/'preflight.json',result);print(result['summary']);print([(h['id'],len(h['plantings']),len(h['boundary_spans']),h['terrain_min_m'],h['terrain_max_m'])for h in holdings],flush=True)
if __name__=='__main__':main()
