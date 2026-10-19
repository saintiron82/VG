"""Hash-bound finite dry-top and above-floor side composition for four crossings."""
import json,math,collections
from . import select_profiles as s,finite
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a,side_clearance as side
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.regeneration_interfaces import clean3
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.audit_retired_boundaries import interval as old_interval
from world_city.runtime_city.checks import placement as g
HERE=s.HERE
interval=finite.interval

def lift(poly,plane):return[[x,a.common.height(plane,[x,z]),z]for x,z in poly]
def clip3(poly,fn):return clean3(side.halfspace(poly,fn))
def split3(poly,mask):
 inside=poly;outside=[];sign=1 if g.signed_polygon_area(mask)>0 else-1
 for p,q in zip(mask,mask[1:]+mask[:1]):
  L=math.dist(p,q)
  if L<1e-10:continue
  fn=lambda v:sign*g._cross(p,q,[v[0],v[2]])/L
  # A source face exactly at the outer ownership boundary remains exterior.
  if inside and max(abs(fn(v))for v in inside)<1e-9:return[poly],[]
  part=clip3(inside,lambda v:-fn(v))
  if part:outside.append(part)
  inside=clip3(inside,fn)
  if not inside:break
 return outside,inside

def planar_clip3(poly,mask):
 sign=1 if g.signed_polygon_area(mask)>0 else-1;out=poly
 for p,q in zip(mask,mask[1:]+mask[:1]):
  L=math.dist(p,q)
  if L<1e-10:continue
  out=clip3(out,lambda v:sign*g._cross(p,q,[v[0],v[2]])/L)
  if not out:break
 return out

def subspans(spans):
 knots=sorted({0.,1.}|{max(0,min(1,x))for span in spans for x in span});out=[]
 for lo,hi in zip(knots,knots[1:]):
  if hi-lo<1e-9:continue
  mid=(lo+hi)/2
  if not any(u-1e-10<=mid<=v+1e-10 for u,v in spans):out.append((lo,hi))
 return out

