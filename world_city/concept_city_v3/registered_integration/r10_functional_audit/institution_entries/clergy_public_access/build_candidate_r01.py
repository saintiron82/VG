"""Bounded 2 m high-bench public approach; reuse native gate and relocate one bed."""
import json,sys,math,hashlib,copy,importlib.util
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[5];sys.path.insert(0,str(ROOT))
S=H.parent/'abbey_repair_r03/candidate_r03/source_snapshot';sp=importlib.util.spec_from_file_location('clergy_fixed_helpers',S/'finite_helpers_frozen.py');fh=importlib.util.module_from_spec(sp);sp.loader.exec_module(fh)
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.review_geometry import DomainCut,fan,clean
Ground,area3,cut3,split3,xz,up=fh.Ground,fh.area3,fh.cut3,fh.split3,fh.xz,fh.up
C=ROOT/'world_city/concept_city_v3';BASE=C/'evidence/r8_final110_runtime_r01/scene.json';SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def ref(p):return dict(path=str(Path(p).relative_to(ROOT)),sha256=sha(p))
def write(n,x):(H/n).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def circle(p,r):return [[p[0]+r*math.cos(k*math.pi/16),p[1]+r*math.sin(k*math.pi/16)]for k in range(32)]
def ribbons(ps,w):return [g.road_ribbon(a,b,w)for a,b in zip(ps,ps[1:])]+[circle(p,w/2)for p in ps[1:-1]]
def unique(polys):
 out=[]
 for p in polys:
  out.extend(DomainCut([dict(polygon_xz_m=q)for q in out]).subtract(p))
 return out
def area(ps):return sum(g.polygon_area(p)for p in ps)
def cut(polys,masks):
 dd=DomainCut([dict(polygon_xz_m=p)for p in masks]);return [q for p in polys for q in dd.subtract(p)]
def contacts(polys,obstacles):return [dict(id=b['id'],area_m2=ar)for p in polys for b in obstacles if(ar:=g.intersection_area(p,b['polygon_xz_m']))>1e-8]

