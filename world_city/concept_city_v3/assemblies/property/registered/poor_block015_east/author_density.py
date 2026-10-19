"""Reconstructed B015 source after executor loss. Geometry uses retained bounded specs; new seal required."""
from __future__ import annotations
import json,math,copy,hashlib
from pathlib import Path
from collections import Counter
from world_city.concept_city_v3.registered_source.author import Domain,box,nearest
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import footprint,transform,union_bounds,dimensions,closest,seed
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).parent;CITY=HERE.parents[3];ROOT=CITY.parents[1]
PLAN=CITY/'registered_source/plan.json';PRIOR=CITY/'assemblies/ordinary/registered/resolved_placements.json';CACHE=ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json'
BLOCK_ID='BLOCK_015'
SUBAREA_ID='BLOCK_015_EAST'
SUBAREA=[[282.371296,169.720134],[341.614287,157.322487],[396.442227,138.221416],[375.47033,231.33076],[341.845381,303.188166],[317.579076,317.203892],[309.101337,256.298027]]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(Path(p).relative_to(ROOT)),'sha256':sha(p)}
def write(p,d):p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def unit(v):l=math.hypot(*v);return [x/l for x in v]
def sub(a,b):return [a[i]-b[i] for i in(0,1)]
def bbox(p):return [min(v[0] for v in p),min(v[1] for v in p),max(v[0] for v in p),max(v[1] for v in p)]
def disjoint(polys):
 result=[];index=geo._SpatialIndex(32)
 for p in polys:
  parts=[p]
  for i in sorted(index.candidates(p)):parts=[q for r in parts for q in geo.convex_difference(r,result[i]) if geo.polygon_area(q)>1e-7]
  for r in parts:index.add(len(result),r);result.append(r)
 return result

