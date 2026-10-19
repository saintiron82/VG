"""Finite owner-composed native planting; no terrain, mesh or base mutation."""
from __future__ import annotations
import collections,copy,hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];CITY=ROOT/'world_city/concept_city_v3';sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_source.geometry import triangulate
from world_city.concept_city_v3.assemblies.property.registered.author import LAYOUTS
BASE=CITY/'evidence/r8_final110_runtime_r01/scene.json'
BASE_SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
PROP=CITY/'assemblies/property/registered/r1/resolved_placements.json'
LAND=CITY/'assemblies/landscape/registered/resolved_placements.json'
CATALOG=CITY/'traversal_r5/revisions/r06_r8_precinct/primary_goals_extension_r01/route_catalog_493_r02.json'
PHASE1=CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase01/active_ground_plan.json'
PHASE2=CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/design_plan.json'
PLAN=CITY/'registered_source/plan.json'
CYPRESS='registered_landscape_columnar_cypress';HAZEL='c3_property_fabric_r3_05a88415aae614ab'
def load(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).relative_to(ROOT))
def ref(p):return dict(path=rel(p),sha256=sha(p))
def write(p,d):
 p=Path(p);assert HERE in p.parents;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def box(x,z,w,d=None):
 d=w if d is None else d;return [[x-w/2,z-d/2],[x+w/2,z-d/2],[x+w/2,z+d/2],[x-w/2,z+d/2]]
def transform(poly,p):
 c,s=math.cos(p['yaw_rad']),math.sin(p['yaw_rad']);v=p['position_m'];return [[v[0]+c*x+s*z,v[2]-s*x+c*z]for x,z in poly]
def ring(b,p,margin=0):
 a,h=b['min'],b['max'];return transform([[a[0]-margin,a[2]-margin],[h[0]+margin,a[2]-margin],[h[0]+margin,h[2]+margin],[a[0]-margin,h[2]+margin]],p)
def overlap(a,b):return geo.positive_area_overlap(a,b,0)
def up(q):
 a,b,c=q[:3];return (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2])>1e-9
class Index:
 def __init__(self):self.rows=[];self.index=geo._SpatialIndex(8)
 def add(self,id,poly,**attrs):
  if geo.polygon_area(poly)<1e-9:return
  self.index.add(len(self.rows),poly);self.rows.append(dict(id=id,poly=poly,**attrs))
 def query(self,poly):return [self.rows[i]for i in self.index.candidates(poly)if overlap(poly,self.rows[i]['poly'])]