def main():
 assert sha(BASE)==SHA
 ctx=read(H.parent/'context.json')['sites']['clergy'];rows=ctx['surface_rows'];ground=Ground(rows);plan=read(H/'exploration_r02.json');ps=plan['points'];public=ps[:-1];inside=ps[-2:];gate=public[-1];moved_id='FIELD_SITE_CLERGY_035:12:bed:1';bed=next(r for r in ctx['instances']if r['instance']['id']==moved_id);old=bed['instance'];new=copy.deepcopy(old);new['position_m'][0]-=2;new['source_pack']='r10_clergy_public_entry_r01';asset=bed['asset'];oldpoly=g.transformed_aabb_xz_m(asset['bounds'],old['position_m'],old['yaw_rad']);newpoly=g.transformed_aabb_xz_m(asset['bounds'],new['position_m'],new['yaw_rad']);relocation=rect(181.5,-151,189.5,-148);native=DomainCut(ctx['floors']);path_polys=unique(ribbons(public,2));path_owner=unique([q for p in path_polys for q in native.subtract(p)]);private_owner=cut([relocation],path_owner);owners=path_owner+private_owner;domain=DomainCut([dict(polygon_xz_m=p)for p in owners]);assert area(cut([newpoly],private_owner))<1e-7
 oldreleased=cut([oldpoly],[newpoly]);otherfill=cut(oldreleased,path_owner);tops={};tiny=[]
 def emit(m,p):
  for v in fan(p):
   t=up([[x,14.,z]for x,z in v]);a=np.array(t,dtype=np.float32);nn=np.cross(a[1]-a[0],a[2]-a[0]);ar=area3(t)
   if ar<1e-12:continue
   if np.dot(nn,nn)==0:
    tiny.append(dict(kind='appended',material=m,area_m2=ar,triangle=t));continue
   tops.setdefault(m,[]).extend(t)
 for p in path_owner:emit('road',p)
 for p in otherfill:emit('ground_grass',p)
 # All ordinary path points lie on the existing Y14 bench. The only missing
 # original support is within the relocated native bed's source-bound footprint.
 flat=DomainCut([dict(polygon_xz_m=r['polygon'])for r in ground.rows if max(abs(v[1]-14)for v in r['triangle'])<1e-6]+ctx['floors']+[dict(polygon_xz_m=oldpoly)])
 missing=area([q for p in path_owner+otherfill for q in flat.subtract(p)]);assert missing<1e-6,missing
 edges=[];edits=[];source_mats=set();wet=[]
 for r in rows:
  t=r['triangle'];pp=[xz(v)for v in t];inds=list(domain.index.candidates(pp))
  if not inds:continue
  if r['material']=='water':
   if any(g.intersection_area(pp,owners[i])>1e-12 for i in inds):wet.append(r)
   continue
  changed=False
  for i in inds:
   mask=owners[i];cur=t
   for aa,bb in zip(mask,mask[1:]+mask[:1]):
    if not cur:break
    cur,_=split3(cur,aa,bb,1 if g.signed_polygon_area(mask)>0 else -1)
   if all(g.point_in_convex_polygon(v,mask,0)for v in pp)or(len(cur)>=3 and sum(area3(v)for v in fan(cur))>1e-14):changed=True;break
  if not changed:continue
  parts=[t]
  for i in inds:parts=[qq for p in parts for qq in cut3(p,owners[i])]
  repl=[]
  for p in parts:
   for tt in fan(p):
    ar=area3(tt)
    if ar<1e-12:continue
    aa=np.array(tt,dtype=np.float32);n=np.cross(aa[1]-aa[0],aa[2]-aa[0]);dd=np.array(tt);dn=np.cross(dd[1]-dd[0],dd[2]-dd[0])
    if np.dot(n,n)==0 or np.dot(n,dn)<=0:
     assert ar<1e-5; tiny.append(dict(kind='outside_fragment',material=r['material'],source_triangle_index=r['triangle_index'],area_m2=ar,triangle=tt));continue
    repl.append(tt)
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_xyz_m=t,source_triangle_sha256=ch(t),replacement_triangles_xyz_m=repl));source_mats.add(r['material'])
 assert not wet and sum(r['area_m2']for r in tiny)<1e-5
 s=read(BASE);pack=dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=SHA,common_assets={old['asset_key']:asset},remove_instance_ids=[old['id']],add_instances=[new],instance_relocations=[dict(id=old['id'],source_instance=old,source_instance_sha256=ch(old),replacement_instance=new,translation_xyz_m=[-2,0,0],source_footprint_xz_m=oldpoly,replacement_footprint_xz_m=newpoly,crop_area_before_m2=18.,crop_area_after_m2=18.)]);write('pack.json',pack)
 own=[dict(id='R10_CLERGY_HIGH_PUBLIC_PATH',ownership_polygons_xz_m=path_owner,core_polygons_xz_m=path_owner,access='unrestricted_public',road_source_id='GOAL:MARKET_TO_CATHEDRAL',gate_native_id='CLERGY_GUEST_ALMS',design_width_m=2.),dict(id='R10_CLERGY_BED_RELOCATION',ownership_polygons_xz_m=private_owner,access='private_cultivation_and_released_margin',source_instance_id=old['id'],source_instance_sha256=ch(old),new_native_footprint_xz_m=newpoly,released_ground_polygons_xz_m=otherfill)]
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R10_CLERGY_HIGH_PUBLIC_APPROACH_R01',status='source_candidate_runtime_and_view_pending',base_scene=ref(BASE),base_scene_sha256=SHA,source_surface_hashes={m:ch(s['surfaces'][m])for m in sorted(source_mats)},surface_edits=edits,appended_surfaces=tops,removed_foundation_proxy_ids=[],ownership=own,summary=dict(source_triangle_edits=len(edits),appended_triangles=sum(len(v)//3 for v in tops.values()),public_path_ownership_area_m2=area(path_owner),private_relocation_ownership_area_m2=area(private_owner),total_changed_area_m2=area(owners),uncovered_old_bed_repaired_area_m2=area(oldreleased),crop_area_before_m2=18.,crop_area_after_m2=18.,native_building_edits=0,wall_edits=0,relocated_instances=1,water_edits=0,float32_slivers=len(tiny),float32_removed_area_m2=sum(r['area_m2']for r in tiny)))
 write('surface_patch.json',patch);write('ground_ownership.json',dict(owners=own,transition=dict(point_xyz_m=[gate[0],14,gate[1]],outside='unrestricted_public',inside='admitted_guest_alms_staff',existing_gate_clear_width_m=4.,native_gate_unchanged=True),excluded_private_holdings=[i['instance']['id']for i in ctx['instances']if i['instance']['id'].startswith('R06_SITE_CLERGY_')and':boundary_'in i['instance']['id']]));write('numeric_filter_ledger.json',tiny)
 # Physical after-state: one relocated native collider and exact finite ground.
 bodies=[dict(b,polygon_xz_m=[[x-2,z]for x,z in b['polygon_xz_m']])if b['id']==moved_id else b for b in ctx['bodies']]
 assert not contacts([newpoly],[b for b in bodies if b['id']!=moved_id]),'Relocated bed collides with retained native'
 mapping=read(C/'registered_integration/r10_functional_audit/network/observed_route_observation_mapping.json');source=next(r for r in mapping if r['id']=='GOAL:MARKET_TO_CATHEDRAL');q0,q1=source['original_points_xyz_m'][-2:];dx,dz=q1[0]-q0[0],q1[2]-q0[2];ll=math.hypot(dx,dz);u=[dx/ll,dz/ll];origin=ps[0];left=[origin[k]-3*u[k]for k in [0,1]];right=[origin[k]+3*u[k]for k in [0,1]];v=[ps[1][k]-origin[k]for k in [0,1]];vl=math.hypot(*v);junction=[origin[k]+2*v[k]/vl for k in [0,1]]
 defs=[('R10_CLERGY_HIGH_PUBLIC_THROUGH',[left,origin,right],'unrestricted_public'),('R10_CLERGY_PUBLIC_APPROACH',public,'unrestricted_public'),('R10_CLERGY_GATE_ADMISSION',inside,'admitted_guest_alms_staff'),('R10_CLERGY_LEFT_TURN',[left,origin,junction],'unrestricted_public'),('R10_CLERGY_RIGHT_TURN',[right,origin,junction],'unrestricted_public')]
 lookup={(e['material'],e['triangle_index']):e for e in edits};actual=[]
 for r in rows:
  e=lookup.get((r['material'],r['triangle_index']));actual.extend([dict(r,triangle=t)for t in e['replacement_triangles_xyz_m']]if e else[r])
 actual +=[dict(material=m,triangle_index=k//3,triangle=vv[k:k+3])for m,vv in tops.items()for k in range(0,len(vv),3)];gg=Ground(actual);support=DomainCut([dict(polygon_xz_m=r['polygon'])for r in gg.rows]+ctx['floors']);routes=[];tests=[]
 private=[]
 for r in ctx['instances']:
  i=r['instance'];a=r['asset']
  if i['id'].startswith('R06_SITE_CLERGY_')and ':boundary_'in i['id']:private.append(dict(id=i['id'],polygon_xz_m=g.transformed_aabb_xz_m(a['bounds'],i['position_m'],i['yaw_rad'])))
 for rid,points,access in defs:
  rr=ribbons(points,2.);hit=contacts(rr,bodies);phit=contacts(rr,private);miss=area([p for q in rr for p in support.subtract(q)]);pts=[]
  for a,b in zip(points,points[1:]):
   n=math.ceil(math.dist(a,b)/.25)
   for k in range(n):
    p=[a[i]+(b[i]-a[i])*k/n for i in [0,1]];y=14 if any(g.point_in_convex_polygon(p,r['polygon_xz_m'],0)for r in ctx['floors'])else gg.at(p);pts.append([p[0],y,p[1]])
  p=points[-1];y=14 if any(g.point_in_convex_polygon(p,r['polygon_xz_m'],0)for r in ctx['floors'])else gg.at(p);pts.append([p[0],y,p[1]])
  test=dict(id=rid,length_horizontal_m=sum(math.dist(a,b)for a,b in zip(points,points[1:])),native_contacts=hit,private_holding_contacts=phit,missing_support_area_m2=miss,max_sampled_step_m=max(abs(b[1]-a[1])for a,b in zip(pts,pts[1:])),width_m=2.,passes=not hit and not phit and miss<2e-6);tests.append(test);routes.append(dict(id=rid,group='CLERGY_HIGH_GATE',points=pts,width_m=2.,design_clear_width_m=2.,public_access=access,source_road_ids=['GOAL:MARKET_TO_CATHEDRAL','CATHEDRAL_APPROACH'],cart_test=False,test_scope='Pedestrian public access to existing gate and admitted standing point only; no almonry doorway passage, cart, or capacity claim.'))
 assert all(t['passes']for t in tests),tests
 idx=read(C/'registered_integration/r9/integration_r02_camera/index.json');idx['packs'].append(ref(H/'pack.json'));write('index.json',idx);write('routes.json',dict(schema='riverstone.r10.institution_runtime_request.v1',base_scene=ref(BASE),base_scene_sha256=SHA,finite_patch=ref(H/'surface_patch.json'),visual_index=ref(H/'index.json'),collision_margin_m=8,gate_native_id='CLERGY_GUEST_ALMS',gate_center_xyz_m=[gate[0],14,gate[1]],gate_clear_width_m=4.,source_plan=ref(C/'registered_source/plan.json'),routes=routes,public_graph_policy='Only unrestricted public approach and existing road junction join public graph. Gate interior standing point is admitted only.',cameras=[dict(id='R10_CLERGY_HIGH_ROUTE_OVERVIEW',position=[166,49,-160],target=[190,14,-159]),dict(id='R10_CLERGY_CROP_PINCH_EYE',position=[186,16,-163],target=[190,15,-151]),dict(id='R10_CLERGY_GATE_EYE',position=[198,16,-130],target=[212,15,-135])]))
 write('source_tests.json',dict(status='SOURCE_PASS_RUNTIME_AND_VIEW_PENDING',base_unchanged=sha(BASE)==SHA,summary=patch['summary'],tests=tests,before_contacts_on_same_approach=contacts(ribbons(public,2),ctx['bodies']),source_public_route_observations=source['observations'],old_private_holdings_retained=True,relocated_native_source=bed,runtime_capsule_tested=False,gui_viewed=False));print(json.dumps(dict(summary=patch['summary'],tests=tests),indent=2))
if __name__=='__main__':main()
