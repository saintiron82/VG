#!/usr/bin/env python3
"""Prepare finite landscape inputs without editing the frozen source or placing assets."""
import json,hashlib,math,copy
from pathlib import Path
from collections import defaultdict
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.source.ground_program import subtract
HERE=Path(__file__).parent
EXPECTED='b341bdf4547dffd3a8ca8e7c2e4ed5bae8520c36bcfa13e3bea925bd9e89f89a'
def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def bbox(poly):return [min(x for x,z in poly),min(z for x,z in poly),max(x for x,z in poly),max(z for x,z in poly)]
def merged_frame(pieces,kind):
 if kind not in ('monastery_garden','clergy_garden','productive_orchard'):return None
 bounds=[bbox(p) for p in pieces];x0=min(b[0] for b in bounds);z0=min(b[1] for b in bounds);x1=max(b[2] for b in bounds);z1=max(b[3] for b in bounds)
 index=g._SpatialIndex(48)
 for i,p in enumerate(pieces):index.add(i,p)
 sizes=[(w,d) for w in ([160,120,100,80,60,44,40,30,20] if kind=='productive_orchard' else [44,40]) for d in ([40,30,24,20] if kind=='productive_orchard' else [44,40])]
 for w,d in sorted(sizes,key=lambda v:-v[0]*v[1]):
  if w>x1-x0 or d>z1-z0:continue
  for z in range(math.ceil((z0+d/2)/2)*2,math.floor((z1-d/2)/2)*2+1,2):
   for x in range(math.ceil((x0+w/2)/2)*2,math.floor((x1-w/2)/2)*2+1,2):
    r=rect(x-w/2,z-d/2,x+w/2,z+d/2);near=[pieces[i] for i in index.candidates(r)]
    if g.uncovered_area_by_union(r,near,0)<1e-6:return {'origin_xz_m':[x,z],'width_m':w,'depth_m':d,'yaw_rad':0,'polygon_xz_m':r,'verified_union_uncovered_area_m2':0.}
 return None