class World:
 def __init__(self):
  assert sha(BASE)==BASE_SHA;self.scene=load(BASE);self.assets=self.scene['common_assets'];self.prop=load(PROP);self.land=load(LAND);self.plan=load(PLAN);self.routes=load(CATALOG)['routes'];self.owners={};self.native=Index();self.support=Index();self.reserve=Index();self.asset_refs={};self.native_instances=0
  for p in self.prop['ownership_masks']:self.owners[p['property_id']]=dict(id=p['property_id'],floor=p['floor_y_m'],parts=triangulate(p['polygon_xz_m']),source=ref(PROP),source_id=p['property_id'],ownership_kind='private_noble_estate',polygon_xz_m=p['polygon_xz_m'])
  for s in self.land['sites']:
   if s['kind']not in ('public_park','cemetery'):self.owners[s['id']]=dict(id=s['id'],floor=s['floor'],parts=triangulate(s['polygon_xz_m']),source=ref(LAND),source_id=s['id'],ownership_kind=s['kind'],polygon_xz_m=s['polygon_xz_m'])
  for path in [PHASE1,PHASE2]:
   for h in load(path)['holdings']:
    if h['terrain_min_m']==h['terrain_max_m']:self.owners[h['id']]=dict(id=h['id'],floor=h['terrain_min_m'],parts=h['polygon_parts_xz_m'],source=ref(path),source_id=h['id'],ownership_kind=h['function'])
  self.ownerindex=Index()
  for o in self.owners.values():
   for p in o['parts']:self.ownerindex.add(o['id'],p)
  def line(id,points,width,kind):
   width=max(1.2,width)
   for a,b in zip(points,points[1:]):
    if math.dist(a,b)>1e-8:self.reserve.add(id,geo.road_ribbon(a,b,width),kind=kind)
   for x,z in points:self.reserve.add(id,box(x,z,width),kind=kind)
  for r in self.routes:line(r['id'],[[p[0],p[2]]for p in r['points_xyz_m']],r.get('source_width_m')or 1.2,'public_493')
  for r in self.plan['roads']:line(r['id'],r['polyline_xz_m'],r['width_m'],'public_road')
  for r in self.prop['internal_routes']+self.land['internal_routes']:line(r['id'],r['polyline_xz_m'],r['width_m'],'garden_or_service_path')
  for r in self.land['external_connections']:
   if r.get('polyline_xz_m'):line(r['id'],r['polyline_xz_m'],r.get('width_m',2.2),'garden_entrance')
  for path in [PHASE1,PHASE2]:
   for h in load(path)['holdings']:
    r=h['source_access'];line(h['id']+':access',r['polyline_xz_m'],r.get('width_m',2.0),'holding_entrance')
  for p in self.prop['actual_doors']:
   x,y,z=p['door_xyz_m'];self.reserve.add(p['id'],box(x,z,4),kind='door_landing')
  for s in self.land['sites']:
   for g in s['gates']:
    x,z=g['center_xz_m'];self.reserve.add(g['id'],box(x,z,6),kind='garden_gate_turning')
  for o,layout in LAYOUTS.items():
   pt,w,d=layout['court'];self.reserve.add(o+':PRIVATE_SERVICE_COURT',box(*pt,w,d),kind='private_court_no_planting')
  for s in self.plan['spaces']:
   if s['id']in ('SITE_TRAIN','SITE_CEMETERY','SITE_MARKET','SITE_PORT'):
    for p in triangulate(s['polygon_xz_m']):self.reserve.add(s['id'],p,kind='entire_protected_use')
  for s in self.land['sites']:
   if s['kind']=='cemetery':self.reserve.add(s['id'],s['polygon_xz_m'],kind='entire_cemetery_no_planting')
  print('owners and reservations ready',flush=True)
  cache={}
  for p in self.scene['common_instances']:
   a=self.assets[p['asset_key']];rp=ROOT/a['render_path'];b=a.get('bounds')
   if b is None:
    if str(rp)not in cache:cache[str(rp)]=load(rp)
    b=cache[str(rp)]['bounds'];a['bounds']=b
   poly=ring(b,p);touch=self.ownerindex.query(poly)
   if not touch:continue
   self.native_instances+=1
   if str(rp)not in cache:cache[str(rp)]=load(rp)
   rd=cache[str(rp)];assert sha(rp)==a['render_sha256'];self.asset_refs[p['asset_key']]=ref(rp)
   floors={self.owners[r['id']]['floor']for r in touch}
   for g in rd['groups']:
    for q in g['quads']:
     if not up(q)or any(abs(v[1]-q[0][1])>1e-8 for v in q):continue
     y=q[0][1]+p['position_m'][1];poly=transform([[v[0],v[2]]for v in q],p)
     if not self.ownerindex.query(poly):continue
     if any(abs(y-floor)<.03 for floor in floors):self.support.add(p['id'],poly,y=y,material=g['material'],source='native_top_face')
     if y>min(floors)+.05:self.native.add(p['id'],poly,y=y,material=g['material'])
  for p in self.scene['boxes']:
   sz=p['size_m'];b=dict(min=[-v/2 for v in sz],max=[v/2 for v in sz]);poly=ring(b,p);touch=self.ownerindex.query(poly)
   if touch:
    y=p['position_m'][1]+sz[1]/2
    self.native.add(p['id'],poly,y=y,material=p.get('material','base_box'))
  print('native exact tops ready',self.native_instances,len(self.native.rows),flush=True)
  for key,verts in self.scene['surfaces'].items():
   if key in ('water','bank'):continue
   a=np.asarray(verts,dtype=np.float64).reshape((-1,3,3));lo=a.min(axis=1);hi=a.max(axis=1)
   mask=((hi[:,1]-lo[:,1])<.03)&(lo[:,1]>=7.95)&(hi[:,1]<=16.05)
   for tri in a[mask]:
    poly=tri[:,[0,2]].tolist()
    if geo.polygon_area(poly)>1e-9 and self.ownerindex.query(poly):self.support.add('scene:'+key,poly,y=float(tri[0,1]),material=key,source='base_scene_triangle')
  self.native_source_quads=len(self.native.rows)
 def contained(self,poly,owner):
  covers=[p for p in self.owners[owner]['parts']if overlap(poly,p)];return geo.polygon_covered_by_union(poly,covers,0)
 def check(self,p,owner):
  b=self.assets[p['asset_key']]['bounds'];poly=ring(b,p);floor=self.owners[owner]['floor'];bad=[]
  if not self.contained(ring(b,p,.15),owner):bad.append('outside_owned_margin')
  bad += ['reservation:'+r['id']for r in self.reserve.query(ring(b,p,.2))]
  bad += ['native:'+r['id']for r in self.native.query(ring(b,p,.15))if r['y']>floor+.05]
  root=box(p['position_m'][0],p['position_m'][2],1.0 if p['asset_key']==CYPRESS else 2.0)
  supports=[r for r in self.support.query(root)if abs(r['y']-floor)<.03]
  if not geo.polygon_covered_by_union(root,[r['poly']for r in supports],0):bad.append('native_root_support_unproven')
  return sorted(set(bad)),poly,root,[dict(id=r['id'],y_m=r['y'],source=r['source'])for r in supports]
