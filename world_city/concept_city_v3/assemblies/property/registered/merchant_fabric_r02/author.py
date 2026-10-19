"""Bounded ordinary-town expansion selected by real native masks and source grade."""
import json,math,copy,hashlib,time
from collections import Counter
from pathlib import Path
from .grammar import *
from ..merchant_block011 import author as first
from ..merchant_block011.prepare_handoff import union,subtract
from world_city.concept_city_v3.registered_source.author import Domain
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import closest
from world_city.concept_city_v3.validation.check_landmark_access_candidate import transform as native_transform
from world_city.concept_city_v3.registered_topography.revisions.r13_precinct_interfaces import materials as terrain
BASE=HERE.parent/'merchant_block011';PRECINCT=CITY/'assemblies/landmarks/registered/precinct_r04'
BLOCKS=('BLOCK_000','BLOCK_002','BLOCK_003','BLOCK_004','BLOCK_005','BLOCK_006','BLOCK_008','BLOCK_010','BLOCK_011','BLOCK_014','BLOCK_015','BLOCK_016','BLOCK_017','BLOCK_018')
MAX_COMPOUNDS=30

def context():
 c=first.context();c['prior_pack']=json.loads((BASE/'resolved_placements.json').read_text());c['prior_handoff']=json.loads((BASE/'terrain_handoff.json').read_text());c['old_removed']=set(c['prior_pack']['replaced_placement_ids']);c['native_index']=g._SpatialIndex(24);c['native_cache']={};c['old_by_id']={p['id']:p for p in c['old']['placements']};c['access_by_owner']={};c['path_index']=g._SpatialIndex(24);c['path_polys']=[]
 c['city_domain']=Domain([c['plan']['boundary_xz_m']])
 collar=json.loads((HERE/'collar_reservation.json').read_text());c['hard'].add(rect(*collar['candidate_bounds_xz_m']),'r14_merchant_public_collar')
 for q in terrain.finite_water_polygons():
  if q.get('polygon_xz_m'):c['hard'].add(q['polygon_xz_m'],'current_finite_water')
 for p in c['prior_handoff']['properties']:
  c['hard'].add(p['platform_polygon_xz_m'],'sealed_merchant:'+p['property_id']);c['hard'].add(p['finite_gate_approach']['polygon_xz_m'],'sealed_merchant_gate:'+p['property_id'])
 for i,p in enumerate(c['old']['placements']):
  if p['id'] not in c['old_removed']:c['native_index'].add(i,p['actual_outer_footprint_xz_m'])
 for r in c['old']['access_proposals']:
  owner=r['source_mass_id'];c['access_by_owner'].setdefault(owner,[]).append(r)
  if owner in c['old_removed']:continue
  polys=r['reserved_connection_polygons_xz_m']+[prior.circles(q,r['width_m']) for q in r['complete_proposed_connection_xz_m'][1:-1]]
  for poly in polys:c['path_index'].add(len(c['path_polys']),poly);c['path_polys'].append(dict(owner_id=owner,route_id=r['id'],polygon_xz_m=poly))
 # Preserve the separately sealed poor-row candidate and both its exact dry
 # routes and lower-yard ownership. Never retire these IDs a second time.
 poorpath=HERE.parent/'poor_block015_east/route_repair_01/effective_placements.json';poor=json.loads(poorpath.read_text());poor_source=json.loads((ROOT/poor['candidate']['path']).read_text());c['hard'].add(poor_source['block']['polygon_xz_m'],'sealed_B015_east');c['old_removed'].update(poor['replaced_placement_ids'])
 for r in poor['access_proposals']:
  for poly in r['reserved_connection_polygons_xz_m']+r.get('reserved_round_join_polygons_xz_m',[]):c['hard'].add(poly,'sealed_B015_dry_route')
 for gr in poor['ground_ownership_records']:
  for poly in gr['polygons_xz_m']:c['hard'].add(poly,'sealed_B015_ground')
 c['extra_sources']=dict(collar_reservation=ref(HERE/'collar_reservation.json'),prior_merchant_pack=ref(BASE/'resolved_placements.json'),prior_merchant_handoff=ref(BASE/'terrain_handoff.json'),poor_east_pack=ref(poorpath),precinct_pack=ref(PRECINCT/'resolved_placements.json'),precinct_access=ref(PRECINCT/'access_r02/exterior_access_proposal.json'),precinct_belts=ref(PRECINCT/'boundary_belts/preflight.json'))
 precinct=json.loads((PRECINCT/'resolved_placements.json').read_text());access=json.loads((PRECINCT/'access_r02/exterior_access_proposal.json').read_text());belts=json.loads((PRECINCT/'boundary_belts/preflight.json').read_text())
 for q in precinct['owned_floors']+precinct['actual_bearing_footprints']:c['hard'].add(q['polygon_xz_m'],'native_precinct:'+q['id'])
 for r in access['routes']:
  for poly in r['ribbon_polygons_xz_m']+[prior.circles(q,r['width_m']) for q in r['polyline_xz_m'][1:-1]]:c['hard'].add(poly,'precinct_access:'+r['id'])
 for m in belts['native_modules']:c['hard'].add(m['native_footprint_xz_m'],'precinct_belt:'+m['id'])
 return c

