#!/usr/bin/env python3
"""Cache-only ordinary resolver. No scaling, compilation, plan edit or scene output."""
from __future__ import annotations
import copy,hashlib,json,math,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
HERE=Path(__file__).parent;CITY=HERE.parents[1]
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.topography import author as terrain
PLAN=CITY/'source/plan.json';CACHE=ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json'
ROOFS={'clay_red':['a16b51','ac775c','80523f','b18a6c'],'wood_brown':['80664a','8c7355','624f3d','9c8568'],'slate_gray':['646f73','748085','4a565c','879096']}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def seed(value):return int(hashlib.sha256(value.encode()).hexdigest()[:12],16)
def transform(p,origin,yaw):return [origin[0]+math.cos(yaw)*p[0]+math.sin(yaw)*p[1],origin[1]-math.sin(yaw)*p[0]+math.cos(yaw)*p[1]]
def footprint(bounds,origin,yaw):return [transform([x,z],origin,yaw) for x,z in [(bounds['min'][0],bounds['min'][2]),(bounds['max'][0],bounds['min'][2]),(bounds['max'][0],bounds['max'][2]),(bounds['min'][0],bounds['max'][2])]]
def union_bounds(lods):return {'min':[min(a['bounds']['min'][i] for a in lods.values()) for i in range(3)],'max':[max(a['bounds']['max'][i] for a in lods.values()) for i in range(3)]}
def dimensions(bb):return [bb['max'][i]-bb['min'][i] for i in range(3)]
def closest(p,line):
 out=[]
 for i,(a,b) in enumerate(zip(line,line[1:])):
  dx,dz=b[0]-a[0],b[1]-a[1];ll=dx*dx+dz*dz
  if ll<1e-12:continue
  t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dz)/ll));q=[a[0]+t*dx,a[1]+t*dz];out.append((math.dist(p,q),q,i,t))
 return min(out,key=lambda v:v[0]) if out else None
def clean_line(line):
 out=[]
 for p in line:
  if not out or math.dist(out[-1],p)>1e-7:out.append(p)
 return out