def boundaries(fields,bridges,index):
 fi=g._SpatialIndex(8)
 for i,t in enumerate(fields):fi.add(i,t['polygon_xz_m'])
 rows=[];closures=[];miss=[]
 for i,t in enumerate(fields):
  tri=t['vertices_xyz_m'];poly=t['polygon_xz_m']
  for p,q in zip(tri,tri[1:]+tri[:1]):
   xz=[[p[0],p[2]],[q[0],q[2]]];L=math.dist(*xz)
   if L<1e-8:continue
   # Orient interior left, outward right in XZ.
   if g.signed_polygon_area(poly)<0:p,q=q,p;xz=xz[::-1]
   normal=[(xz[1][1]-xz[0][1])/L,-(xz[1][0]-xz[0][0])/L];inside=[]
   for j in fi.candidates(xz):
    if j==i:continue
    other=fields[j];span=interval(*xz,other['polygon_xz_m'])
    if not span:continue
    u=sum(span)/2;probe=[xz[0][k]+u*(xz[1][k]-xz[0][k])+normal[k]*1e-6 for k in(0,1)]
    if max(sum((v[k]-xz[0][k])*normal[k]for k in(0,1))for v in other['polygon_xz_m'])>1e-9:inside.append(span)
   for lo,hi in subspans(inside):
    u=[[p[k]+v*(q[k]-p[k])for k in range(3)]for v in(lo,hi)];edge=[[v[0],v[2]]for v in u];length=math.dist(*edge)
    if length<1e-7:continue
    candidates=[]
    # Native shared edges are explicit support, with no duplicate retaining face.
    for b in bridges:
     span=interval(*edge,b['native_ownership_polygon_xz_m'])
     if not span:continue
     mid=sum(span)/2;probe=[edge[0][k]+mid*(edge[1][k]-edge[0][k])+normal[k]*1e-6 for k in(0,1)]
     if max(sum((v[k]-edge[0][k])*normal[k]for k in(0,1))for v in b['native_ownership_polygon_xz_m'])>1e-9:candidates.append((span,'native',b))
    for j in index.index.candidates(edge):
     r=index.rows[j];span=interval(*edge,r['polygon_xz_m'])
     if not span:continue
     mid=sum(span)/2;probe=[edge[0][k]+mid*(edge[1][k]-edge[0][k])+normal[k]*1e-6 for k in(0,1)]
     if max(sum((v[k]-edge[0][k])*normal[k]for k in(0,1))for v in r['polygon_xz_m'])>1e-9:candidates.append((span,'source',r))
    knots=sorted({0.,1.}|{max(0,min(1,v))for span,_,_ in candidates for v in span})
    for aa,bb in zip(knots,knots[1:]):
     if (bb-aa)*length<1e-7:continue
     mid=(aa+bb)/2;rs=[(kind,r)for span,kind,r in candidates if span[0]-1e-9<=mid<=span[1]+1e-9];ns=[r for kind,r in rs if kind=='native'];top=[[u[0][k]+v*(u[1][k]-u[0][k])for k in range(3)]for v in(aa,bb)]
     if ns:
      if any(abs(v[1]-ns[0]['deck_top_y_m'])>1e-6 for v in top):raise ValueError('Mismatched native seam')
      rows.append(dict(field_id=t['owner_id'],edge_xyz_m=top,kind='exact_native_deck_seam',native_id=ns[0]['placement_id'],maximum_delta_m=0));continue
     rs=[r for kind,r in rs if kind=='source']
     if not rs:miss.append(dict(field_id=t['owner_id'],edge_xyz_m=top,length_m=(bb-aa)*length));continue
     bottoms=[lift([[v[0],v[2]]for v in top],r['plane_y_xz_m'])for r in rs]
     if any(max(v[k][1]for v in bottoms)-min(v[k][1]for v in bottoms)>1e-5 for k in(0,1)):raise ValueError('Incompatible exterior support planes')
     bottom=bottoms[0];delta=max(abs(v[1]-w[1])for v,w in zip(top,bottom));row=dict(field_id=t['owner_id'],edge_xyz_m=top,old_edge_xyz_m=bottom,source_material=rs[0]['material'],source_triangle_index=rs[0]['triangle_index'],source_triangle_sha256=rs[0]['source_triangle_sha256'],kind='nonwalking_lateral_retaining'if delta>1e-6 else'exact_original_surface_seam',maximum_delta_m=delta);rows.append(row)
     if delta>1e-6:
      quad=[top[0],top[1],bottom[1],bottom[0]]
      for tr in[[quad[0],quad[1],quad[2]],[quad[0],quad[2],quad[3]]]:
       if side.area3d(tr)>1e-10:closures.append(tr)
 return rows,closures,miss