def build():
 raw=(HERE/'plan.json').read_bytes();sha=hashlib.sha256(raw).hexdigest();assert sha==EXPECTED,('Frozen plan changed',sha)
 plan=json.loads(raw);wall=plan['boundary_xz_m'];exclusions=[];exidx=g._SpatialIndex(48)
 def exclude(identity,kind,poly,**extra):
  if len(poly)>2 and g.polygon_area(poly)>1e-7:exidx.add(len(exclusions),poly);exclusions.append({'id':identity,'kind':kind,'polygon_xz_m':poly,**extra})
 for b in plan['buildings']:exclude('BUILDING:'+b['id'],'full_building_envelope',b['footprint_xz_m'])
 for p in plan['plots']:exclude('PROPERTY:'+p['id'],'exclusive_private_property_floor',p['polygon_xz_m'])
 for road in plan['roads']:
  for i,(a,b) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   exclude('ROAD:'+road['id']+':'+str(i),'public_road_and_margin',g.road_ribbon(a,b,road['width_m']+2),source_width_m=road['width_m'],additional_margin_per_side_m=1.)
 for path in plan['paths']:
  for i,(a,b) in enumerate(zip(path['polyline_xz_m'],path['polyline_xz_m'][1:])):
   if math.dist(a,b)>1e-6:exclude('ACCESS:'+path['id']+':'+str(i),'individual_door_or_gate_path',g.road_ribbon(a,b,path['width_m']+.5),source_width_m=path['width_m'],additional_margin_per_side_m=.25)
 water=plan['water_reservations']
 for key,width in [('service_canal_polyline_xz_m',water['service_corridor_width_m']),('spring_feeder_polyline_xz_m',water['spring_feeder_reserve_width_m'])]:
  line=water[key]
  for i,(a,b) in enumerate(zip(line,line[1:])):exclude('WATER:'+key+':'+str(i),'reserved_water_corridor',g.road_ribbon(a,b,width),reservation_width_m=width)
 exclude('WATER:RESERVOIR','reservoir_outer_bank_reservation',water['reservoir_outer_polygon_xz_m']);exclude('WATER:RIVER','river_water_domain',water['river_polygon_xz_m'])
 # Ground ledger records are disjoint finite ownership pieces, not district envelopes.
 ground_index=g._SpatialIndex(48);ground_parts=[]
 for ground in plan['grounds']:
  for poly in ground['polygons_xz_m']:ground_index.add(len(ground_parts),poly);ground_parts.append((ground['id'],poly))
 kinds={'LAND_PUBLIC_COMMON':'public_park','LAND_MONASTERY_WEST':'monastery_garden','LAND_MONASTERY_SOUTH':'productive_orchard','LAND_CLERGY_CEMETERY':'cemetery_facility_pending','LAND_CLERGY_KITCHEN':'clergy_garden','LAND_NORTH_ORCHARD':'productive_orchard','LAND_FOREST_NW':'outside_woodland','LAND_FOREST_NE':'outside_woodland'}
 sites=[]
 for source in plan['landscape_patches']:
  sid=source['id'];kind=kinds[sid];ownership=defaultdict(list)
  for poly in source['polygons_xz_m']:
   if kind=='outside_woodland':pieces=subtract(poly,[wall]);owner_records=[(sid,q) for q in pieces]
   elif sid=='LAND_PUBLIC_COMMON':
    space=next(s for s in plan['spaces'] if s['id']=='S_COMMON');q=g.convex_intersection(poly,space['polygon_xz_m']);owner_records=[('S_COMMON',q)] if len(q)>2 and g.polygon_area(q)>1e-7 else []
   else:
    owner_records=[]
    for i in ground_index.candidates(poly):
     gid,ground=ground_parts[i];q=g.convex_intersection(poly,ground)
     if len(q)>2 and g.polygon_area(q)>1e-7:owner_records.append((gid,q))
   for owner,q in owner_records:
    obs=[exclusions[i]['polygon_xz_m'] for i in exidx.candidates(q)]
    ownership[owner].extend(subtract(q,obs))
  pieces=[q for qs in ownership.values() for q in qs];amount=sum(g.polygon_area(q) for q in pieces)
  rec={'id':sid,'source_landscape_patch_id':sid,'source_ground_ids':sorted(ownership),'landscape_kind':kind,'polygons_xz_m':pieces,'area_m2':amount,'source_reserved_area_m2':source['area_m2'],'excluded_or_unowned_area_m2':source['area_m2']-amount,
   'owned_ground_regions':[{'source_ground_id':gid,'polygons_xz_m':qs,'area_m2':sum(g.polygon_area(q) for q in qs)} for gid,qs in sorted(ownership.items())],
   'purpose':source['purpose'],'approval_status':'proposed_input_pending_root_blockout_approval','scene_placement_authorized':False,
   'floor_ownership':'existing ground owner only; do not add a floor plane','height_resolution_required':True,'terrain_support_contract':'Evaluate current terrain H on each 2x2m root/base footprint; project Y only. Report support delta over0.75m; do not scale or lift canopy arbitrarily.',
   'observed_vs_inferred':'Social function and broad placement follow approved concept; finite polygons and planting programs are authored source design, not pixel measurements.'}
  if kind=='outside_woodland':
   rec.update(planting_pattern='irregular clustered woodland with varied crown forms and winding clearings',productive_ground=False,maximum_trees=400,seed=101 if sid.endswith('NW') else 202,wall_canopy_standoff_m=12,ownership_note='Existing outside LAND_FOREST patch is the ground owner; interior GROUND ledger does not extend beyond the wall.')
  elif kind=='productive_orchard':rec.update(planting_pattern='intentional productive fruit-tree rows',productive_ground=True,row_spacing_m=10,seed=303)
  elif kind=='public_park':rec.update(planting_pattern='sparse shade groups around open common; no forest density',maximum_trees=5,seed=404,park_walks=[],access_policy='Existing reserved common-edge routes stay excluded. Any additional garden path must receive a separate verified external entry link.')
  elif kind=='monastery_garden':rec.update(planting_pattern='productive kitchen/herb beds and a few orchard trees',seed=505)
  elif kind=='clergy_garden':rec.update(planting_pattern='formal quiet garden beds and shade; separate from cemetery',seed=606)
  else:rec.update(planting_pattern='bounded burial rows with burial access, no automatic garden-bed substitution',required_facility_recipe='cemetery_rows_and_memorials',api_status='unsupported_by_landscape_tree_api; separate burial facility design required')
  frame=merged_frame(pieces,kind)
  if frame:
   rec.update({k:frame[k] for k in ['origin_xz_m','width_m','depth_m','yaw_rad']});rec['coherent_recipe_frame']=frame
   # Remove computational ownership seams only inside a proven covered frame.
   # This is exactly the same union, not an expanded bounding rectangle.
   rec['polygons_xz_m']=[frame['polygon_xz_m']]+[q for p in pieces for q in subtract(p,[frame['polygon_xz_m']])]
   rec['recipe_frame_status']='coherent_frame_proven_inside_owned_union'
  elif kind in ('monastery_garden','clergy_garden','productive_orchard'):rec['recipe_frame_status']='unresolved_no_coherent_frame; do_not_force_fit'
  else:rec['recipe_frame_status']='not_required'
  ids=set()
  for poly in rec['polygons_xz_m']:ids.update(exidx.candidates(poly))
  # Include wall stand-off as actual finite exclusions for woodland inputs.
  if kind=='outside_woodland':
   for i,(a,b) in enumerate(zip(wall,wall[1:]+wall[:1])):
    exclude('WOODLAND_WALL_EDGE:'+str(i),'outside_canopy_wall_standoff',g.road_ribbon(a,b,24))
    exclude('WOODLAND_WALL_CORNER:'+str(i),'outside_canopy_corner_standoff',rect(a[0]-12,a[1]-12,a[0]+12,a[1]+12))
   for poly in rec['polygons_xz_m']:ids.update(exidx.candidates(poly))
  rec['exclusion_ids']=sorted({exclusions[i]['id'] for i in ids})
  # No hard collider may overlap any offered owned land. Wall standoff is a
  # canopy rule applied at recipe time, so it is excluded from this ground test.
  conflicts=[]
  for poly in rec['polygons_xz_m']:
   for i in exidx.candidates(poly):
    e=exclusions[i]
    if e['kind'].startswith('outside_canopy'):continue
    if g.positive_area_overlap(poly,e['polygon_xz_m'],1e-6):conflicts.append(e['id'])
  rec['source_checks']={'hard_exclusion_conflicts':sorted(set(conflicts)),'offered_union_area_m2':sum(g.polygon_area(p) for p in rec['polygons_xz_m']),'owned_area_m2':amount,'area_error_m2':sum(g.polygon_area(p) for p in rec['polygons_xz_m'])-amount,'actual_scene_placement_count':0}
  assert not conflicts,(sid,conflicts);assert abs(rec['source_checks']['area_error_m2'])<1e-5,sid
  sites.append(rec)
 # Duplicate stand-off IDs from the second woodland site represent identical
 # geometry. Keep one catalog entry for each stable exclusion identity.
 unique={e['id']:e for e in exclusions}
 return {'schema':'riverstone.concept_city.proposed_landscape_sites.v1','status':'proposed_recipe_inputs_pending_root_3d_blockout_approval','frozen_source_plan_sha256':sha,'frozen_plan_unchanged':True,'wall_polygon_xz_m':wall,
  'api':'concept_city_v3.assemblies.landscape.recipes.build_landscape_recipe(site, wall_polygon_xz_m, exclusions)',
  'instructions':'For an approved site, pass only exclusion_catalog records matching exclusion_ids. Resolve terrain support before scene placement. Cemetery requires a separate facility recipe. No floor planes or actual city assets are created by this proposal.',
  'sites':sites,'exclusion_catalog':list(unique.values()),'totals':{'site_count':len(sites),'owned_area_m2':sum(s['area_m2'] for s in sites),'interior_area_m2':sum(s['area_m2'] for s in sites if s['landscape_kind']!='outside_woodland'),'outside_woodland_area_m2':sum(s['area_m2'] for s in sites if s['landscape_kind']=='outside_woodland'),'actual_scene_placement_count':0}}

def main():
 data=build();out=HERE/'proposed_landscape_sites.json';out.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
 print(json.dumps(data['totals']));print(json.dumps([{k:s.get(k) for k in ('id','landscape_kind','area_m2','recipe_frame_status','width_m','depth_m')} for s in data['sites']]))
 assert hashlib.sha256((HERE/'plan.json').read_bytes()).hexdigest()==EXPECTED
if __name__=='__main__':main()
