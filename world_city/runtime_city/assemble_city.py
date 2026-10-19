"""Deterministic city orchestration. Existing common master/compiler/mesher only.
Source footprint and open-space plans are immutable inputs. No generated-cell edits.
"""
from __future__ import annotations
import argparse, collections, copy, hashlib, json, math, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from voxel_character.common import coordinate_planes, core, render_data

STYLE={'D01':'institutional','D02':'institutional','D03':'merchant','D04':'merchant','D05':'port','D06':'artisan','D07':'old_timber','D08':'garden','D09':'institutional','D10':'institutional','S01':'garden'}
PROTECTED={
'D03-B016':(9.6,15.6,1,'gable','merchant','approved_teal','warm_gray'),
'D03-B017':(12.8,20.8,2,'twin_gable_z','merchant','slate_blue','warm_gray'),
'D03-B022':(12.8,15.6,2,'twin_gable_x','merchant','dark_slate','gray_brown'),
'D03-B023':(6.4,26,1,'gable','artisan','weathered_teal','approved_gray'),
'D03-B024':(6.4,26,3,'gable','old_timber','slate_blue','gray_brown'),
'D03-B025':(9.6,15.6,2,'gable','merchant','approved_teal','gray_brown'),
'D03-B026':(9.6,15.6,1,'twin_gable_x','merchant','dark_slate','warm_gray')}
ROOFS={'approved_teal':['45676a','658284','355157','7b8f8a'],'slate_blue':['4b6270','6c7d8b','354b5c','7d8b94'],'dark_slate':['3e5659','5a7176','2f4448','718383'],'weathered_teal':['557472','738e8a','405a58','899b91']}
STONE={'approved_gray':['9e9b88','b7b19b','7e8075','666c63'],'warm_gray':['a39a85','bab098','877f70','6b6b61'],'gray_brown':['9a9180','b3a68f','7d766b','68665e']}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
def seed(s):return int(hashlib.sha256(s.encode()).hexdigest()[:16],16)
def dist_segment(p,a,b):
 dx,dz=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dz)/(dx*dx+dz*dz)));return math.dist(p,[a[0]+t*dx,a[1]+t*dz])
def frame(b):
 q=b['footprint_xz_m']; c=[sum(x[i] for x in q)/4 for i in (0,1)]; e=b['entrance']['position_xz_m']
 edge=min(range(4),key=lambda i:dist_segment(e,q[i],q[(i+1)%4]));a=q[edge];bb=q[(edge+1)%4];fm=[(a[i]+bb[i])/2 for i in (0,1)];v=[fm[i]-c[i] for i in (0,1)];n=math.hypot(*v);front=[x/n for x in v]
 return c,front,math.dist(a,bb),2*n,math.atan2(front[0],front[1])
def dimension(value,bins):
 avail=value-1.3
 return max([v for v in bins if v<=avail],default=math.floor(avail*2)/2)
def pick_era(rule,key):
 r=(seed(key+'era')%1000000)/1000000;total=0
 for k,w in rule['era_mix'].items():
  total+=w
  if r<total:return k
 return list(rule['era_mix'])[-1]
def palette(roof,stone):
 return dict(zip(['slate','slate_light','slate_dark','slate_worn'],ROOFS[roof]))|dict(zip(['stone','stone_light','stone_dark','mortar'],STONE[stone]))

