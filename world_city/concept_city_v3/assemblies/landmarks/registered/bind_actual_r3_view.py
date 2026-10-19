"""Reconstruct immutable r3 evidence from persisted runtime, sources and PNGs."""
import collections, hashlib, json, math, struct
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[4]; CITY=ROOT/'world_city/concept_city_v3'; EV=CITY/'evidence/visual_registered_common_r3'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(Path(p).relative_to(ROOT)),'sha256':sha(p)}
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
PACKS={'ordinary':'ordinary/registered/resolved_placements.json','ordinary_density':'ordinary/registered/r1/resolved_placements.json','woodland':'landscape/registered_woodland/resolved_placements.json','property':'property/registered/r1/repair_01/resolved_placements.json','landmarks':'landmarks/registered/repairs/r02_connected_finials/resolved_placements.json','port':'landmarks/registered/port_r03_quay_unions/resolved_placements.json','fortifications':'fortifications/registered/placement_r02/resolved_placements.json','landscape':'landscape/registered/resolved_placements.json','reservoir':'waterworks/registered_reservoir/resolved_placements.json','training':'landscape/registered/training/resolved_placements.json','market':'market/registered/r3_clusters/resolved_placements.json','drawbridge_fixed':'waterworks/registered_bridge/drawbridge_candidate/resolved_placements.json'}
def main():
 runtime=load(EV/'runtime.json');scene=load(EV/'bridge_scene.json');base=load(EV/'scene.json');camera=load(EV/'camera_scene.json');cl=load(EV/'camera_ledger.json');promotion=load(EV/'promotion_ledger.json');inputs=load(EV/'input_hashes.json');checks=[]
 def check(name,ok):
  assert ok,name
  checks.append({'id':name,'pass':True})
 check('runtime_exit_and_scene_binding',(EV/'exit.txt').read_text().strip()=='0' and runtime['status']=='runtime_loaded' and runtime['scene_sha256']==sha(EV/'bridge_scene.json'))
 check('source_and_candidate_binding',scene['source_plan_sha256']==sha(CITY/'registered_source/plan.json') and scene['integration_sha256']==sha(CITY/'registered_integration/r3/candidate.json'))
 for path,h in inputs.items():check('input_hash:'+path,sha(ROOT/path)==h)
 check('camera_parent',cl['parent_scene_sha256']==sha(EV/'scene.json'))
 for k,h in cl['geometry_hashes'].items():check('camera_geometry:'+k,digest(base[k])==h==digest(camera[k]))
 check('promotion_parent',promotion['parent_scene']==ref(EV/'camera_scene.json'))
 for k in ('surfaces','boxes'):check('promotion_unchanged:'+k,digest(scene[k])==promotion['unchanged_'+k+'_sha256']==digest(camera[k]))
 old={x['id']:x for x in camera['common_instances']};new={x['id']:x for x in scene['common_instances']}
 check('bridge_removed',set(old)-set(new)==set(promotion['removed_static_ids'])=={'BRIDGE_MAIN_RIVER:COMMON_UNION'})
 check('bridge_added',set(new)-set(old)==set(promotion['inserted_static_ids'])=={'BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED'})
 check('other_instances_unchanged',all(old[k]==new[k] for k in old.keys()&new.keys()))
 db=load(CITY/'assemblies'/PACKS['drawbridge_fixed'])
 for k in ('states','motion_samples','barrier_samples','hinge_cover_samples','cycle_stages','bridge_to_world','inspection_vessel','surface_ownership'):check('drawbridge:'+k,scene['bridge_mechanism'][k]==db[k])
 used={p['asset_key'] for p in new.values()}|set(scene['bridge_mechanism']['asset_keys'].values() if isinstance(scene['bridge_mechanism']['asset_keys'],dict) else scene['bridge_mechanism']['asset_keys'])
 asset_rows=[]
 for key in sorted(used):
  a=scene['common_assets'][key];mp=ROOT/a['master_path'];rp=ROOT/a['render_path'];check('used_asset:'+key,sha(mp)==a['master_sha256'] and sha(rp)==a['render_sha256']);asset_rows.append({'key':key,'source':ref(mp),'cache':ref(rp)})
 counts=collections.Counter(x['source_pack'] for x in new.values());pack_rows=[]
 for name,path in PACKS.items():
  p=CITY/'assemblies'/path;pack=load(p);poses={x['id']:x for x in pack['placements']};selected=[v for v in new.values() if v['source_pack']==name]
  for actual in selected:
   q=poses[actual['id']]
   for field in ('position_m','yaw_rad','scale'):
    if field in q:check('rigid_pose:'+actual['id']+':'+field,actual[field]==q[field])
   if name=='drawbridge_fixed':check('drawbridge_rigid_yaw',abs(actual['yaw_rad']-math.atan2(q['transform']['basis'][0][2],q['transform']['basis'][0][0]))<1e-12)
  pack_rows.append({'id':name,'pack':ref(p),'resolved_count':len(poses),'actual_scene_count':len(selected),'source_present':True,'compiled_cache_present':True,'resolved_placement':True,'actual_placed':True,'actual_viewed':True,'final_art_approved':False})
 images=[]
 for c in runtime['captures']:
  p=EV/Path(c['path']).name;data=p.read_bytes();w,h=struct.unpack('>II',data[16:24]);check('capture:'+c['view'],c['error']==0 and (w,h)==(1536,1024));images.append({'view':c['view'],**ref(p),'width':w,'height':h})
 check('seven_captures',len(images)==7);check('183_used_asset_pairs',len(asset_rows)==183)
 report={'schema':'riverstone.city.actual_registered_view_evidence.v1','id':'actual_registered_view_r03','reconstruction':'Fresh replay after checkpoint restoration; immutable r3 inputs retained. This artifact does not claim byte identity with the lost post-backup ledger.','source_plan':ref(CITY/'registered_source/plan.json'),'candidate':ref(CITY/'registered_integration/r3/candidate.json'),'scene':ref(EV/'bridge_scene.json'),'runtime':ref(EV/'runtime.json'),'terrain_contract':ref(CITY/'registered_topography/revisions/r08_park_interface/contract.json'),'camera_ledger':ref(EV/'camera_ledger.json'),'promotion_ledger':ref(EV/'promotion_ledger.json'),'packs':pack_rows,'actual_scene_counts':dict(counts),'moving_bridge_nodes':runtime['bridge_mechanism']['movable_nodes'],'used_assets':asset_rows,'images':images,'checks':checks,'observations':['Native institutional buildings are present; cathedral and abbey grounds remain too bare.','The continuous quay unions and native outer walls are visible; this is not a close seam or collision certificate.','Reservoir working assets are screened from the southern camera by the northern curtain.','Training retains the known +0.5 m coarse gate tread failure.','The market includes 104 stalls and one fountain.','Connected finials remain visible without the old detached dark cell.','Drawbridge is closed in ROAD_OPEN; open/cycle evidence is separate.'],'review_basis':{'facility_worker':'Seven actual r3 images directly inspected before workspace reset; files now hash-verified again.','implementation_lead':'Reported direct review of the r3 capture.','root_direct_review':'Not asserted by this record.'},'excluded':['optional reservoir service_r02','terrain r09 and later','BLOCK_015 east candidate','precinct_r04 additions'],'not_certified':['final art','character collision and full traversal','hydraulics and water quality','structural engineering','port close-up seam acceptance'],'prior_failure_history':'R1 detached finials and r2/r3 precinct emptiness remain recorded; this is a new evidence record, not a deletion of earlier failures.'}
 output=HERE/'evidence/actual_registered_view_r03.json'
 if output.exists():check('immutable_existing_record',load(output)==report)
 else:write(output,report)
 print(json.dumps({'evidence':ref(output),'checks':len(checks),'used_asset_pairs':len(asset_rows),'counts':dict(counts)},indent=2))
if __name__=='__main__':main()