def native_masks(p,ctx):
 key=p['asset_key']
 if key not in ctx['native_cache']:
  a=ctx['old']['assets'][key];assert ref(ROOT/a['render_path'])['sha256']==a['render_sha256'];r=json.loads((ROOT/a['render_path']).read_text());ctx['native_cache'][key]=dict(found=slab_rectangles(r,.49,.499),walk=slab_rectangles(r,.55,2.35),roof=roof_rects(r),source=ref(ROOT/a['render_path']))
 return {kind:[native_transform(q,p) for q in ctx['native_cache'][key][kind]] for kind in ('found','walk','roof')}

def triangle_grade(tri):
 (x0,y0,z0),(x1,y1,z1),(x2,y2,z2)=tri;det=(x1-x0)*(z2-z0)-(x2-x0)*(z1-z0)
 if abs(det)<1e-9:return 0
 a=((y1-y0)*(z2-z0)-(y2-y0)*(z1-z0))/det;b=((x1-x0)*(y2-y0)-(x2-x0)*(y1-y0))/det
 return math.hypot(a,b)

def gate_profile(frame,recipe,road):
 gate=recipe['gate_position_xz_m'];_,end,si,t=closest(gate,road['polyline_xz_m']);length=math.dist(gate,end)
 if length<1:return None,'gate_link_too_short'
 v=[(end[k]-gate[k])/length for k in (0,1)];cross=[-v[1],v[0]];ends=[[end[k]+s*1.75*cross[k] for k in (0,1)] for s in(-1,1)];floor=terrain.land_height_at(*end);local=recipe['gate_local_xz_m'];gates=[xform([local[0]+s*1.75,local[1]],frame['origin_xz_m'],frame['yaw_rad']) for s in(-1,1)]
 if math.dist(gates[0],ends[0])+math.dist(gates[1],ends[1])>math.dist(gates[0],ends[1])+math.dist(gates[1],ends[0]):ends.reverse()
 points=[];triangles=[]
 for j in range(9):
  u=j/8;a=[gates[0][k]*(1-u)+gates[1][k]*u for k in(0,1)];b=[ends[0][k]*(1-u)+ends[1][k]*u for k in(0,1)];points.append((a,b,terrain.land_height_at(*b)))
 for (a,b,y),(c,d,z) in zip(points,points[1:]):triangles.extend([[[a[0],floor,a[1]],[b[0],y,b[1]],[d[0],z,d[1]]],[[a[0],floor,a[1]],[d[0],z,d[1]],[c[0],floor,c[1]]]])
 grade=max(triangle_grade(q) for q in triangles)
 if grade>.12+1e-7:return None,'finished_gate_triangles_over_12pct'
 return dict(road_id=road['id'],segment_index=si,segment_t=t,polyline_xz_m=[gate,end],polygon_xz_m=[gates[0],gates[1],ends[1],ends[0]],width_m=3.5,finished_floor_y_m=floor,triangles_xyz_m=triangles,maximum_source_grade=grade,public_edge_profile=[dict(point_xz_m=b,y_m=y) for a,b,y in points],seam_status='Source finite linear seam; exact public collar ownership remains unapproved'),None