def build():
 plan_bytes=PLAN.read_bytes();cache_bytes=CACHE.read_bytes();plan=json.loads(plan_bytes);old=json.loads(cache_bytes)
 plan_sha=hashlib.sha256(plan_bytes).hexdigest();assert terrain.SOURCE_PLAN_SHA256==plan_sha,'Terrain imported against a different source plan'
 plots={p['id']:p for p in plan['plots']};roads={r['id']:r for r in plan['roads']};oldids={b['id']:b for b in old['instances']}
 recipe_ids={p['id'] for p in plan['plots'] if p['property_type'] in ('noble_estate','merchant_court','poor_block')}
 suppressed=set(plan['landmark_component_suppressed_building_ids']);eligible=[];excluded=[]
 for b in plan['buildings']:
  reason='recipe_owned_parcel' if b.get('plot_id') in recipe_ids else 'suppressed_landmark_component_envelope' if b['id'] in suppressed else 'dedicated_facility_assembly' if b.get('replace_by_assembly_key') else None
  (excluded if reason else eligible).append({'source_mass_id':b['id'],'reason':reason} if reason else b)
 catalog=[]
 for key,spec in old['asset_specs'].items():
  if spec.get('family')!='ordinary_r2':continue
  asset=old['assets'][key]['coarse'];bb=union_bounds(old['assets'][key]);w,h,d=dimensions(bb)
  catalog.append({'key':key,'spec':spec,'asset':asset,'outer':bb,'w':w,'d':d,'h':h,'lod':'coarse'})
 catalog.sort(key=lambda v:v['key'])
 # Conservative source envelopes bound every independently resolved neighbor.
 obstacles=[];index=g._SpatialIndex(32)
 def obstacle(identity,poly,kind,owner=None):
  index.add(len(obstacles),poly);obstacles.append({'id':identity,'polygon':poly,'kind':kind,'owner':owner})
 for b in plan['buildings']:obstacle(b['id'],b['footprint_xz_m'],'building',b['id'])
 for p in plan['plots']:obstacle(p['id'],p['polygon_xz_m'],'other_property',p['id'])
 water=plan['water_reservations']
 for key,width in [('service_canal_polyline_xz_m',water['service_corridor_width_m']),('spring_feeder_polyline_xz_m',water.get('spring_feeder_reserve_width_m',8))]:
  line=water.get(key,[])
  for i,(a,b) in enumerate(zip(line,line[1:])):obstacle(key+':'+str(i),g.road_ribbon(a,b,width),'water')
 obstacle('reservoir',water['reservoir_outer_polygon_xz_m'],'water');obstacle('river',water['river_polygon_xz_m'],'water')
 owner_paths=defaultdict(list)
 for p in plan['paths']:
  if p.get('owner_building_id'):owner_paths[p['owner_building_id']].append(p)
 def clear(poly,b,allow_own_body=False):
  if not g.convex_polygon_contains(plan['boundary_xz_m'],poly,1e-5):return False,'wall_boundary'
  for j in index.candidates(poly):
   ob=obstacles[j]
   if ob['owner'] in (b['id'],b.get('plot_id')):continue
   if g.positive_area_overlap(poly,ob['polygon'],1e-6):return False,ob['id']
  return True,None
 def fit(c,b):
  p=footprint(c['outer'],b['position_xz_m'],b['yaw_rad'])
  return g.convex_polygon_contains(b['footprint_xz_m'],p,1e-5) and (not b.get('plot_id') or g.convex_polygon_contains(plots[b['plot_id']]['polygon_xz_m'],p,1e-5))
 def door_links(c,b):
  asset=c['asset'];meta=asset['author_metadata'];en=meta['entrance'];entries=en.get('all_positions') or [en['position']];origin=b['position_xz_m'];yaw=b['yaw_rad'];outer=c['outer'];body=footprint(meta['body_bounds'],origin,yaw)
  paths=owner_paths[b['id']];result=[]
  for i,e in enumerate(entries):
   door=transform([e[0],e[2]],origin,yaw);lip=transform([e[0],outer['max'][2]],origin,yaw);stand=transform([e[0],outer['max'][2]+1],origin,yaw)
   # The one-metre threshold landing is part of the reserved connection,
   # not an untested gap between cached porch and external path.
   landing=[lip,stand];landing_poly=g.road_ribbon(*landing,1.8)
   landing_ok,landing_obstacle=clear(landing_poly,b)
   if not landing_ok or g.positive_area_overlap(landing_poly,body,1e-6):
    return None,{'check':'threshold_landing_clearance_unresolved','door_index':i,'blocking_id':landing_obstacle or 'own_body'}
   choices=[]
   for p in paths:
    hit=closest(stand,p['polyline_xz_m'])
    if hit:
     _,q,seg,t=hit
     for line in [[stand,q],[stand,transform([0,outer['max'][2]+1],origin,yaw),q],[stand,transform([e[0],b['depth_m']/2+1],origin,yaw),q]]:
      line=clean_line(line)
      if len(line)<2:continue
      ribbons=[g.road_ribbon(a,z,1.8) for a,z in zip(line,line[1:])];errors=[]
      for qpoly in ribbons:
       ok,why=clear(qpoly,b)
       if not ok:errors.append(why)
       if g.positive_area_overlap(qpoly,body,1e-6):errors.append('own_body')
      length=sum(math.dist(a,z) for a,z in zip(line,line[1:]))
      if not errors and length<=8:choices.append((length,line,p['id'],seg,t))
   # A link may meet the source public road directly; still bounded and tested.
   road=roads.get(b.get('road_id'))
   if road:
    hit=closest(stand,road['polyline_xz_m'])
    if hit:
     _,q,seg,t=hit;line=clean_line([stand,q])
     if len(line)>1:
      ribbon=g.road_ribbon(*line,1.8);ok,why=clear(ribbon,b)
      if ok and not g.positive_area_overlap(ribbon,body,1e-6) and math.dist(*line)<=8:choices.append((math.dist(*line),line,road['id'],seg,t))
   if not choices:return None,{'check':'actual_offset_door_link_unresolved','door_index':i,'door_xz_m':door,'standing_xz_m':stand,'limit_m':8}
   length,line,target,seg,t=min(choices,key=lambda v:(v[0],v[2]))
   # The door-to-lip segment lies inside the existing cached threshold/porch.
   result.append({'id':b['id']+':ACTUAL_DOOR:'+str(i),'door_index':i,'door_local_m':e,'actual_door_xz_m':door,'threshold_lip_xz_m':lip,'interaction_anchor_xz_m':stand,
    'interaction_anchor_provenance':'authored external standing point at cached door X and all-LOD outer front +1m, not a cached metadata claim',
    'cached_threshold_stub_xz_m':[door,lip],'threshold_landing_polyline_xz_m':landing,'threshold_landing_reserved_run_m':1.0,'threshold_landing_width_m':1.8,'external_approach_polyline_xz_m':line,'complete_proposed_connection_xz_m':clean_line([lip]+line),'width_m':1.8,'external_length_m':length,'connects_source_path_or_road_id':target,'connects_segment_index':seg,'connects_segment_t':t,
    'source_proxy_entrance_xz_m':b['entrance_xz_m'],'actual_door_offset_from_proxy_m':math.dist(door,b['entrance_xz_m']),
    'horizontal_check':'bounded_ribbon_clear_of_other_buildings_properties_water_and_wall','collision_policy':'closed_exterior_door_interaction_only; no interior passage or opening is claimed'})
  return result,None
 # Preserve approved geometry/palette only where an existing ordinary source
 # slot contains the exact sampled envelope and all offset doors can be linked.
 protected=[];reserved={};used=set()
 for source_id in old['protected_design_records']:
  oldinst=oldids[source_id];key=oldinst['asset_key'];lods=old['assets'][key];lod='fine' if 'fine' in lods else 'coarse';a=lods[lod];bb=union_bounds(lods);w,h,d=dimensions(bb)
  c={'key':key,'spec':old['asset_specs'][key],'asset':a,'outer':bb,'w':w,'h':h,'d':d,'lod':lod,'source_design_id':source_id,'protected_instance':oldinst}
  candidates=[]
  for b in eligible:
   if b['id'] in used or b['district_id'] not in ('D_CIVIC','D_MERCHANT_N','D_MERCHANT_E','D_OLD'):continue
   distance=math.dist(b['position_xz_m'],[20,40])
   if distance>160 or not fit(c,b):continue
   links,err=door_links(c,b)
   if links is not None:candidates.append((distance,b,c,links))
  if candidates:
   _,b,c,links=min(candidates,key=lambda t:(t[0],t[1]['id']));reserved[b['id']]=(c,links);used.add(b['id']);status='resolved_existing_market_near_slot'
   protected.append({'source_design_id':source_id,'source_mass_id':b['id'],'source_plot_id':b.get('plot_id'),'asset_key':key,'status':status,'palette_id':oldinst['palette_id'],'palette_override':oldinst['palette_override'],'all_cached_lod_bounds':bb,'market_center_distance_m':math.dist(b['position_xz_m'],[20,40])})
  else:protected.append({'source_design_id':source_id,'asset_key':key,'status':'unresolved_no_fitting_existing_market_near_ordinary_slot','all_cached_lod_bounds':bb,'required_sampled_width_depth_m':[w,d],'constraint':'No scaling, source parcel merger, displacement of neighbors or circulation change is permitted by this resolver.'})
 # Score finite immutable variants by actual fit, class, era, style and floors.
 placed=[];unresolved=[];access=[];assets={};selection_counts=Counter()
 for b in eligible:
  desire='poor_row' if b['district_id'] in ('D_POOR','D_CRAFT_N','D_CRAFT_S') else 'regular_house'
  style='merchant' if b['district_id'] in ('D_CIVIC','D_MERCHANT_N','D_MERCHANT_E') else 'artisan' if 'CRAFT' in b['district_id'] else 'old_timber'
  era=('early','late','rebuilt')[seed(b['id']+':era')%3];best=None;rejections=[]
  if b['id'] in reserved:best=reserved[b['id']]
  else:
   choices=[]
   for c in catalog:
    s=c['spec']
    if s.get('assembly_class') not in (desire,'regular_house','servant_lodge'):continue
    if c['w']>b['width_m']+1e-5 or c['d']>b['depth_m']+1e-5:continue
    cover=c['w']*c['d']/(b['width_m']*b['depth_m'])
    if cover<.50 or not fit(c,b):continue
    score=(1-cover)*24+abs(s['floors']-b.get('floors',2))*2+abs(c['h']-b['height_m'])*.12+(0 if s['assembly_class']==desire else 3)+(0 if s.get('style')==style else 1.5)+(0 if s.get('construction_era')==era else .5)+(seed(b['id']+c['key'])%1000)/2500
    choices.append((score,c))
   for score,c in sorted(choices,key=lambda p:(p[0],p[1]['key'])):
    links,err=door_links(c,b)
    if links is not None:best=(c,links);break
    rejections.append({'asset_key':c['key'],**err})
  if best is None:
   unresolved.append({'source_mass_id':b['id'],'source_plot_id':b.get('plot_id'),'reason':'no_dimension_and_actual_door_clearance_fit_in_immutable_cache','source_width_depth_m':[b['width_m'],b['depth_m']],'route_failures':rejections[:5]});continue
  c,links=best;meta=c['asset']['author_metadata'];s=c['spec'];p=b['position_xz_m'];yaw=b['yaw_rad'];body=meta['body_bounds'];outer=c['outer'];bodypoly=footprint(body,p,yaw);outerpoly=footprint(outer,p,yaw)
  # Full rigid body support footprint and every cached porch lip are sampled
  # against exact H. Finite samples are evidence, not an analytic support proof.
  support=[]
  for u in (0.,.25,.5,.75,1.):
   for v in (0.,.25,.5,.75,1.):support.append(transform([body['min'][0]+u*(body['max'][0]-body['min'][0]),body['min'][2]+v*(body['max'][2]-body['min'][2])],p,yaw))
  support.extend(q['threshold_lip_xz_m'] for q in links);heights=[terrain.height_at(*q) for q in support];base=max(heights)
  support_rec={'sampling_policy':'5x5 body grid plus each cached threshold lip; each sample evaluates exact terrain.height_at, not a fitted plane','support_samples_xzy_m':[[q[0],q[1],h] for q,h in zip(support,heights)],'terrain_min_m':min(heights),'terrain_max_m':max(heights),'terrain_height_range_m':max(heights)-min(heights),'proposed_base_y_m':base,'maximum_under_plinth_gap_m':base-min(heights),'foundation_extension_required':base-min(heights)>.05,'status':'sampled_flat_support' if base-min(heights)<=.05 else 'requires_explicit_foundation_or_grade_resolution','no_unsupported_geometry_promoted':True}
  for link in links:
   e=link['door_local_m'];link['actual_door_xyz_m']=[link['actual_door_xz_m'][0],base+e[1],link['actual_door_xz_m'][1]];link['threshold_lip_xyz_m']=[link['threshold_lip_xz_m'][0],base+e[1],link['threshold_lip_xz_m'][1]]
   stand=link['interaction_anchor_xz_m'];sy=terrain.height_at(*stand);link['interaction_anchor_xyz_m']=[stand[0],sy,stand[1]];rise=base+e[1]-sy
   profile=[]
   for a,z in zip(link['complete_proposed_connection_xz_m'],link['complete_proposed_connection_xz_m'][1:]):
    for i in range(max(1,math.ceil(math.dist(a,z)/.25))+1):
     t=i/max(1,math.ceil(math.dist(a,z)/.25));q=[a[j]+t*(z[j]-a[j]) for j in (0,1)];profile.append([q[0],terrain.height_at(*q),q[1]])
   grades=[abs(v[1]-u[1])/math.hypot(v[0]-u[0],v[2]-u[2]) for u,v in zip(profile,profile[1:]) if math.hypot(v[0]-u[0],v[2]-u[2])>1e-7]
   link.update(source_mass_id=b['id'],source_plot_id=b.get('plot_id'),asset_key=c['key'],threshold_above_exact_ground_m=base+e[1]-terrain.height_at(*link['actual_door_xz_m']),threshold_to_standing_rise_m=rise,
    proposed_short_step_count=math.ceil(abs(rise)/.18) if abs(rise)>.08 else 0,minimum_step_run_m=math.ceil(abs(rise)/.18)*.28 if abs(rise)>.08 else 0,
    proposed_step_run_fits_reserved_landing=math.ceil(abs(rise)/.18)*.28<=link['threshold_landing_reserved_run_m'] if abs(rise)>.08 else True,
    exact_H_sampled_profile_xyz_m=profile,maximum_sampled_ground_grade=max(grades,default=0),vertical_status='requires_threshold_step_or_support_review' if abs(rise)>.08 or max(grades,default=0)>.12 else 'sampled_ground_connection_only; capsule_not_tested',proposal_only=True)
   access.append(link)
  if c.get('protected_instance'):palette_id=c['protected_instance']['palette_id'];palette=copy.deepcopy(c['protected_instance']['palette_override']);palette_provenance='verbatim preserved protected design instance in immutable scene.flat_property.json'
  else:
   roof=b.get('roof_material','clay_red');roof={'red_clay':'clay_red','gray_slate':'slate_gray','brown_shingle':'wood_brown'}.get(roof,roof)
   if roof not in ROOFS:roof='wood_brown' if desire=='poor_row' else 'clay_red'
   palette_id=roof;palette=dict(zip(('slate','slate_light','slate_dark','slate_worn'),ROOFS[roof]));palette_provenance='external semantic roof-slot palette; cached material geometry unchanged'
  item={'id':b['id'],'source_mass_id':b['id'],'source_plot_id':b.get('plot_id'),'source_design_id':c.get('source_design_id'),'asset_key':c['key'],'lod':c['lod'],'position_m':[p[0],base,p[1]],'yaw_rad':yaw,'scale':[1,1,1],'palette_id':palette_id,'palette_override':palette,'palette_provenance':palette_provenance,
   'source_function':b['function'],'source_district_id':b['district_id'],'assembly_class':s.get('assembly_class','protected_ordinary'),'construction_era':s.get('construction_era'),'roof_form':s.get('roof_form'),'style':s.get('style'),'floors':s['floors'],
   'actual_body_bounds_local_m':body,'actual_body_footprint_xz_m':bodypoly,'actual_sampled_bounds_local_m':c['asset']['bounds'],'all_cached_lod_outer_bounds_local_m':outer,'actual_outer_footprint_xz_m':outerpoly,
   'source_mass_bounds_size_m':[b['width_m'],b['height_m'],b['depth_m']],'height_delta_from_source_mass_m':dimensions(c['asset']['bounds'])[1]-b['height_m'],'source_proxy_entrance_xz_m':b['entrance_xz_m'],'actual_entrance_ids':[l['id'] for l in links],
   'foundation_support':support_rec,'horizontal_status':'exact_cached_outer_envelope_contained_by_source_mass_and_parcel','promotion_status':'resolved_cache_geometry_with_explicit_support_and_threshold_requirements; not_traversal_certified','interior_status':'closed_exterior_only'}
  placed.append(item);assets[c['key']]=copy.deepcopy(c['asset']);selection_counts[c['key']]+=1
 # Prove every selected master/render byte stream is the immutable cached input.
 manifest=[]
 for key,a in sorted(assets.items()):
  for typ in ('master','render'):
   path=ROOT/a[typ+'_path'];assert path.exists(),path;assert sha(path)==a[typ+'_sha256'],('Cache hash mismatch',path)
  manifest.append({'asset_key':key,'master_path':a['master_path'],'master_sha256':a['master_sha256'],'render_path':a['render_path'],'render_sha256':a['render_sha256'],'quad_count':a['quad_count'],'pitch_m':a.get('pitch_m',a['key'].get('pitch')),'instance_count':selection_counts[key]})
 summary={'eligible_source_masses':len(eligible),'resolved_placements':len(placed),'unresolved_source_masses':len(unresolved),'excluded_source_masses':len(excluded),'selected_unique_cached_assets':len(assets),'selected_unique_quads':sum(a['quad_count'] for a in assets.values()),'drawn_instance_quads':sum(assets[p['asset_key']]['quad_count'] for p in placed),'ordinary_r2_catalog_variants':len(catalog),'ordinary_r2_catalog_unique_coarse_quads':sum(c['asset']['quad_count'] for c in catalog),'protected_designs_resolved':sum(p['status'].startswith('resolved') for p in protected),'protected_designs_unresolved':sum(p['status'].startswith('unresolved') for p in protected),'actual_doors':len(access),'foundation_extension_required':sum(p['foundation_support']['foundation_extension_required'] for p in placed),'threshold_or_grade_review_required':sum(p['vertical_status'].startswith('requires') for p in access),'new_compile_count':0,'geometry_scaling_count':0,'geometry_class_counts':dict(Counter(p['assembly_class'] for p in placed)),'era_counts':dict(Counter(p['construction_era'] for p in placed)),'roof_form_counts':dict(Counter(p['roof_form'] for p in placed))}
 summary.update(threshold_step_run_exceeds_one_metre_reservation=sum(not p['proposed_step_run_fits_reserved_landing'] for p in access),
  proposed_ground_links_exceeding_twelve_percent=sum(p['maximum_sampled_ground_grade']>.12 for p in access),
  maximum_sampled_ground_grade=max(p['maximum_sampled_ground_grade'] for p in access),
  threshold_to_standing_rise_range_m=[min(p['threshold_to_standing_rise_m'] for p in access),max(p['threshold_to_standing_rise_m'] for p in access)],
  actual_door_offset_from_proxy_range_m=[min(p['actual_door_offset_from_proxy_m'] for p in access),max(p['actual_door_offset_from_proxy_m'] for p in access)],
  height_delta_from_source_mass_range_m=[min(p['height_delta_from_source_mass_m'] for p in placed),max(p['height_delta_from_source_mass_m'] for p in placed)])
 result={'schema':'riverstone.concept_city.ordinary_cached_placement_pack.v1','status':'resolved_horizontal_cache_placement_pack_with_explicit_vertical_requirements','source_plan_sha256':plan_sha,'source_cache_path':str(CACHE.relative_to(ROOT)),'source_cache_sha256':hashlib.sha256(cache_bytes).hexdigest(),'terrain_author_path':str(Path(terrain.__file__).relative_to(ROOT)),'terrain_author_sha256':sha(terrain.__file__),'terrain_source_plan_sha256':terrain.SOURCE_PLAN_SHA256,
  'scope':'Existing ordinary cached geometry only. No Godot scene, new compile, whole-house scaling, source-plan change, cache change or unverified open doorway. All new offset access lines are bounded proposals, not built surfaces.',
  'summary':summary,'assets':assets,'cache_manifest':manifest,'placements':placed,'access_proposals':access,'protected_design_resolution':protected,'unresolved':unresolved,'excluded_source_records':excluded,
  'terrain_height_schema':'position_m is XYZ; support_samples_xzy_m explicitly stores X,Z,H; all other *_xyz_m are X,Y,Z',
  'limitations':['Source body pads were based on proxy door positions. Actual offset thresholds need the exported short-step/support review.','5x5 exact-H support sampling is finite evidence, not an analytic full-footprint foundation certificate.','Protected large designs remain unresolved rather than resizing or merging approved parcels.','Closed cached door leaves retain exterior interaction only; no interiors or through-passage are claimed.']}
 assert sha(PLAN)==plan_sha and sha(CACHE)==result['source_cache_sha256'],'Read-only inputs changed during resolution'
 return result

def main():
 result=build();(HERE/'resolved_placements.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');(HERE/'summary.json').write_text(json.dumps(result['summary'],sort_keys=True,indent=2)+'\n');print(json.dumps(result['summary'],sort_keys=True))
if __name__=='__main__':main()
