"""Build a hash-bound local R5 edit pack for the accepted seven holdings."""
import json,math,time,copy
from collections import defaultdict
from . import author as a, frozen as f, subset as s, restore_ground as rg, local_ground as lg

PROFILE_PATH=a.HERE/'public_interfaces/accepted_public_profiles.json'
MANIFEST=a.HERE/'public_interfaces/accepted_subset_manifest.json'
EXPECTED_MANIFEST='33e985cbe5086ccca3d47c28ce579368a6d03a888b2de67ca59bc3e40d110ae0'

def write(name,data):
 p=s.HERE/name
 raw=json.dumps(data,separators=(',',':'),allow_nan=False)+'\n'
 if p.exists():
  if p.read_text()!=raw:raise ValueError('Refusing to overwrite changed '+str(p))
 else:p.write_text(raw)
 return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))

def side_triangles(a0,a1,b0,b1):
 out=[]
 for tri in [[a0,a1,b1],[a0,b1,b0]]:
  u=[tri[1][k]-tri[0][k] for k in range(3)];v=[tri[2][k]-tri[0][k] for k in range(3)]
  area=math.sqrt(sum((u[(k+1)%3]*v[(k+2)%3]-u[(k+2)%3]*v[(k+1)%3])**2 for k in range(3)))/2
  if area>1e-10:out.append(tri)
 return out

def build_sides(ground,profiles):
 rows=ground['triangles']+[dict(r,kind='public_gate',property_id=p['property_id']) for p in profiles for r in p['triangles']]
 mesh=rg.MeshIndex(rows);ref=lg.LocalReference();out=[];issues=[];seen=set();native=lg.PatchQuery([r['polygon_xz_m'] for r in s.HOLES])
 boundaries=[dict(id=r['id'],polygon_xz_m=r['polygon_xz_m'],kind='merchant_platform') for r in s.PLATFORMS]+[dict(id=r['id'],polygon_xz_m=r['polygon_xz_m'],kind='retired_owner_restoration') for r in ground['restoration_domains']]
 segments=[]
 for r in boundaries:
  poly=r['polygon_xz_m'];orientation=1 if a.geo.signed_polygon_area(poly)>0 else -1
  for p,q in zip(poly,poly[1:]+poly[:1]):segments.append((r,p,q,orientation))
 # Profile boundary vertices have exactly the accepted shared knot values.
 for profile in profiles:
  for edge in profile['boundary']:
   u,v=edge['vertices_xyz_m'];p,q=[u[0],u[2]],[v[0],v[2]]
   length=math.dist(p,q)
   if length<1e-9:continue
   mid=lg.point(p,q,.5);normal=[(q[1]-p[1])/length,(p[0]-q[0])/length]
   inside1=any(r.get('kind')=='public_gate' for r in mesh.at([mid[k]-normal[k]*1e-5 for k in (0,1)]))
   segments.append((dict(id=profile['gate_id'],kind='public_gate',boundary_class=edge['kind']),p,q,1 if inside1 else -1))
 for r,p,q,orientation in segments:
  length=math.dist(p,q)
  if length<1e-9:continue
  normal=[orientation*(q[1]-p[1])/length,orientation*(p[0]-q[0])/length]
  ts=sorted(set(round(max(0.,min(1.,t)),12) for t in ref.edge_knots(p,q)+mesh.knots(p,q)))
  for lo,hi in zip(ts,ts[1:]):
   if (hi-lo)*length<1e-7:continue
   u,v=lg.point(p,q,lo),lg.point(p,q,hi);mid=lg.point(u,v,.5);pin=[mid[k]-normal[k]*1e-5 for k in (0,1)];pout=[mid[k]+normal[k]*1e-5 for k in (0,1)]
   inside=mesh.at(pin)
   if not inside:
    if native.inside(pin):continue
    issues.append(dict(owner=r['id'],edge=[u,v],issue='No new inside top'));continue
   outside=mesh.at(pout);source='new_patch'
   if not outside:outside=ref.at(pout);source='frozen_R5'
   if not outside:
    owner=a.base.owner_at(*pout)
    if not owner.get('render_land',True):continue # Retained native wall closes its own footprint.
    issues.append(dict(owner=r['id'],edge=[u,v],issue='No outside top'));continue
   aa,bb=inside[0],outside[0];a0=[u[0],lg.plane_y(aa,u),u[1]];a1=[v[0],lg.plane_y(aa,v),v[1]];b0=[u[0],lg.plane_y(bb,u),u[1]];b1=[v[0],lg.plane_y(bb,v),v[1]]
   if max(abs(a0[1]-b0[1]),abs(a1[1]-b1[1]))<1e-7:continue
   key=tuple(sorted(tuple(round(x,7) for x in vv) for vv in [a0,a1,b0,b1]))
   if key in seen:continue
   seen.add(key)
   out.append(dict(id='R15_SUBSET:SIDE:'+str(len(out)),owner=r['id'],inside_kind=aa['kind'],outside_kind=bb.get('kind',source),boundary_class=r.get('boundary_class','finite_nonwalking_platform_or_restored_ground_edge'),walkable_crossing=False,inside_vertices_xyz_m=[a0,a1],outside_vertices_xyz_m=[b0,b1],triangles_xyz_m=side_triangles(a0,a1,b0,b1)))
 return dict(records=out,issues=issues)

