"""Finite accepted-profile intervals and actual solid native wall evidence."""
import json, math, collections, itertools, time
from .height_field import HERE
from . import finite_geometry_r03 as g
from .classify_unknown_edges_r01 import interval, union_length, ref
from ..r17_district_batches import author as a
from world_city.concept_city_v3.traversal_r5 import prepare as b
from functools import lru_cache
ref=lru_cache(None)(ref)

def main():
 start=time.monotonic();source=HERE/'north_connected_unknown_context_r03.json';data=json.loads(source.read_bytes());sp=a.CITY/'evidence/r8_district_r04/scene.json';scene=json.loads(sp.read_bytes());root=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01';np=root/'noble_entry_batch_r01/fixed_public_interfaces_r18.json';n=json.loads(np.read_bytes());assert a.sha(np)=='9d57c840e36f185d59b595b5ea341c7487529317de219338f7346b939ea5468a'
 profiles=[dict(r,native_owner_id=o['owner_id'],source=ref(np))for o in n['owners']for r in o['physical_public_top_pieces']]
 north=a.CITY/'assemblies/waterworks/registered_bridge/north_approach_r03/profile.json';northdata=json.loads(north.read_bytes())
 for i,r in enumerate(northdata['triangles']):
  t=r['triangle_xyz_m'];profiles.append(dict(id='ACCEPTED_NORTH_WALK:'+str(i),polygon_xz_m=[[v[0],v[2]]for v in t],plane_y_xz_m=a.common.plane(t),native_owner_id='NORTH_CONTINUOUS_ROAD',source=ref(north)))
 cp=root/'common_entry_repair_r03/candidate_r02/collision_contract.json';common=json.loads(cp.read_bytes());ts=common['add_triangles_world_xyz_m'];cut=common['retained_native_triangle_count'];assert len(ts)-cut==common['walking_triangle_count']
 for i,t in enumerate(ts[cut:],cut):profiles.append(dict(id='ACCEPTED_COMMON_WALK:'+str(i),polygon_xz_m=[[v[0],v[2]]for v in t],plane_y_xz_m=a.common.plane(t),native_owner_id='COMMON_CONTINUOUS_WALK',source=ref(cp)))
 pi=a.geo._SpatialIndex(4)
 for i,r in enumerate(profiles):pi.add(i,r['polygon_xz_m'])
 wanted={h['surface'].get('native_instance_id')for r in data['rows']for h in r['native_and_contract_intervals']if h['surface'].get('native_instance_id') and ':registered_r1:'not in h['surface']['native_instance_id']}
 faces=[];fi=a.geo._SpatialIndex(4);refs=[]
 for pose in scene['common_instances']:
  if pose['id']not in wanted:continue
  asset=scene['common_assets'][pose['asset_key']];p=a.ROOT/asset['render_path'];assert a.sha(p)==asset['render_sha256'];refs.append(ref(p));render=json.loads(p.read_bytes())
  for gi,group in enumerate(render['groups']):
   for qi,q in enumerate(group['quads']):
    world=[b.transform(v,pose)for v in q];xz=[[v[0],v[2]]for v in world]
    if abs(a.normal_y(world[:3]))>1e-12:continue
    ys=sorted({v[1]for v in world})
    if len(ys)!=2:continue
    u,v=max(itertools.combinations(xz,2),key=lambda t:math.dist(*t))
    if math.dist(u,v)<1e-9:continue
    r=dict(id=pose['id']+':SIDE:'+str(gi)+':'+str(qi),native_instance_id=pose['id'],vertices_xyz_m=world,segment_xz_m=[u,v],bottom_y_m=ys[0],top_y_m=ys[-1]);fi.add(len(faces),[u,v]);faces.append(r)
 def side_span(u,v,f):
  p,q=f['segment_xz_m'];L=math.dist(p,q)
  # This is a reported roundoff bound for transformed coincident planes, not
  # a physical edge expansion or a change to the emitted geometry.
  dist=max(abs(g.cross(p,q,x))/L for x in(u,v))
  if dist>2e-7:return None
  D=math.dist(u,v)**2;ts=[sum((x[k]-u[k])*(v[k]-u[k])for k in(0,1))/D for x in(p,q)];lo=max(0.,min(ts));hi=min(1.,max(ts))
  return([lo,hi],dist)if hi>lo else None
 rows=[];accepted={};summary=collections.defaultdict(lambda:dict(count=0,length_m=0.));actionable=[]
 for r in data['rows']:
  u,v=r['edge_xz_m'];L=r['length_m'];hits=[];closed=[];joins=[];h0=a.common.height(r['owner_plane_y_xz_m'],u);h1=a.common.height(r['owner_plane_y_xz_m'],v)
  for i in pi.candidates(r['outside_probe_segment_xz_m']):
   p=profiles[i];span=interval(*r['outside_probe_segment_xz_m'],p['polygon_xz_m'])
   if span:accepted[p['id']]=p;hits.append(dict(profile_id=p['id'],interval_t=span,plane_y_xz_m=p['plane_y_xz_m']))
  for i in fi.candidates([u,v]):
   f=faces[i];spn=side_span(u,v,f)
   if not spn:continue
   (lo,hi),dist=spn;knots=[lo,hi]
   if h1!=h0:knots +=[t for y in(f['bottom_y_m'],f['top_y_m'])if lo<(t:=(y-h0)/(h1-h0))<hi]
   for p,q in zip(sorted(knots),sorted(knots)[1:]):
    y=h0+(p+q)/2*(h1-h0);record=dict(native_face=f,interval_t=[p,q],coincident_plane_max_distance_m=dist,road_y_interval_m=[h0+p*(h1-h0),h0+q*(h1-h0)])
    if f['bottom_y_m']-1e-9<=y<=f['top_y_m']+1e-9:closed.append(record)
    elif y>f['top_y_m'] and f['native_instance_id']in('BRIDGE_MAIN_RIVER:NORTH_SUPPORTED_CAUSEWAY','R06_COMMON_R02:fine_access','BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED'):
     joins.append(dict(record,actual_structural_top_plane_y_xz_m=[0,0,f['top_y_m']],semantics='nonwalking retaining connection to measured native support top; not an adjacent walking floor'))
  coverage=union_length([x['interval_t']for x in hits+closed]);supported=union_length([x['interval_t']for x in hits+closed+joins]);category='PARTIAL_OR_UNRESOLVED'
  if r['category']=='CURRENT_NATIVE_BOUNDARY_REQUIRES_HEIGHT_CLASSIFICATION'and any('SITE_CEMETERY'in x['surface']['id']for x in r['native_and_contract_intervals']):category='HELD_OBSOLETE_CEMETERY_PATH_CAP_INTRUSION'
  elif coverage>=1-1e-8:category='EXACT_ACCEPTED_PROFILE_OR_SOLID_NATIVE_SIDE'
  elif supported>=1-1e-8:category='NONWALKING_NATIVE_SUPPORT_JOIN_REQUIRED'
  elif r['category']=='NOBLE_ATOMIC_REPLACEMENT_BOUNDARY':category='REQUERY_AFTER_ATOMIC_NOBLE_EMISSION_TRIM'
  elif r['category'].startswith('NORTH'):category='BOUNDED_OBSOLETE_BRIDGE_MASK_RESTORATION_REQUIRED'
  elif r['category'].startswith('SMALL'):category='EXACT_SMALL_FRAGMENT_REMAINS_UNRESOLVED'
  row=dict(owner_id=r['owner_id'],edge_index=r['edge_index'],edge_xz_m=r['edge_xz_m'],length_m=L,category=category,accepted_physical_profile_intervals=hits,already_closed_native_side_intervals=closed,nonwalking_native_support_join_intervals=joins,accepted_or_closed_length_m=coverage*L,with_structural_join_length_m=supported*L,legacy_owner=r['legacy_midpoint_owner']);rows.append(row);summary[category]['count']+=1;summary[category]['length_m']+=L
 out=dict(schema='riverstone.r18.boundary_closure_handoff.v1',status='BOUNDED_ACTIONABLE_INTERVALS_WITH_EXPLICIT_REMAINING_HOLDS',sources=[ref(source),ref(sp),ref(np),ref(north),ref(cp)]+refs,code_sha256=a.sha(__file__),accepted_adjacent_physical_owners=list(accepted.values()),all_noble_physical_owners=[r for r in profiles if r['native_owner_id'].startswith('E')],rows=rows,summary=dict(summary),seconds=time.monotonic()-start,limits=['Physical profile polygons are finite and may be supplied to the outside-owner query.','Only exact actual vertical native side spans are classified already closed.','Measured structural support joins are nonwalking retaining connectors, never inferred roof/cap walking floors.','The seven noble replacements and revised public mask must activate atomically.','Recompute final boundary segments after emission trimming; this ledger retains the exact199 r05 unknown-edge provenance and native R04 source faces.'])
 target=HERE/'north_connected_native_closure_r04.json';target.write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps(dict(summary=out['summary'],seconds=out['seconds'],output=ref(target))))
if __name__=='__main__':main()
