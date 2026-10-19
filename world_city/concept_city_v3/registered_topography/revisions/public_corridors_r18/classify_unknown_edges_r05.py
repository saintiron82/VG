"""Exact projected native intervals for the current unresolved public side edges."""
import json, math, collections, time
from pathlib import Path
from .height_field import HERE
from . import finite_geometry_r03 as g
from ..r17_district_batches import author as a
from ..r14_precinct_merchant import author as old
from world_city.concept_city_v3.traversal_r5 import prepare as b

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def interval(u,v,poly):
 poly=g.normalize_mask(poly)
 if len(poly)<3 or g.area(poly)<=g.MIN_AREA:return None
 sign=1 if g.signed_area(poly)>0 else-1;lo,hi=0.,1.
 for p,q in zip(poly,poly[1:]+poly[:1]):
  f=sign*g.cross(p,q,u);h=sign*g.cross(p,q,v)
  if f<0 and h<0:return None
  if f<0:lo=max(lo,f/(f-h))
  elif h<0:hi=min(hi,f/(f-h))
  if hi<=lo:return None
 return[lo,hi]
def union_length(spans):
 out=[]
 for lo,hi in sorted(spans):
  if out and lo<=out[-1][1]:out[-1][1]=max(out[-1][1],hi)
  else:out.append([lo,hi])
 return math.fsum(b-a for a,b in out)
