"""Bounded common-grid support for the exact southern abbey bearing cells."""
import json,hashlib,math,time
from pathlib import Path
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
from ..r13_precinct_interfaces import materials as terrain
HERE=Path(__file__).resolve().parent;CITY=terrain.CITY;ROOT=CITY.parents[1];geo=terrain.geo
PACK_PATH=CITY/'assemblies/landmarks/registered/precinct_r04/resolved_placements.json'
PACK_SHA='a351eb3dfed14c2218a7f7c39720f09c578952de3ccb9db1ce4de1175f5df83a'
ORIGIN=[-330,0,240];PITCH=.5;BOTTOM=2.;TOP=7.5;CAP=10000
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
if sha(PACK_PATH)!=PACK_SHA:raise ValueError('Precinct support source changed')
PACK=json.loads(PACK_PATH.read_bytes());BEARINGS=[r for r in PACK['actual_bearing_footprints'] if r['maximum_vertex_gap_m']>1e-6]

def master():
 ops=[]
 for i,r in enumerate(BEARINGS):
  p=terrain.polygon(r['polygon_xz_m'])
  assert r['bottom_y_m']==TOP and r['finished_floor_y_m']==8
  assert all(abs(v/PITCH-round(v/PITCH))<1e-8 for q in p for v in q)
  ops.append(dict(id='exact_native_bearing_'+str(i),part='solid',action='paint',material='stone',shape=dict(kind='extrusion',polygon=[[x-ORIGIN[0],-(z-ORIGIN[2])] for x,z in p],z_min=BOTTOM,z_max=TOP),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
 return dict(schema='riverstone.voxel.master.v1',id='registered_abbey_bearing_support_r14',revision=14,axes=dict(up='+Y',front='+Z',right='+X'),grid_origin=[0,0,0],materials={'stone':'7e8075'},components=[dict(id='bearing_union',parts=[dict(id='solid',pivot=[0,0,0])],operations=ops)],instances=[dict(id='bearing_union',component='bearing_union')],metadata=dict(source_pack_sha256=PACK_SHA,world_origin_m=ORIGIN,world_grid_origin_m=[0,0,0],pitch_m=PITCH,owned_bearing_ids=[r['id'] for r in BEARINGS],top_y_m=TOP,bottom_y_m=BOTTOM,policy='Exact native half-metre bearing footprints only. Union removes internal support faces. Native precinct contact faces remain buried at the unchanged floor; no cross-mesh hidden-face removal claim.'))

def preflight():
 roads=[r for r in terrain.prior.r07._owners() if r['kind']=='road'];roadindex=geo._SpatialIndex(16)
 for i,r in enumerate(roads):roadindex.add(i,r['polygon_xz_m'])
 conflicts=[];samples=[]
 for r in BEARINGS:
  p=r['polygon_xz_m'];ps=p+[[sum(q[k] for q in p)/len(p) for k in (0,1)]]
  heights=[terrain.land_height_at(*q) for q in ps];samples.append(dict(bearing_id=r['id'],land_min_m=min(heights),land_max_m=max(heights),bottom_burial_min_m=min(heights)-BOTTOM,top_contact_y_m=TOP))
  for i in roadindex.candidates(p):
   q=terrain.polygon(geo.convex_intersection(p,roads[i]['polygon_xz_m']))
   if q:conflicts.append(dict(bearing_id=r['id'],road_id=roads[i]['road_id'],polygon_xz_m=q,area_m2=geo.polygon_area(q)))
  for w in terrain.finite_water_polygons():
   q=terrain.polygon(geo.convex_intersection(p,w['polygon_xz_m']))
   if q:conflicts.append(dict(bearing_id=r['id'],water_id=w['surface_id'],polygon_xz_m=q,area_m2=geo.polygon_area(q)))
 b=candidate_budget(master(),PITCH)
 result=dict(schema='riverstone.precinct_native_support.preflight.v1',source_pack_sha256=PACK_SHA,bearing_count=len(BEARINGS),projected_area_m2=sum(geo.polygon_area(r['polygon_xz_m']) for r in BEARINGS),pitch_m=PITCH,world_origin_m=ORIGIN,bottom_y_m=BOTTOM,top_y_m=TOP,maximum_visible_fill_m=5.3,candidate_budget=b,compile_candidate_cap=CAP,compile_output_cap=CAP,support_samples=samples,road_water_conflicts=conflicts,no_citywide_compile=True)
 assert not conflicts and min(s['bottom_burial_min_m'] for s in samples)>=.2-1e-8
 write(HERE/'support_preflight.json',result);return result

def run():
 pre=preflight();m=master();mp=HERE/'support/abbey_support.master.json';write(mp,m)
 start=time.monotonic();compiled=coordinate_planes.compile_master(m,{'pitch':PITCH},max_candidate_cells=CAP,max_output_cells=CAP)
 assert compiled['valid'];render=render_data.make_render_data(compiled);cp=HERE/'support/abbey_support.compiled.json';rp=HERE/'support/abbey_support.render.json';write(cp,compiled);write(rp,render)
 record=dict(schema='riverstone.precinct_native_support.resolved.v1',source_pack_sha256=PACK_SHA,asset_key=m['id'],source={'path':str(mp.relative_to(ROOT)),'sha256':sha(mp)},cache={'path':str(rp.relative_to(ROOT)),'sha256':sha(rp)},position_m=ORIGIN,yaw_rad=0,scale=[1,1,1],pitch_m=PITCH,cell_count=render['cell_count'],quad_count=render['quad_count'],candidate_cells=compiled['candidate_cells'],elapsed_s=time.monotonic()-start,bounds=render['bounds'],bearing_contract=BEARINGS,status='bounded native support candidate; exact union coverage test pending')
 write(HERE/'support/resolved_support.json',record);return record
if __name__=='__main__':
 import sys
 print(json.dumps(run() if '--compile' in sys.argv else preflight(),indent=2))
