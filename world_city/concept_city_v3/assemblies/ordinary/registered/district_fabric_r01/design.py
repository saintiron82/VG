"""R8 ordinary district fabric. Native reusable court-bearing common assemblies."""
from pathlib import Path
import copy,json,math,hashlib
from world_city.runtime_city.archetypes import ordinary_r2
from world_city.concept_city_v3.assemblies.property.registered.merchant_fabric_r02.prepare_cache import make_master as union_master
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.compile_rows import count_master
from world_city.runtime_city.parts.author import Source
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[5]; CITY=ROOT/'world_city/concept_city_v3'
R7=CITY/'evidence/visual_registered_common_r7_palette_r01/scene.json'
R7_SHA='1429ae51b7c72b12940dcf0dd7e12c2684cab95f81735d228bba64dc819317c1'
PITCH=.5

def load(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def write(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def xform(q,origin,yaw):
 c,s=math.cos(yaw),math.sin(yaw);return [origin[0]+c*q[0]+s*q[1],origin[1]-s*q[0]+c*q[1]]
def spec(w,d,kind='regular_house',style='artisan',floors=1,fh=2.75,pitch=36,era='early',roof='gable',units=1):
 return dict(width_m=w,depth_m=d,assembly_class=kind,style=style,floors=floors,floor_height_m=fh,roof_pitch_degrees=pitch,construction_era=era,roof_form=roof,attached_units=units)
# Frontage and return walls are resolved as a single native occupancy union. The
# courtyard is open to +Z. Dimensions are authored in metres, never mesh scaling.
FAMILIES={
 'domestic_L':dict(role='Attached modest lodging frontage with a return workshop and shared domestic court',palette='clay_red',court=rect(-2.5,-2,10.5,11),modules=[
 ('west_lodging',spec(8,9,'poor_row','old_timber',2,2.5,44,units=2),[-8,0,-8],0),
 ('middle_repair',spec(9,9,floors=1,fh=3,pitch=31,era='rebuilt'),[-.5,0,-8],0),
 ('east_lodging',spec(9,9,'poor_row','old_timber',2,2.5,39,era='late',units=2),[7.5,0,-8],0),
 ('return_workshop',spec(18,8,style='artisan',floors=1,pitch=26),[-8,0,3],math.pi/2)]),
 'craft_U':dict(role='Attached three-sided craft and dry-storage court with broad working doors',palette='wood_brown',court=rect(-5.5,-2.5,5.5,12),modules=[
 ('west_craft',spec(10,10,style='artisan',floors=2,fh=2.5,pitch=35,era='rebuilt'),[-10,0,-9],0),
 ('middle_store',spec(11,10,style='port',floors=1,fh=3.25,pitch=18,roof='shed'),[-.5,0,-9],0),
 ('east_craft',spec(11,10,style='artisan',floors=1,fh=3.25,pitch=32),[9.5,0,-9],0),
 ('west_return',spec(22,8,style='port',floors=1,fh=3,pitch=15,roof='shed'),[-11,0,2],math.pi/2),
 ('east_return',spec(22,8,'poor_row','old_timber',1,2.5,38,units=4),[11,0,2],-math.pi/2)]),
 'compact_L':dict(role='Compact attached artisan pair with service return and an open shared court',palette='slate_gray',court=rect(-.5,-.5,6.5,10),modules=[
 ('west_artisan',spec(8,8,style='artisan',floors=2,fh=2.5,pitch=38,era='rebuilt'),[-4,0,-5],0),
 ('east_lodging',spec(9,8,'poor_row','old_timber',1,2.5,43,units=2),[3.5,0,-5],0),
 ('service_return',spec(14,7,style='port',floors=1,fh=2.75,pitch=19,roof='shed'),[-4.5,0,4],math.pi/2)])}

def run():
 assert ref(R7)['sha256']==R7_SHA
 variants={}
 for name,f in FAMILIES.items():
  entries=[];assets={};modules=[]
  for role,sp,tr,yaw in f['modules']:
   key='district_r01_'+name+'_'+role;params=dict(sp,asset_id=key);m=ordinary_r2.make_master(params)
   m['provenance'].update(parameter_author=ref(Path(__file__)),ordinary_r2_factory=ref(Path(ordinary_r2.__file__)))
   path=HERE/'masters/modules'/f'{key}.json';write(path,m);assets[key]=dict(master_path=ref(path)['path'],master_sha256=ref(path)['sha256'])
   entries.append(dict(asset_key=key,translation=tr,yaw_rad=yaw));modules.append(dict(id=role,asset_key=key,translation_m=tr,yaw_rad=yaw,params=params,metadata=m['metadata'],source=ref(path)))
  key='district_r01_'+name;master=union_master(entries,key,assets,ref(R7));master['metadata'].update(assembly_class='ordinary_district_attached_court',family=name,role=f['role'],modules=modules,palette=f['palette'],court_local_polygon_xz_m=f['court'],physical_entrances_only=True)
  master['provenance'].update(author=ref(Path(__file__)),policy='Native continuous dimension-authored common modules unioned at unit scale. Source doors occluded by attached returns are not exterior portals.',no_scene_edits=True)
  p=HERE/'masters'/f'{key}.json';write(p,master);cost=count_master(master);assert cost<250000
  variants[key]=dict(master=ref(p),pitch_m=.5,predicted_candidate_cells=cost,candidate_cap=250000,output_cap=70000,modules=modules)
 # A low continuous rail segment gives private productive/court boundaries actual
 # native geometry. Every public/private opening is cut at placement selection.
 a=Source('district_r01_boundary_2m',[-1,-.25,-.125],[1,1.25,.125])
 for j,x in enumerate((-.875,.875)):a.box('post'+str(j),[x-.125,-.25,-.125],[x+.125,1.25,.125],'timber_dark')
 for j,y in enumerate((.375,1.0)):a.box('rail'+str(j),[-1,y,-.125],[1,y+.25,.125],'timber')
 m=a.finish();m['provenance'].update(author=ref(Path(__file__)),policy='Finite native reusable two-metre parcel boundary; units never scaled. Access openings remain unobstructed.')
 key='district_r01_boundary_2m';p=HERE/'masters'/f'{key}.json';write(p,m)
 from world_city.concept_city_v3.assemblies.ordinary.registered.working_ranges_r01.court_phase01.author import count
 variants[key]=dict(master=ref(p),pitch_m=.125,predicted_candidate_cells=count(m),candidate_cap=10000,output_cap=5000,modules=[])
 b=dict(schema='riverstone.district_fabric.compile_budget.v1',author=ref(Path(__file__)),actual_scene=ref(R7),variants=variants,summary=dict(new_unique_compiled_assemblies=len(variants),source_building_modules=sum(len(v['modules'])for v in variants.values()),predicted_total_candidate_visits=sum(v['predicted_candidate_cells']for v in variants.values()),largest_candidate_visits=max(v['predicted_candidate_cells']for v in variants.values()),estimated_peak_memory_mib=[60,200],serial_only=True,whole_house_scales=0,new_engine=False,cell_edits=0));write(HERE/'compile_budget.json',b);print(json.dumps(b['summary'],indent=2));return b
if __name__=='__main__':run()
