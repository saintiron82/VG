"""Registered source to immutable coarse-cache candidates, with floor datums."""
from __future__ import annotations
import copy,hashlib,json,math
from pathlib import Path
from collections import Counter,defaultdict
from ..resolve_cached import sha,seed,transform,footprint,union_bounds,dimensions,closest,clean_line,ROOFS
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.registered_source.author import Domain
from world_city.concept_city_v3.registered_topography import author as terrain
HERE=Path(__file__).parent;CITY=HERE.parents[2];ROOT=CITY.parents[1]
PLAN=CITY/'registered_source/plan.json';CACHE=ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json'

def build():
 pb=PLAN.read_bytes();cb=CACHE.read_bytes();plan=json.loads(pb);old=json.loads(cb);ph=hashlib.sha256(pb).hexdigest();plots={p['id']:p for p in plan['plots']};roads={r['id']:r for r in plan['roads']};source_masses={b['id']:b for b in plan['buildings']}
 recipe_ids={p['id'] for p in plan['plots'] if 'noble_estate' in p['property_type'] or p['property_type'] in ('merchant_court','poor_block')};suppressed=set(plan.get('landmark_component_suppressed_building_ids',[]));eligible=[];excluded=[]
 for b in plan['buildings']:
  reason='recipe_owned_property' if b.get('plot_id') in recipe_ids else 'landmark_component_owner' if b['id'] in suppressed else 'dedicated_facility' if b.get('replace_by_assembly_key') else None
  if reason:excluded.append({'source_mass_id':b['id'],'reason':reason})
  else:eligible.append(b)
 catalog=[]
 for key,spec in old['asset_specs'].items():
  if spec.get('family')!='ordinary_r2':continue
  asset=old['assets'][key]['coarse'];bb=union_bounds(old['assets'][key]);w,h,d=dimensions(bb);catalog.append({'key':key,'spec':spec,'asset':asset,'outer':bb,'w':w,'d':d,'h':h})
 boundary=Domain([plan['boundary_xz_m']]);obstacles=Domain();owners={}
 for b in plan['buildings']:obstacles.add(b['footprint_xz_m'],b['id'])
 for p in plan['plots']:obstacles.add(p['polygon_xz_m'],p['id'])
 # Exact finite current water and explicit bank/service reservations; no old canal.
 for w in plan['water_reservations']['finite_water_polygons']:obstacles.add(w['polygon_xz_m'],'WATER:'+w['surface_id'])
 for w in plan['water_reservations']['channels']:
  for i,(a,b) in enumerate(zip(w['polyline_xz_m'],w['polyline_xz_m'][1:])):obstacles.add(g.road_ribbon(a,b,w['width_m']+6),'BANK:'+w['id']+':'+str(i))
 owner_paths=defaultdict(list)
 for p in plan['paths']:
  if p.get('owner_building_id'):owner_paths[p['owner_building_id']].append(p)
 def clear(poly,b):return boundary.contains(poly) and not obstacles.hits(poly,(b['id'],b.get('plot_id')))
 def fit(c,b):
  poly=footprint(c['outer'],b['position_xz_m'],b['yaw_rad'])
  return boundary.contains(poly) and Domain([b['footprint_xz_m']]).contains(poly) and Domain([plots[b['plot_id']]['polygon_xz_m']]).contains(poly)
 def access(c,b):
  meta=c['asset']['author_metadata'];entries=meta['entrance'].get('all_positions') or [meta['entrance']['position']];result=[];origin=b['position_xz_m'];yaw=b['yaw_rad'];body=footprint(meta['body_bounds'],origin,yaw)
  for i,e in enumerate(entries):
   door=transform([e[0],e[2]],origin,yaw);lip=transform([e[0],c['outer']['max'][2]],origin,yaw);stand=transform([e[0],c['outer']['max'][2]+1],origin,yaw);landing=g.road_ribbon(lip,stand,1.8)
   if not clear(landing,b) or g.positive_area_overlap(landing,body,1e-6):return None,'threshold_landing_conflict'
   choices=[]
   for route in owner_paths[b['id']]+[roads[b['road_id']]]:
    hit=closest(stand,route['polyline_xz_m'])
    if not hit:continue
    _,q,si,t=hit
    lines=[[stand,q],[stand,transform([0,c['outer']['max'][2]+1],origin,yaw),q]]
    for line in lines:
     line=clean_line(line)
     if len(line)<2:continue
     full=clean_line([lip]+line);ribs=[g.road_ribbon(a,z,1.8) for a,z in zip(full,full[1:])];length=sum(math.dist(a,z) for a,z in zip(line,line[1:]))
     if length<=10 and all(clear(poly,b) and not g.positive_area_overlap(poly,body,1e-6) for poly in ribs):choices.append((length,full,route['id'],si,t,ribs))
   if not choices:return None,'no_bounded_actual_offset_approach'
   length,line,target,si,t,ribs=min(choices,key=lambda v:(v[0],v[2]));result.append({'id':b['id']+':ACTUAL_DOOR:'+str(i),'door_index':i,'door_local_m':e,'actual_door_xz_m':door,'threshold_lip_xz_m':lip,'interaction_anchor_xz_m':stand,'cached_threshold_stub_xz_m':[door,lip],'complete_proposed_connection_xz_m':line,'reserved_connection_polygons_xz_m':ribs,'width_m':1.8,'external_length_m':length,'connects_source_path_or_road_id':target,'connects_segment_index':si,'connects_segment_t':t,'actual_door_offset_from_proxy_m':math.dist(door,b['entrance_xz_m']),'source_proxy_entrance_xz_m':b['entrance_xz_m'],'source_frontage_reservation_polygon_xz_m':plots[b['plot_id']].get('frontage_reservation_polygon_xz_m'),'interaction_anchor_provenance':'authored exterior standing anchor at actual door X and cached all-LOD front+1m','collision_policy':'closed exterior interaction; no open portal or walk-through interior claim','proposal_only':True})
  return result,None
 protected=[];reserved={};oldids={b['id']:b for b in old['instances']};market=next(q for q in plan['correspondences'] if q['id']=='MARKET');market_center=[99.4982,27.278]
 used=set()
 for sid in old['protected_design_records']:
  inst=oldids[sid];key=inst['asset_key'];bb=union_bounds(old['assets'][key]);w,h,d=dimensions(bb);c={'key':key,'spec':old['asset_specs'][key],'asset':old['assets'][key]['coarse'],'outer':bb,'w':w,'d':d,'h':h,'source_design_id':sid,'protected_instance':inst};choices=[]
  for b in eligible:
   if b['id'] in used or b['district_id']=='D_POOR' or math.dist(b['position_xz_m'],market_center)>160 or not fit(c,b):continue
   links,reason=access(c,b)
   if links is not None:choices.append((math.dist(b['position_xz_m'],market_center),b,c,links))
  if choices:
   _,b,c,links=min(choices,key=lambda v:(v[0],v[1]['id']));reserved[b['id']]=(c,links);used.add(b['id']);protected.append({'source_design_id':sid,'source_mass_id':b['id'],'asset_key':key,'status':'resolved_existing_registered_market_near_slot','palette_id':inst['palette_id'],'palette_override':inst['palette_override'],'all_cached_lod_outer_bounds_local_m':bb})
  else:protected.append({'source_design_id':sid,'asset_key':key,'status':'unresolved_no_exact_existing_registered_market_slot','required_outer_width_depth_m':[w,d],'policy':'No scaling, parcel changes or displacement of approved source masses.'})
 placements=[];links_out=[];unresolved=[];assets={};used_assets=Counter()
 for b in eligible:
  poor=b['district_id']=='D_POOR';desire='poor_row' if poor else 'regular_house';target_era=('early','late','rebuilt')[seed(b['id']+':era')%3];choice=reserved.get(b['id'])
  if choice is None:
   candidates=[]
   for c in catalog:
    s=c['spec']
    if s.get('assembly_class') not in (desire,'regular_house','servant_lodge') or c['w']>b['width_m']+1e-5 or c['d']>b['depth_m']+1e-5:continue
    cover=c['w']*c['d']/(b['width_m']*b['depth_m'])
    if cover<.5 or not fit(c,b):continue
    score=(1-cover)*24+abs(s['floors']-b['floors'])*2+abs(c['h']-b['height_m'])*.12+(0 if s['assembly_class']==desire else 3)+(0 if s.get('construction_era')==target_era else .4)+(seed(b['id']+c['key'])%1000)/2500
    candidates.append((score,c))
   failures=[]
   for _,c in sorted(candidates,key=lambda v:(v[0],v[1]['key'])):
    links,reason=access(c,b)
    if links is not None:choice=(c,links);break
    failures.append({'asset_key':c['key'],'reason':reason})
   if choice is None:unresolved.append({'source_mass_id':b['id'],'reason':'no_immutable_cached_envelope_and_actual_entry_fit','failures':failures[:5]});continue
  c,links=choice;asset=c['asset'];meta=asset['author_metadata'];s=c['spec'];floor=b['pad_floor_y_m'];local_floor=meta['entrance']['position'][1];origin_y=floor-local_floor;p=b['position_xz_m'];yaw=b['yaw_rad'];body=meta['body_bounds'];support=[]
  for u in (0,.25,.5,.75,1):
   for v in (0,.25,.5,.75,1):
    q=transform([body['min'][0]+u*(body['max'][0]-body['min'][0]),body['min'][2]+v*(body['max'][2]-body['min'][2])],p,yaw);support.append([q[0],terrain.height_at(*q),q[1]])
  hs=[q[1] for q in support];intrusion=max(0,max(hs)-floor);gap=max(0,origin_y+c['outer']['min'][1]-min(hs));foundation={'sampling_policy':'5x5 exact current H samples over actual body; finite sample evidence only','support_samples_xyz_m':support,'terrain_min_m':min(hs),'terrain_max_m':max(hs),'terrain_range_m':max(hs)-min(hs),'terrain_intrusion_above_finished_floor_m':intrusion,'unsupported_gap_below_cached_plinth_m':gap,'intentional_foundation_embed_at_flat_floor_m':local_floor-c['outer']['min'][1],'status':'requires_owned_grade_or_foundation_resolution' if intrusion>.05 or gap>.05 else 'sampled_support_with_intentional_plinth_embed','no_automatic_origin_raise':True}
  for l in links:
   e=l['door_local_m'];door_y=origin_y+e[1];lip=l['threshold_lip_xz_m'];stand=l['interaction_anchor_xz_m'];sy=terrain.height_at(*stand);profile=[]
   for a,z in zip(l['complete_proposed_connection_xz_m'],l['complete_proposed_connection_xz_m'][1:]):
    n=max(1,math.ceil(math.dist(a,z)/.25))
    for i in range(n+1):
     q=[a[k]+i/n*(z[k]-a[k]) for k in (0,1)];profile.append([q[0],terrain.height_at(*q),q[1]])
   grades=[abs(v[1]-u[1])/math.hypot(v[0]-u[0],v[2]-u[2]) for u,v in zip(profile,profile[1:]) if math.hypot(v[0]-u[0],v[2]-u[2])>1e-7]
   l.update(source_mass_id=b['id'],source_plot_id=b['plot_id'],asset_key=c['key'],pad_floor_y_m=floor,asset_origin_y_m=origin_y,actual_door_xyz_m=[l['actual_door_xz_m'][0],door_y,l['actual_door_xz_m'][1]],threshold_lip_xyz_m=[lip[0],door_y,lip[1]],interaction_anchor_xyz_m=[stand[0],sy,stand[1]],door_floor_error_from_authored_datum_m=door_y-floor,threshold_to_existing_standing_ground_delta_m=door_y-sy,exact_H_sampled_profile_xyz_m=profile,maximum_sampled_ground_grade=max(grades,default=0),vertical_status='requires_owned_frontage_grade_review' if abs(door_y-sy)>.08 or max(grades,default=0)>.12 else 'sampled_grade_connection; capsule_not_tested',step_geometry_authored=False)
   links_out.append(l)
  if c.get('protected_instance'):palette_id=c['protected_instance']['palette_id'];palette=copy.deepcopy(c['protected_instance']['palette_override']);palette_provenance='verbatim protected design palette in immutable source cache'
  else:
   roof={'red_clay':'clay_red','gray_slate':'slate_gray','brown_shingle':'wood_brown'}.get(b.get('roof_material'),'clay_red');palette_id=roof;palette=dict(zip(('slate','slate_light','slate_dark','slate_worn'),ROOFS[roof]));palette_provenance='external semantic roof-slot mapping; master unchanged'
  placements.append({'id':b['id'],'source_mass_id':b['id'],'source_plot_id':b['plot_id'],'source_district_id':b['district_id'],'source_function':b['function'],'source_design_id':c.get('source_design_id'),'asset_key':c['key'],'lod':'coarse','position_m':[p[0],origin_y,p[1]],'yaw_rad':yaw,'scale':[1,1,1],'pad_floor_y_m':floor,'cached_primary_door_local_y_m':local_floor,'origin_datum_rule':'origin_y=pad_floor_y_m-cached_primary_door_local_y_m','actual_entrance_ids':[l['id'] for l in links],'actual_body_bounds_local_m':body,'actual_body_footprint_xz_m':footprint(body,p,yaw),'actual_sampled_bounds_local_m':asset['bounds'],'all_cached_lod_outer_bounds_local_m':c['outer'],'actual_outer_footprint_xz_m':footprint(c['outer'],p,yaw),'source_mass_size_m':[b['width_m'],b['height_m'],b['depth_m']],'height_delta_from_source_mass_m':dimensions(asset['bounds'])[1]-b['height_m'],'foundation_support':foundation,'assembly_class':s.get('assembly_class','protected_ordinary'),'construction_era':s.get('construction_era'),'roof_form':s.get('roof_form'),'floors':s['floors'],'palette_id':palette_id,'palette_override':palette,'palette_provenance':palette_provenance,'horizontal_status':'actual_all_LOD_envelope_contained; bounded_real_door_links_reserved','promotion_status':'candidate_only_pending_registered_blockout_and_independent_review'})
  assets[c['key']]=copy.deepcopy(asset);used_assets[c['key']]+=1
 manifest=[]
 for key,a in sorted(assets.items()):
  for typ in ('master','render'):assert sha(ROOT/a[typ+'_path'])==a[typ+'_sha256']
  manifest.append({'asset_key':key,'master_path':a['master_path'],'master_sha256':a['master_sha256'],'render_path':a['render_path'],'render_sha256':a['render_sha256'],'quad_count':a['quad_count'],'instance_count':used_assets[key]})
 summary={'eligible_source_masses':len(eligible),'resolved_placements':len(placements),'unresolved_source_masses':len(unresolved),'excluded_source_masses':len(excluded),'actual_doors':len(links_out),'selected_unique_cached_assets':len(assets),'selected_unique_quads':sum(a['quad_count'] for a in assets.values()),'drawn_instance_quads':sum(assets[p['asset_key']]['quad_count'] for p in placements),'protected_designs_resolved':sum(q['status'].startswith('resolved') for q in protected),'protected_designs_unresolved':sum(q['status'].startswith('unresolved') for q in protected),'finished_floor_datum_errors':sum(abs(l['door_floor_error_from_authored_datum_m'])>1e-8 for l in links_out),'foundation_review_required':sum(p['foundation_support']['status'].startswith('requires') for p in placements),'frontage_grade_review_required':sum(l['vertical_status'].startswith('requires') for l in links_out),'automatic_stair_count':0,'new_compile_count':0,'geometry_scaling_count':0,'era_counts':dict(Counter(p['construction_era'] for p in placements)),'roof_form_counts':dict(Counter(p['roof_form'] for p in placements))}
 result={'schema':'riverstone.registered_city.ordinary_cached_candidate.v1','status':'candidate_pack_pending_registered_blockout_review','source_plan_sha256':ph,'source_plan_path':str(PLAN.relative_to(ROOT)),'source_cache_sha256':hashlib.sha256(cb).hexdigest(),'source_cache_path':str(CACHE.relative_to(ROOT)),'terrain_author_sha256':sha(terrain.__file__),'terrain_module':'world_city.concept_city_v3.registered_topography.author','registration_controls_sha256':plan['registration']['controls_sha256'],'market_anchor_xz_m':market_center,'summary':summary,'assets':assets,'cache_manifest':manifest,'placements':placements,'access_proposals':links_out,'excluded_source_records':excluded,'unresolved':unresolved,'protected_design_resolution':protected,'limits':['No source-plan, old resolver, cache or scene mutation. No new compilation or whole-building scaling.','Native coarse cache only; all-LOD conservative horizontal envelope is checked.','Finished threshold floor is authoritative: originY=floor-cached local doorway Y. No automatic 0.5m stairs.','Exact-H support sampling and bounded horizontal links are proposals, not capsule or foundation approval.','Reserved frontage grade changes and unsupported plinth/terrain intersections require the separate terrain owner.']}
 assert sha(PLAN)==ph and sha(CACHE)==result['source_cache_sha256'];return result

def main():
 d=build();(HERE/'resolved_placements.json').write_text(json.dumps(d,sort_keys=True,indent=2)+'\n');(HERE/'summary.json').write_text(json.dumps(d['summary'],sort_keys=True,indent=2)+'\n');print(json.dumps(d['summary'],sort_keys=True))
if __name__=='__main__':main()