def make_plan():
 plan=json.loads((ROOT/'world_city/data/city_brief.v2.json').read_text()); history=json.loads((ROOT/'world_city/city_history.json').read_text())
 specs={};instances=[]
 for b in plan['building_plans']:
  bid=b['id'];did=b['district_id'];role=b['functional_role'];c,front,w,d,yaw=frame(b);rule=history['district_rules'][did]
  landmark_kind={'교구 교회':'church','성채 예배당':'church','수도원':'monastery','곡물 창고':'warehouse','수운 창고':'warehouse','직물 창고':'warehouse'}.get(role,role)
  landmark=landmark_kind in ['castle_keep','cathedral','town_hall','gatehouse','wall_tower','church','monastery','warehouse']
  protected=bid in PROTECTED
  if landmark:
   aw,ad=w,d;h=b['height_candidate_m'];spec={'kind':landmark_kind,'width_m':round(aw,3),'depth_m':round(ad,3),'height_m':h}; family='landmark'
   # Gate/tower standard footprints contain millimetric plan rounding; use exact reusable dimensions.
   if role=='gatehouse':spec['width_m']=18.;spec['depth_m']=14.
   if role=='wall_tower':spec['width_m']=10.;spec['depth_m']=10.
   aw,ad=spec['width_m'],spec['depth_m'];roof='dark_slate';stone='approved_gray'
   if bid=='D09-B004':spec['secondary_openings']=[{'min':[-9,0,0],'max':[-5,5,7]}]
   if bid=='D09-B029':spec['secondary_openings']=[{'min':[-5,0,2.5],'max':[5,3,5]}]
  else:
   style=STYLE[did];floors=max(1,min(3,round((b['height_candidate_m']-3.3)/2.5)));floors=max(rule['floors'][0],min(rule['floors'][1],floors));floors=min(floors,3)
   aw=dimension(w,[4.,6.,8.,10.,12.,16.,20.,24.,30.]);ad=dimension(d,[6.,10.,14.,18.,24.,30.,38.]);h=b['height_candidate_m'];roof_form='twin_gable_z' if aw>=12 else 'gable'
   if did in ['D08','S01'] and floors<=2:h=min(h,9.0)
   if role=='rear_workshop_or_store':
    ad=max(3.5,ad);floors=1;h=min(h,5.5);roof_form='gable';style='artisan' if did=='D06' else 'port' if did=='D05' else 'garden'
   if bid in PROTECTED:aw,ad,floors,roof_form,style,roof,stone=PROTECTED[bid]
   else:
    roof=list(ROOFS)[seed(bid+'roof')%4];stone=list(STONE)[seed(bid+'stone')%3]
   spec={'width_m':aw,'depth_m':ad,'height_m':h,'floors':floors,'style':style,'roof_form':roof_form,'construction_era':('early' if did in ['D01','D02','D07'] else 'late' if did in ['D08','S01'] else 'rebuilt')};family='ordinary'
  if min(aw,ad)<=2: raise ValueError(('too small',bid,w,d))
  key=family+'_'+hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()[:14]
  specs.setdefault(key,{'asset_id':key,'family':family,**spec})
  shift=0 if landmark else (d-ad)/2-.45
  pos=[round(c[0]+front[0]*shift,6),0.,round(c[1]+front[1]*shift,6)]
  entry=[round(pos[0]+front[0]*(ad/2-.5),6),0.,round(pos[2]+front[1]*(ad/2-.5),6)]
  inst={'id':bid,'source_footprint_id':bid,'district_id':did,'functional_role':role,'asset_key':key,'position_m':pos,'yaw_rad':yaw,'source_footprint_xz_m':b['footprint_xz_m'],'local_bounds':{'min':[-aw/2,0,-ad/2],'max':[aw/2,h,ad/2]},'entrance':{'position_m':entry,'road_id':b['road_access']['road_id'],'road_connection_m':[b['road_access']['connection_xz_m'][0],0,b['road_access']['connection_xz_m'][1]],'status':'closed_exterior_door_approach_only' if not role=='gatehouse' else 'open_through_passage'},'implementation_tier':b['implementation_tier'],'preserved_record':protected,'reconstruction_status':'protected_design_reconstructed_not_original_mesh' if protected else 'new_common_master_assembly','era_id':pick_era(rule,bid),'palette_id':roof+'__'+stone,'palette_override':palette(roof,stone),'source_height_candidate_m':b['height_candidate_m'],'height_delta_m':round(h-b['height_candidate_m'],3),'chunk_id':f'{math.floor(pos[0]/64)}_{math.floor(pos[2]/64)}','collision_policy':'conservative_exterior_envelope_except_explicit_gate_opening'}
  if role=='gatehouse':
   gate_roads={'D09-B001':['RT_SOUTH_MARKET.000','RT_BRIDGE.000'],'D09-B002':['RT_EAST_MARKET.000','RT_SUB_E.000'],'D09-B003':['RT_NORTH_MARKET.000'],'D09-B004':['RT_WEST_MARKET.000']}[bid]
   inst['gate_openings']=[{'local_bounds':{'min':[-5,0,-ad/2],'max':[5,5,ad/2]},'road_ids':gate_roads}]
   for opening in spec.get('secondary_openings',[]):inst['gate_openings'].append({'local_bounds':opening,'road_ids':gate_roads})
  if bid=='D09-B029':inst['road_openings']=[{'local_bounds':{'min':[-5,0,2.5],'max':[5,3,5]},'road_ids':['L13.013'],'clearance_height_m':3}]
  instances.append(inst)
 scene={'schema':'riverstone.city.scene.v1','revision':'recovered_r1','status':'authoring_not_visual_pass','coordinate_system':plan['coordinate_system'],'sources':{'layout':'world_city/data/city_brief.v2.json','layout_sha256':sha(ROOT/'world_city/data/city_brief.v2.json'),'history':'world_city/city_history.json','history_sha256':sha(ROOT/'world_city/city_history.json')},'source_recovery':'source/recovery_record.json','terrain_grade_policy':'flat_coarse_voxel_platform_y0_initial_exterior_milestone; original candidate heights unresolved','lod_policy':{'same_continuous_master':True,'coarse_pitch_m':.5,'fine_pitch_m':.25,'fine_radius_m':110,'fine_instance_cap':48,'chunk_span_m':64,'geometry_transform_scale':[1,1,1]},'instances':instances,'asset_specs':specs,'assets':{},'roads':plan['roads'],'road_nodes':plan['road_nodes'],'site_features':plan['site_features'],'river_reservation':plan['river_reservation'],'district_rules':history['district_rules'],'protected_design_records':list(PROTECTED),'open_space_policy':'original road ribbons and plot courtyards are immutable reservations'}
 return scene

