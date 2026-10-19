"""R8 route-first whole-city source plan. Read-only native caches; no compile/GUI.
All output is confined to this directory. Run from repository root with
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/mpl python -m <module>.
"""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/r8-coverage-mpl')
import sys,json,math,hashlib,time,collections,heapq
from pathlib import Path
import numpy as np
from scipy import ndimage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];CITY=ROOT/'world_city/concept_city_v3'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(CITY/'assemblies/landmarks/registered/coverage_r5_draft_01'))
from project_native import classify_roof_materials,roof_rectangles,cells_to_rectangles
from world_city.concept_city_v3.registered_source.geometry import triangulate
from world_city.runtime_city.checks import placement as geo
PITCH=1.;BOUNDS=(-540.,-540.,540.,660.);NX=int((BOUNDS[2]-BOUNDS[0])/PITCH);NZ=int((BOUNDS[3]-BOUNDS[1])/PITCH);SHAPE=(NZ,NX)
SCENE=CITY/'evidence/visual_registered_common_r7_palette_r01/scene.json';SHA='1429ae51b7c72b12940dcf0dd7e12c2684cab95f81735d228bba64dc819317c1'
NATIVE_BUILD_PACKS={'ordinary','ordinary_density','ordinary_density_b15','merchant_compounds','merchant_seven_r02','working_ranges_r01'}
PRESERVE_PACKS={'ordinary_density','ordinary_density_b15','merchant_compounds','merchant_seven_r02','working_ranges_r01','working_courts_phase01','b13_workyards','productive_grounds_phase01','precinct_belts','precinct_support','merchant_support','abbey_guard'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def write(name,d): (HERE/name).write_text(json.dumps(d,indent=2)+'\n')
def ref(p):return {'path':str(Path(p).relative_to(ROOT)),'sha256':sha(p)}
def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def xform(p,i):
 c=math.cos(i['yaw_rad']);s=math.sin(i['yaw_rad']);x,y,z=i['position_m'];return [[x+c*q[0]+s*q[1],z-s*q[0]+c*q[1]]for q in p]
def add(m,p):
 if len(p)<3 or geo.polygon_area(p)<1e-9:return
 x0=max(0,math.floor((min(q[0]for q in p)-BOUNDS[0])/PITCH));x1=min(NX,math.ceil((max(q[0]for q in p)-BOUNDS[0])/PITCH));z0=max(0,math.floor((min(q[1]for q in p)-BOUNDS[1])/PITCH));z1=min(NZ,math.ceil((max(q[1]for q in p)-BOUNDS[1])/PITCH))
 if x0>=x1 or z0>=z1:return
 xs=BOUNDS[0]+(np.arange(x0,x1)+.5)*PITCH;zs=BOUNDS[1]+(np.arange(z0,z1)+.5)*PITCH;inside=np.ones((z1-z0,x1-x0),bool);sgn=1 if geo.signed_polygon_area(p)>0 else -1
 for a,b in zip(p,p[1:]+p[:1]):inside &=sgn*((b[0]-a[0])*(zs[:,None]-a[1])-(b[1]-a[1])*(xs[None,:]-a[0]))>=-1e-8
 m[z0:z1,x0:x1]|=inside

def mask(ps,concave=False):
 m=np.zeros(SHAPE,bool)
 for p in ps:
  for t in (triangulate(p) if concave else [p]):add(m,t)
 return m

def buffer(m,d):return ndimage.distance_transform_edt(~m)*PITCH<=d

def parts(m):
 out=[];active={}
 zz,xx=np.where(m)
 if not len(xx):return []
 for z in range(int(zz.min()),int(zz.max())+2):
  row=m[z]if z<SHAPE[0]else np.zeros(NX,bool);edges=np.flatnonzero(np.diff(np.r_[False,row,False]));runs=list(zip(edges[::2],edges[1::2]));new={}
  for run in runs:new[run]=active.pop(run,z)
  for (x0,x1),z0 in active.items():out.append(rect(BOUNDS[0]+int(x0)*PITCH,BOUNDS[1]+z0*PITCH,BOUNDS[0]+int(x1)*PITCH,BOUNDS[1]+z*PITCH))
  active=new
 return out

def ribbon(line,w):return [geo.road_ribbon(a,b,w)for a,b in zip(line,line[1:])if math.dist(a,b)>1e-8]
def area(m):return int(m.sum())*PITCH**2

def project():
 start=time.monotonic();assert sha(SCENE)==SHA;s=load(SCENE);p=load(CITY/'registered_source/plan.json');old=load(CITY/'assemblies/landmarks/registered/coverage_r5_draft_01/asset_projection_proofs.json')['assets'];assets={};by=collections.defaultdict(set)
 for i in s['common_instances']:by[i['asset_key']].add(i['source_pack'])
 for n,(key,a) in enumerate(s['common_assets'].items()):
  needed=bool(by[key]&(NATIVE_BUILD_PACKS|PRESERVE_PACKS))
  if not needed:continue
  mp,rp=ROOT/a['master_path'],ROOT/a['render_path'];assert sha(mp)==a['master_sha256'];assert sha(rp)==a['render_sha256'];master=load(mp);r=load(rp)
  if key in old and old[key]['master']['sha256']==a['master_sha256']and old[key]['render']['sha256']==a['render_sha256']:
   roofs=old[key]['roof_rectangles_local_xz_m'];proof=old[key]['roof_proof'];method='hash_identical_R5_native_projection_reused_for_actual_R7_instance'
  else:
   selected,proof=classify_roof_materials(master,r,by[key]);roofs,rproof=roof_rectangles(r,selected,proof['operation_geometry_selectors']);proof.update(rproof);method='current_R7_native_cache_projection'
  # Full solid projection from all horizontal native exterior faces. Includes
  # native floor slabs and courts; these are owner exclusions, never roofs.
  full,fullproof=roof_rectangles(r,{g['material']for g in r['groups']})
  assets[key]={'source_packs':sorted(by[key]),'master':ref(mp),'render':ref(rp),'roof_parts_local_xz_m':roofs,'native_owner_parts_local_xz_m':full,'roof_classification':proof,'projection_method':method,'native_owner_projection_proof':fullproof}
  if n%20==0:print('project',n,key,flush=True)
 rows=[];roof=np.zeros(SHAPE,bool);ordinary=np.zeros(SHAPE,bool);retained=np.zeros(SHAPE,bool);native_total=np.zeros(SHAPE,bool)
 for i in s['common_instances']:
  if i['asset_key']not in assets:continue
  a=assets[i['asset_key']];rp=[xform(q,i)for q in a['roof_parts_local_xz_m']];fp=[xform(q,i)for q in a['native_owner_parts_local_xz_m']];rm=mask(rp);fm=mask(fp);roof|=rm;native_total|=fm
  if i['source_pack']=='ordinary':ordinary|=rm
  elif i['source_pack']in PRESERVE_PACKS:retained|=fm
  rows.append({'id':i['id'],'asset_key':i['asset_key'],'source_pack':i['source_pack'],'position_m':i['position_m'],'yaw_rad':i['yaw_rad'],'roof_parts_xz_m':rp,'native_owner_parts_xz_m':fp,'roof_area_m2':sum(geo.polygon_area(q)for q in rp),'native_owner_area_m2':sum(geo.polygon_area(q)for q in fp)})
 source_roads=[q for r in p['roads']for q in ribbon(r['polyline_xz_m'],r['width_m'])];road=mask(source_roads);spaces=mask([q['polygon_xz_m']for q in p['spaces']],True);estates=mask([q['polygon_xz_m']for q in p['plots']if q['land_use']=='enclosed_noble_compound'],True);water=mask([q['polygon_xz_m']for q in p['water_reservations']['finite_water_polygons']],True);wall=mask(ribbon(p['wall_registration']['polygon_xz_m']+[p['wall_registration']['polygon_xz_m'][0]],24))
 # Explicit finite native/pack footprint masks are protected. New geometry must
 # also preserve all retained actual door paths; provisional detached-house
 # source doors may retire only with their named building.
 retain_ids={i['id']for i in s['common_instances']if i['source_pack']!='ordinary'}
 access=[]
 for q in p['paths']:
  if q.get('owner_building_id')in retain_ids or q.get('owner_plot_id','').startswith('E'):access+=ribbon(q['polyline_xz_m'],q.get('width_m',1.8))
 access_mask=mask(access)
 domain=np.zeros(SHAPE,np.uint8);block_rows=[]
 for bi,b in enumerate(p['blocks'],1):
  bm=mask([b['polygon_xz_m']],True);assert not np.any((domain>0)&bm),b['id'];domain[bm]=bi
  protected=bm&(spaces|estates|water|road|wall|retained|access_mask);ordinary_domain=bm&~(spaces|estates|water|road|wall|retained|access_mask)
  exact=geo.polygon_area(b['polygon_xz_m']);block_rows.append({'block_id':b['id'],'district_id':b['district_id'],'polygon_xz_m':b['polygon_xz_m'],'boundary_road_ids':b['boundary_road_ids'],'source_gross_area_m2':exact,'planning_grid_gross_m2':area(bm),'protected_or_retained_m2':area(protected),'ordinary_replanning_domain_m2':area(ordinary_domain),'actual_R7_detached_roof_in_domain_m2':area(ordinary_domain&ordinary),'actual_R7_all_screened_roof_m2':area(bm&roof),'ordinary_unroofed_replanning_domain_m2':area(ordinary_domain&~roof),'status':'unfinished; native presence is not functional completion','ordinary_replanning_polygon_parts_xz_m':parts(ordinary_domain)})
 np.savez_compressed(HERE/'baseline_masks.npz',roof=roof,ordinary_roof=ordinary,retained_native=retained,road=road,spaces=spaces,estates=estates,water=water,wall=wall,retained_access=access_mask,block_labels=domain,pitch=PITCH,bounds=BOUNDS)
 write('native_projection.json',{'schema':'riverstone.r8.actual_native_plan_projection.v1','scene':ref(SCENE),'method':'Exact local native exterior horizontal face projection, transformed by each actual R7 native instance; 1 m plan center-sampled union for accounting. No old design building counts or cache AABB areas. Native owners include actual floors/courts and are not counted as roofs.','assets':assets,'instances':rows,'seconds':time.monotonic()-start})
 write('baseline_blocks.json',{'scene':ref(SCENE),'source_plan':ref(CITY/'registered_source/plan.json'),'source_controls':ref(CITY/'registered_source/road_controls.json'),'blocks':block_rows,'grid_pitch_m':PITCH,'measurement_note':'Exact source polygon areas; category areas are 1 m center samples with max corner radius 0.707107 m. This is not an exact vector boolean area. Replanning excludes traced institutional spaces, noble estate plots, public roads, water, 12 m conservative wall corridor and actual retained finite native owner footprints. Ordinary detached plots may be consolidated only by listed native ID retirement.','summary':{'block_count':len(block_rows),'actual_scene_instances':len(s['common_instances']),'actual_detached_instances':sum(i['source_pack']=='ordinary'for i in s['common_instances']),'ordinary_replanning_domain_m2':sum(r['ordinary_replanning_domain_m2']for r in block_rows),'ordinary_unroofed_replanning_domain_m2':sum(r['ordinary_unroofed_replanning_domain_m2']for r in block_rows)}})
 print('baseline',[(q['block_id'],q['ordinary_replanning_domain_m2'])for q in block_rows],flush=True)

if __name__=='__main__':project()
