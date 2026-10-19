"""Finite registered reservoir solids built with the existing common grammar."""
import copy,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'world_city/concept_city_v3/assemblies/landmarks/registered'))
from build_audit import ref,write,source_bounds,estimate_candidates,pose
from world_city.runtime_city.parts.author import Source,extrusion,approved_palette
from world_city.concept_city_v3.assemblies.waterworks import author as staged
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_topography import author as water
CONTRACT=ROOT/'world_city/concept_city_v3/registered_topography/revisions/r02_assembly_overlay/contract.json'
DATA=json.loads(CONTRACT.read_text());BASIN=next(w for w in DATA['water_surfaces'] if w['id']=='NORTHERN_RESERVOIR');ORIGIN=[-30.,16.,-366.]
PITCH=.2


def final(a,role):
 s=a.finish();s['id']='registered_reservoir_'+a.kind;s['materials']=approved_palette('slate_gray');s['provenance'].update(registered_reservoir_author=ref(Path(__file__)),registered_water_contract=ref(CONTRACT),reused_waterworks_factory=ref(Path(staged.__file__)),fictional_game_design=True,new_engine=False,new_mesher=False);s['extensions'].update(local_bounds_m=source_bounds(s),network_role=role,registered_source_origin_xyz_m=ORIGIN,actual_scene_loaded=False,actual_visual_review=False,fluid_surface_owner='Existing exact water domains; no opaque water material in this asset.');return s


def polygon_slab(a,name,polygon,low,high,material='stone_dark',component='lining'):
 a.op(name,extrusion([[x,-z] for x,z in polygon],low,high),material,component=component,transform={'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[0,0,0]})


def bed_source():
 a=Source('basin_bed',[-35,-2.7,-30],[35,-2.4,30]);polygon_slab(a,'registered_six_sided_bed',[[x-ORIGIN[0],z-ORIGIN[2]] for x,z in BASIN['polygon_xz_m']],-2.7,-2.4);a.support('excavated_bearing',[-35,-2.7,-30],[35,-2.6,30],'Exact polygon bed, backed by the existing excavation. Source slab0.3m; actual sampled top is checked at13.6m.');s=final(a,'raw_storage');s['extensions']['water_head_y_m']=16;s['extensions']['bed_top_y_m']=13.6;return s


def banks_source():
 a=Source('basin_perimeter',[-36,-2.7,-31],[36,3.1,31]);rows=[]
 for index,b in enumerate(DATA['water_support']['exterior_banks']):
  if b['surface_id']!='NORTHERN_RESERVOIR':continue
  p,q=b['from_xz_m'],b['to_xz_m'];length=math.dist(p,q);u=[(q[j]-p[j])/length for j in (0,1)];mid=[(p[j]+q[j])/2 for j in (0,1)];inside=[mid[0]-u[1]*.1,mid[1]+u[0]*.1];sign=-1 if geo.point_in_convex_polygon(inside,BASIN['polygon_xz_m'],0) else 1;lo,hi=(-.3,0) if sign<0 else (0,.3);rot={'basis':[[u[0],0,-u[1]],[0,1,0],[u[1],0,u[0]]],'translation':[mid[0]-ORIGIN[0],0,mid[1]-ORIGIN[2]]}
  a.box(f'lining_{index}',[-length/2,-2.7,lo],[length/2,1.7,hi],'stone',component='lining',transform=rot)
  a.box(f'coping_{index}',[-length/2,1.7,min(0,sign*.45)],[length/2,2,max(0,sign*.45)],'stone_light',component='coping',transform=rot)
  a.box(f'edge_guard_{index}',[-length/2,2,lo],[length/2,3.0,hi],'stone',component='guard',transform=rot)
  rows.append({'exterior_bank_contract_index':index,'record':b,'wall_thickness_m':.3,'dry_side_sign':sign})
 s=final(a,'raw_storage_protective_edge');s['extensions'].update(exact_exterior_bank_records=rows,openings_policy='Only the47 registered exterior faces are authored. Existing inlet and outlet mouths remain unfilled.',bank_y_m=18,protective_edge_top_y_m=19);return s


def source_inventory():
 entries=[{'id':'basin_bed','stage':'new_continuous_source','network':'raw_storage','role':'Exact six-sided bed lining at13.6, water stays16.'},{'id':'basin_perimeter','stage':'new_continuous_source','network':'raw_storage','role':'47 existing exterior bank intervals, coping18, protective edge19; actual water mouths retained.'}]
 for id,role in [('spring_intake','Source head24, existing2m feeder'),('sluice_bay','Raised2m outlet control, network-mapped to one-way overflow'),('covered_wellhouse','Dry bank-side drawpoint with head15.5 requires a registered shaft variant'),('covered_clean_conduit','Protected reservoir-to-cistern connection; route/invert still to be authored'),('canal_footbridge','Two finite service crossings at inlet/outlet if ring access is completed')]:
  entries.append({'id':id,'stage':'existing_compiled_local_master_not_registered_placement','network':'protected_supply' if id in ('covered_wellhouse','covered_clean_conduit') else 'raw_source_or_overflow','source':ref(staged.HERE/'masters'/f'{id}.json'),'role':role})
 for id,role in [('covered_cistern_shell','Separate physical covered tank on dry bank, linked to logical graph node'),('reservoir_service_apron','Finite18m apron joining existing RESERVOIR_SERVICE endpoint'),('settling_baffles','Inlet energy dissipation/settling geometry still missing'),('district_distribution','Full routes to cathedral/market/monastery draw nodes remain unresolved'),('safe_overflow_capacity','Flood-stage control, discharge and water quality unvalidated')]:entries.append({'id':id,'stage':'missing_registered_source_or_placement','role':role})
 return entries


def main():
 rows=[]
 for s in (bed_source(),banks_source()):
  path=HERE/'masters'/f"{s['id']}.json";write(path,s);estimate=estimate_candidates(s,PITCH)['candidate_cells_exact_aabb_visits'];rows.append({'id':s['id'],'source':ref(path),'candidate_cells':estimate,'pitch_m':PITCH});assert estimate<600000,(s['id'],estimate)
 value={'schema':'riverstone.city.registered_reservoir_preflight.v1','source_plan':ref(ROOT/'world_city/concept_city_v3/registered_source/plan.json'),'water_contract':ref(CONTRACT),'water_graph':DATA['water_graph'],'basin':BASIN,'source_origin_xyz_m':ORIGIN,'sources':rows,'inventory':source_inventory(),'budget':{'first_phase_new_sources':2,'candidate_cap_each':600000,'output_cap_each':200000,'pitch_m':PITCH,'sequential':True,'whole_city_compile':False},'service_reservations':[r for r in DATA['roads'] if r['id'] in ('RESERVOIR_SERVICE','NORTH_WATERKEEPER')],'logical_node_warning':'COVERED_CISTERN shares the reservoir-centre graph coordinate. A dry bank physical tank requires a separately recorded endpoint; this does not relocate the graph or district.','actual_placed':False,'actual_viewed':False,'hydraulic_or_potable_certification':False};write(HERE/'preflight.json',value);print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
