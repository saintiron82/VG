"""Bounded central-merchant source batch from shared native court grammar. No compilation."""
import copy,json,math
from collections import Counter
from pathlib import Path
from .grammar import *
from world_city.concept_city_v3.registered_source.author import Domain
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import closest
from world_city.concept_city_v3.assemblies.property.registered.poor_block015_east.author_density import disjoint
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access import review as terrain
ACCESS=CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json'
LANDMARKS=CITY/'assemblies/landmarks/registered/assembly_r01/resolved_placements.json'
LANDSCAPE=CITY/'assemblies/landscape/registered/resolved_placements.json'
BLOCKS=('BLOCK_008','BLOCK_010','BLOCK_011','BLOCK_012','BLOCK_014','BLOCK_016','BLOCK_017','BLOCK_018')

def context():
 plan=json.loads(PLAN.read_text());old=json.loads(ORDINARY.read_text());landmarks=json.loads(LANDMARKS.read_text());landscape=json.loads(LANDSCAPE.read_text());access=json.loads(ACCESS.read_text());hard=Domain();roads=Domain();rd={r['id']:r for r in plan['roads']}
 for w in plan['water_reservations']['finite_water_polygons']:hard.add(w['polygon_xz_m'],'water:'+w['surface_id'])
 for p in landmarks['placements']:hard.add(p['outer_footprint_xz_m'],'native_landmark:'+p['id'])
 for p in landscape['sites']:hard.add(p['polygon_xz_m'],'owned_garden:'+p['id'])
 for s in plan['spaces']:
  for poly in s.get('polygons_xz_m',[s.get('polygon_xz_m')]):
   if poly:hard.add(poly,s['id'])
 # Recovered actual profiles plus a declared conservative 0.9 m margin, because
 # original round-join route records were lost. This can reject extra sites.
 for kind in ('approaches','landings'):
  for i,r in enumerate(access[kind]['masks']):
   for tri in estate.triangulate(r['polygon_xz_m']):
    hard.add(tri,f'recovered_landmark_{kind}:{i}');x0=min(q[0] for q in tri)-.9;z0=min(q[1] for q in tri)-.9;x1=max(q[0] for q in tri)+.9;z1=max(q[1] for q in tri)+.9;hard.add(rect(x0,z0,x1,z1),f'conservative_missing_join_clearance:{kind}:{i}')
 for r in plan['roads']:
  for i,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):roads.add(g.road_ribbon(a,b,r['width_m']),r['id']+':'+str(i))
 return dict(plan=plan,old=old,hard=hard,roads=roads,roadmap=rd,blocks={b['id']:b for b in plan['blocks']},plots={p['id']:p for p in plan['plots']})