def screen(frame,ctx):
 f=FAMILIES[frame['family']];W,D=f['width'],f['depth'];poly=transform_polys([rect(-W/2,-D/2,W/2,D/2)],frame['origin_xz_m'],frame['yaw_rad'])[0]
 if not Domain([ctx['blocks'][frame['block_id']]['polygon_xz_m']]).contains(poly):return None,'outside_traced_block'
 if not ctx['city_domain'].contains(poly):return None,'outside_registered_city_boundary'
 if ctx['roads'].hits(poly):return None,'actual_public_strip_overlap'
 if ctx['hard'].hits(poly):return None,'protected_water_or_finite_owner'
 nearby=[ctx['old']['placements'][i] for i in ctx['native_index'].candidates(poly) if ctx['old']['placements'][i]['id'] not in ctx['old_removed']];retired=[p for p in nearby if any(estate.overlap(poly,q) for q in native_masks(p,ctx)['found'])];ids={p['id'] for p in retired}
 if not retired:return None,'no_existing_native_foundation'
 if any(ctx['plots'][p['source_plot_id']].get('block_id')!=frame['block_id'] for p in retired):return None,'retirement_crosses_block'
 if not any(ctx['plots'][p['source_plot_id']].get('road_id')==frame['road_id'] and math.cos(p['yaw_rad']-frame['yaw_rad'])>.75 for p in retired):return None,'not_true_existing_street_frontage'
 if frame['block_id'] in ('BLOCK_003','BLOCK_005','BLOCK_015') and any(p['source_district_id']=='D_POOR' for p in retired):return None,'retain_poor_quarter_character'
 for i in ctx['path_index'].candidates(poly):
  r=ctx['path_polys'][i]
  if r['owner_id'] not in ids and r['owner_id'] not in ctx['old_removed'] and estate.overlap(poly,r['polygon_xz_m']):return None,'retained_actual_native_door_route'
 # Floor is derived from the real road endpoint; old gate soil height is only
 # support/cut-fill evidence, never the finished ramp slope.
 gate=xform([W/2-2,D/2],frame['origin_xz_m'],frame['yaw_rad']);road=ctx['roadmap'][frame['road_id']];_,end,_,_=closest(gate,road['polyline_xz_m']);floor=terrain.land_height_at(*end);frame=dict(frame,floor_y_m=floor);recipe=build_recipe(frame);link,reason=gate_profile(frame,recipe,road)
 if reason:return None,reason
 if ctx['hard'].hits(link['polygon_xz_m']):return None,'gate_hits_protected_owner'
 sampled=[]
 for i in range(7):
  for j in range(7):
   q=xform([-W/2+i*W/6,-D/2+j*D/6],frame['origin_xz_m'],frame['yaw_rad']);y=terrain.land_height_at(*q);sampled.append(dict(point_xz_m=q,existing_y_m=y,cut_m=max(0,y-floor),fill_m=max(0,floor-y)))
 cut=max(q['cut_m'] for q in sampled);fill=max(q['fill_m'] for q in sampled)
 if cut>1.5+1e-7:return None,'cut_over_1.5m'
 if fill>2.5+1e-7:return None,'fill_over_2.5m'
 # Broader nearby roofs enter only as exact sampled roof projection polygons.
 checkpolys=[q for p in recipe['placements'] for q in p['native_roof_polygons_xz_m']]+[link['polygon_xz_m']];checkids=set()
 for q in checkpolys:checkids.update(ctx['native_index'].candidates(q))
 for i in checkids:
  p=ctx['old']['placements'][i]
  if p['id'] in ids or p['id'] in ctx['old_removed']:continue
  native=native_masks(p,ctx)
  if any(estate.overlap(a,b) for a in [q for p in recipe['placements'] for q in p['native_roof_polygons_xz_m']] for b in native['roof']):return None,'retained_actual_roof_overlap'
  if any(estate.overlap(link['polygon_xz_m'],q) for q in native['walk']):return None,'public_link_retained_native_solid'
 newbody=union([q for p in recipe['placements'] for q in p['native_foundation_polygons_xz_m']]);oldbody=union([q for p in retired for q in native_masks(p,ctx)['found']]);gain=sum(g.polygon_area(q) for q in newbody)-sum(g.polygon_area(q) for q in oldbody)
 if gain<50 or sum(g.polygon_area(q) for q in newbody)<sum(g.polygon_area(q) for q in oldbody)*1.10:return None,'insufficient_native_coverage_gain'
 frontage=20 if frame['family']=='deep_older_workyard' else 18 if frame['family'].startswith('compact') or frame['family']=='deep_workyard' else 22
 recipe.update(source_frame=frame,block_id=frame['block_id'],road_id=frame['road_id'],source_retired_native_ids=sorted(ids),source_plot_ids=sorted({p['source_plot_id'] for p in retired}),superseded_source_path_ids=[p['id'] for p in ctx['plan']['paths'] if p.get('owner_building_id') in ids],superseded_native_access_ids=[r['id'] for p in retired for r in ctx['access_by_owner'].get(p['id'],[])],external_gate_link=link,body_gain_m2=gain,native_foundation_area_m2=sum(g.polygon_area(q) for q in newbody),native_street_frontage_m=frontage,terrain_feasibility=dict(author=ref(Path(terrain.__file__)),finished_floor_y_m=floor,maximum_sampled_cut_m=cut,maximum_sampled_fill_m=fill,samples=sampled,status='Source eligibility only; finite support and public collar acceptance pending'),retired_native_geometry=[dict(id=p['id'],source_plot_id=p['source_plot_id'],**native_masks(p,ctx)) for p in retired]);return recipe,None

