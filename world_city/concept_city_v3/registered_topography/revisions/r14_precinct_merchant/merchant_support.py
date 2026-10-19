"""Native coarse foundation fill under the raised M11 merchant compound only."""
import json,math,time
from pathlib import Path
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
from . import author as a
from .support import sha,write
HERE=a.HERE;PITCH=.5;TOP=3.5;BOTTOM=.5;CAP=50000
POSE=next(r for r in a.MERCHANT['placements'] if r['id']=='M11_SHOP_COURT:front');ORIGIN=[POSE['position_m'][0],0,POSE['position_m'][2]];YAW=POSE['yaw_rad'];C=math.cos(YAW);S=math.sin(YAW)
POLYS=next(r['native_foundation_regions_xz_m'] for r in a.HANDOFF['properties'] if r['property_id']=='M11_SHOP_COURT')
def local(p):
 x,z=p[0]-ORIGIN[0],p[1]-ORIGIN[2];q=[C*x-S*z,S*x+C*z]
 assert all(abs(v/PITCH-round(v/PITCH))<1e-7 for v in q)
 return [round(v/PITCH)*PITCH for v in q]
def world(x,z):return [ORIGIN[0]+C*x+S*z,ORIGIN[2]-S*x+C*z]
def master():
 ops=[]
 for i,p in enumerate(POLYS):
  q=[local(v) for v in p];ops.append(dict(id='native_foundation_'+str(i),part='solid',action='paint',material='stone',shape=dict(kind='extrusion',polygon=[[x,-z] for x,z in q],z_min=BOTTOM,z_max=TOP),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
 return dict(schema='riverstone.voxel.master.v1',id='registered_merchant_m11_support_r14',revision=14,axes=dict(up='+Y',front='+Z',right='+X'),grid_origin=[0,0,0],materials={'stone':'7e8075'},components=[dict(id='support',parts=[dict(id='solid',pivot=[0,0,0])],operations=ops)],instances=[dict(id='support',component='support')],metadata=dict(source_pack_sha256=a.REFERENCES['assemblies/property/registered/merchant_block011/resolved_placements.json'],pose_origin_m=ORIGIN,yaw_rad=YAW,grid_contract='Same rigid native property frame and0.5m pitch as its building foundation sections; source world Y planes at0.5 and3.5.',native_foundation_polygons_xz_m=POLYS,policy='Exact raised M11 native foundation sections only; six lower flat compounds retain their embedded native plinths. No broad platform microfill.'))
def preflight():
 m=master();b=candidate_budget(m,PITCH);samples=[]
 for poly in POLYS:
  q=[local(p) for p in poly];x0=min(v[0] for v in q);x1=max(v[0] for v in q);z0=min(v[1] for v in q);z1=max(v[1] for v in q)
  for ix in range(round(x0*2),round(x1*2)+1):
   for iz in range(round(z0*2),round(z1*2)+1):
    x,z=ix/2,iz/2
    if a.geo.point_in_convex_polygon([x,z],q,1e-8):samples.append(a.prior.land_height_at(*world(x,z)))
 result=dict(schema='riverstone.merchant_native_support.preflight.v1',source_pack_sha256=a.REFERENCES['assemblies/property/registered/merchant_block011/resolved_placements.json'],candidate_budget=b,hard_candidate_cap=CAP,foundation_regions=len(POLYS),source_area_m2=sum(a.geo.polygon_area(p) for p in POLYS),minimum_sampled_inherited_ground_y_m=min(samples),maximum_sampled_inherited_ground_y_m=max(samples),sample_count=len(samples),bottom_y_m=BOTTOM,top_y_m=TOP,minimum_burial_m=min(samples)-BOTTOM,native_top_contact_y_m=TOP,grid_contract=m['metadata']['grid_contract'])
 assert min(samples)-BOTTOM>=.25 and b['exact_candidate_visits_without_cell_sampling']<CAP
 write(HERE/'merchant_support_preflight.json',result);return result

def run():
 pre=preflight();m=master();mp=HERE/'support/merchant_support.master.json';write(mp,m);start=time.monotonic();c=coordinate_planes.compile_master(m,{'pitch':PITCH},max_candidate_cells=CAP,max_output_cells=CAP);assert c['valid'];r=render_data.make_render_data(c);cp=HERE/'support/merchant_support.compiled.json';rp=HERE/'support/merchant_support.render.json';write(cp,c);write(rp,r)
 d=dict(schema='riverstone.merchant_native_support.resolved.v1',asset_key=m['id'],source={'path':str(mp.relative_to(a.ROOT)),'sha256':sha(mp)},cache={'path':str(rp.relative_to(a.ROOT)),'sha256':sha(rp)},position_m=ORIGIN,yaw_rad=YAW,scale=[1,1,1],pitch_m=PITCH,cell_count=r['cell_count'],quad_count=r['quad_count'],candidate_cells=c['candidate_cells'],elapsed_s=time.monotonic()-start,bounds=r['bounds'],ownership_polygons_xz_m=POLYS,source_pack_sha256=pre['source_pack_sha256'],top_y_m=TOP,bottom_y_m=BOTTOM,status='native support candidate; exact contact coverage audit pending')
 write(HERE/'support/resolved_merchant_support.json',d);return d
if __name__=='__main__':
 import sys
 print(json.dumps(run() if '--compile' in sys.argv else preflight(),indent=2))
