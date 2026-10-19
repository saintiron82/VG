"""Actual compiled port cap parity, retained native contact and source regeneration."""
from build import *
def main():
 pack=read(H/'resolved_placements_r02.json');profile=read(H.parent/'side_joins_r01/port_profile_candidate.json');infill=read(H/'native_infill_plan.json');fine=read(ROOT/pack['assets'][1]['cache']['path']);coarse=read(ROOT/pack['assets'][0]['cache']['path']);rect=[];overlap=[];dev=[];spill=[];guard=[]
 for gi,gg in enumerate(coarse['groups']):
  for qi,q in enumerate(gg['quads']):
   ar=np.asarray(q);n=np.cross(ar[1]-ar[0],ar[2]-ar[0])
   if n[1]>0:rect.append([[v[0],v[2]]for v in q])
 maxmissing=0;floors=[]
 for gi,gg in enumerate(fine['groups']):
  for qi,q in enumerate(gg['quads']):
   ar=np.asarray(q);n=np.cross(ar[1]-ar[0],ar[2]-ar[0])
   if n[1]<=0:continue
   poly=[[v[0],v[2]]for v in q];floors.append(poly);missing=g.subtract([poly],[z for z in rect if a.intersects(a.bounds(poly),a.bounds(z))]);maxmissing=max(maxmissing,sum(g.area(z)for z in missing))
   for oldfloor in infill['source_native_floors']:
    op=oldfloor['polygon_local_xz_m']
    if not a.intersects(a.bounds(poly),a.bounds(op)):continue
    z=g.clip(poly,op)
    if z and g.area(z)>1e-9:overlap.append(dict(instance=oldfloor['instance'],new_group=gi,new_quad=qi,old_group=oldfloor['group'],old_quad=oldfloor['quad'],area_m2=g.area(z),new_y_m=q[0][1],old_y_m=oldfloor['local_quad_xyz_m'][0][1]))
   covered=[]
   for r in profile['owners']:
    if not a.intersects(a.bounds(poly),a.bounds(r['polygon_local_xz_m'])):continue
    z=g.clip(poly,r['polygon_local_xz_m'])
    if z and g.area(z)>1e-9:
     covered.append(z);delta=[q[0][1]-a.common.height(r['plane_local_y_xz_m'],v)for v in z];dev.extend(delta)
   spill.extend(g.subtract([poly],covered))
 old=read(H/'cache/registered_port_approach_r01_fine_r02.compiled.json');new=read(ROOT/pack['assets'][1]['compiled']['path']);oc=set(map(tuple,old['cells']));nc=set(map(tuple,new['cells']));removed=sorted(oc-nc);assert not(nc-oc);assert len(removed)==31
 # Source/cache proof uses the unchanged common compiler at each declared pitch.
 regenerated=[]
 for ass in pack['assets']:
  m=read(ROOT/ass['source']['path']);compiled=coordinate_planes.compile_master(m,dict(pitch=ass['pitch_m']),max_candidate_cells=4000000,max_output_cells=1000000);render=render_data.make_render_data(compiled);actual=read(ROOT/ass['compiled']['path']);cached=read(ROOT/ass['cache']['path']);regenerated.append(dict(id=ass['id'],compiled_value_exact=compiled==actual,render_value_exact=render==cached));assert compiled==actual and render==cached
 coplanar=sum(r['area_m2']for r in overlap if abs(r['new_y_m']-r['old_y_m'])<1e-9)
 checks=dict(both_common_regenerations_exact=all(r['compiled_value_exact']and r['render_value_exact']for r in regenerated),all_fine_top_projection_supported=maxmissing<1e-8,no_new_coplanar_native_top_area=coplanar<1e-9,only_31_new_fine_quay_contact_cells_removed=len(removed)==31 and not(nc-oc),fine_visible_error_bounded=max(map(abs,dev))<=.051,new_support_not_above_walking_profile=not read(H/'ownership_requests.json')['coarse_above_walking_profile'],original_native_cache_unchanged=all(sha(ROOT/r['asset']['render_path'])==r['asset']['render_sha256']for r in infill['source_native_refs']))
 report=dict(status='PASS'if all(checks.values())else'HOLD',checks=checks,native_pack=ref(H/'resolved_placements_r02.json'),contract=ref(H/'collision_contract_r02.json'),regenerated=regenerated,removed_new_fine_cells=removed,coplanar_overlap_m2=coplanar,other_native_sampling_contacts=overlap,maximum_fine_support_missing_m2=maxmissing,visible_height_error_range_m=[min(dev),max(dev)],fine_sampling_spill_area_m2=sum(g.area(p)for p in spill),fine_sampling_spill_polygons_local_xz_m=spill,limits=['Native fine sampling spill is a nonwalking border, excluded from the walking profile.','The collision envelope is source-grounded and bounded; structural engineering, live fluid and bridge mechanisms are outside this static exterior completion.'])
 write(H/'native_audit_r02.json',report);print(json.dumps(dict(status=report['status'],checks=checks,visible_error=report['visible_height_error_range_m'],coplanar_area=coplanar)));assert all(checks.values())
if __name__=='__main__':main()
