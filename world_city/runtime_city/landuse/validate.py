#!/usr/bin/env python3
"""Measured-source validation of the new land-use overlay, without compilation."""
import json,math,sys,hashlib
from collections import Counter,defaultdict,deque
from pathlib import Path
from author import ROOT,HERE,FILES,load,g,area,clean,Constraints,PATH_ALLOW,terrain
from world_city.runtime_city.checks import revision2 as r2

def validate(data,source,context):
 failures=[];counts=Counter();scene=source['scene'];fabric=source['fabric'];block=data['first_infill_block'];field=terrain.field_from_brief(source['brief'])
 def check(name,ok,detail=None):
  counts[name]+=1
  if not ok:failures.append({'check':name,'detail':detail})
 def actual(catalog,key):
  bounds=[]
  for _,res in r2._resources(catalog[key]):
   raw=(ROOT/res['render_path']).read_bytes();mesh=json.loads(raw)
   check('compiled_resource_hash',hashlib.sha256(raw).hexdigest()==res['render_sha256'],res['render_path'])
   bounds.append(r2.mesh_vertex_bounds(mesh))
  check('compiled_resource_exists',bool(bounds),key)
  return r2.union_bounds(bounds)
 original={b['id'] for b in scene['instances']};new=block['building_instances'];ids=[b['id'] for b in new]
 check('new_unique_ids',len(set(ids))==len(ids));check('source_id_preservation',not original.intersection(ids))
 assets={k:actual(scene['assets'],k) for k in block['source_assets_reused']}
 envelopes={}
 for b in new:
  key=b['asset_key'];poly=g.transformed_aabb_xz_m(assets[key],b['position_m'],b['yaw_rad']);envelopes[b['id']]=poly
  check('unit_scale_buildings',b['transform_scale']==[1,1,1],b['id'])
  check('actual_envelope_matches_placement',abs(area(poly)-g.intersection_area(poly,b['source_footprint_xz_m']))<1e-5 and abs(area(poly)-area(b['source_footprint_xz_m']))<1e-5,b['id'])
  check('building_source_clear',not context.hits(poly),{'id':b['id'],'hits':[r['id'] for r in context.hits(poly)]})
  check('actual_floor_count_varies',scene['asset_specs'][key].get('floors') in (1,2,3),b['id'])
  heights=[terrain._eval(f['plane'],*v) for f in field.facets(poly) for v in f['polygon_xz_m']]
  f=b['foundation_requirement'];check('exact_H_foundation_range',abs(min(heights)-f['terrain_min_y_m'])<1e-8 and abs(max(heights)-f['terrain_max_y_m'])<1e-8,b['id'])
  local=b['all_entrances_local_m'];c,s=math.cos(b['yaw_rad']),math.sin(b['yaw_rad']);x,y,z=b['position_m']
  projected=[[x+c*a+s*zz,y+yy,z-s*a+c*zz] for a,yy,zz in local]
  check('actual_entrance_transform',all(math.dist(a,b)<1e-7 for a,b in zip(projected,b['all_entrances_world_m'])),b['id'])
  links=[p for p in block['paths'] if p.get('owner_building_id')==b['id']]
  check('every_actual_door_has_link',len(links)==len(local),b['id'])
 for i,a in enumerate(new):
  for b in new[:i]:check('no_new_building_overlap',not g.positive_area_overlap(envelopes[a['id']],envelopes[b['id']],1e-6),[a['id'],b['id']])
 # A path graph joins centre lines at crossings/endpoints; widths are separately
 # tested against solids. This is exterior access connectivity, not a navmesh.
 paths=block['paths'];adj=defaultdict(set)
 def crosses(p,q):
  for a,b in zip(p['polyline_xz_m'],p['polyline_xz_m'][1:]):
   for c,d in zip(q['polyline_xz_m'],q['polyline_xz_m'][1:]):
    if min(g.point_segment_distance(a,c,d),g.point_segment_distance(b,c,d),g.point_segment_distance(c,a,b),g.point_segment_distance(d,a,b))<1e-6:return True
    if g.positive_area_overlap(g.road_ribbon(a,b,.0001),g.road_ribbon(c,d,.0001)):return True
  return False
 for i,p in enumerate(paths):
  check('path_width',1.8<=p['width_m']<=3.,p['id'])
  for poly in p['ribbon_polygons_xz_m']:
   check('path_source_clear',not context.hits(poly,PATH_ALLOW),{'id':p['id'],'hits':[r['id'] for r in context.hits(poly,PATH_ALLOW)]})
   for bid,ob in envelopes.items():
    if bid!=p.get('owner_building_id'):check('path_other_building_clear',not g.positive_area_overlap(poly,ob,1e-6),[p['id'],bid])
  for j,q in enumerate(paths[:i]):
   if crosses(p,q):adj[i].add(j);adj[j].add(i)
 seeds=[i for i,p in enumerate(paths) if p['connected_public_road_id']];check('two_public_connections',len(seeds)>=2)
 seen=set(seeds);todo=deque(seeds)
 while todo:
  i=todo.popleft()
  for j in adj[i]-seen:seen.add(j);todo.append(j)
 check('all_block_paths_connected_to_public_roads',len(seen)==len(paths),[p['id'] for i,p in enumerate(paths) if i not in seen])
 facilities=block['facility_placements']+data['market_program']['facility_placements'];fassets={key:actual(fabric['assets'],key) for key in {p['asset_key'] for p in facilities}}
 fpolys=[]
 for f in facilities:
  poly=g.transformed_aabb_xz_m(fassets[f['asset_key']],f['position_m'],f['yaw_rad']);fpolys.append((f['id'],poly))
  check('unit_scale_facility',f['transform_scale']==[1,1,1],f['id'])
  allow={'market_square'} if f['id'].startswith('LU_R3_MARKET') else set()
  check('facility_actual_source_clear',not context.hits(poly,allow),{'id':f['id'],'hits':[r['id'] for r in context.hits(poly,allow)]})
  for bid,ob in envelopes.items():check('facility_new_building_clear',not g.positive_area_overlap(poly,ob,1e-6),[f['id'],bid])
  for path in paths:
   for ribbon in path['ribbon_polygons_xz_m']:check('facility_path_clear',not g.positive_area_overlap(poly,ribbon,1e-6),[f['id'],path['id']])
 for i,(fid,p) in enumerate(fpolys):
  for qid,q in fpolys[:i]:check('no_facility_overlap',not g.positive_area_overlap(p,q,1e-6),[fid,qid])
 # Source allocation fragments must be real residuals, never bbox claims.
 total=0.;patch_index=g._SpatialIndex(32);parts=[]
 for patch in data['patches']:
  patch_area=0.
  for poly in patch['polygons_xz_m']:
   check('finite_convex_patch_polygon',g.is_convex_polygon(poly),patch['id'])
   check('residual_not_assigned_twice',not context.hits(poly),patch['id'])
   for j in patch_index.candidates(poly):
    check('residual_fragments_disjoint',not g.positive_area_overlap(poly,parts[j],1e-6),patch['id'])
   patch_index.add(len(parts),poly);parts.append(poly);patch_area+=area(poly)
  check('patch_area_exact',abs(patch_area-patch['area_m2'])<1e-5,patch['id']);total+=patch_area
 check('total_residual_area_exact',abs(total-data['coverage']['exact_source_residual_assigned_m2'])<1e-5)
 route_context=Constraints(context.records+[{'category':'building_envelopes','id':k,'polygon':v} for k,v in envelopes.items()]+[{'category':'fabric_envelopes','id':k,'polygon':v} for k,v in fpolys])
 for r in data['residual_region_access']['regions']:
  check('substantial_region_connected',r['path'] is not None,r['id'])
  if r['path']:
   for poly in r['path']['ribbon_polygons_xz_m']:
    hits=route_context.hits(poly,PATH_ALLOW)
    if r['source_plot_strip_reassignments']:
     check('easement_only_declared_plot_types',all(h['category'] in ('original_plot_grounds','remaining_reserved_courtyards') for h in hits),r['id'])
     for h in hits:
      intersection=clean(g.convex_intersection(poly,h['polygon']));covers=[e['polygon_xz_m'] for e in r['source_plot_strip_reassignments'] if e['source_id']==h['id'] and e['source_category']==h['category']]
      if intersection:check('easement_geometry_explicit',g.uncovered_area_by_union(intersection,covers)<1e-6,[r['id'],h['id']])
    else:check('service_path_source_clear',not hits,{'id':r['id'],'hits':[h['id'] for h in hits]})
 return {'schema':'riverstone.city.landuse.validation.v1','pass':not failures,'failure_count':len(failures),'failures':failures,
 'evaluated_checks':dict(counts),'summary':{'new_buildings':len(new),'new_building_assets':len(assets),'actual_door_links':sum(len(b['all_entrances_local_m']) for b in new),
 'public_gateway_ids':[paths[i]['connected_public_road_id'] for i in seeds],'new_facilities':len(facilities),'landuse_patches':len(data['patches']),
 'residual_convex_fragments':len(parts),'exact_residual_area_m2':total,'substantial_residual_regions':data['residual_region_access']['substantial_region_count'],
 'regions_with_plot_strip_revision':sum(bool(r['source_plot_strip_reassignments']) for r in data['residual_region_access']['regions'])},
 'limitations':['Source/actual-geometry placement and explicit access validation only. Not a compiled merged city, physics traversal, structural or visual pass.',
 'Foundation source requirements and broad land-use surfaces still require coordinated terrain/common integration.']}

def main():
 data=json.loads((HERE/'candidate_overlay.json').read_text());source,context=load();result=validate(data,source,context)
 (HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({'pass':result['pass'],'failure_count':result['failure_count'],'summary':result['summary']}));return int(not result['pass'])
if __name__=='__main__':sys.exit(main())