def main():
 start=time.monotonic();rp=a.CITY/'registered_integration/r8/joint_boundary_r05/boundary_review.json';sp=a.CITY/'evidence/r8_district_r04/scene.json';pp=HERE/'finite_field_candidate_r07_native_bound.json';proof=json.loads(rp.read_bytes());scene=json.loads(sp.read_bytes());owners={r['id']:r for r in json.loads(pp.read_bytes())['records']};edges=proof['unknown_exterior_segments'];windows=[]
 for sub in ['contour_bulk_r01','coherent_batch18_r01']:
  data=json.loads((a.CITY/'registered_topography/revisions/r17_district_batches'/sub/'physical_owner_handoff_r02.json').read_bytes());owners.update({r['id']:r for r in data['physical_earth_owners']})
 owners.update({r['id']:r for r in json.loads((HERE/'north_mask_restoration_r01.json').read_bytes())['physical_earth_owners']})
 for r in edges:
  bb=a.bounds(r['edge_xz_m']);windows.append([[bb[0]-.001,bb[1]-.001],[bb[2]+.001,bb[1]-.001],[bb[2]+.001,bb[3]+.001],[bb[0]-.001,bb[3]+.001]])
 wi=a.geo._SpatialIndex(8);wboxes=[a.bounds(p)for p in windows]
 for i,p in enumerate(windows):wi.add(i,p)
 surfaces=[];ni=a.geo._SpatialIndex(4);cache={};refs=[]
 def near(poly):return any(a.intersects(a.bounds(poly),wboxes[i])for i in wi.candidates(poly))
 def add(r):ni.add(len(surfaces),r['polygon_xz_m']);surfaces.append(r)
 for p in scene['common_instances']:
  asset=scene['common_assets'][p['asset_key']];bounds=asset.get('bounds');path=a.ROOT/asset['render_path']
  if bounds is None:
   if p['asset_key']not in cache:
    assert a.sha(path)==asset['render_sha256'];cache[p['asset_key']]=json.loads(path.read_bytes());refs.append(ref(path))
   bounds=cache[p['asset_key']]['bounds']
  bb=b.instance_bounds(p,bounds)
  if not near([[bb[0],bb[1]],[bb[2],bb[1]],[bb[2],bb[3]],[bb[0],bb[3]]]):continue
  if p['asset_key']not in cache:
   assert a.sha(path)==asset['render_sha256'];cache[p['asset_key']]=json.loads(path.read_bytes());refs.append(ref(path))
  for gi,group in enumerate(cache[p['asset_key']]['groups']):
   for qi,q in enumerate(group['quads']):
    world=[b.transform(v,p)for v in q]
    if a.normal_y(world[:3])<=1e-12:continue
    poly=[[v[0],v[2]]for v in world]
    if near(poly):add(dict(id=p['id']+':UP:'+str(gi)+':'+str(qi),kind='actual_native_upface',native_instance_id=p['id'],polygon_xz_m=poly,plane_y_xz_m=a.common.plane(world[:3]),vertices_xyz_m=world,collision_policy=p.get('collision_policy')))
 for contract in scene.get('collision_contracts',[]):
  for i,t in enumerate(contract.get('add_triangles_world_xyz_m',[])):
   if abs(a.normal_y(t))<=1e-12:continue
   poly=[[v[0],v[2]]for v in t]
   if near(poly):add(dict(id=contract['id']+':TRI:'+str(i),kind='declared_collision_face',polygon_xz_m=poly,plane_y_xz_m=a.common.plane(t),vertices_xyz_m=t))
 rows=[];summary=collections.defaultdict(lambda:dict(count=0,length_m=0.))
 for n,r in enumerate(edges):
  owner=owners[r['owner_id']];u,v=r['edge_xz_m'];L=math.dist(u,v);sign=1 if g.signed_area(owner['polygon_xz_m'])>0 else-1;outward=[sign*(v[1]-u[1])/L,sign*(u[0]-v[0])/L];probe=[[x[k]+outward[k]*1e-5 for k in(0,1)]for x in(u,v)];hits=[]
  for i in ni.candidates(probe):
   s=surfaces[i];span=interval(*probe,s['polygon_xz_m'])
   if span:
    pts=[[u[k]+t*(v[k]-u[k])for k in(0,1)]for t in span];deltas=[a.common.height(s['plane_y_xz_m'],p)-a.common.height(owner['plane_y_xz_m'],p)for p in pts];hits.append(dict(surface=s,interval_t=span,edge_portion_xz_m=pts,delta_y_range_m=[min(deltas),max(deltas)]))
  mid=[(probe[0][k]+probe[1][k])/2 for k in(0,1)];legacy=old.owner_at(*mid);wet=[]
  for w in scene['terrain_contract']['water_domain_polygons']:
   span=interval(*probe,w['polygon_xz_m'])
   if span:wet.append(dict(surface_id=w['surface_id'],interval_t=span))
  native_ids={h['surface'].get('native_instance_id','')for h in hits};coverage=union_length([h['interval_t']for h in hits]);near_coverage=union_length([h['interval_t']for h in hits if max(abs(x)for x in h['delta_y_range_m'])<.5]);category='NO_CURRENT_NATIVE_PROFILE_INTERVAL'
  if any(s.startswith('E')and':registered_r1:'in s for s in native_ids)or legacy.get('property_id','').startswith('E'):category='NOBLE_ATOMIC_REPLACEMENT_BOUNDARY'
  elif any('COMMON'in s for s in native_ids):category='COMMON_RETAINED_NATIVE_BOUNDARY'
  elif any('BRIDGE_MAIN_RIVER'in s for s in native_ids)or legacy['kind']=='bridge_hole':category='NORTH_BRIDGE_NATIVE_OR_LEGACY_MASK_BOUNDARY'
  elif hits:category='CURRENT_NATIVE_BOUNDARY_REQUIRES_HEIGHT_CLASSIFICATION'
  elif wet:category='FINITE_WATER_BOUNDARY'
  elif L<.005:category='SMALL_UNMATCHED_BOUNDARY_EXPLICIT_ACCOUNTING'
  rows.append(dict(**r,edge_index=n,length_m=L,owner_plane_y_xz_m=owner['plane_y_xz_m'],outside_probe_segment_xz_m=probe,legacy_midpoint_owner=legacy,native_and_contract_intervals=hits,native_projection_covered_length_m=coverage*L,near_height_diagnostic_covered_length_m=near_coverage*L,water_intervals=wet,category=category));summary[category]['count']+=1;summary[category]['length_m']+=L
 out=dict(schema='riverstone.r18.unknown_boundary_classification.v1',status='R05_EDGES_WITH_R04_NATIVE_CONTEXT_DIAGNOSTIC_ONLY',sources=[ref(rp),ref(sp),ref(pp),ref(Path(old.__file__))]+refs,code_sha256=a.sha(__file__),summary=dict(summary),rows=rows,indexed_native_and_contract_faces=len(surfaces),seconds=time.monotonic()-start,limits=['Exact convex interval intersections describe projected coverage only.','Each native face retains its height difference; roofs and wall caps are not inferred walking floors.','The0.5m near-height number is a diagnostic summary, never an acceptance tolerance.','Native replacements, finite side generation and controller replay remain separate.'])
 target=HERE/'unknown_boundary_classification_r05_context.json';target.write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps(dict(summary=out['summary'],seconds=out['seconds'],output=ref(target))))
if __name__=='__main__':main()