def main():
 started=time.time()
 if a.sha(MANIFEST)!=EXPECTED_MANIFEST:raise ValueError('Changed public manifest')
 manifest=json.loads(MANIFEST.read_bytes())
 profiles=json.loads(PROFILE_PATH.read_bytes())['profiles']
 if {r['property_id'] for r in profiles}!=s.IDS:raise ValueError('Subset/profile mismatch')
 for p in profiles:
  if not p['accepted'] or p['proof']['maximum_actual_clipped_triangle_grade']>.120000001:raise ValueError('Unaccepted profile')
 profile_masks=[r['polygon_xz_m'] for p in profiles for r in p['ownership_masks']]
 restorations=s.restoration_domains();masks=[r['polygon_xz_m'] for r in s.PLATFORMS]+[r['polygon_xz_m'] for r in restorations]+profile_masks
 maskidx=a.geo._SpatialIndex(8)
 for i,p in enumerate(masks):maskidx.add(i,p)
 # Original retained owners are now protected even if another inactive candidate would retire them.
 inactive=set(a.RETIRED)-set(s.RETIRED);conflicts=[]
 for r in a.retired_owner_domains():
  if r['old_owner_id'].split(':')[0] not in inactive:continue
  for i in maskidx.candidates(r['polygon_xz_m']):
   p=a.polygon(a.geo.convex_intersection(r['polygon_xz_m'],masks[i]))
   if p and a.geo.polygon_area(p)>1e-7:conflicts.append(dict(owner=r['old_owner_id'],mask_index=i,area_m2=a.geo.polygon_area(p)))
 if conflicts:raise ValueError('Inactive R5 owner overlap '+str(conflicts[:3]))
 ground=rg.build(profile_masks,s.PROPERTIES,restorations);print('Ground built',len(ground['triangles']),flush=True)
 ground['edge_review']=rg.edge_review(ground,profile_masks,masks)
 if ground['edge_review']['issues'] or ground['edge_review']['failed_edges']:raise ValueError('Restored retained-edge failure '+str(ground['edge_review']['failed_edges']))
 sides=build_sides(ground,profiles);print('Sides built',len(sides['records']),'issues',len(sides['issues']),flush=True)
 if sides['issues']:write('side_issues.json',sides);raise ValueError('Incomplete side ownership')
 groundref=write('ground_and_edges.json',ground);sideref=write('finite_sides.json',sides)
 scene=f.load_scene();edits=[];source_hashes={};old_count=sum(len(v)//3 for v in scene['surfaces'].values());removed_area=defaultdict(float)
 for material,vertices in scene['surfaces'].items():
  if material=='water':continue
  for start in range(0,len(vertices),3):
   tri=vertices[start:start+3];poly=[[v[0],v[2]] for v in tri];candidates=sorted(maskidx.candidates(poly))
   if not candidates:continue
   cuts=[masks[i] for i in candidates]
   result=f.clip_vertical_triangle(tri,cuts) if a.geo.polygon_area(poly)<=a.MIN_AREA_M2 else a.clip_frozen_triangle(tri,cuts)
   if result['unchanged']:continue
   if material not in source_hashes:source_hashes[material]=f.canonical_sha(vertices)
   edits.append(dict(material=material,triangle_index=start//3,source_triangle_sha256=f.canonical_sha(tri),replacement_triangles_xyz_m=result['triangles_xyz_m']))
   removed_area[material]+=a.geo.polygon_area(poly)-sum(a.geo.polygon_area([[v[0],v[2]] for v in t]) for t in result['triangles_xyz_m'])
  print('Edited',material,sum(x['material']==material for x in edits),flush=True)
 append=defaultdict(list)
 for r in ground['triangles']:append[r['material']].extend(r['vertices_xyz_m'])
 for profile in profiles:
  for r in profile['triangles']:append[r['material']].extend(r['vertices_xyz_m'])
 for r in sides['records']:
  for t in r['triangles_xyz_m']:append['bank'].extend(t)
 removed_boxes=[r['id'] for r in scene['boxes'] if r.get('source_mass_id') in s.RETIRED]
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R15_MERCHANT_ACCEPTED_SEVEN',status='FINITE_SOURCE_ACCEPTED_PENDING_ACTUAL_SCENE_REVIEW',base_scene_sha256=f.SCENE_SHA256,source_surface_hashes=source_hashes,surface_edits=edits,appended_surfaces=dict(append),removed_foundation_proxy_ids=removed_boxes,source_bindings=dict(source_contract_sha256=a.sha(a.HERE/'source_contract.json'),public_manifest_sha256=a.sha(MANIFEST),ground=groundref,sides=sideref),accepted_property_ids=sorted(s.IDS),retired_source_ids=s.RETIRED,inactive_property_ids=sorted({r['property_id'] for r in a.PLATFORMS}-s.IDS),inactive_original_ids=sorted(inactive))
 # Reapply against the original arrays to prove untouched values and order.
 output=f.apply_edits(scene,patch)
 disjoint=[];changed={(r['material'],r['triangle_index']) for r in edits}
 others=[a.CITY/'traversal_r5/revisions/r02/scene_patch.json',a.CITY/'assemblies/landmarks/registered/precinct_r05_ground/local_frame_r01/corner_repair_r01/terrain_patch/surface_patch.json']
 for path in others:
  other=json.loads(path.read_bytes());hits=changed & {(r['material'],r['triangle_index']) for r in other['surface_edits']};disjoint.append(dict(path=str(path.relative_to(a.ROOT)),sha256=a.sha(path),source_index_conflicts=sorted(hits)))
  if hits:raise ValueError('Cross-pack source index conflicts '+str(hits))
 pack=s.filtered_pack();support=s.filtered_support();packref=write('merchant_pack.json',pack);supportref=write('support_pack.json',support);patchref=write('scene_patch.json',patch)
 audit=dict(status='PASS_FINITE_SOURCE_PENDING_VIEW_AND_TRAVERSAL',base_scene_sha256=f.SCENE_SHA256,subset_indices=list(s.INDICES),accepted_property_ids=sorted(s.IDS),retired_source_ids=s.RETIRED,inactive_original_ids=sorted(inactive),native_placement_count=len(pack['placements']),actual_door_count=len(pack['actual_doors']),native_hole_count=len(s.HOLES),support_placement_count=len(support['placements']),removed_foundation_proxy_ids=removed_boxes,source_triangle_count=old_count,edited_source_triangle_count=len(edits),appended_triangle_counts={k:len(v)//3 for k,v in append.items()},removed_projected_area_m2=dict(removed_area),restored_retained_edge_count=len(ground['edge_review']['edges']),maximum_step_increase_m=ground['edge_review']['maximum_step_increase_m'],inactive_owner_overlap=[],cross_patch_index_checks=disjoint,unchanged_triangle_ledger=output['local_terrain_patch']['unchanged_triangle_ledger'],limits=['No new capsule/cart approval.','New vertical faces are nonwalking retaining/curb edges.','Inactive twelve merchant candidates retain all original R5 owners.'],elapsed_s=time.time()-started)
 auditref=write('acceptance_report.json',audit)
 files=[patchref,packref,supportref,auditref,groundref,sideref]
 files += [dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p)) for p in [a.HERE/'subset.py',a.HERE/'restore_ground.py',a.HERE/'build_subset.py',a.HERE/'frozen.py',PROFILE_PATH,MANIFEST]]
 seal=write('freeze_manifest.json',dict(schema='riverstone.r15_seven_freeze.v1',base_scene_sha256=f.SCENE_SHA256,files=files,accepted_property_ids=sorted(s.IDS),activation=False))
 print(json.dumps(dict(patch=patchref,merchant=packref,support=supportref,audit=auditref,seal=seal,elapsed_s=time.time()-started)),flush=True)

if __name__=='__main__':main()
