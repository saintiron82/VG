"""Optional roof-only market variation; original poses and all low native cells stay fixed."""
import collections,copy,hashlib,json
from pathlib import Path
from voxel_character.common.coordinate_planes import compile_master
from voxel_character.common.render_data import make_render_data
from world_city.runtime_city.parts.author import extrusion
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[5]
CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'evidence/r8_final110_runtime_r01/scene.json'
BASE_SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
MARKET=CITY/'assemblies/market/registered/r3_clusters/resolved_placements.json'
WALK=CITY/'assemblies/market/registered/r3_clusters/walkspace_report.json'
FAMILIES={'grain':{'roof':'c9b88f','purpose':'Western grain exchange: low flax-colored ridge canopies.'},'produce':{'roof':'a5a479','purpose':'Northeastern produce quarter: rising one-sided sage canvas.'},'textile':{'roof':'b36c58','stripe':'e1d2af','purpose':'Southeastern textile quarter: high red-and-linen ridge canopies.'}}

def load(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rel(p):return str(Path(p).relative_to(ROOT))
def ref(p):return {'path':rel(p),'sha256':sha(p)}
def write(p,d):
 assert HERE==p.parent or HERE in p.parents;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def lowcells(c):return sorted(r for r in c['cells']if c['grid_origin'][1]+r[1]*c['pitch']<2.2)
def lowcolors(c,overrides):return sorted([*r[:6],overrides.get(r[5],c['materials'][r[5]])]for r in lowcells(c))
def family(p):
 x,_,z=p['position_m'];return 'grain'if x<95 else 'produce'if z<40 else 'textile'

def altered(original,trade,key):
 m=copy.deepcopy(original);m['id']=key;m['metadata']['r9_canopy_trade']=trade;m['metadata']['r9_change_scope']='Only roof cells >=3m and produce uphill post extensions >=3m; native occupied cells intersecting y<2.2m unchanged.'
 m['materials']['r9_canopy']=FAMILIES[trade]['roof']
 if trade=='textile':m['materials']['r9_linen']=FAMILIES[trade]['stripe']
 comp=m['components'][0];roof=next(o for o in comp['operations']if o['id']=='op_004');assert roof['shape']['kind']=='box' and roof['shape']['min'][1]==3
 w=roof['shape']['max'][0];loz=roof['shape']['min'][2];hiz=roof['shape']['max'][2]
 if trade=='grain':poly=[[-w,3],[0,3.5],[w,3],[w,3.25],[0,3.75],[-w,3.25]]
 elif trade=='textile':poly=[[-w,3],[0,4.25],[w,3],[w,3.25],[0,4.5],[-w,3.25]]
 else:
  poly=[[-w,3],[w,3.75],[w,4],[-w,3.25]]
  for op in comp['operations']:
   shape=op['shape']
   if op['id']in ['op_002','op_003']:
    assert shape['min'][1]==-.5 and shape['max'][1]==3;shape['max'][1]=3.75
 roof['shape']=extrusion(poly,loz,hiz);roof['material']='r9_canopy'
 if trade=='textile':
  # Three wide native fabric panels, all above the unchanged standing-volume geometry.
  roof['shape']=extrusion(poly,loz,-.75)
  for id,z0,z1,mat in [('r9_roof_linen',-.75,.75,'r9_linen'),('r9_roof_red',.75,hiz,'r9_canopy')]:
   q=copy.deepcopy(roof);q['id']=id;q['shape']=extrusion(poly,z0,z1);q['material']=mat;comp['operations'].append(q)
 return m

def build():
 assert sha(BASE)==BASE_SHA;scene=load(BASE);stalls=[p for p in scene['common_instances']if p['id'].startswith('MARKET_stall_')];assert len(stalls)==104
 assets={};proofs=[];compiled={};used={};replacements=[]
 for p in stalls:used.setdefault((p['asset_key'],family(p)),[]).append(p)
 for (oldkey,trade),placements in sorted(used.items()):
  a=scene['common_assets'][oldkey];mp=ROOT/a['master_path'];rp=ROOT/a['render_path'];assert sha(mp)==a['master_sha256'] and sha(rp)==a['render_sha256'];master=load(mp);pitch=a['pitch_m'];assert pitch==.25
  old=compile_master(master,{'pitch':pitch},max_candidate_cells=150000,max_output_cells=50000);oldrd=make_render_data(old);stored=load(rp);assert oldrd==stored,'Original common compile must exactly reproduce the actual bound cache.'
  key='r9_canopy_'+trade+'_'+oldkey.removeprefix('market_r3_');newmaster=altered(master,trade,key);comp=compile_master(newmaster,{'pitch':pitch},max_candidate_cells=150000,max_output_cells=50000);assert comp['valid'];rd=make_render_data(comp)
  before=lowcells(old);after=lowcells(comp);assert before==after
  assert all(oldrd['bounds'][side][k]==rd['bounds'][side][k]for side in ('min','max')for k in (0,2))
  assert rd['bounds']['min'][1]==oldrd['bounds']['min'][1]
  for p in placements:assert lowcolors(old,p.get('palette_override',{}))==lowcolors(comp,{})
  newmp=HERE/'masters'/f'{key}.json';newrp=HERE/'cache'/f'{key}.render.json';write(newmp,newmaster);write(newrp,rd)
  assets[key]=dict(master_path=rel(newmp),master_sha256=sha(newmp),render_path=rel(newrp),render_sha256=sha(newrp),bounds=rd['bounds'],pitch_m=pitch,quad_count=rd['quad_count'],source_asset_key=oldkey)
  proofs.append(dict(old_asset_key=oldkey,new_asset_key=key,trade_family=trade,source_master=ref(mp),source_render=ref(rp),new_master=ref(newmp),new_render=ref(newrp),original_native_cache_reproduced_exactly=True,pitch_m=pitch,protected_volume_local_y_less_than_m=2.2,protected_cell_selection='Every occupied cell whose lower Y is less than 2.2m, including cells straddling 2.2m.',protected_cells_count=len(before),old_low_cells_sha256=canonical(before),new_low_cells_sha256=canonical(after),low_material_and_palette_equivalent_for_all_replaced_instances=True,old_bounds=oldrd['bounds'],new_bounds=rd['bounds'],unchanged_xz_bounds=True,affected_instance_ids=[p['id']for p in placements],actual_native_cell_count=rd['cell_count'],actual_native_quad_count=rd['quad_count']))
  for p in placements:replacements.append(dict(id=p['id'],expected_asset_key=p['asset_key'],expected_position_m=p['position_m'],expected_yaw_rad=p['yaw_rad'],asset_key=key,palette_id='r9_market_'+trade,palette_override={}))
 proof=dict(schema='riverstone.market_canopy.low_volume_parity.v1',status='PASS',base_scene=ref(BASE),author=ref(Path(__file__)),original_customer_paths=ref(WALK),original_market_ownership=ref(MARKET),source_public_route_count=104,replaced_stalls=104,unchanged_ids_and_poses=True,unchanged_customer_paths=True,all_base_stalls_replaced_exactly_once=True,assets=proofs,families=FAMILIES,family_counts=collections.Counter(family(p)for p in stalls),changed_height_policy='Only new silhouette above local Y=3m; all original cells intersecting Y<2.2m and their displayed materials are identical. Maximum native canopy Y 4.5m. XZ bounds identical.',limits=['Static native cell parity does not certify new physics replay.','This changes canopy silhouettes without relocating the retained market grid.','Root must transactionally validate every expected pose and asset key before applying any replacements.','Roof colors are explicit trade-family materials; no random instance palette noise.'])
 pp=HERE/'proof.json';write(pp,proof)
 for r in replacements:r.update(proof_path=rel(pp),proof_sha256=sha(pp))
 pack=dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=BASE_SHA,common_assets=assets,add_instances=[],remove_instance_ids=[],replace_instances=replacements,inspection_cameras={'r9_market_canopy_eye':dict(position_m=[110.55407546238989,5.65,85.52227311729304],target_m=[125,6.8,45],eye_height_m=1.65,source_route='MARKET_stall_6_6:south:CUSTOMER',purpose='Same statically checked 1.65m customer-lane eye as cargo pack, turned toward retained stalls and varied canopy roofs.'),'r9_market_trade_canopies':dict(position_m=[108,65,146],target_m=[100,4,43],ortho_size_m=115,render_size_px=[1536,1024])})
 write(HERE/'pack.json',pack);write(HERE/'handoff.json',dict(schema='riverstone.market_canopy.handoff.v1',pack=ref(HERE/'pack.json'),proof=ref(pp),base_scene_sha256=BASE_SHA,replaced_stalls=104,native_assets=len(assets),family_counts=proof['family_counts'],status='PARITY_PASS_OPTIONAL_INTEGRATED_VISUAL_REVIEW_REQUIRED'))
 print(json.dumps(dict(status=proof['status'],replaced_stalls=104,native_assets=len(assets),families=proof['family_counts'],pack_sha256=sha(HERE/'pack.json'),proof_sha256=sha(pp))))
if __name__=='__main__':build()
