"""Finite owner-scale grounds on actual R7 level bands; no native compile."""
from build_ledger import *
from scipy.ndimage import minimum_filter, maximum_filter
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex
TARGETS={'SITE_CLERGY','SITE_MONASTERY','SITE_CASTLE','SITE_TRAIN','SITE_COMMON','E1','E2','E3','E4','E5','E6','E7'}

def terrain_raster(scene,owner):
 heights=np.full(b.SHAPE,np.nan);grades=np.full(b.SHAPE,np.nan);public=np.zeros(b.SHAPE,bool)
 for n,(mat,j,tri,p) in enumerate(terrain.source_rows(scene)):
  x0=max(0,math.floor(min(v[0]for v in p)-b.BOUNDS[0]));x1=min(b.NX,math.ceil(max(v[0]for v in p)-b.BOUNDS[0]));z0=max(0,math.floor(min(v[1]for v in p)-b.BOUNDS[1]));z1=min(b.NZ,math.ceil(max(v[1]for v in p)-b.BOUNDS[1]))
  if x0>=x1 or z0>=z1 or not np.any(owner[z0:z1,x0:x1]):continue
  xs=b.BOUNDS[0]+np.arange(x0,x1)+.5;zs=b.BOUNDS[1]+np.arange(z0,z1)+.5;inside=np.ones((z1-z0,x1-x0),bool);sgn=1 if geo.signed_polygon_area(p)>0 else -1
  for a,c in zip(p,p[1:]+p[:1]):inside&=sgn*((c[0]-a[0])*(zs[:,None]-a[1])-(c[1]-a[1])*(xs[None,:]-a[0]))>=-1e-8
  plane=terrain.common.plane(tri);ys=plane[0]*xs[None,:]+plane[1]*zs[:,None]+plane[2];height=heights[z0:z1,x0:x1];take=inside&(~np.isfinite(height)|(ys>height-1e-7));height[take]=ys[take];grades[z0:z1,x0:x1][take]=math.hypot(*plane[:2]);public[z0:z1,x0:x1]|=inside if mat in('road','alley')else False
 return heights,grades,public

