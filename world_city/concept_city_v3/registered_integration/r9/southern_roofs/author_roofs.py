"""Bounded roof/storey variants of four cached southern range masters."""
import copy,hashlib,json,math,time
from collections import Counter
from pathlib import Path
from voxel_character.common import coordinate_planes,render_data,core
from world_city.runtime_city.archetypes import ordinary_r2
from world_city.concept_city_v3.assemblies.property.registered.merchant_fabric_r02.prepare_cache import make_master as union_master
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.compile_rows import count_master
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.finalize_rows import face_bijection
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];CITY=ROOT/'world_city/concept_city_v3'
BASE=CITY/'evidence/r8_final110_runtime_r01/scene.json';BASE_SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
SOURCES=CITY/'assemblies/ordinary/registered/working_ranges_r01';PITCH=.5;CUTOFF=2.5
# Each tuple is roof form, explicit pitch, actual floor count. Ground-floor height never changes.
DESIGNS={
 'bank_joinery':{'a':[('hip',36,1),('twin_gable_x',40,1),('gable',30,1)],'b':[('twin_gable_x',44,1),('hip',31,1),('hip',34,1)]},
 'bank_loft_store':{'a':[('twin_gable_x',42,1),('hip',40,2),('gable',34,1)],'b':[('hip',35,1),('twin_gable_x',48,2),('shed',18,1)]},
 'bank_craft_lodging':{'a':[('hip',34,2),('twin_gable_x',40,2),('gable',30,1)],'b':[('twin_gable_x',45,2),('gable',43,1),('hip',36,1)]},
 'market_lodging':{'a':[('hip',24,2),('twin_gable_x',40,1),('gable',43,1)],'b':[('twin_gable_x',42,1),('hip',36,1),('hip',24,2)]}}
def load(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).relative_to(ROOT))
def ref(p):return dict(path=rel(p),sha256=sha(p))
def canonical(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,d):
 assert HERE==p.parent or HERE in p.parents;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def low(c):return sorted(r for r in c['cells']if c['grid_origin'][1]+r[1]*c['pitch']<CUTOFF)