def screen(frame,ctx,selected):
 poly=worldpoly(rect(-18,-21,18,21),frame);region=Domain([ctx['blocks'][frame['block_id']]['polygon_xz_m']])
 if not region.contains(poly):return None,'outside_traced_block'
 if ctx['roads'].hits(poly):return None,'actual_public_strip_overlap'
 if ctx['hard'].hits(poly):return None,'water_precinct_or_reserved_access_overlap'
 if any(g.positive_area_overlap(poly,p['polygon_xz_m'],1e-7) for p in selected):return None,'selected_platform_overlap'
 retired=[p for p in ctx['old']['placements'] if estate.overlap(poly,p['actual_outer_footprint_xz_m'])];retiredids={p['id'] for p in retired}
 if not retired:return None,'no_existing_source_frontage'
 # Consolidate only the current block's source parcels, retaining every old ID.
 if any(ctx['plots'][p['source_plot_id']].get('block_id')!=frame['block_id'] for p in retired):return None,'retirement_crosses_block_boundary'
 for r in ctx['plan']['paths']:
  if r.get('owner_building_id') in retiredids:continue
  if any(g.positive_area_overlap(poly,g.road_ribbon(a,b,r.get('width_m',1.8)),1e-7) for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):return None,'retained_source_access_overlap'
 road=ctx['roadmap'][frame['road_id']];gate=xform([16,21],frame['origin_xz_m'],frame['yaw_rad']);_,end,si,tt=closest(gate,road['polyline_xz_m']);floor=terrain.land_height_at(*end);frame=dict(frame,floor_y_m=floor)
 gate_anchors=[xform([16+v,21],frame['origin_xz_m'],frame['yaw_rad']) for v in(-1.75,0,1.75)];approach=g.road_ribbon(gate,end,3.5)
 if ctx['hard'].hits(approach):return None,'external_gate_reservation_overlap'
 samples=[]
 for x in range(-18,19,6):
  for z in range(-21,22,6):
   q=xform([x,z],frame['origin_xz_m'],frame['yaw_rad']);y=terrain.land_height_at(*q);samples.append(dict(point_xz_m=q,existing_y_m=y,cut_m=max(0,y-floor),fill_m=max(0,floor-y)))
 gateys=[terrain.land_height_at(*q) for q in gate_anchors];maxcut=max(s['cut_m'] for s in samples);maxfill=max(s['fill_m'] for s in samples)
 if maxcut>.75+1e-6:return None,'cut_over_0.75m'
 if maxfill>3+1e-6:return None,'fill_over_3m'
 if max(gateys)-min(gateys)>.15+1e-6:return None,'full_width_gate_crossfall_over_0.15m'
 if max(abs(y-floor) for y in gateys)/max(math.dist(gate,end),1e-5)>.12:return None,'gate_approach_grade_over_12pct'
 recipe=build_recipe(frame)
 newbody=sum(g.polygon_area(q) for q in disjoint([p['actual_body_footprint_xz_m'] for p in recipe['placements']]));oldbody=sum(g.polygon_area(p['actual_body_footprint_xz_m']) for p in retired)
 if newbody<oldbody*1.10 or newbody-oldbody<70:return None,'insufficient_whole_block_body_gain'
 recipe['body_gain_m2']=newbody-oldbody;recipe.update(block_id=frame['block_id'],road_id=frame['road_id'],source_frame=frame,source_retired_native_ids=sorted(retiredids),source_plot_ids=sorted({p['source_plot_id'] for p in retired}),superseded_source_path_ids=[r['id'] for r in ctx['plan']['paths'] if r.get('owner_building_id') in retiredids],external_gate_link=dict(polyline_xz_m=[gate,end],ribbon_polygon_xz_m=approach,width_m=3.5,road_id=road['id'],segment_index=si,segment_t=tt,gate_floor_y_m=floor,public_floor_y_m=floor),terrain_feasibility=dict(author=ref(Path(terrain.__file__)),floor_y_m=floor,maximum_sampled_cut_m=maxcut,maximum_sampled_fill_m=maxfill,gate_full_width_anchors_xz_m=gate_anchors,gate_anchor_heights_m=gateys,samples=samples,status='finite gate and cut/fill screening; exact retaining/floor assembly ownership pending'),status='source_only_native_recipe_pending_platform_and_independent_access_review')
 issues=[]
 for r in recipe['internal_routes']:
  for q in r['ribbon_polygons_xz_m']+r['round_join_polygons_xz_m']:
   if not estate.contained(q,poly):issues.append('full_width_outside_frame')
   if any(estate.overlap(q,p['actual_outer_footprint_xz_m']) for p in recipe['placements']):issues.append('native_roof_access_overlap')
 for a in recipe['placements']:
  if not estate.contained(a['actual_outer_footprint_xz_m'],poly):issues.append('native_envelope_outside_frame')
 if issues:return None,','.join(sorted(set(issues)))
 return recipe,None

def frames(ctx):
 # The two previously reviewed source frames are replayed first.
 yield dict(id='M11_PALAZZO',block_id='BLOCK_011',variant='palazzo_service',origin_xz_m=[-.8079641749322661,34.31099317962711],yaw_rad=1.9316573104720398,road_id='MARKET_WEST_EDGE')
 yield dict(id='M11_SHOP_COURT',block_id='BLOCK_011',variant='attached_shop_court',origin_xz_m=[12.96215171037381,70.79912698371801],yaw_rad=1.9316573104720398,road_id='MARKET_WEST_EDGE')
 for bid in BLOCKS:
  block=ctx['blocks'][bid]
  for rid in block['boundary_road_ids']+([bid+':ALLEY'] if bid+':ALLEY' in ctx['roadmap'] else []):
   road=ctx['roadmap'][rid];line=road.get('frontage_control_polyline_xz_m',road['polyline_xz_m'])
   for si,(a,b) in enumerate(zip(line,line[1:])):
    length=math.dist(a,b)
    if length<42:continue
    t=[(b[k]-a[k])/length for k in (0,1)]
    for station in range(23,max(24,math.floor(length-18)),12):
     for side in (-1,1):
      inward=[-t[1]*side,t[0]*side];out=[-v for v in inward];yaw=math.atan2(out[0],out[1]);origin=[a[k]+station*t[k]+inward[k]*(road['width_m']/2+1+21) for k in(0,1)];ident=f'M_BATCH_{bid[6:]}_{rid}_{si}_{station}_{side:+}'
      yield dict(id=ident,block_id=bid,variant='attached_shop_wing_court',origin_xz_m=origin,yaw_rad=yaw,road_id=rid)

