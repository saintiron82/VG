"""Bounded common compile and exact cell-difference proof. Activation is separate.

Run only after the finite terrain restoration/seam handoff is accepted. Its exact
file and SHA are mandatory so the compiled candidate cannot lose that provenance.
"""
import argparse,copy,hashlib,json,pathlib,resource,sys,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def ref(p):return {'path':str(pathlib.Path(p).resolve().relative_to(ROOT)),'sha256':sha(p)}
def write(p,v):
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def checked(r):
 p=ROOT/r['path'];assert sha(p)==r['sha256'],p;return p

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--terrain-binding',type=pathlib.Path,required=True);parser.add_argument('--terrain-sha256',required=True);args=parser.parse_args()
 terrain=args.terrain_binding.resolve();assert terrain.is_file()and sha(terrain)==args.terrain_sha256,'Unbound terrain restoration input'
 candidates=read(H/'source_candidates.json');contacts=read(checked(candidates['contact_source']));oldpack=read(checked(contacts['sources']['pack']));contactby={r['property_id']:r for r in contacts['records']}
 cache=H/'cache';cache.mkdir(exist_ok=True);evidence=[];assets={};placements=[]
 for record in candidates['records']:
  pid=record['property_id'];mp=checked(record['source_master']);op=checked(record['original_master']);cp=checked(record['original_cell_snapshot']);rp=checked(record['original_render'])
  master=read(mp);original=read(op);before=read(cp);oldrender=read(rp)
  # Original source operations, grids, transforms, materials and features are exact.
  a=copy.deepcopy(master);b=copy.deepcopy(original)
  a['components'][0]['operations']=a['components'][0]['operations'][:record['original_operation_count']]
  for k in ['id','revision','metadata']:a.pop(k,None);b.pop(k,None)
  assert a==b,'Non-cut source mutation'
  removed={tuple(v)for v in record['expected_removed_grid_cells']}
  beforeby={tuple(c[:3]):c for c in before['cells']};assert len(beforeby)==len(before['cells'])
  assert removed<=beforeby.keys()
  assert all(beforeby[k][6].startswith('r1_access_skin_')for k in removed)
  expected=[c for c in before['cells']if tuple(c[:3])not in removed]
  budget=candidate_budget(master);assert budget['within_candidate_cap']and budget['exact_candidate_visits_without_cell_sampling']<=300000
  t=time.monotonic();compiled=coordinate_planes.compile_master(master,{'pitch':.5},max_candidate_cells=300000,max_output_cells=100000);render=render_data.make_render_data(compiled);elapsed=time.monotonic()-t
  assert compiled['valid'] and compiled['cells']==expected,'Actual compiled cell delta differs from exact access-skin removal'
  for k in ['pitch','grid_origin','materials','components','instances']:assert before[k]==compiled[k],k
  assert render['bounds']==oldrender['bounds'],'Outer native bounds changed unexpectedly'
  assert render['cell_count']==record['expected_retained_cell_count']
  dst=cache/(record['asset_key']+'.compiled.json');rdst=cache/(record['asset_key']+'.render.json');write(dst,compiled);write(rdst,render)
  placement=copy.deepcopy(contactby[pid]['placement']);oldkey=placement['asset_key'];placement['asset_key']=record['asset_key'];placements.append(placement)
  asset=copy.deepcopy(oldpack['asset_manifest'][oldkey]);asset.update(asset_key=record['asset_key'],master_path=str(mp),master_file_sha256=sha(mp),master_source_sha256=compiled['master_hash'],common_master_hash=compiled['master_hash'],compiled_asset_ref=str(rdst),render_path=str(rdst.relative_to(ROOT)),render_sha256=sha(rdst),bounds=render['bounds'],cell_count=render['cell_count'],quad_count=sum(len(g['quads'])for g in render['groups']),common_payload_hash=compiled['payload_hash'],compile_identity=compiled['payload_hash'])
  assets[record['asset_key']]=asset
  evidence.append({'property_id':pid,'source_master':ref(mp),'original_master':ref(op),'original_render':ref(rp),'compiled':ref(dst),'render':ref(rdst),'before_cells':len(before['cells']),'after_cells':len(compiled['cells']),'removed_cells':len(removed),'removed_grid_cells':sorted(removed),'all_other_full_cell_rows_exact':True,'all_other_source_operations_exact':True,'same_bounds':True,'walls_gates_materials_and_features_preserved':True,'candidate_visits':compiled['candidate_cells'],'wall_seconds':elapsed,'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'outside_traffic_restore_area_m2':record['outside_traffic_cell_fraction_area_m2']})
  print(json.dumps({k:evidence[-1][k]for k in ['property_id','removed_cells','after_cells','candidate_visits','wall_seconds','peak_process_rss_kib']}),flush=True)
 report={'schema':'riverstone.estate_public_lane_exact_native_delta.v1','status':'PASS_EXACT_NATIVE_CUT_ONLY_TERRAIN_AND_PHYSICS_SEPARATE','sources':ref(H/'source_candidates.json'),'terrain_binding':ref(terrain),'implementation':ref(pathlib.Path(__file__)),'records':evidence,'controller_changed':False,'scene_activation':False}
 write(H/'native_difference_proof.json',report)
 pack={'schema':'riverstone.estate_public_lane_native_replacements.v1','status':'CANDIDATE_PENDING_COMPOSED_TERRAIN_AND_CONTROLLER_REPLAY','placements':placements,'asset_manifest':assets,'replace_instance_ids':[p['id']for p in placements],'original_pack':contacts['sources']['pack'],'terrain_binding':ref(terrain),'native_difference_proof':ref(H/'native_difference_proof.json'),'applied_to_scene':False,'activation_requirements':['Compose exact traffic and private-column restoration with the accepted terrain boundary profiles.','Confirm no exposed source holes, duplicated road floors or unowned private fractions.','Replay original-controller public lanes and native gate/edge controls on exact composed scene.']}
 write(H/'resolved_placements.json',pack);print(json.dumps({'pack':ref(H/'resolved_placements.json'),'proof':ref(H/'native_difference_proof.json')}))
if __name__=='__main__':main()