def proposals(world):
 out=[]
 def add(owner,xy,key=CYPRESS,intent='private garden edge sentinels',fit=2):
  for x,z in xy:out.append(dict(id=f'R9_PLANT:{owner}:{sum(p["owner"]==owner for p in out):02d}',owner=owner,desired_xz_m=[x,z],asset_key=key,intent=intent,maximum_local_fit_m=fit,yaw_rad=0))
 # Named finite compositions; never land-cover scatter or density search.
 add('E1',[(-196,-332),(-184,-330),(-171,-326),(-168,-308),(-209,-291),(-209,-280)])
 add('E2',[(-146,-322),(-135,-322),(-123,-320),(-104,-301),(-158,-280),(-158,-266)])
 add('E3',[(-84,-309),(-75,-311),(-63,-310),(-51,-309),(-90,-288),(-39,-285)])
 add('E4',[(-227,-229),(-216,-229),(-205,-227),(-193,-224),(-233,-200),(-233,-188),(-178,-207),(-178,-197)])
 add('E5',[(-157,-209),(-157,-199),(-157,-189),(-155,-225),(-138,-225),(-117,-225)])
 add('E6',[(-65,-238),(-54,-238),(-44,-240),(-80,-213),(-68,-188),(-69,-175)])
 add('E7',[(-140,-157),(-128,-158),(-115,-158),(-135,-87),(-121,-101),(-143,-104)])
 add('E4',[(-231,-181)],HAZEL,'manor side-garden small canopy',fit=1)
 add('E6',[(-64,-177)],HAZEL,'side garden small canopy',fit=1)
 def local(owner,points,intent):
  s=next(s for s in world.land['sites']if s['id']==owner);yaw=math.radians(s['yaw']);par=dict(position_m=[s['position'][0],s['floor'],s['position'][1]],yaw_rad=yaw)
  add(owner,transform(points,par),intent=intent,fit=.5)
  for p in out:
   if p['owner']==owner:p['yaw_rad']=yaw
 local('CLERGY_CLOISTER_GARDEN',[(x,z)for x in (-18,18)for z in (-8,8)]+[(x,z)for x in (-8,8)for z in (-18,18)],'cloister edge upright rhythm around retained crosswalk')
 local('CLERGY_KITCHEN_GARDEN',[(x,z)for x in (-20.5,-10.5,10.5,20.5)for z in (-18,18)],'chapter kitchen border; crop beds and crosswalk kept')
 local('MONASTERY_HERB_GARDEN',[(x,z)for x in (-26,-13,13,26)for z in (-17,17)],'abbey herb garden sheltered perimeter')
 local('MONASTERY_KITCHEN_GARDEN',[(x,z)for x in (-34,-22,-10,10,22,34)for z in (-30.5,30.5)],'abbey productive garden outer ends; retained crops and cart crosswalk')
 add('C_CHAPTER_GARDEN:1',[(206,-246),(219,-237),(236,-240),(256,-265),(269,-277),(277,-287)],intent='chapter garden clipped-edge sentinels')
 add('A_WEST_BOUNDARY:1',[(-390,-10),(-387,34),(-383,57),(-376,78)],intent='abbey nursery boundary punctuation')
 add('A_SOUTH_KITCHEN_PLOTS:1',[(-313,196),(-313,216),(-287,167),(-283,176)],intent='abbey southern kitchen ownership border')
 return out