def main():
 t=time.monotonic();scene=terrain.load_scene();ledger=load(HERE/'actual_owner_use_ledger.json');m=np.load(HERE/'owner_masks.npz');labels=m['labels'];owners=ledger['owners'];target=np.isin(labels,[i+1 for i,o in enumerate(owners)if o['owner_id']in TARGETS]);
 if(HERE/'terrain_raster.npz').exists():r=np.load(HERE/'terrain_raster.npz');h,grade,public=r['height'],r['grade'],r['public']
 else:
  h,grade,public=terrain_raster(scene,b.buffer(target,30));np.savez_compressed(HERE/'terrain_raster.npz',height=h,grade=grade,public=public)
 free=target&~b.buffer(m['native'],2)&~b.buffer(m['reserved'],1)&~b.buffer(public,2)&~b.buffer(m['water'],4)&~m['wall']&np.isfinite(h)&(grade<1e-8)
 # Parent owns separate draw facilities. Preserve source water service nodes.
 water=load(CITY/'registered_source/plan.json').get('water_network',{})
 # parent-supplied reservations, if present, are additive and exact.
 if(HERE/'water_service_reservations.json').exists():
  for q in load(HERE/'water_service_reservations.json')['regions']:free&=~b.mask([q['polygon_xz_m']],True)
 units=[];rejected=[];windows=[o['source_polygon_xz_m']for o in owners if o['owner_id']in TARGETS];index=terrain.TriangleIndex(scene,windows);sides=SideIndex(scene,windows);counter=collections.Counter()
 # Long institutional productive domains use32×24m; estate extensions use smaller18m fields. Four-sided gateways preserve circulation choice.
 for oi,o in sorted(enumerate(owners,1),key=lambda v:-v[1]['categories_disjoint_grid_m2']['remaining_without_finite_implemented_use']):
  if o['owner_id']not in TARGETS:continue
  om=labels==oi;count=0
  choices=[(32,24),(24,24),(18,18),(24,14),(18,12),(14,14)] if o['owner_id'].startswith('SITE_')else[(18,18),(14,14)]
  # Named existing exercise and parade functions should not be carpeted by crops.
  cap=5 if o['owner_id']in('SITE_TRAIN','SITE_CASTLE','SITE_COMMON')else 3 if o['owner_id'].startswith('E')else 80
  for w,d in choices:
   while count<cap:
    cur=free&om;fit=minimum_filter(cur.astype(np.uint8),size=(d+2,w+2),mode='constant',cval=0).astype(bool)
    maxh=maximum_filter(np.nan_to_num(h,nan=-999),size=(d+2,w+2),mode='constant',cval=-999);minh=minimum_filter(np.nan_to_num(h,nan=999),size=(d+2,w+2),mode='constant',cval=999);fit&=abs(maxh-minh)<1e-7
    zz,xx=np.where(fit)
    if not len(xx):break
    # Coherent broad rows: deterministic west-to-east positions, with existing
    # useful ground physically separated by at least2m working passage.
    idx=np.lexsort((xx,zz))[0];iz,ix=int(zz[idx]),int(xx[idx]);x=float(b.BOUNDS[0]+ix);z=float(b.BOUNDS[1]+iz);p=b.rect(x-w/2,z-d/2,x+w/2,z+d/2);y=float(h[iz,ix]);test=terrain.audit_polygon(index,p,y);side=sides.audit([{'id':'candidate','polygon_xz_m':p,'floor_y_m':y,'headroom_m':9}])
    if not test['passes_existing_surface']or side['contacts']:
     free[iz,ix]=False;rejected.append({'owner_id':o['owner_id'],'polygon_xz_m':p,'floor_y_m':y,'missing_m2':test['missing_area_m2'],'max_delta_m':test['max_floor_delta_m'],'side_contacts':len(side['contacts'])});continue
    count+=1;counter[o['owner_id']]+=1;kind=('stable_service'if o['owner_id']in('SITE_CASTLE','SITE_TRAIN')else'common_maintenance'if o['owner_id']=='SITE_COMMON'else['orchard','kitchen_beds','medicinal_nursery','fuel_workyard'][count%4])
    if kind=='orchard'and min(w,d)<18:kind='medicinal_nursery'
    if o['owner_id'].startswith('E'):kind=['orchard','kitchen_beds','fuel_workyard'][(count-1)%3]
    uid='R06_'+o['owner_id']+'_'+str(count).zfill(2);units.append({'id':uid,'owner_id':o['owner_id'],'function':kind,'polygon_xz_m':p,'area_m2':w*d,'dimensions_m':[w,d],'position_m':[x,y,z],'floor_y_m':y,'surface_check':{k:v for k,v in test.items()if k not in('source_pieces','uncovered_polygons_xz_m')},'source_surface_pieces':test['source_pieces'],'retained_side_clearance':{'status':side['status'],'tested_pairs':side['tested_face_owner_pairs']},'gate_clear_width_m':4,'internal_cross_aisle_width_m':4,'gateway_directions':['north','south','east','west'],'runtime_ready':False})
    free&=~b.mask([b.rect(x-w/2-2,z-d/2-2,x+w/2+2,z+d/2+2)])
    print('unit',uid,kind,w*d,[x,y,z],flush=True)
  print('owner_done',o['owner_id'],count,flush=True)
 summary={'units':len(units),'area_m2':sum(u['area_m2']for u in units),'owner_counts':dict(counter),'function_counts':dict(collections.Counter(u['function']for u in units)),'rejected_level_or_bank_candidates':len(rejected),'seconds':time.monotonic()-t}
 write('grounds_plan.json',{'schema':'riverstone.precinct.r06.whole_ground_source.v1','scene':ref(terrain.SCENE_PATH),'owner_ledger':ref(HERE/'actual_owner_use_ledger.json'),'units':units,'summary':summary,'compile_status':'NOT_COMPILED','activation':False,'limitations':['Per-unit whole-domain existing surface and retained-bank checks are exact.','External gate routes must be checked before final promotion.','Unallocated residual owner land remains explicit; no green-area completion claim.']});write('rejected_source_candidates.json',rejected);print(summary,flush=True)
if __name__=='__main__':main()
