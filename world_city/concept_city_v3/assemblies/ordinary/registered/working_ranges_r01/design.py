"""Four bounded attached lower-city range families; immutable common sources only."""
from pathlib import Path
import copy,json,math,hashlib
from world_city.runtime_city.archetypes import ordinary_r2
from world_city.concept_city_v3.assemblies.property.registered.merchant_fabric_r02.prepare_cache import make_master as union_master
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.compile_rows import count_master
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[5];CITY=ROOT/'world_city/concept_city_v3'
PLAN=CITY/'assemblies/landmarks/registered/remaining_land_r01'
R5=CITY/'evidence/visual_registered_common_r5'
PITCH=.5

def ref(p):
 p=Path(p);return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def write(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def load(p):return json.loads(Path(p).read_text())
def xform(q,origin,yaw):
 c,s=math.cos(yaw),math.sin(yaw);return [origin[0]+c*q[0]+s*q[1],origin[1]-s*q[0]+c*q[1]]
def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def spec(w,d,kind,style,floors,fh,pitch,era,roof='gable',units=1):return dict(width_m=w,depth_m=d,assembly_class=kind,style=style,floors=floors,floor_height_m=fh,roof_pitch_degrees=pitch,construction_era=era,roof_form=roof,attached_units=units)
FAMILIES={
 'market_lodging':dict(parcel_id='B15_MARKET_LODGING:RANGE:1',holding_id='B15_MARKET_LODGING:1',palette='clay_red',flip=False,role='Attached poorer market lodgings and shared repair front',modules=[('shared_lodging_west',spec(8,9,'poor_row','old_timber',2,2.5,44,'early',units=2)),('low_repair_front',spec(9,9,'regular_house','artisan',1,3,32,'rebuilt')),('shared_lodging_east',spec(9,9,'poor_row','old_timber',2,2.5,39,'late',units=2))]),
 'bank_joinery':dict(parcel_id='B15_UPPER_BANK_WORK:RANGE:1',holding_id='B15_UPPER_BANK_WORK:1',palette='wood_brown',flip=True,role='Older joinery/repair range with low dry store and working fronts',modules=[('joinery_bay',spec(10,10,'regular_house','artisan',1,3.25,36,'early')),('low_dry_store',spec(11,10,'regular_house','port',1,3.25,17,'early',roof='shed')),('repair_bay',spec(11,10,'regular_house','artisan',1,3.25,32,'rebuilt'))]),
 'bank_loft_store':dict(parcel_id='B15_UPPER_BANK_WORK:RANGE:2',holding_id='B15_UPPER_BANK_WORK:1',palette='slate_gray',flip=False,role='Fire-conscious dry goods loft range, broad handling doors and high storage windows',modules=[('west_low_store',spec(10,10,'regular_house','port',1,3.5,34,'rebuilt')),('central_loft_store',spec(11,10,'regular_house','port',2,2.75,38,'rebuilt')),('east_low_store',spec(11,10,'regular_house','port',1,3.5,30,'early'))]),
 'bank_craft_lodging':dict(parcel_id='B15_UPPER_BANK_WORK:RANGE:3',holding_id='B15_UPPER_BANK_WORK:1',palette='clay_red',flip=True,role='Rebuilt craft/work lodging range joining the market edge to the dry work court',modules=[('west_craft',spec(10,10,'regular_house','artisan',2,2.5,35,'rebuilt')),('service_lodging',spec(11,10,'poor_row','old_timber',1,2.5,43,'early',units=2)),('east_store',spec(11,10,'regular_house','port',1,3.25,29,'late'))])}

def run():
 plan=load(PLAN/'remaining_land_plan.json');seq=load(PLAN/'implementation_sequence.json');rows={p['id']:p for p in plan['range_parcels']};variants={};placements=[];allmods={}
 for name,f in FAMILIES.items():
  parcel=rows[f['parcel_id']];body_width=sum(s['width_m']-1 for _,s in f['modules']);assert body_width+1==parcel['width_m'];x=-body_width/2;entries=[];assets={};modules=[]
  for j,(role,sp) in enumerate(f['modules']):
   key='working_r01_'+name+'_'+role;params=dict(sp,asset_id=key);m=ordinary_r2.make_master(params);m['provenance']['parameter_author']=ref(Path(__file__));m['provenance']['ordinary_r2_factory']=ref(Path(ordinary_r2.__file__));path=HERE/'masters/modules'/f'{key}.json';write(path,m);cx=x+(sp['width_m']-1)/2;x+=sp['width_m']-1
   assets[key]=dict(master_path=str(path.relative_to(ROOT)),master_sha256=ref(path)['sha256']);entries.append(dict(asset_key=key,translation=[cx,0,0],yaw_rad=0));modules.append(dict(id=role,asset_key=key,translation_m=[cx,0,0],params=params,metadata=m['metadata'],source=ref(path)));allmods[key]=assets[key]
  key='working_r01_'+name;source=ref(PLAN/'remaining_land_plan.json');master=union_master(entries,key,assets,source);master['metadata'].update(assembly_class='lower_city_attached_working_range',family=name,role=f['role'],modules=modules,palette=f['palette'],native_dimensions_m=[parcel['width_m'],parcel['depth_m']],physical_entrances_only=True);master['provenance'].update(author=ref(Path(__file__)),approved_concept=ref(ROOT/'world_city/reference/revision_03/city_social_water_concept.png'),social_geography='Lower market poorer households and dry canal-related work fronts; exact trade names are inferred.',scope='New attached source union only; not scene activation.');p=HERE/'masters'/f'{key}.json';write(p,master);count=count_master(master);assert count<250000
  variants[key]=dict(master=ref(p),predicted_candidate_cells=count,candidate_cap=250000,output_cap=70000,pitch_m=PITCH,modules=modules)
  yaw=math.radians(parcel['yaw_degrees'])+(math.pi if f['flip']else 0);placements.append(dict(id=f['parcel_id'],asset_key=key,holding_id=f['holding_id'],zone_id=parcel['zone_id'],source_block_id='BLOCK_015',source_district_id='D_POOR',source_parcel=parcel,position_m=[parcel['center_xz_m'][0],2.0,parcel['center_xz_m'][1]],yaw_rad=yaw,scale=[1,1,1],finished_floor_y_m=2.5,palette_id=f['palette'],role=f['role'],floor_status='Proposed +2.5 m subject to exact frozen R5 triangle and full-width route checks',native_support_bottom_y_m=2.0,unimplemented=['Finite native terrain holes and doorstep reservations not activated','Courts and external access are source proposals until independent terrain review','No interior, character or navigation completion']))
 selected={p['id']for p in placements};holdings=[h for z in plan['zones'] for h in z['contiguous_holdings'] if h['id']in {p['holding_id']for p in placements}]
 selection=dict(schema='riverstone.working_ranges_r01.selection.v1',selected_parcel_ids=sorted(selected),selected_holdings=holdings,placements=placements,all_candidate_status=[dict(q,status='native_design_selected'if q['parcel_id']in selected else'deferred_unimplemented_preserved')for q in seq['range_design_queue']],area_ledger=dict(selected_source_envelopes_m2=sum(p['source_parcel']['width_m']*p['source_parcel']['depth_m']for p in placements),selected_holdings_m2=sum(h['area_m2']for h in holdings),other_B15_range_parcels_unimplemented=10),references=[ref(PLAN/n) for n in ['remaining_land_plan.json','implementation_sequence.json','access_review.json','terrain_screen.json','review_masks.npz']]+[ref(R5/'scene.json'),ref(R5/'registered.png')],status='Native source candidate, no sealed scene edits or activation')
 write(HERE/'selection.json',selection);budget=dict(schema='riverstone.working_ranges_r01.compile_budget.v1',selection=ref(HERE/'selection.json'),author=ref(Path(__file__)),variants=variants,sequential=True,new_voxel_engine=False,whole_house_scaling=0,output_cell_edits=0,summary=dict(unique_family_count=len(variants),native_module_count=len(allmods),predicted_total_candidate_visits=sum(v['predicted_candidate_cells']for v in variants.values()),largest_candidate_visits=max(v['predicted_candidate_cells']for v in variants.values()),candidate_cap_each=250000,output_cap_each=70000,estimated_peak_memory_mib=[60,180],max_one_job_at_once=True));write(HERE/'compile_budget.json',budget);print(json.dumps(budget['summary'],indent=2));return budget
if __name__=='__main__':run()
