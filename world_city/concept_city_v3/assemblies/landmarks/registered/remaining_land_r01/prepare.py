"""Source-only remaining-land review. Conservative 0.5 m cells; no scene edits."""
import sys,json,math,hashlib
from pathlib import Path
import numpy as np
from scipy import ndimage
HERE=Path(__file__).resolve().parent; PREV=HERE.parent/'coverage_r5_draft_01'; ROOT=HERE.parents[5];CITY=ROOT/'world_city/concept_city_v3'
sys.path[:0]=[str(PREV),str(ROOT)]
from account_coverage import layer_from,load,ref,write,BOUNDS,PITCH,SHAPE,xform
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_source.geometry import triangulate

def layer(ps,concave=True):return layer_from(ps,concave)
def mask(ps,mode=1,concave=True):return layer(ps,concave)[mode]
def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def buffer(m,d):return ndimage.distance_transform_edt(~m)*PITCH<=d

def build():
 p=load(CITY/'registered_source/plan.json');r=np.load(PREV/'plan_raster.npz');elig=load(CITY/'assemblies/property/registered/merchant_fabric_r02/effective_eligibility.json');hand=load(CITY/'assemblies/property/registered/merchant_fabric_r02/terrain_handoff.json');water=load(CITY/'registered_topography/revisions/r02_assembly_overlay/contract.json')
 domains={b['id']:layer([b['polygon_xz_m']])for b in p['blocks']if b['id']in['BLOCK_003','BLOCK_005','BLOCK_015']};domains.update({s['id']:layer([s['polygon_xz_m']])for s in p['spaces']if s['id']in['SITE_CLERGY','SITE_MONASTERY']})
 public=[geo.road_ribbon(a,b,road['width_m'])for road in p['roads']for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])];public+=[geo.road_ribbon(a,b,road.get('width_m',1.8))for road in p['paths']for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])]
 mer=[]
 for q in elig['properties']:
  mer.append(q['polygon_xz_m']);mer.append(q['external_gate_link']['polygon_xz_m'])
  for route in q['internal_routes']:mer+=route['ribbon_polygons_xz_m']+route['round_join_polygons_xz_m']
 for q in hand['properties']:mer+=q['retained_lower_ground']['polygons_xz_m']
 wm=mask([q['polygon_xz_m']for q in water['water_domain_polygons']],2)
 wall=p['wall_registration']['polygon_xz_m']; wall_polys=[geo.road_ribbon(a,b,24)for a,b in zip(wall,wall[1:]+wall[:1])]
 reservations={'wall_and_tower_review_corridor':mask(wall_polys,2),'public_and_existing_private_access':buffer(mask(public,2),.75),'native_roof_clearance':buffer(r['roof'],1.0),'pending_merchant_19':buffer(mask(mer,2),.75),'wet_bank_and_service_clearance':buffer(wm,4.0)}
 # Existing plots remain intact. Land-use change requires its own explicit retirement proposal.
 ordinary_res=buffer(mask([s['polygon_xz_m']for s in p['spaces']]+[q['polygon_xz_m']for q in p['plots']],2),.75)
 precinct_res=buffer((r['precinct_classes']>0)&(r['precinct_classes']<9),.75)
 common=np.logical_or.reduce(list(reservations.values()))
 domain_polys={b['id']:b['polygon_xz_m']for b in p['blocks']+p['spaces']if b['id']in domains}
 # Center union minus a conservative 0.75 m true-boundary band avoids artificial
 # gaps along internal triangulation seams while retaining whole-cell containment.
 available={}
 for k,d in domains.items():
  q=domain_polys[k];edge=mask([geo.road_ribbon(a,b,1.5)for a,b in zip(q,q[1:]+q[:1])if math.dist(a,b)>1e-8],2,False)
  available[k]=d[1]&~edge&~common&~(ordinary_res if k.startswith('BLOCK')else precinct_res)
 noble=mask([d['polygon_xz_m']for d in p['districts']if d['id']=='D_NOBLE'],1)
 np.savez_compressed(HERE/'review_masks.npz',**available,public=reservations['public_and_existing_private_access'],merchant=reservations['pending_merchant_19'],water=reservations['wet_bank_and_service_clearance'],roof=r['roof'],noble=noble,precinct_classes=r['precinct_classes'])
 refs=[CITY/'registered_source/plan.json',PREV/'coverage_accounting.json',PREV/'plan_raster.npz',CITY/'assemblies/property/registered/merchant_fabric_r02/effective_eligibility.json',CITY/'assemblies/property/registered/merchant_fabric_r02/terrain_handoff.json',CITY/'registered_topography/revisions/r02_assembly_overlay/contract.json']
 write(HERE/'input_refs.json',{'schema':'riverstone.remaining_land.inputs.v1','source_refs':[ref(q)for q in refs],'merchant_count':len(elig['properties']),'available_before_new_program_m2':{k:float(v.sum())*PITCH**2 for k,v in available.items()},'method':'Whole-cell interior clip, touch-cell obstacle exclusion, then explicit metric clearance. Source-only 0.5 m analysis grid, not authoring an engine or mesher.'})
 print({k:float(v.sum())*PITCH**2 for k,v in available.items()},flush=True)
if __name__=='__main__':build()