def frames(ctx):
 for bid in BLOCKS:
  block=ctx['blocks'][bid]
  for rid in block['boundary_road_ids']+([bid+':ALLEY'] if bid+':ALLEY' in ctx['roadmap'] else []):
   road=ctx['roadmap'][rid];line=road.get('frontage_control_polyline_xz_m',road['polyline_xz_m'])
   for si,(a,b) in enumerate(zip(line,line[1:])):
    length=math.dist(a,b)
    if length<26:continue
    tangent=[(b[k]-a[k])/length for k in (0,1)]
    for station in range(15,max(16,int(length-12)),4):
     for side in(-1,1):
      inward=[-tangent[1]*side,tangent[0]*side];yaw=math.atan2(-inward[0],-inward[1])
      older=('ALLEY' in rid or 'SOUTH_MERCHANT' in rid or (bid in ('BLOCK_003','BLOCK_018') and station%3==0))
      for family in('deep_older_workyard' if older else 'deep_workyard','wide_early_court','compact_old' if older else 'compact_rebuilt'):
       D=FAMILIES[family]['depth'];origin=[a[k]+station*tangent[k]+inward[k]*(road['width_m']/2+1+D/2) for k in(0,1)];identity=f'MF02_{bid[6:]}_{rid}_{si}_{station}_{side:+}_{family}'
       yield dict(id=identity,block_id=bid,road_id=rid,family=family,origin_xz_m=origin,yaw_rad=yaw)

def build():
 started=time.monotonic();ctx=context();candidates=[];rejects=Counter();rejections=[]
 for i,frame in enumerate(frames(ctx)):
  r,reason=screen(frame,ctx)
  if reason:rejects[reason]+=1;rejections.append(dict(id=frame['id'],block_id=frame['block_id'],reason=reason))
  else:candidates.append(r);print('viable',r['id'],round(r['body_gain_m2'],1),round(r['floor_y_m'],3),flush=True)
  if i%250==0:print('screened',i,'viable',len(candidates),'seconds',round(time.monotonic()-started,1),flush=True)
 selected=[];used=set();blocks=Counter();candidates.sort(key=lambda p:(-(p['body_gain_m2']/(p['width_m']*p['depth_m'])),-p['body_gain_m2'],p['id']))
 for r in candidates:
  if blocks[r['block_id']]>=8:continue
  if used.intersection(r['source_retired_native_ids']):continue
  if any(estate.overlap(r['polygon_xz_m'],p['polygon_xz_m']) or estate.overlap(r['external_gate_link']['polygon_xz_m'],p['polygon_xz_m']) or estate.overlap(p['external_gate_link']['polygon_xz_m'],r['polygon_xz_m']) for p in selected):continue
  selected.append(r);used.update(r['source_retired_native_ids']);blocks[r['block_id']]+=1
  if len(selected)>=MAX_COMPOUNDS:break
 result=dict(schema='riverstone.merchant_fabric_r02_eligibility.v1',status='source_only_eligibility_pending_whole_block_plan_review',sources=dict(plan=ref(PLAN),ordinary=ref(ORDINARY),history=ref(CITY/'city_history_v3.json'),terrain=ref(Path(terrain.__file__)),**ctx['extra_sources']),grammar=ref(HERE/'grammar.py'),author=ref(Path(__file__)),properties=selected,replacement_ledger=dict(replaced_placement_ids=sorted(used),superseded_source_path_ids=sorted({x for p in selected for x in p['superseded_source_path_ids']}),superseded_native_access_ids=sorted({x for p in selected for x in p['superseded_native_access_ids']})),summary=dict(properties=len(selected),blocks=dict(blocks),families=dict(Counter(p['family'] for p in selected)),retired_native_ids=len(used),native_modules=sum(len(p['placements']) for p in selected),actual_doors=sum(len(p['actual_doors']) for p in selected),owned_platform_area_m2=sum(p['width_m']*p['depth_m'] for p in selected),service_court_area_m2=sum(p['court']['area_m2'] for p in selected),native_body_gain_m2=sum(p['body_gain_m2'] for p in selected),continuous_native_street_front_m=sum(p['native_street_frontage_m'] for p in selected),screened=i+1,viable_before_overlap_selection=len(candidates),source_scan_seconds=time.monotonic()-started),rejection_counts=dict(rejects),rejections=rejections,eligible_unselected_frames=[dict(id=p['id'],block_id=p['block_id'],family=p['family'],body_gain_m2=p['body_gain_m2']) for p in candidates if p not in selected],limits=['No common compilation or scene placement.','Exact native masks drive ownership/roof tests; cache bounds are broadphase only.','Source terrain eligibility is sampled. Explicit finite support, gate collar and remaining-yard ownership follow this bounded plan.','All seven earlier compounds and sealed poor-row/institutional sources remain unchanged.']);write(HERE/'eligibility.json',result);print(json.dumps(result['summary'],indent=2),flush=True);return result
if __name__=='__main__':build()
