"""Independent same-plane / native-hole / reserved-route patch audit."""
from . import geometry as g
from .activate_backlands_subset import BASE,MaskIndex
NATIVE=BASE/'phase02_ownership_correction_r01'
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from collections import defaultdict
import time,math,sys
OUT=BASE/(sys.argv[2] if len(sys.argv)>2 else 'activation_patch_review_r02')
PATCH=g.ROOT/sys.argv[1] if len(sys.argv)>1 else g.CITY/'registered_integration/r8/backland_activation_r02/surface_patch.json'

def run():
 started=time.monotonic();patch=g.load(PATCH);scene=g.load(g.R7);native=g.load(NATIVE/'resolved_placements_r02.json');hand=g.load(NATIVE/'terrain_handoff.json');orig=g.load(BASE/'terrain_handoff.json');snapshot=g.load(NATIVE/'reservation_snapshot.json');OUT.mkdir(exist_ok=True)
 assert patch['base_scene_sha256']==g.ref(g.R7)['sha256'];assert len(native['placements'])==835
 feet=[dict(id=p['id'],kind='selected_native_bottom',polygon_xz_m=q)for p in native['placements']for q in p['native_foundation_polygons_xz_m']];fi=MaskIndex(feet);reserved=[r for r in snapshot['reservations']if r['kind']!='actual_water']
 for kind,key in [('retained_access','existing_access_reservations'),('sealed_B15_access','sealed_B15_routes'),('pending_city_access','current_city_route_reservations')]:reserved += [dict(id=kind+':'+str(j),kind=kind,polygon_xz_m=q)for j,q in enumerate(orig[key])]
 ri=MaskIndex(reserved);source=[];index=g.geo._SpatialIndex(8);used=set();fail=[];bykey={};emitted=defaultdict(list);newarea=0.;maxdelta=0.;maximum_source_hash_errors=0
 for r in patch['surface_edits']:
  key=(r['material'],r['triangle_index']);assert key not in used;used.add(key);t=scene['surfaces'][key[0]][key[1]*3:key[1]*3+3];poly=[[v[0],v[2]]for v in t];plane=a.common.plane(t);sha=a.canonical_sha(t)
  if sha!=r['source_triangle_sha256']:fail.append(dict(kind='source_hash',key=key))
  row=dict(key=key,poly=poly,plane=plane,source=t,source_sha=sha);bykey[key]=len(source);index.add(len(source),poly);source.append(row)
  for tr in r['replacement_triangles_xyz_m']:
   q=[[v[0],v[2]]for v in tr];dy=max(abs(v[1]-a.common.height(plane,[v[0],v[2]]))for v in tr);maxdelta=max(maxdelta,dy)
   if dy>1e-7 or a.normal_y(tr)<=0:fail.append(dict(kind='changed_retained_plane_or_orientation',key=key,delta_y_m=dy))
   emitted[len(source)-1].append(q)
 print('indexed',len(source),'original edited tops',flush=True)
 paint_hits=[];foot_hits=[];unbound=[];outside=[];appended_count=0
 for material,vs in patch['appended_surfaces'].items():
  for j in range(0,len(vs),3):
   t=vs[j:j+3];q=[[v[0],v[2]]for v in t];area=g.geo.polygon_area(q);center=[[sum(v[0]for v in q)/3,sum(v[1]for v in q)/3]];matches=[]
   for k in sorted(index.candidates(center)):
    s=source[k]
    if not all(g.geo.point_in_convex_polygon(p,s['poly'],1e-8)for p in q):continue
    dy=max(abs(v[1]-a.common.height(s['plane'],[v[0],v[2]]))for v in t)
    if dy<=1e-7:matches.append((k,dy))
   if not matches:
    # Micrometre-wide inherited triangles have ill-conditioned edge-distance
    # predicates. Exact clipped area is the independent containment fallback.
    for k in sorted(index.candidates(q)):
     ss=source[k];clip=a.clip(q,ss['poly']);ca=g.geo.polygon_area(clip) if clip else 0.;dy=max(abs(v[1]-a.common.height(ss['plane'],[v[0],v[2]]))for v in t)
     if abs(area-ca)<=1e-10 and dy<=1e-7:matches.append((k,dy))
   if not matches:unbound.append(dict(material=material,triangle_index=j//3,vertices_xyz_m=t));continue
   k,dy=matches[0];maxdelta=max(maxdelta,dy);emitted[k].append(q);newarea+=area;appended_count+=1
   if a.normal_y(t)<=0:fail.append(dict(kind='nonupward_new_top',material=material,triangle_index=j//3))
   for r in ri.hit([q]):paint_hits.append(dict(material=material,triangle_index=j//3,**r))
   for r in fi.hit([q]):foot_hits.append(dict(material=material,triangle_index=j//3,**r))
   if appended_count%50000==0:print('checked appended',appended_count,'sec',round(time.monotonic()-started,1),flush=True)
 maxgap=0.;maxexcess=0.;holearea=0.;partitionfails=[];nativecuts=defaultdict(list)
 for k,s in enumerate(source):
  candidates=[(j,feet[j])for j in fi.index.candidates(s['poly'])];holes=[]
  for j,f in candidates:
   q=a.clip(s['poly'],f['polygon_xz_m'])
   if q and g.geo.polygon_area(q)>1e-8:holes.append(q);nativecuts[f['id']].append(q)
  holes=a.common.disjoint_union(holes);ha=sum(g.geo.polygon_area(q)for q in holes);holearea+=ha;expected=g.geo.polygon_area(s['poly']);parts=emitted[k]+holes;actual=sum(g.geo.polygon_area(q)for q in parts);gap=sum(g.geo.polygon_area(q)for q in a.common.subtract([s['poly']],parts));excess=max(0,actual-expected+gap);maxgap=max(maxgap,gap);maxexcess=max(maxexcess,excess)
  if gap>1e-7 or excess>1e-7:partitionfails.append(dict(key=s['key'],missing_m2=gap,excess_m2=excess,original_m2=expected,emitted_plus_holes_m2=actual))
  for q in emitted[k]:
   for r in fi.hit([q]):foot_hits.append(dict(source_key=s['key'],**r))
  if k%10000==0:print('partition',k,'sec',round(time.monotonic()-started,1),flush=True)
 coverage=[];all_source_index=a.TriangleIndex(scene,[f['polygon_xz_m']for f in feet]);inherited_missing=[]
 for p in native['placements']:
  ps=p['native_foundation_polygons_xz_m'];cuts=nativecuts[p['id']];gap_polys=a.common.subtract(ps,cuts);gap=sum(g.geo.polygon_area(q)for q in gap_polys);source_remaining=sum(a.audit_polygon(all_source_index,q,None,grade_limit=math.inf)['covered_area_m2']for q in gap_polys);inherited=max(0.,gap-source_remaining);coverage.append(dict(id=p['id'],footing_area_m2=sum(g.geo.polygon_area(q)for q in ps),actual_source_cut_area_m2=sum(g.geo.polygon_area(q)for q in cuts),unremoved_existing_source_top_area_m2=source_remaining,inherited_missing_source_top_area_m2=inherited,passes=source_remaining<=1e-7));
  if inherited>1e-7:inherited_missing.append(dict(id=p['id'],polygons_xz_m=gap_polys,area_m2=inherited,policy='No R7 source top exists here. Preserve the native occupied hole when composing any independent producer restoration or appended source plane.'))
 badcoverage=[r for r in coverage if not r['passes']];assert patch['removed_foundation_proxy_ids']==[]
 checks=dict(all_source_triangle_hashes_exact=not any(r['kind']=='source_hash'for r in fail),every_emitted_top_on_original_source_plane=maxdelta<=1e-7 and not unbound,original_domains_partition_to_tops_and_only_selected_native_holes=not partitionfails,all_existing_source_tops_under_835_native_bottoms_removed=not badcoverage,no_emitted_top_inside_new_native_bottoms=not foot_hits,no_private_or_public_reserved_route_repaint=not paint_hits,no_old_native_holes_filled=not unbound,old_retained_bearing_preserved_outside_new_native_feet=not partitionfails and not unbound,no_bank_edits_or_appends=not any(r['material']=='bank'for r in patch['surface_edits'])and'bank'not in patch['appended_surfaces'],upward_output_winding=not any('orientation'in r['kind']or r['kind']=='nonupward_new_top'for r in fail),no_retained_foundation_retirements=not patch['removed_foundation_proxy_ids'])
 summary=dict(source_top_edits=len(source),emitted_material_triangles=appended_count,measured_functional_paint_area_m2=newarea,measured_native_bottom_hole_area_m2=holearea,checked_native_instances=len(coverage),inherited_missing_source_native_bottom_area_m2=sum(r['area_m2']for r in inherited_missing),maximum_plane_delta_m=maxdelta,maximum_partition_gap_m2=maxgap,maximum_partition_excess_m2=maxexcess,reserved_route_contacts=len(paint_hits),emitted_top_native_hole_contacts=len(foot_hits),unbound_new_triangles=len(unbound),seconds=time.monotonic()-started)
 report=dict(schema='riverstone.backland.independent_surface_acceptance.v1',patch=g.ref(PATCH),original_source_scene=g.ref(g.R7),actual_native_base_scene=native['base_scene'],native_pack=g.ref(NATIVE/'resolved_placements_r02.json'),actual_native_support_clearance=g.ref(NATIVE/'corrected_actual_scene_audit.json'),reserved_domains=g.ref(NATIVE/'reservation_snapshot.json'),source_material_contract=g.ref(BASE/'terrain_handoff.json'),author=g.ref(__file__),checks=checks,passed=all(checks.values()),summary=summary,native_bottom_checks=coverage,inherited_missing_source_native_bottoms=inherited_missing,failures=dict(source_or_orientation=fail,partitions=partitionfails,unbound_triangles=unbound,reserved_route_contacts=paint_hits,new_top_native_bottom_contacts=foot_hits),integration_limits=['This original-R7-index patch must be geometrically composed with R18/B15/private23 edits; do not apply source-index patches sequentially.','The selected native poses were separately checked against actual r8_district_r04. Their terrain bottoms are intentionally removed here, with support retained as the original solid earth plane.','Final composite sides, route continuity and unchanged-controller review remain integration gates.']);g.write(OUT/'acceptance.json',report);print(summary,flush=True);print('PASSED',report['passed'],flush=True);print(g.ref(OUT/'acceptance.json'),flush=True)
if __name__=='__main__':run()
