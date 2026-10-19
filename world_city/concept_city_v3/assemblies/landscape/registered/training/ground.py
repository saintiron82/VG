"""One finite common solid for earth drill floor, peripheral courts and approach."""
import copy,json,math
from . import author as t
from .. import author as landscape
from world_city.concept_city_v3.assemblies.property.registered import author as a
from world_city.concept_city_v3.assemblies.property.registered.r1 import author as surfaces
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget

def build(pack=None):
 p=pack or json.loads((t.OUT/'source_pack.json').read_text());origin=[-330,-180];ops=[];regions=[];native=[x for x in p['placements'] if x.get('entrances')]
 # A half-cell-plus clearance preserves native foundation faces without
 # pretending the empty gap is a hole: the underlying level TRAIN bench remains.
 cuts=[]
 for x in native:
  b=x['local_bounds'];w=b['max'][0]-b['min'][0]+1;d=b['max'][2]-b['min'][2]+1;cuts.append(a.rect([x['position_m'][0],x['position_m'][2]],w,d,x['yaw_rad']))
 def floor(label,poly,material):
  pieces=[poly]
  for cut in cuts:pieces=[q for piece in pieces for q in a.geom.convex_difference(piece,cut) if a.geom.polygon_area(q)>1e-7]
  for j,poly in enumerate(pieces):
   regions.append(dict(id=label+':'+str(j),polygon_xz_m=poly,material=material,floor_y_m=t.FLOOR));ops.append(dict(id=label+':'+str(j),part='solid',action='paint',material=material,shape=dict(kind='extrusion',polygon=[[q[0]-origin[0],-(q[1]-origin[1])] for q in poly],z_min=-.5,z_max=0),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
 for i,tri in enumerate(a.triangulate(t.CORE)):floor('TRAIN:central_drill:'+str(i),tri,'earth')
 for label,pos,w,d,yaw in [('barrack_court',[-383,-187],7,37,0),('stable_court',[-350,-153],25,7,-.38),('store_court',[-372,-161],12,7,-.38),('practice_edge',[-365,-217],35,7,.38)]:
  poly=a.rect(pos,w,d,yaw);assert a.contained(poly,p['source_space']['polygon_xz_m']);floor('TRAIN:'+label,poly,'earth')
 for r in p['internal_routes']:
  for j,poly in enumerate(r['ribbon_polygons_xz_m']):floor(r['id']+':'+str(j),poly,'earth' if r.get('kind')=='open_field_access' else 'stone_light')
 m=landscape.standard('registered_training_ground',ops);m['metadata']=dict(origin_xz_m=origin,floor_y_m=t.FLOOR,one_solid_owned_ground_and_approach=True,source_space_id=t.SITE,central_open_area_m2=a.geom.polygon_area(t.CORE),owned_floor_regions=regions,no_broad_precinct_floor=True)
 surfaces.append_surface(m,p['external_surface'],origin,t.FLOOR);m['id']='registered_training_ground_'+a.sha(m['components'])[:12];budget=candidate_budget(m);assert budget['within_candidate_cap'];path=t.OUT/(m['id']+'.master.json');t.write(path,m);record=dict(id='TRAIN:owned_ground',asset_key=m['id'],source_path=str(path.relative_to(t.c.ROOT)),source_sha256=a.file_sha(path),resource={'pitch':.5},candidate_budget=budget,position_m=[origin[0],t.FLOOR,origin[1]],yaw_rad=0,scale=[1,1,1],owned_floor_regions=regions,external_surface=p['external_surface']);t.write(t.OUT/'ground_wrapper.json',record);print(json.dumps(dict(wrapper=m['id'],budget=budget)),flush=True);return record
if __name__=='__main__':build()
