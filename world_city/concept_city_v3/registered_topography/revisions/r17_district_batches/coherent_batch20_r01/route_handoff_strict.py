"""Exact source-plane public-to-gate chains for the matched ready subset."""
import json,math
from .screen import HERE,write
from .. import author as a,native_clearance
from ..coherent_batch18_r01.route_interval import interval

def run():
 hand=json.loads((HERE/'physical_owner_handoff_r02.json').read_bytes());layout=json.loads((HERE/'effective_source_layout_r03.json').read_bytes());native=json.loads((HERE/'native_pack_ready_r02.json').read_bytes());selected=set(hand['accepted_holding_ids']);regions=hand['public_fixed_regions']+hand['physical_earth_owners'];idx=a.geo._SpatialIndex(2)
 for i,r in enumerate(regions):idx.add(i,r['polygon_xz_m'])
 entries=[];fail=[]
 for h in layout['holdings']:
  if h['id']not in selected:continue
  xyz=[];source_refs=set();errors=[]
  for p,q in zip(h['external_route'],h['external_route'][1:]):
   if math.dist(p,q)<1e-10:continue
   spans=[]
   for j in idx.candidates([p,q]):
    span=interval(p,q,regions[j]['polygon_xz_m'])
    if span:spans.append((span,j))
   knots=sorted({0.,1.}|{t for span,_ in spans for t in span});knots=[t for k,t in enumerate(knots)if k==0 or t-knots[k-1]>1e-9]
   for lo,hi in zip(knots,knots[1:]):
    if not any(s[0]-1e-9<=(lo+hi)/2<=s[1]+1e-9 for s,_ in spans):errors.append(dict(kind='uncovered_centerline_interval',a_xz_m=p,b_xz_m=q,parameters=[lo,hi]))
   for t in knots:
    x=[p[k]+t*(q[k]-p[k])for k in(0,1)];matches=[j for span,j in spans if span[0]-1e-9<=t<=span[1]+1e-9];ys=[a.common.height(regions[j]['plane_y_xz_m'],x)for j in matches]
    if not ys:errors.append(dict(kind='missing_source_point',point_xz_m=x));continue
    if max(ys)-min(ys)>1e-6:errors.append(dict(kind='source_height_seam',point_xz_m=x,heights_m=ys));continue
    v=[x[0],ys[0],x[1]]
    if not xyz or math.dist(v,xyz[-1])>1e-8:xyz.append(v)
    source_refs.update(regions[j]['id']for j in matches)
  entry=dict(id=h['id']+':PUBLIC_ENTRY',holding_id=h['id'],public_road_id=h['public_road_id'],width_m=h['external_width_m'],polyline_xyz_m=list(reversed(xyz)),public_start_xyz_m=xyz[-1]if xyz else None,court_gate_xyz_m=xyz[0]if xyz else None,source_reserved_polygons_xz_m=h['external_route_polygons_xz_m'],source_plane_owner_ids=sorted(source_refs),maximum_centerline_grade=max([abs(v[1]-u[1])/math.hypot(v[0]-u[0],v[2]-u[2])for u,v in zip(xyz,xyz[1:])if math.hypot(v[0]-u[0],v[2]-u[2])>1e-8]+[0]),errors=errors,status='SOURCE_PLANES_BOUND'if not errors else'HELD_ROUTE_HANDOFF');entries.append(entry)
  if errors:fail.append(h['id'])
 access=json.loads((HERE/'atomic_rebind_binding_r01.json').read_bytes())['exact_internal_routes']
 assert {r['holding_id']for r in access}==selected
 write('route_handoff_strict_r01.json',dict(schema='riverstone.r17.ready_private_routes.v1',status='SOURCE_BOUND_PENDING_COMPOSED_SCENE_REPLAY',terrain_handoff=dict(path=str((HERE/'physical_owner_handoff_r02.json').relative_to(a.ROOT)),sha256=a.sha(HERE/'physical_owner_handoff_r02.json')),base_scene_sha256=a.SCENE_SHA256,accepted_holding_ids=sorted(selected),entries=entries,internal_door_routes=access,actual_doors=native['actual_doors'],failures=fail,summary=dict(entries=len(entries),actual_doors=len(native['actual_doors']),internal_door_routes=len(access),source_profile_holds=len(fail)),activation=False));print(dict(entries=len(entries),door_routes=len(access),failures=fail),flush=True)
if __name__=='__main__':run()
