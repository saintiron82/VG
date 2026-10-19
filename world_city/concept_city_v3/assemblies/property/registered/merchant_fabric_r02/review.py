"""Native full-width route, finite owner, source-frontage and threshold regression."""
import json,math
from pathlib import Path
from .grammar import HERE,ROOT,CITY,ref,write,g,estate,rect,slab_rectangles,roof_rects
from world_city.concept_city_v3.validation.check_landmark_access_candidate import transform
from .final_selection import additional_owners
from .author import context,native_masks,triangle_grade
from world_city.concept_city_v3.registered_source.author import Domain
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import closest

def run():
 source=json.loads((HERE/'effective_eligibility.json').read_text());pack=json.loads((HERE/'resolved_placements.json').read_text());ctx=context();assert pack['eligibility']==ref(HERE/'effective_eligibility.json');assert pack['sources']==source['sources'];issues=[];native=Domain([q['polygon_xz_m'] for q in pack['native_walking_slabs']]);retired=set(pack['replaced_placement_ids'])|ctx['old_removed'];counts=dict(routes=0,ribbons=0,round_joins=0,actual_thresholds=len(pack['actual_doors']),foundation_regions=0,external_links=0,service_courts=0)
 b013_path=CITY/'assemblies/ordinary/registered/r1/resolved_placements.json';b013=json.loads(b013_path.read_text())
 for p in b013['placements']:
  a=b013['assets'][p['asset_key']];assert ref(ROOT/a['render_path'])['sha256']==a['render_sha256'];r=json.loads((ROOT/a['render_path']).read_text())
  for q in slab_rectangles(r,.49,.499)+roof_rects(r):ctx['hard'].add(transform(q,p),'sealed_B013_actual_native')
 for r in b013['access_proposals']:
  for q in r.get('reserved_connection_polygons_xz_m',[])+r.get('reserved_round_join_polygons_xz_m',[]):ctx['hard'].add(q,'sealed_B013_native_access')
 extra,extra_sources=additional_owners()
 for poly,identity in zip(extra.polys,extra.ids):ctx['hard'].add(poly,identity)
 def check(poly,identity,kind,check_native=True):
  if check_native and any(native.hits(q) for q in estate.triangulate(poly)):issues.append(dict(kind=kind+'_new_native_walking_slab',id=identity))
  if any(ctx['hard'].hits(q) for q in estate.triangulate(poly)):issues.append(dict(kind=kind+'_protected_owner_or_water',id=identity))
  for i in ctx['native_index'].candidates(poly):
   p=ctx['old']['placements'][i]
   if p['id'] in retired:continue
   for q in native_masks(p,ctx)['walk' if check_native else 'found']:
    if estate.overlap(poly,q):issues.append(dict(kind=kind+'_retained_native_solid',id=identity,other_id=p['id']))
 props={p['id']:p for p in source['properties']}
 for r in pack['access_proposals']:
  counts['routes']+=1;prop=props[r['property_id']]
  assert math.dist(r['polyline_xz_m'][-1],prop['gate_position_xz_m'])<1e-7;assert r['finished_floor_y_m']==prop['floor_y_m']
  for field,counter in [('ribbon_polygons_xz_m','ribbons'),('round_join_polygons_xz_m','round_joins')]:
   for q in r[field]:check(q,r['id'],counter);counts[counter]+=1;assert estate.contained(q,prop['polygon_xz_m'])
 for link in pack['external_gate_links']:
  counts['external_links']+=1;check(link['polygon_xz_m'],link['id'],'external_gate');assert closest(link['polyline_xz_m'][-1],ctx['roadmap'][link['road_id']]['polyline_xz_m'])[0]<1e-7
  assert max(triangle_grade(t) for t in link['triangles_xyz_m'])<=.12+1e-7
 for court in pack['courts']:counts['service_courts']+=1;check(court['polygon_xz_m'],court['id'],'service_court')
 for mask in pack['ownership_masks']:
  for q in mask['terrain_exclusion_regions_xz_m']:
   counts['foundation_regions']+=1;check(q,mask['owner_id'],'foundation',False)
   if ctx['roads'].hits(q):issues.append(dict(kind='foundation_public_lane',id=mask['owner_id']))
 for pid,prop in props.items():
  if ctx['roads'].hits(prop['polygon_xz_m']) or ctx['hard'].hits(prop['polygon_xz_m']):issues.append(dict(kind='platform_reserved_owner',id=pid))
  assert prop['terrain_feasibility']['maximum_sampled_cut_m']<=1.5+1e-7;assert prop['terrain_feasibility']['maximum_sampled_fill_m']<=2.5+1e-7
 for d in pack['actual_doors']:
  p=next(q for q in pack['placements'] if q['id']==d['actual_runtime_group_id']);assert abs(d['actual_door_xyz_m'][1]-p['pad_floor_y_m'])<1e-8;assert d['actual_union_threshold_evidence'];assert next(r for r in pack['access_proposals'] if r['actual_door_id']==d['id'])['polyline_xz_m'][0]==d['threshold_lip_xz_m']
 assert len(pack['replaced_placement_ids'])==len(set(pack['replaced_placement_ids']));assert not set(pack['replaced_placement_ids'])&set(ctx['prior_pack']['replaced_placement_ids'])
 result=dict(schema='riverstone.merchant_fabric_r02_native_review.v1',pack=ref(HERE/'resolved_placements.json'),additional_B013_reservation=ref(b013_path),reviewer=ref(Path(__file__)),status='pass_native_full_width_static_clearance' if not issues else 'failed',counts=counts,issues=issues,limits=['External finite triangles have source grades; public-side continuity collars and finished support remain unaccepted.','Closed native leaf anchors do not certify interior openings or capsule/horse-controller traversal.','All whole-group broadphase bounds are excluded from final intersection decisions.']);write(HERE/'native_review.json',result);print(json.dumps(result,indent=2));return result
if __name__=='__main__':raise SystemExit(bool(run()['issues']))
