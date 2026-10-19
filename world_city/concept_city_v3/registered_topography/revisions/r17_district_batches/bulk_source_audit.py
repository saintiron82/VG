"""Amortized complete finite source proof for one sealed district handoff."""
import json,time
from . import author as a,preflight_layout,side_clearance,native_clearance,retired_access
FABRIC=a.CITY/'assemblies/ordinary/registered/district_fabric_r01'
def run():
 folder=a.HERE/'bulk_b15_r01'
 if folder.exists():raise SystemExit('Preserve previous bulk proof')
 folder.mkdir();start=time.monotonic();hand=json.loads((FABRIC/'terrain_handoff.json').read_bytes());layout=native_clearance.require_ref(hand['layout']);access=native_clearance.require_ref(hand['access']);equipment=native_clearance.require_ref(hand['court_equipment']);native_clearance.require_ref(hand['native_local']);scene=a.load_scene();owners=[]
 for parcel in hand['parcels']:
  for key,kind in [('footing_polygons_xz_m','footing'),('walk_polygons_xz_m','walking'),('court_polygons_xz_m','court'),('whole_holding_polygons_xz_m','holding')]:
   for j,p in enumerate(parcel[key]):owners.append(dict(id=parcel['id']+':'+kind+':'+str(j),parcel_id=parcel['id'],kind=kind,polygon_xz_m=p,floor_y_m=parcel['floor_y_m']))
 windows=[r['polygon_xz_m']for r in owners];index=a.TriangleIndex(scene,windows);actual=len(index.rows);restores,held=preflight_layout.virtual_restorations(index,layout);checks=[]
 for owner in owners:
  proof=a.audit_polygon(index,owner['polygon_xz_m'],owner['floor_y_m']);checks.append(dict(owner,**proof))
 side=side_clearance.SideIndex(scene,windows).audit([o for o in owners if o['kind']in('walking','court')]);retirement=retired_access.build(layout,scene);native=native_clearance.check(layout)
 failed=[c['id']for c in checks if not c['passes_existing_surface']]
 report=dict(schema='riverstone.r17.full_bulk_source_audit.v1',base_scene_sha256=a.SCENE_SHA256,input_handoff=dict(path=str((FABRIC/'terrain_handoff.json').relative_to(a.ROOT)),sha256=a.sha(FABRIC/'terrain_handoff.json')),layout=hand['layout'],access=hand['access'],court_equipment=hand['court_equipment'],native_local=hand['native_local'],top_checks=checks,retained_side_clearance=side,held_retirements=held,native=native,summary=dict(parcels=len(hand['parcels']),holdings=len(layout['holdings']),doors=len(layout['actual_doors']),door_routes=len(access['routes']),finite_regions=len(owners),passing_regions=len(checks)-len(failed),failed_regions=failed,side_contacts=len(side['contacts']),actual_source_triangles=actual,hypothetical_restoration_triangles=len(restores),seconds=time.monotonic()-start),passes_source_gate=not(failed or held or side['contacts']or native['retained_native_conflicts']),remaining=['Seven exact public-tail/interface bindings.','One original-index top/native-hole/retirement partition.','Retained face finite cuts where explicit interface grade changes apply.','Actual scene and unchanged-controller review.'],activation=False)
 for name,d in [('source_audit.json',report),('retirement.json',retirement)]:
  p=folder/name;p.write_text(json.dumps(d,separators=(',',':'))+'\n')
 print(report['summary']);print(a.sha(folder/'source_audit.json'))
if __name__=='__main__':run()
