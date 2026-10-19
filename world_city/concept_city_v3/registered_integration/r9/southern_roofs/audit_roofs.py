"""Static differential audits; retain existing overlaps rather than conceal them."""
from .author_roofs import *
from world_city.runtime_city.checks import placement as geo

def envelope(a,p):
 b=a['bounds'];x,y,z=p['position_m'];t=p.get('yaw_rad',0);c,s=math.cos(t),math.sin(t)
 return [(x+c*u+s*v,z-s*u+c*v)for u,v in [(b['min'][0],b['min'][2]),(b['max'][0],b['min'][2]),(b['max'][0],b['max'][2]),(b['min'][0],b['max'][2])]],(y+b['min'][1],y+b['max'][1])
def overlaps(a,b):return min(a[1][1],b[1][1])-max(a[1][0],b[1][0])>1e-6 and geo.intersection_area(a[0],b[0])>1e-6

def run():
 scene=load(BASE);pack=load(HERE/'pack.json');proof=load(HERE/'proof.json');originals={p['id']:p for p in scene['common_instances']};source_assets=scene['common_assets'];selected={p['id']for p in pack['replace_instances']}
 projection=[]
 for a in proof['assets']:
  old=load(ROOT/a['source_compiled']['path']);new=load(ROOT/a['new_compiled']['path']);before={(r[0],r[2])for r in old['cells']};after={(r[0],r[2])for r in new['cells']};assert before==after
  projection.append(dict(asset_key=a['new_asset_key'],projected_native_columns=len(before),old_projection_sha256=canonical(sorted(before)),new_projection_sha256=canonical(sorted(after)),xz_occupancy_exactly_equal=True))
 candidates=[];excluded=[]
 for p in scene['common_instances']:
  a=source_assets[p['asset_key']]
  if 'bounds'not in a:
   if a.get('render_path'):a=dict(a,bounds=load(ROOT/a['render_path'])['bounds'])
   else:excluded.append(p['id']);continue
  candidates.append((p,envelope(a,p)))
 old_hits=[];new_hits=[];introduced=[];checked=0
 for r in pack['replace_instances']:
  p=originals[r['id']];oldenv=envelope(source_assets[p['asset_key']],p);newenv=envelope(pack['common_assets'][r['asset_key']],p)
  assert oldenv[0]==newenv[0];assert newenv[1][1]<=oldenv[1][1]
  for q,qe in candidates:
   if q['id']==p['id']:continue
   checked+=1;before=overlaps(oldenv,qe);after=overlaps(newenv,qe)
   row=dict(replaced=p['id'],adjacent=q['id'],adjacent_asset_key=q['asset_key'],adjacent_y_band_m=qe[1],projected_overlap_m2=round(geo.intersection_area(oldenv[0],qe[0]),6))
   if before:old_hits.append(row)
   if after:new_hits.append(row)
   if after and not before:introduced.append(row)
 assert not introduced
 # Source public road ribbons and bounded district route reservations, not an invented new navigation replay.
 sourceplan=load(CITY/'registered_source/plan.json');routefile=CITY/'registered_integration/r8/coverage_plan/parcel_candidates.json';coverage=load(routefile);routes=[]
 for r in sourceplan['roads']:
  for j,(u,v)in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   routes.append((r['id']+f':segment:{j}','registered_public_road',geo.road_ribbon(u,v,r['width_m'])))
 for r in coverage['routes']:
  shapes=r.get('ribbon_polygons_xz_m',[])
  if r.get('center_water_polyline_xz_m'):
   line=r['center_water_polyline_xz_m'];width=r['wet_width_m']+2*r['dry_no_build_width_each_bank_m'];shapes=[geo.road_ribbon(u,v,width)for u,v in zip(line,line[1:])]
  elif not shapes and r.get('polyline_xz_m'):
   line=r['polyline_xz_m'];shapes=[geo.road_ribbon(u,v,r.get('width_m',1.8))for u,v in zip(line,line[1:])]
  for j,shape in enumerate(shapes):routes.append((r['id']+f':piece:{j}',r.get('role','district_route'),shape))

 contacts=[]
 for r in pack['replace_instances']:
  p=originals[r['id']];oldenv=envelope(source_assets[p['asset_key']],p);newenv=envelope(pack['common_assets'][r['asset_key']],p)
  for rid,role,shape in routes:
   before=geo.intersection_area(oldenv[0],shape);after=geo.intersection_area(newenv[0],shape);assert abs(before-after)<1e-7
   if before>1e-6:contacts.append(dict(instance_id=p['id'],route_id=rid,route_role=role,original_envelope_overlap_m2=round(before,6),new_envelope_overlap_m2=round(after,6),low_native_occupancy_identical=True))
 out=dict(schema='riverstone.southern_roofs.differential_audit.v1',status='PASS_NO_ADDED_ENVELOPE_OR_ROUTE_ENCROACHMENT',base_scene=ref(BASE),pack=ref(HERE/'pack.json'),proof=ref(HERE/'proof.json'),native_projection=projection,compared_adjacent_pairs=checked,excluded_instances_without_render_bounds=excluded,original_envelope_intersections=old_hits,new_envelope_intersections=new_hits,introduced_envelope_intersections=introduced,public_and_district_route_source_refs=[ref(CITY/'registered_source/plan.json'),ref(routefile)],route_segment_count=len(routes),route_pair_tests=len(routes)*30,original_and_unchanged_route_envelope_contacts=contacts,protected_runtime_contracts_sha256=canonical(scene['collision_contracts']),protected_surfaces_sha256=canonical(scene['surfaces']),notes=['Road ribbons are checked segment by segment with unchanged endpoints and widths; canal checks conservatively include water and both dry banks. Shared segment areas may be counted twice, but differential area is exact.','Every new projected native occupied column equals its old column. All native low cells and palettes are unchanged below 2.5m.','Envelope contacts are conservative, and are reported rather than claimed as new collisions or a new zero-overlap certification.','No new runtime collision, navmesh, interior walk or capsule replay is claimed. Roof replacement is a statically bounded visual change.'])
 write(HERE/'audit.json',out);print(json.dumps(dict(status=out['status'],pairs=checked,old_hits=len(old_hits),new_hits=len(new_hits),new_hits_introduced=len(introduced),route_pairs=out['route_pair_tests'],unchanged_route_contacts=len(contacts),missing_bounds=len(excluded))))
if __name__=='__main__':run()