def run():
 scene=a.load_scene();doc=json.loads((HERE/'fields.json').read_text());assert doc['status']=='PREFLIGHT_PASS';profiles=doc['profiles'];bridges=json.loads((HERE.parent/'crossing_interfaces.json').read_text())['crossings'];fields=[];domains=[]
 for p in profiles:
  domains.extend(dict(id=p['id'],polygon_xz_m=q,kind='approach')for q in p['polygons_xz_m'])
  for t in p['triangles']:fields.append(dict(t,owner_id=p['id']))
 holes=[dict(id=b['placement_id'],polygon_xz_m=b['native_ownership_polygon_xz_m'],kind='native')for b in bridges];owners=holes+domains;windows=[r['polygon_xz_m']for r in owners];ix=a.TriangleIndex(scene,windows);oi=g._SpatialIndex(8)
 for i,o in enumerate(owners):oi.add(i,o['polygon_xz_m'])
 edits=[];partitions=[];oldparts=[]
 for r in ix.rows:
  masks=[owners[i]['polygon_xz_m']for i in oi.candidates(r['polygon_xz_m'])];remain=finite.subtract([r['polygon_xz_m']],masks);oldarea=g.polygon_area(r['polygon_xz_m']);after=sum(g.polygon_area(p)for p in remain)
  if oldarea-after<=1e-9:continue
  assigned=[];rest=[r['polygon_xz_m']]
  for mask in masks:
   assigned.extend(q for p in rest if(q:=finite.intersect(p,mask)));rest=finite.subtract(rest,[mask])
  owned=sum(g.polygon_area(p)for p in assigned)
  if abs(oldarea-after-owned)>1e-7:raise ValueError('Source top partition failure')
  repl=[t for poly in remain for t in a.fan_upward(lift(poly,r['plane_y_xz_m']))];edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=repl));partitions.append(dict(material=r['material'],triangle_index=r['triangle_index'],old_area_m2=oldarea,retained_area_m2=after,removed_area_m2=owned));oldparts.extend(dict(material=r['material'],triangle_index=r['triangle_index'],polygon_xz_m=p,plane_y_xz_m=r['plane_y_xz_m'])for p in assigned)
 print('dry top edits',len(edits),flush=True)
 # Side masks use the actual varying road plane. Bank below that plane remains
 # byte-identical where uncut; native deck cuts start only at its underside.
 sideowners=[dict(id=b['placement_id'],polygon_xz_m=b['native_ownership_polygon_xz_m'],plane_y_xz_m=[0,0,b['deck_underside_y_m']],cut_kind='native_deck_above_underside')for b in bridges]+[dict(id=t['owner_id'],polygon_xz_m=t['polygon_xz_m'],plane_y_xz_m=t['plane_y_xz_m'],cut_kind='approach_above_finished_floor')for t in fields];si=g._SpatialIndex(8)
 for i,o in enumerate(sideowners):si.add(i,o['polygon_xz_m'])
 oldside=side.SideIndex(scene,windows);removed=[];sidepartitions=[]
 for r in oldside.rows:
  remaining=[r['vertices_xyz_m']];cutrows=[]
  for i in si.candidates(r['projection_xz_m']):
   owner=sideowners[i];nextpieces=[]
   for piece in remaining:
    outside,inside=split3(piece,owner['polygon_xz_m']);nextpieces.extend(outside)
    if not inside:continue
    h=lambda v:v[1]-a.common.height(owner['plane_y_xz_m'],[v[0],v[2]])
    keep=clip3(inside,lambda v:-h(v));cut=clip3(inside,h)
    if keep:nextpieces.append(keep)
    if cut and side.area3d(cut)>1e-9:cutrows.append(dict(owner_id=owner['id'],cut_kind=owner['cut_kind'],cut_plane_y_xz_m=owner['plane_y_xz_m'],vertices_xyz_m=cut,area_m2=side.area3d(cut)))
   remaining=nextpieces
  if not cutrows:continue
  before=side.area3d(r['vertices_xyz_m']);after=sum(side.area3d(p)for p in remaining);cutarea=sum(x['area_m2']for x in cutrows)
  if abs(before-after-cutarea)>1e-6:raise ValueError('Side area partition mismatch '+str((r['triangle_index'],before,after,cutarea)))
  repl=[[p[0],p[j],p[j+1]]for p in remaining for j in range(1,len(p)-1)if side.area3d([p[0],p[j],p[j+1]])>1e-10];edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=repl));removed.extend(dict(x,material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'])for x in cutrows);sidepartitions.append(dict(material=r['material'],triangle_index=r['triangle_index'],before_area_m2=before,retained_area_m2=after,removed_area_m2=cutarea))
 print('side cuts',len(sidepartitions),len(removed),flush=True)
 seams,closure,missing=boundaries(fields,bridges,ix);print('boundaries',len(seams),'closure',len(closure),'missing',len(missing),flush=True)
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='WATER_COMPLETION_FOUR_CROSSING_APPROACHES_R02',status='INACTIVE_PENDING_SOURCE_AND_COMPOSITION_TESTS',base_scene_sha256=a.SCENE_SHA256,source_surface_hashes={m:a.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in edits})},surface_edits=edits,appended_surfaces=dict(road=[v for t in fields for v in t['vertices_xyz_m']],bank=[v for t in closure for v in t]),removed_foundation_proxy_ids=[])
 report=dict(base_scene_sha256=a.SCENE_SHA256,field_source_sha256=a.sha(HERE/'fields.json'),public_handoff_sha256=a.sha(HERE/'public_handoff.json'),dry_top_partitions=partitions,source_top_owned_pieces=oldparts,side_partitions=sidepartitions,removed_side_pieces=removed,boundary_seams=seams,missing_boundary_segments=missing,appended_top_triangles=len(fields),appended_retaining_triangles=len(closure),water_policy='No water triangle index, vertex or order is edited.',bank_policy='Only exact finite side pieces above the declared local road plane or frozen deck underside are cut. Submerged geometry preservation is independently tested.',activation=False)
 s.write('surface_patch.json',patch);s.write('patch_report.json',report)
 if missing:print('FIRST MISSING',missing[:8],flush=True)
if __name__=='__main__':run()
