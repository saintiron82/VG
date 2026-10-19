"""Recovery revision of the optional reservoir service circuit, common grammar only."""
import sys,json,math,copy
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
from author_reservoir import ROOT,ORIGIN,BASIN,DATA,CONTRACT,Source,extrusion,approved_palette,ref,write,source_bounds,estimate_candidates,water,geo
from author_interfaces import CISTERN_ORIGIN
from world_city.runtime_city.urban_fabric.revisions.r3.probe import offset
from world_city.concept_city_v3.review_geometry import DomainCut
BRIDGES=[{'id':'SPRING','center_xyz_m':[-63.855338946835126,18,-371.706902924584],'yaw_degrees':111.62848186434645,'water_y_m':16.0548290214499},{'id':'NORTHERN_CHANNEL','center_xyz_m':[4.048146251639395,18,-360.7946330139951],'yaw_degrees':-60.47957740729323,'water_y_m':15.953174679088749}]
def slab(a,id,poly,low,high,action='paint'):
 a.op(id,extrusion([[x-ORIGIN[0],-(z-ORIGIN[2])] for x,z in poly],low-18,high-18),'stone_dark',action=action,component='service',transform={'basis':[[1,0,0],[0,0,1],[0,-1,0]]})
def source():
 a=Source('reservoir_service_walk_and_crossings_recovery_r07',[-40,-1,-35],[40,2,40]);outer=offset(BASIN['polygon_xz_m'],-2.6);inner=offset(BASIN['polygon_xz_m'],-.4)
 for i in range(len(outer)):slab(a,'ring_side_'+str(i),[outer[i],outer[(i+1)%len(outer)],inner[(i+1)%len(inner)],inner[i]],17.6,18)
 # Original inlet/outlet domains remain truly wet below raised crossing decks.
 wet=water.finite_water_polygons()
 for i,w in enumerate(wet):
  if w.get('surface_id',w.get('id'))!='NORTHERN_RESERVOIR' and geo.positive_area_overlap(w['polygon_xz_m'],outer,0):slab(a,'wet_keepout_'+str(i),offset(w['polygon_xz_m'],-.15),17.3,18.1,'cut')
 for b in BRIDGES:
  p=b['center_xyz_m'];ang=math.radians(b['yaw_degrees']);transform={'basis':[[math.cos(ang),0,math.sin(ang)],[0,1,0],[-math.sin(ang),0,math.cos(ang)]],'translation':[p[0]-ORIGIN[0],0,p[2]-ORIGIN[2]]}
  a.box(b['id']+'_deck',[-3.6,-.4,-1.4],[3.6,0,1.4],'timber',component='service',transform=transform)
  for x in (-3.3,3.3):a.box(b['id']+'_bearing_'+str(x),[x-.3,-.7,-.6],[x+.3,-.4,.6],'stone',component='service',transform=transform)
  for z in (-1.3,1.3):
   a.box(b['id']+'_rail_'+str(z),[-3.6,.8,z-.16],[3.6,1.2,z+.16],'timber',component='service',transform=transform)
   for x in (-3.4,-1.7,0,1.7,3.4):a.box(b['id']+f'_post_{x}_{z}',[x-.16,0,z-.16],[x+.16,1.2,z+.16],'timber_dark',component='service',transform=transform)
 # The base drawpoint is an existing independent native body; one top owner per piece.
 apron=[[CISTERN_ORIGIN[0]+x,CISTERN_ORIGIN[2]+z] for x,z in [(-4,-4),(10.4,-4),(10.4,6),(-4,6)]];slab(a,'existing_drawpoint_keepout',apron,17.2,19.3,'cut')
 s=a.finish();s['id']='registered_reservoir_service_walk_and_crossings_recovery_r07';s['grid_origin']=[0,0,(CISTERN_ORIGIN[2]-ORIGIN[2])%.2];s['materials']=approved_palette('slate_gray');s['provenance'].update(author=ref(Path(__file__)),base_pack=ref(HERE.parent/'resolved_placements.json'),water_contract=ref(CONTRACT),recovery='Reconstructed from dimensional handoff after workspace reset. Previous916e253a pack bytes were unavailable; fresh geometry and hashes require revalidation.');s['extensions'].update(local_bounds_m=source_bounds(s),registered_origin_xyz_m=[ORIGIN[0],18,ORIGIN[2]],walk_width_m=2.2,bridge_span_m=7.2,bridge_total_width_m=2.8,bridge_rail_inner_clear_width_m=2.28,bridge_deck_y_m=18,bridge_underside_y_m=17.6,bearing_bottom_y_m=17.3,bridges=BRIDGES,base_drawpoint_keepout_xz_m=apron,actual_placed=False,actual_viewed=False);return s
if __name__=='__main__':
 s=source();p=HERE/'masters'/f"{s['id']}.json";write(p,s);estimate=estimate_candidates(s,.2);assert estimate['candidate_cells_exact_aabb_visits']<600000;write(HERE/'preflight.json',{'source':ref(p),'estimate':estimate,'candidate_cap':600000,'output_cap':200000,'pitch_m':.2,'recovery_revision':7});print(estimate['candidate_cells_exact_aabb_visits'])