def compile_one(spec,out,pitch):
 if spec['family']=='ordinary':
  from world_city.runtime_city.archetypes.ordinary import make_master
 elif spec['family']=='landmark':
  from world_city.runtime_city.landmarks.author import make_master
 else:raise ValueError(spec)
 master=make_master({k:v for k,v in spec.items() if k!='family'})
 mpath=out/'masters'/f"{spec['asset_id']}.json";write(mpath,master)
 rpath=out/'renders'/f"{spec['asset_id']}_{pitch}.json"; cpath=out/'compiled'/f"{spec['asset_id']}_{pitch}.json"; meta=out/'cache'/f"{spec['asset_id']}_{pitch}.json"
 key={'master':sha(mpath),'pitch':pitch,'compiler':sha(ROOT/'voxel_character/common/core.py'),'planes':sha(ROOT/'voxel_character/common/coordinate_planes.py'),'exporter':sha(ROOT/'voxel_character/common/render_data.py'),'mesher':sha(ROOT/'voxel_character/tools/mesh.py')}
 if meta.exists() and rpath.exists():
  old=json.loads(meta.read_text())
  if old['key']==key and old['render_sha256']==sha(rpath):return old
 start=time.monotonic()
 result=coordinate_planes.compile_master(master,{'pitch':pitch},max_candidate_cells=6500000,max_output_cells=1600000)
 if not result['valid']:raise ValueError((spec['asset_id'],result.get('validation')))
 render=render_data.make_render_data(result);write(rpath,render)
 # Compiled cells are regeneration products; keep small cache entries and master, not duplicate full city cells.
 stats={'key':key,'render_path':str(rpath.relative_to(ROOT)),'render_sha256':sha(rpath),'master_path':str(mpath.relative_to(ROOT)),'master_sha256':sha(mpath),'cell_count':render['cell_count'],'quad_count':render['quad_count'],'bounds':render['bounds'],'seconds':round(time.monotonic()-start,3),'constraints':result.get('constraints',result.get('validation',{})),'author_metadata':master.get('metadata',{}),'author_extensions':master.get('extensions',{})}
 write(meta,stats);return stats

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan-only',action='store_true');ap.add_argument('--limit',type=int);ap.add_argument('--fine',action='store_true');ap.add_argument('--asset');args=ap.parse_args()
 scene=make_plan();out=HERE/'generated'/'r1';out.mkdir(parents=True,exist_ok=True);write(out/'authoring_plan.json',scene)
 print(json.dumps({'instances':len(scene['instances']),'unique_masters':len(scene['asset_specs']),'styles':dict(collections.Counter(x.get('style',x.get('kind')) for x in scene['asset_specs'].values()))}),flush=True)
 if args.plan_only:return
 for i,(key,spec) in enumerate(scene['asset_specs'].items()):
  if args.asset and args.asset!=key:continue
  if args.limit is not None and i>=args.limit:break
  stats=compile_one(spec,out,.5);scene['assets'][key]={'coarse':stats}
  if args.fine and any(x['asset_key']==key and x['preserved_record'] for x in scene['instances']):scene['assets'][key]['fine']=compile_one(spec,out,.25)
  print(json.dumps({'index':i,'id':key,'cells':stats['cell_count'],'quads':stats['quad_count'],'seconds':stats['seconds']}),flush=True)
 # Load already verified fine records, never pretend an unbuilt catalog entry exists.
 for key in scene['assets']:
  for name,pitch in [('fine',.25)]:
   meta=out/'cache'/f'{key}_{pitch}.json'
   if meta.exists():
    data=json.loads(meta.read_text())
    if data['key']['master']==scene['assets'][key]['coarse']['master_sha256'] and (ROOT/data['render_path']).exists() and sha(ROOT/data['render_path'])==data['render_sha256']:scene['assets'][key][name]=data
 for inst in scene['instances']:
  if inst['asset_key'] in scene['assets']:
   asset=scene['assets'][inst['asset_key']]['coarse']
   all_lod=list(scene['assets'][inst['asset_key']].values());inst['local_bounds']={'min':[min(a['bounds']['min'][j] for a in all_lod) for j in range(3)],'max':[max(a['bounds']['max'][j] for a in all_lod) for j in range(3)]}
   master=json.loads((ROOT/asset['master_path']).read_text());asset['author_metadata']=master.get('metadata',{});asset['author_extensions']=master.get('extensions',{})
   ent=asset.get('author_metadata',{}).get('entrance',{})
   if not ent and asset.get('author_extensions',{}).get('entrances'):
    ent={'position':asset['author_extensions']['entrances'][0]['threshold_local_m']}
   if 'position' in ent:
    local=ent['position'];yaw=inst['yaw_rad'];p=inst['position_m'];inst['entrance']['local_position_m']=local
    inst['entrance']['position_m']=[p[0]+math.cos(yaw)*local[0]+math.sin(yaw)*local[2],p[1]+local[1],p[2]-math.sin(yaw)*local[0]+math.cos(yaw)*local[2]]
    inst['entrance']['facade_inset_m']=inst['local_bounds']['max'][2]-local[2]
    inst['entrance']['author_metadata_verified']=True
 scene['catalog_complete']=len(scene['assets'])==len(scene['asset_specs']);write(out/'scene.json',scene)
 print(json.dumps({'catalog_complete':scene['catalog_complete'],'assets':len(scene['assets']),'scene':str(out/'scene.json')}),flush=True)
if __name__=='__main__':main()