def build():
 started=time.monotonic();w=World();proposed=proposals(w);accepted=[];rejected=[];ledger=[]
 for c in proposed:
  found=None;initial=None
  ds=sorted((dx*dx+dz*dz,dx/2,dz/2)for dx in range(-4,5)for dz in range(-4,5)if math.hypot(dx/2,dz/2)<=c['maximum_local_fit_m']+1e-9)
  for _,dx,dz in ds:
   x,z=c['desired_xz_m'];floor=w.owners[c['owner']]['floor'];p=dict(id=c['id'],asset_key=c['asset_key'],position_m=[x+dx,floor,z+dz],yaw_rad=c['yaw_rad'],scale=[1,1,1],palette_id='r9_owned_precinct_planting',palette_override={'grass':'4e694a'if c['asset_key']==CYPRESS else '668254'},source_pack='r9_precinct_gardens',source_owner=c['owner'],functional_intent=c['intent'])
   bad,poly,root,support=w.check(p,c['owner'])
   if any(overlap(ring(w.assets[q['asset_key']]['bounds'],q,.3),poly)for q in accepted):bad.append('new_planting_overlap')
   if initial is None:initial=bad
   if not bad:found=(p,poly,root,support,dx,dz);break
  if found is None:rejected.append(dict(**c,initial_rejection_reasons=initial));continue
  p,poly,root,support,dx,dz=found;accepted.append(p);ledger.append(dict(id=p['id'],owner=c['owner'],intent=c['intent'],desired_xz_m=c['desired_xz_m'],actual_xz_m=[p['position_m'][0],p['position_m'][2]],local_fit_m=math.hypot(dx,dz),native_canopy_footprint_xz_m=poly,root_support_footprint_xz_m=root,native_root_support_sources=support,ground_datum_y_m=p['position_m'][1],native_root_embed_m=1.0,ownership_verified=True,routes_and_entrances_clear=True,native_above_ground_clear=True))
 assets={k:copy.deepcopy(w.assets[k])for k in sorted({p['asset_key']for p in accepted})}
 for k,a in assets.items():
  assert sha(ROOT/a['master_path'])==a['master_sha256'];assert sha(ROOT/a['render_path'])==a['render_sha256']
 pack=dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=BASE_SHA,common_assets=assets,add_instances=accepted,remove_instance_ids=[],inspection_cameras={'r9_noble_gardens':dict(position_m=[-76,112,-109],target_m=[-140,14,-235],ortho_size_m=210,render_size_px=[1536,1024]),'r9_clergy_gardens':dict(position_m=[372,119,-84],target_m=[263,14,-219],ortho_size_m=175,render_size_px=[1536,1024]),'r9_abbey_gardens':dict(position_m=[-164,107,307],target_m=[-306,8,111],ortho_size_m=220,render_size_px=[1536,1024])})
 write(HERE/'pack.json',pack);write(HERE/'placement_ledger.json',dict(schema='riverstone.city.owned_planting_ledger.v1',proposals=proposed,accepted=ledger,rejected=rejected,owners={k:v for k,v in w.owners.items()if any(c['owner']==k for c in proposed)}))
 affected=[]
 for r in w.routes:
  hits=[];pts=[[v[0],v[2]]for v in r['points_xyz_m']]
  for p in accepted:
   poly=ring(assets[p['asset_key']]['bounds'],p)
   if any(math.dist(a,b)>1e-8 and overlap(poly,geo.road_ribbon(a,b,20))for a,b in zip(pts,pts[1:])):hits.append(p['id'])
  if hits:affected.append(dict(route_id=r['id'],directions=2 if r.get('bidirectional')else 1,nearby_within_10m_instance_ids=hits,static_route_exclusion_clear=True))
 report=dict(schema='riverstone.city.owned_planting_static_review.v1',status='PASS',base_scene=ref(BASE),pack=ref(HERE/'pack.json'),source_refs=[ref(p)for p in [PROP,LAND,CATALOG,PHASE1,PHASE2,PLAN,Path(__file__)]],proposal_count=len(proposed),accepted_instances=len(accepted),rejected_candidates=len(rejected),instances_by_owner=dict(collections.Counter(p['source_owner']for p in accepted)),native_asset_count=len(assets),native_instances_inspected=w.native_instances,native_top_faces_tested=w.native_source_quads,native_cache_refs=w.asset_refs,reservation_polygons_checked=len(w.reserve.rows),public_route_count=len(w.routes),public_directional_case_count=sum(2 if r.get('bidirectional')else 1 for r in w.routes),affected_routes=affected,maximum_local_fit_m=max(r['local_fit_m']for r in ledger),whole_city_compile=False,new_asset_compiles=0,terrain_mutations=0,base_instances_removed=0,full_canopy_contained_with_owner_margin_m=.15,route_and_entrance_additional_margin_m=.2,native_clearance_additional_margin_m=.15,new_canopy_spacing_margin_m=.3,root_support_rule='Entire native 1 x 1 m cypress or 2 x 2 m hazel root footprint covered by retained actual native top faces or flat scene triangles at owner datum.',native_obstacle_rule='Every retained upward-facing native quad above owner floor projected into XZ, preserving actual courtyard gaps and excluding wall caps, roof overhangs, beds, trees and props.',limits=['Static native/owner/route checks only; no new capsule or full-controller replay claimed.','Existing native root embedding remains 1 m; every added instance remains scale 1.','Root preview integration and close-camera visual review required.'],seconds=round(time.monotonic()-started,3))
 write(HERE/'static_clearance_report.json',report);print(json.dumps({k:report[k]for k in ['status','accepted_instances','rejected_candidates','instances_by_owner','native_instances_inspected','native_top_faces_tested','seconds']}),flush=True)
 print('Rejected',[(r['id'],r['initial_rejection_reasons'][:4])for r in rejected],flush=True);return report
if __name__=='__main__':build()
