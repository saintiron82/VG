"""Close district backbone roots against exact existing public road planes."""
import json,math,time
from . import author as a,preflight_layout,side_clearance
ROOTS={'B15:R8:LANE:1_0:01'}
FABRIC=a.CITY/'assemblies/ordinary/registered/district_fabric_r01'
def circle(p,r):
 r/=math.cos(math.pi/16)
 return [[p[0]+r*math.cos(j*math.pi/8),p[1]+r*math.sin(j*math.pi/8)]for j in range(16)]
def closest(p,u,v):
 dx,dz=v[0]-u[0],v[1]-u[1];ll=dx*dx+dz*dz;t=max(0.,min(1.,((p[0]-u[0])*dx+(p[1]-u[1])*dz)/ll));return[u[0]+t*dx,u[1]+t*dz]
def run():
 folder=a.HERE/'public_tail_inherited_cap_r01'
 if folder.exists():raise SystemExit('Preserve previous tail evidence')
 folder.mkdir();layout=json.loads((FABRIC/'selected_layout.json').read_bytes());hand=json.loads((FABRIC/'terrain_handoff.json').read_bytes());scene=a.load_scene();plan=json.loads(a.PLAN_PATH.read_bytes());t0=time.monotonic()
 roots=[r for r in layout['shared_private_routes']if r['id']in ROOTS];windows=[]
 for r in roots:
  x,z=r['polyline_xz_m'][-1];windows.append([[x-16,z-16],[x+16,z-16],[x+16,z+16],[x-16,z+16]])
 index=a.TriangleIndex(scene,windows);preflight_layout.virtual_restorations(index,layout);sides=side_clearance.SideIndex(scene,windows)
 protected=[];pi=a.geo._SpatialIndex(16)
 def add(id,p,kind):pi.add(len(protected),p);protected.append(dict(id=id,polygon_xz_m=p,kind=kind))
 projection=json.loads((a.CITY/'registered_integration/r8/coverage_plan/native_projection.json').read_bytes())
 for inst in projection['instances']:
  if inst['id']in layout['retired_source_ids']:continue
  for j,p in enumerate(inst['native_owner_parts_xz_m']):add(inst['id']+':'+str(j),p,'retained_native')
 for p in scene['terrain_contract']['water_domain_polygons']:add(p['surface_id'],p['polygon_xz_m'],'water')
 for p in hand['protected_regions']:add(p['id'],p.get('polygon_xz_m',p.get('polygon')),p['kind'])
 for h in hand['parcels']:
  for f in h.get('native_footing_owners',[]):
   for j,p in enumerate(f['polygons_xz_m']):add(f['id']+':'+str(j),p,'new_native_footing')
 for p in layout['placements']:
  for j,q in enumerate(p['native_walking_obstacles_xz_m']):add(p['id']+':WALKING:'+str(j),q,'new_native_obstacle')
 out=[];failures=[]
 for r in roots:
  q=r['polyline_xz_m'][-1];candidates=[]
  for road in plan['roads']:
   for j,(u,v)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
    end=closest(q,u,v);dist=math.dist(q,end)
    if dist<16:candidates.append((dist,road['id'],j,end,road['width_m'],u,v))
  attempts=[];chosen=None
  for distance,rid,j,end,rw,u,v in sorted(candidates)[:12]:
   polygons=a.common.disjoint_union([a.geo.road_ribbon(q,end,r['width_m']),circle(q,r['width_m']/2),circle(end,min(r['width_m'],rw)/2)])
   checks=[a.audit_polygon(index,p,None)for p in polygons];contacts=[]
   for p in polygons:
    for k in pi.candidates(p):
     b=protected[k];inter=a.clip(p,b['polygon_xz_m'])
     if inter and a.geo.polygon_area(inter)>1e-7:contacts.append(dict(protected_id=b['id'],kind=b['kind'],area_m2=a.geo.polygon_area(inter),polygon_xz_m=inter))
   side=sides.audit([dict(id=r['id']+':PUBLIC_TAIL',polygon_xz_m=p,floor_y_m=r['floor_y_m'])for p in polygons]);roadpoly=a.geo.road_ribbon(u,v,rw);overlaps=[v['intersection_polygon_xz_m']for p in polygons for v in index.covering(p)if v['material']in('road','alley')];semantic=[a.clip(p,roadpoly)for p in polygons];semantic=[p for p in semantic if p];roadgap=sum(a.geo.polygon_area(p)for p in a.common.subtract(semantic,overlaps));passed=all(c['passes_existing_surface']for c in checks)and not contacts and not side['contacts']and roadgap<1e-7
   brief=dict(road_id=rid,segment_index=j,distance_m=distance,passes=passed,failed_top_regions=sum(not c['passes_existing_surface']for c in checks),protected_contacts=len(contacts),side_contacts=len(side['contacts']),semantic_road_missing_area_m2=roadgap)
   attempts.append(brief)
   if passed:
    chosen=dict(id=r['id']+':PUBLIC_TAIL',source_backbone_id=r['id'],road_id=rid,road_segment_index=j,existing_road_width_m=rw,private_approach_width_m=r['width_m'],floor_y_m=r['floor_y_m'],polyline_xyz_m=[[q[0],r['floor_y_m'],q[1]],[end[0],r['floor_y_m'],end[1]]],polygons_xz_m=polygons,source_top_checks=checks,retained_side_clearance=side,public_overlap_polygons_xz_m=semantic,public_seam_rule='All clipped original public vertices retain their original plane; the extension is exactly level. Existing narrower public lane retains its declared width.',surface_mode='retain_original_source_planes',maximum_inherited_triangle_grade=max(c['max_actual_triangle_grade']for c in checks),maximum_height_departure_from_nominal_m=max(abs(v[y]-r['floor_y_m'])for c in checks for v in c['source_pieces']for y in ('min_y_m','max_y_m')),length_m=distance,status='PASSED_FINITE_SOURCE_GATES_PENDING_BATCH_COMPOSITION');break
  if chosen:out.append(chosen)
  else:failures.append(dict(source_backbone_id=r['id'],attempts=attempts))
  print(r['id'],'PASS'if chosen else'HOLD',attempts[:2],flush=True)
 result=dict(schema='riverstone.r17.public_root_tails.v1',base_scene_sha256=a.SCENE_SHA256,source_layout=dict(path=str((FABRIC/'selected_layout.json').relative_to(a.ROOT)),sha256=a.sha(FABRIC/'selected_layout.json')),source_handoff=dict(path=str((FABRIC/'terrain_handoff.json').relative_to(a.ROOT)),sha256=a.sha(FABRIC/'terrain_handoff.json')),tails=out,held_roots=failures,summary=dict(roots=len(roots),passed=len(out),held=len(failures),seconds=time.monotonic()-t0),activation=False)
 p=folder/'handoff.json';p.write_text(json.dumps(result,separators=(',',':'))+'\n');print(result['summary']);print(a.sha(p))
if __name__=='__main__':run()