def relevant(p):return p['id'].startswith('BLOCK_015:R8_D')and p['asset_key'].startswith('working_r01_')
def group(p):return 'a' if p['position_m'][0]<220 else 'b'
def build():
 assert sha(BASE)==BASE_SHA;scene=load(BASE);selected=[p for p in scene['common_instances']if relevant(p)];assert len(selected)==30,len(selected)
 assets={};proofs=[];replacements=[];budget=[]
 for oldkey in sorted({p['asset_key']for p in selected}):
  family=oldkey.removeprefix('working_r01_');sourceasset=scene['common_assets'][oldkey];oldmaster=load(ROOT/sourceasset['master_path']);oldrender=load(ROOT/sourceasset['render_path']);cp=SOURCES/'cache'/f'{oldkey}.compiled.json';old=load(cp)
  assert sha(ROOT/sourceasset['master_path'])==sourceasset['master_sha256'];assert sha(ROOT/sourceasset['render_path'])==sourceasset['render_sha256'];assert old['valid'] and core.digest(old['cells'])==old['payload_hash']==oldrender['payload_hash'];assert render_data.make_render_data(old)==oldrender
  for variant,design in DESIGNS[family].items():
   placements=[p for p in selected if p['asset_key']==oldkey and group(p)==variant]
   if not placements:continue
   key='r9_south_'+family+'_'+variant;entries=[];module_assets={};module_records=[]
   for j,(source,change)in enumerate(zip(oldmaster['metadata']['modules'],design)):
    params=copy.deepcopy(source['params']);params.update(roof_form=change[0],roof_pitch_degrees=change[1],floors=change[2],asset_id=key+f'_bay{j}')
    m=ordinary_r2.make_master(params);m['provenance']['r9_source']=source['source'];m['provenance']['r9_author']=ref(Path(__file__));mp=HERE/'masters/modules'/f'{m["id"]}.json';write(mp,m)
    module_assets[m['id']]=dict(master_path=rel(mp),master_sha256=sha(mp));entries.append(dict(asset_key=m['id'],translation=source['translation_m'],yaw_rad=0));module_records.append(dict(source_module=source['source'],new_module=ref(mp),original_params=source['params'],new_params=params,original_entrances=source['metadata']['entrance'],new_entrances=m['metadata']['entrance']))
    assert source['metadata']['entrance']==m['metadata']['entrance']
   master=union_master(entries,key,module_assets,ref(BASE));master['metadata'].update(assembly_class='southern_roof_variation',original_asset_key=oldkey,variation=variant,source_modules=module_records,protected_native_y_below_m=CUTOFF,design_scope='Upper storeys, roof forms and ridges only; exact original foundation, ground-floor facades, entrances, poses and palettes.')
   master['provenance'].update(author=ref(Path(__file__)),factory=ref(Path(ordinary_r2.__file__)),original_master=ref(ROOT/sourceasset['master_path']),approved_reference=ref(ROOT/'world_city/reference/revision_03/city_social_water_concept.png'),actual_overview=ref(CITY/'evidence/r9_integrated_r01/registered.png'))
   visits=count_master(master);assert visits<75000;start=time.monotonic();new=coordinate_planes.compile_master(master,{'pitch':PITCH},max_candidate_cells=75000,max_output_cells=30000);assert new['valid'],new['constraints'];rd=render_data.make_render_data(new);faces=face_bijection(new,rd)
   assert low(old)==low(new),(key,'low parity');assert old['materials']==new['materials'];assert all(rd['bounds'][side][ax]==oldrender['bounds'][side][ax] for side in ('min','max')for ax in (0,2)),(key,rd['bounds'],oldrender['bounds']);assert rd['bounds']['min'][1]==0 and rd['bounds']['max'][1]<=oldrender['bounds']['max'][1],(key,rd['bounds'])
   mp=HERE/'masters'/f'{key}.json';cp2=HERE/'cache'/f'{key}.compiled.json';rp=HERE/'cache'/f'{key}.render.json';write(mp,master);write(cp2,new);write(rp,rd)
   assets[key]=dict(master_path=rel(mp),master_sha256=sha(mp),render_path=rel(rp),render_sha256=sha(rp),compiled_path=rel(cp2),compiled_sha256=sha(cp2),bounds=rd['bounds'],pitch_m=PITCH,cell_count=rd['cell_count'],quad_count=rd['quad_count'],source_asset_key=oldkey)
   proofs.append(dict(old_asset_key=oldkey,new_asset_key=key,source_master=ref(ROOT/sourceasset['master_path']),source_render=ref(ROOT/sourceasset['render_path']),source_compiled=ref(cp),new_master=ref(mp),new_compiled=ref(cp2),new_render=ref(rp),source_cached_render_exactly_reproduced=True,protected_volume_local_y_less_than_m=CUTOFF,protected_cells=len(low(old)),old_low_cells_sha256=canonical(low(old)),new_low_cells_sha256=canonical(low(new)),old_bounds=oldrender['bounds'],new_bounds=rd['bounds'],unchanged_xz_bounds=True,new_height_within_original_envelope=True,original_materials_and_all_instance_palettes_unchanged=True,module_records=module_records,affected_instance_ids=[p['id']for p in placements],face_bijection=faces))
   budget.append(dict(key=key,candidate_cells=new['candidate_cells'],predicted_candidate_cells=visits,output_cells=rd['cell_count'],quads=rd['quad_count'],seconds=time.monotonic()-start));print(json.dumps(budget[-1]),flush=True)
   for p in placements:replacements.append(dict(id=p['id'],expected_asset_key=p['asset_key'],expected_position_m=p['position_m'],expected_yaw_rad=p['yaw_rad'],asset_key=key,palette_id=p['palette_id'],palette_override=p['palette_override']))
 proof=dict(schema='riverstone.southern_roofs.native_parity.v1',status='NATIVE_PARITY_PASS_PENDING_COMPOSED_VISUAL_REVIEW',base_scene=ref(BASE),author=ref(Path(__file__)),source_coverage_plan=ref(CITY/'registered_integration/r8/coverage_plan/parcel_candidates.json'),unchanged_public_routes=ref(CITY/'registered_source/plan.json'),assets=proofs,selected_instance_ids=sorted(p['id']for p in selected),replacement_count=len(replacements),unique_new_masters=len(assets),shared_variant_counts=Counter(r['asset_key']for r in replacements),native_compile=budget,total_candidate_cells=sum(q['candidate_cells']for q in budget),common_sources=[ref(ROOT/'voxel_character/common'/n)for n in ['core.py','coordinate_planes.py','render_data.py']],limits=['Static native occupancy and mesh proof, not new runtime traversal.','Upper-storey occupancy changes above 2.5m; all occupied cells intersecting y<2.5m are identical, including closed-door parts and displayed materials.','Exact XZ envelopes and maximum height stay within the original envelope. Existing overlapping envelope reservations require differential audit rather than a claim of zero city overlap.','Actual composed overview and street inspection remain required.'])
 pp=HERE/'proof.json';write(pp,proof)
 for q in replacements:q.update(proof_path=rel(pp),proof_sha256=sha(pp))
 pack=dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=BASE_SHA,common_assets=assets,add_instances=[],remove_instance_ids=[],replace_instances=replacements,inspection_cameras={'r9_southern_roof_district':dict(position_m=[465,245,560],target_m=[212,4,230],ortho_size_m=330,render_size_px=[1536,1024],purpose='Southern canal work/lodging district; exact 30 retained range poses.'),'r9_south_cross_gable_detail':dict(position_m=[242,45,316],target_m=[191,5,254],ortho_size_m=125,render_size_px=[1536,1024],purpose='Low/upper-storey contrast, orthogonal and hipped ridges; non-walking inspection camera.')})
 write(HERE/'pack.json',pack);write(HERE/'handoff.json',dict(pack=ref(HERE/'pack.json'),proof=ref(pp),replacement_count=30,new_masters=len(assets),status=proof['status']));print('SOUTHERN_NATIVE_PARITY_PASS',flush=True)
if __name__=='__main__':build()