def build():
 plan=json.loads(PLAN.read_text());prior=json.loads(PRIOR.read_text());cache=json.loads(CACHE.read_text());plots={p['id']:p for p in plan['plots']};block=copy.deepcopy(next(b for b in plan['blocks'] if b['id']==BLOCK_ID));block.update(parent_block_id=BLOCK_ID,id=SUBAREA_ID,polygon_xz_m=SUBAREA,area_m2=geo.polygon_area(SUBAREA),boundary_road_ids=['EAST_RADIAL','POOR_SOUTH_CROSS','EAST_WALL_SERVICE']);roadmap={r['id']:r for r in plan['roads']};alley=roadmap['EAST_RADIAL'];region=Domain([block['polygon_xz_m']]);center=[sum(p[k] for p in block['polygon_xz_m'])/len(block['polygon_xz_m']) for k in(0,1)]
 replaced=[p for p in prior['placements'] if plots[p['source_plot_id']].get('block_id')==BLOCK_ID and region.contains(p['actual_outer_footprint_xz_m'])];oldids={p['id'] for p in replaced};roads=Domain();road_polys=[]
 for r in plan['roads']:
  for i,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   p=geo.road_ribbon(a,b,r['width_m']);roads.add(p,r['id']);road_polys.append({'id':r['id']+':'+str(i),'polygon_xz_m':p})
 fixed=Domain()
 for p in prior['placements']:
  if p['id'] not in oldids:fixed.add(p['actual_outer_footprint_xz_m'],p['id'])
 for p in plan['plots']:
  if p.get('block_id')!=BLOCK_ID:fixed.add(p['polygon_xz_m'],p['id'])
 for s in plan['spaces']:
  for p in s.get('polygons_xz_m',[s.get('polygon_xz_m')]):
   if p:fixed.add(p,s['id'])
 for w in plan['water_reservations']['finite_water_polygons']:fixed.add(w['polygon_xz_m'],'WATER:'+w['surface_id'])
 for r in plan['paths']:
  if r.get('owner_building_id') in oldids:continue
  for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):fixed.add(geo.road_ribbon(a,b,r.get('width_m',1.8)),r['id'])
 courts=[{'id':'B15E_SHARED_WELL_COURT','role':'shared_well_laundry_and_household_court','polygon_xz_m':[[329,203],[343,203],[343,217],[329,217]],'finished_floor_y_m':2.5}, {'id':'B15E_REAR_WORK_COURT','role':'repair_and_shared_workcourt','polygon_xz_m':[[330,254],[340,254],[340,266],[330,266]],'finished_floor_y_m':2.5}]
 access=[];courts_domain=Domain()
 for court in courts:
  assert region.contains(court['polygon_xz_m']);courts_domain.add(court['polygon_xz_m'],court['id']);q=[sum(p[k] for p in court['polygon_xz_m'])/4 for k in(0,1)];_,end,si,t=closest(q,alley['polyline_xz_m']);line=[q,end];poly=geo.road_ribbon(q,end,3)
  access.append({'id':court['id']+':LINK','owner_id':court['id'],'width_m':3,'polyline_xz_m':line,'connects_road_id':alley['id'],'reserved_polygons_xz_m':[poly],'finished_floor_y_m':2.5,'observed_vs_inferred':'New bounded court connection within the traced residential road face.'});courts_domain.add(poly,court['id']+':LINK')
 catalog=[]
 for key,spec in cache['asset_specs'].items():
  if spec.get('assembly_class')!='poor_row' or spec.get('attached_units',1)!=1 or spec['width_m'] not in (10,12) or spec['depth_m'] not in (10,14,18):continue
  a=cache['assets'][key]['coarse'];b=a['author_metadata']['body_bounds'];o=union_bounds(cache['assets'][key]);catalog.append({'key':key,'spec':spec,'asset':a,'body':b,'outer':o,'body_w':b['max'][0]-b['min'][0]})
 controls=[];ring=block['polygon_xz_m']
 for i,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
  if i==4:continue # Finite rear ownership cut, not a new street.
  mid=[(a[k]+b[k])/2 for k in(0,1)];nearest_road=min((nearest(mid,[roadmap[r]])[0] for r in block['boundary_road_ids']),key=lambda q:q[0]);rid=nearest_road[1];t=unit(sub(b,a));n=[-t[1],t[0]]
  if sum((center[k]-mid[k])*n[k] for k in(0,1))<0:n=[-x for x in n]
  controls.append({'id':f'B15E_BOUNDARY_FRONTAGE_{i:02}','a_xz_m':a,'b_xz_m':b,'inward_unit_xz':n,'road_id':rid,'width_m':roadmap[rid]['width_m'],'depth_preference_m':18,'role':'attached_streetfront_house_and_rear_workroom','basis':'Existing registered block edge; exact road strips remain blockers.'})
 bodies=Domain();outers=Domain();placements=[];assets={};groups=[];rejects=Counter();doors=[]
 for control in controls:
  a,b=control['a_xz_m'],control['b_xz_m'];t=unit(sub(b,a));n=control['inward_unit_xz'];out=[-n[0],-n[1]];yaw=math.atan2(out[0],out[1]);length=math.dist(a,b);station=4.;part=0;group=None;count_in_group=0
  while station+5<length-3:
   options=[]
   for c in catalog:
    s=c['spec'];w=c['body_w'];pos_s=station+w/2
    if pos_s+w/2>length-3:continue
    front=[a[k]+t[k]*pos_s+n[k]*(control['width_m']/2+1.6) for k in(0,1)];origin=[front[k]+n[k]*c['outer']['max'][2] for k in(0,1)];body=footprint(c['body'],origin,yaw);outer=footprint(c['outer'],origin,yaw)
    if not region.contains(outer) or roads.hits(outer) or fixed.hits(outer) or courts_domain.hits(outer) or bodies.hits(body):continue
    if outers.hits(outer,(() if group is None else (group['id'],))):continue
    meta=c['asset']['author_metadata'];entry=meta['entrance']['position'];door=transform([entry[0],entry[2]],origin,yaw);lip=transform([entry[0],c['outer']['max'][2]],origin,yaw);_,end,si,tt=closest(lip,roadmap[control['road_id']]['polyline_xz_m']);ribbon=geo.road_ribbon(lip,end,1.8)
    if not region.contains(ribbon) or fixed.hits(ribbon) or bodies.hits(ribbon) or courts_domain.hits(ribbon):continue
    desired_floors=1 if (len(placements)+part)%5==0 else 2;score=abs(s['depth_m']-control['depth_preference_m'])*2+abs(s['floors']-desired_floors)*1.5+(0 if s['width_m']==(12 if len(placements)%3==0 else 10) else .25)+(seed(control['id']+str(part)+c['key'])%100)/1000
    options.append((score,c,origin,body,outer,door,lip,end,ribbon,si,tt))
   if not options:
    rejects[control['id']]+=1;station+=2;group=None;count_in_group=0;continue
   _,c,origin,body,outer,door,lip,end,ribbon,si,tt=min(options,key=lambda q:(q[0],q[1]['key']))
   if group is None:
    group={'id':f'DENS_B15E_GROUP_{len(groups):03}','frontage_control_id':control['id'],'member_ids':[],'join_policy':'Native body side faces touch. Intentional roof/eave intersections are internal to one common union; separate mesh placement is not approved.','finished_floor_y_m':2.5};groups.append(group)
   bid=f'DENS_B15E_HOUSE_{len(placements):03}';did=bid+':ACTUAL_DOOR';meta=c['asset']['author_metadata'];e=meta['entrance']['position'];floor=2.5;placement={'id':bid,'source_mass_id':bid,'source_plot_id':group['id'],'source_district_id':'D_POOR','source_block_id':BLOCK_ID,'source_function':control['role'],'assembly_group_id':group['id'],'asset_key':c['key'],'position_m':[origin[0],floor-e[1],origin[1]],'yaw_rad':yaw,'scale':[1,1,1],'pad_floor_y_m':floor,'cached_primary_door_local_y_m':e[1],'actual_body_bounds_local_m':c['body'],'all_cached_lod_outer_bounds_local_m':c['outer'],'actual_body_footprint_xz_m':body,'actual_outer_footprint_xz_m':outer,'actual_entrance_ids':[did],'floors':c['spec']['floors'],'construction_era':c['spec']['construction_era'],'roof_form':c['spec']['roof_form'],'native_width_depth_m':[c['spec']['width_m'],c['spec']['depth_m']],'floor_authority':'Existing D_POOR finished bench +2.5; new terrain ledger must independently bind exact body and door reservations.','promotion_status':'native-source layout candidate; common group union required before scene placement'};placements.append(placement);assets[c['key']]=c['asset'];group['member_ids'].append(bid)
   bodies.add(body,bid);outers.add(outer,group['id']);doors.append({'id':did,'source_mass_id':bid,'source_plot_id':group['id'],'actual_door_xyz_m':[door[0],floor,door[1]],'door_local_m':e,'threshold_lip_xyz_m':[lip[0],floor,lip[1]],'cached_threshold_stub_xz_m':[door,lip],'complete_proposed_connection_xz_m':[lip,end],'reserved_connection_polygons_xz_m':[ribbon],'width_m':1.8,'connects_source_path_or_road_id':control['road_id'],'connects_segment_index':si,'connects_segment_t':tt,'pad_floor_y_m':floor,'asset_origin_y_m':floor-e[1],'vertical_status':'fixed poor bench proposal; terrain and capsule review pending'})
   station+=c['body_w'];count_in_group+=1;part+=1
   if count_in_group>=4:station+=4;group=None;count_in_group=0
 # Inventory every actual cached doorway, including multi-household row doors.
 doors=[];group_controls={g['id']:next(c for c in controls if c['id']==g['frontage_control_id']) for g in groups}
 for placement in placements:
  a=assets[placement['asset_key']];entry_meta=a['author_metadata']['entrance'];entries=entry_meta.get('all_positions') or [entry_meta['position']];origin=[placement['position_m'][0],placement['position_m'][2]];yaw=placement['yaw_rad'];floor=placement['pad_floor_y_m'];control=group_controls[placement['assembly_group_id']];placement['road_id']=control['road_id'];placement['actual_entrance_ids']=[]
  for i,e in enumerate(entries):
   did=placement['id']+':ACTUAL_DOOR:'+str(i);door=transform([e[0],e[2]],origin,yaw);lip=transform([e[0],placement['all_cached_lod_outer_bounds_local_m']['max'][2]],origin,yaw);_,end,si,tt=closest(lip,roadmap[control['road_id']]['polyline_xz_m']);ribbon=geo.road_ribbon(lip,end,1.8);placement['actual_entrance_ids'].append(did)
   doors.append({'id':did,'source_mass_id':placement['id'],'source_plot_id':placement['source_plot_id'],'actual_door_xyz_m':[door[0],floor,door[1]],'door_local_m':e,'threshold_lip_xyz_m':[lip[0],floor,lip[1]],'cached_threshold_stub_xz_m':[door,lip],'complete_proposed_connection_xz_m':[lip,end],'reserved_connection_polygons_xz_m':[ribbon],'width_m':1.8,'connects_source_path_or_road_id':control['road_id'],'connects_segment_index':si,'connects_segment_t':tt,'pad_floor_y_m':floor,'asset_origin_y_m':floor-e[1],'vertical_status':'fixed poor bench proposal; terrain and capsule review pending'})
 # Groups with interrupted row placement still have explicit contiguous native members.
 outer_union=disjoint([p['actual_outer_footprint_xz_m'] for p in placements]);body_area=sum(geo.polygon_area(p['actual_body_footprint_xz_m']) for p in placements);outer_area=sum(geo.polygon_area(p) for p in outer_union);old_body=sum(geo.polygon_area(p['actual_body_footprint_xz_m']) for p in replaced);old_outer=sum(geo.polygon_area(p) for p in disjoint([p['actual_outer_footprint_xz_m'] for p in replaced]))
 row={'block_id':BLOCK_ID,'gross_block_area_m2':block['area_m2'],'before_houses':len(replaced),'after_houses':len(placements),'before_body_area_m2':old_body,'after_body_area_m2':body_area,'before_outer_union_area_m2':old_outer,'after_outer_union_area_m2':outer_area,'before_body_coverage':old_body/block['area_m2'],'after_body_coverage':body_area/block['area_m2'],'before_outer_coverage':old_outer/block['area_m2'],'after_outer_coverage':outer_area/block['area_m2'],'body_target_range':[.40,.55],'target_met':.4<=body_area/block['area_m2']<=.55,'court_area_m2':sum(geo.polygon_area(c['polygon_xz_m']) for c in courts),'attached_row_groups':sum(len(g['member_ids'])>1 for g in groups),'single_member_groups':sum(len(g['member_ids'])==1 for g in groups),'native_assets':len(assets),'actual_doorways':len(doors),'count_unit':'Native modules; physical entrances do not establish household counts'}
 result={'schema':'riverstone.registered_ordinary_density_revision.v1','revision':'recovered_block015_east_native_attached_candidate','status':'source layout candidate pending density/terrain review and common union compile','source_plan':ref(PLAN),'baseline_native_pack':ref(PRIOR),'source_cache':ref(CACHE),'block':block,'replaced_placement_ids':sorted(oldids),'superseded_old_path_ids':[p['id'] for p in plan['paths'] if p.get('owner_building_id') in oldids],'frontage_controls':controls,'groups':groups,'assets':assets,'placements':placements,'access_proposals':doors,'courts':courts,'court_paths':access,'outer_union_polygons_xz_m':outer_union,'summary':row,'candidate_rejections':dict(rejects),'source_policy':{'new_master_compilation_count':0,'whole_house_scaling_count':0,'old_source_modified':False,'observed':'Three traced streets are retained. The rear subarea cut is not a public lane.','inferred':'All denser rows, party joins, rear courts and exact native module choices are explicit new design.'},'limits':['Roof/eave intersections inside an assembly group require one common occupancy union before runtime; raw overlapping cached meshes are not final geometry.','Gross block coverage excludes no road strip; body and roof-envelope unions are reported separately.','Additional frontage/court physics and exact terrain ownership remain pending.']}
 return result
if __name__=='__main__':
 d=build();write(HERE/'candidate.json',d);write(HERE/'summary.json',d['summary']);print(json.dumps(d['summary'],indent=2))