def build():
 ctx=context();selected=[];rejections=Counter();reject_records=[]
 for frame in frames(ctx):
  recipe,reason=screen(frame,ctx,selected)
  if reason:rejections[reason]+=1;reject_records.append(dict(id=frame['id'],block_id=frame['block_id'],reason=reason));continue
  selected.append(recipe);print('accepted',recipe['id'],recipe['floor_y_m'],recipe['terrain_feasibility']['maximum_sampled_fill_m'],flush=True)
  if len(selected)>=24:break
 retiredids=sorted({i for p in selected for i in p['source_retired_native_ids']});replaced=[p for p in ctx['old']['placements'] if p['id'] in retiredids];assets={};placements=[];routes=[];doors=[];courts=[];residuals=[]
 for p in selected:assets.update(p['assets']);placements+=p['placements'];routes+=p['internal_routes'];doors+=p['actual_doors'];courts.append(p['court'])
 for old in replaced:
  pieces=[old['actual_outer_footprint_xz_m']]
  for p in selected:pieces=[q for poly in pieces for q in g.convex_difference(poly,p['polygon_xz_m']) if g.polygon_area(q)>1e-7]
  if pieces:residuals.append(dict(retired_placement_id=old['id'],source_plot_id=old['source_plot_id'],polygons_xz_m=pieces,area_m2=sum(g.polygon_area(q) for q in pieces),role='lower-grade productive private yard, inspection and service ground',floor_policy='Keep existing terrain outside platform; no automatic lift.',access_status='Residual private-yard paths require separate finite proof; not counted as resolved court access.'))
 metrics=[]
 for bid in BLOCKS:
  block=ctx['blocks'][bid];before=[p for p in ctx['old']['placements'] if ctx['plots'][p['source_plot_id']].get('block_id')==bid];after=[p for p in before if p['id'] not in retiredids]+[q for p in selected if p['block_id']==bid for q in p['placements']];courtarea=sum(p['court']['area_m2'] for p in selected if p['block_id']==bid)
  metrics.append(dict(block_id=bid,block_area_m2=block['area_m2'],before_native_modules=len(before),after_native_modules=len(after),new_compounds=sum(p['block_id']==bid for p in selected),before_body_area_m2=sum(g.polygon_area(p['actual_body_footprint_xz_m']) for p in before),after_body_area_m2=sum(g.polygon_area(q) for q in disjoint([p['actual_body_footprint_xz_m'] for p in after])),before_outer_union_area_m2=sum(g.polygon_area(q) for q in disjoint([p['actual_outer_footprint_xz_m'] for p in before])),after_outer_union_area_m2=sum(g.polygon_area(q) for q in disjoint([p['actual_outer_footprint_xz_m'] for p in after])),new_explicit_service_court_area_m2=courtarea,new_platform_area_m2=1512*sum(p['block_id']==bid for p in selected)))
 out=dict(schema='riverstone.central_merchant_native_batch_proposal.v1',status='source_only_bounded_batch_pending_floor_and_retaining_review',sources=dict(plan=ref(PLAN),ordinary=ref(ORDINARY),cache=ref(CACHE),property=ref(PROPERTY),landmarks=ref(LANDMARKS),landscape=ref(LANDSCAPE),recovered_native_access=ref(ACCESS),terrain_author=ref(Path(terrain.__file__))),grammar=ref(HERE/'grammar.py'),properties=selected,assets=assets,placements=placements,actual_doors=doors,internal_routes=routes,courts=courts,replacement_ledger=dict(replaced_placement_ids=retiredids,superseded_source_path_ids=sorted({i for p in selected for i in p['superseded_source_path_ids']}),retired_source_residuals=residuals),whole_block_metrics=metrics,rejection_counts=dict(rejections),rejections=reject_records,compile_budget=dict(new_building_union_families=3,existing_building_families=5,new_unique_per_plot_building_assets=0,platform_and_retaining_sources='pending exact finite terrain ownership; do not compile generic raised boxes',maximum_compounds=24),limits=['No city scene placement or compilation.','Raw overlapping source module meshes require common union before runtime.','Recovered landmark domains include conservative 0.9m missing-join clearance. Rear chapel remains unresolved.','Retired native residual ground is retained at existing grade, with unresolved private-yard paths explicit.'])
 write(HERE/'proposal.json',out);print(json.dumps(dict(properties=len(selected),native_modules=len(placements),actual_doors=len(doors),retired=len(retiredids),residual_area_m2=sum(r['area_m2'] for r in residuals),rejections=dict(rejections)),indent=2));return out
if __name__=='__main__':build()
