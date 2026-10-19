"""Apply named residual-ground uses to existing finite, unchanged height planes.

This is material assignment over authored geometry, not a terrain generator.
Missing tops, occupied reservations, water and circulation are never filled.
"""
import collections,copy,time
from .build_scene import a
from ...registered_topography.revisions.r17_district_batches import author as g

PROTECTED={'road','alley','water','bank','space_civic'}
TARGETS={'ground_earth','ground_grass'}

def apply(scene,plan,excluded_polygons=(),unpainted_color_budget_m2=0.):
 start=time.monotonic();pieces=[];idx=g.geo._SpatialIndex(8);excluded_idx=g.geo._SpatialIndex(8)
 for i,p in enumerate(excluded_polygons):excluded_idx.add(i,p)
 for region in plan['regions']:
  for source in region['same_plane_functional_ground']:
   if source['material']in PROTECTED or source['proposed_material']not in TARGETS:raise ValueError('Protected or unsupported material disposition')
   p=source['polygon_xz_m'];cuts=[excluded_polygons[i]for i in sorted(excluded_idx.candidates(p))]
   polygons=g.common.subtract([p],cuts)
   for polygon in polygons:
    if not g.geo.polygon_area(polygon):continue
    row=dict(source,region_id=region['id'],polygon_xz_m=polygon,covered=[])
    idx.add(len(pieces),polygon);pieces.append(row)
 changed={};append=collections.defaultdict(list);proof=[];accepted=0.;existing=0.;max_plane_error=0.;retained_boundary=[];retained_area=0.
 for material,flat in scene['surfaces'].items():
  if material in PROTECTED:continue
  for index in range(len(flat)//3):
   tri=flat[3*index:3*index+3]
   if g.normal_y(tri)<=0:continue
   world_poly=[[v[0],v[2]]for v in tri];candidates=sorted(idx.candidates(world_poly))
   if not candidates:continue
   origin=world_poly[0];local=lambda p:[[v[0]-origin[0],v[1]-origin[1]]for v in p];world=lambda p:[[v[0]+origin[0],v[1]+origin[1]]for v in p];poly=local(world_poly)
   rows=[];claimed=[]
   for k in candidates:
    row=pieces[k];q=g.clip(poly,local(row['polygon_xz_m']))
    if not q or g.geo.polygon_area(q)<=1e-12:continue
    if material not in (row['material'],row['proposed_material']):continue
    plane=row['plane_y_xz_m'];error=max(abs(v[1]-g.common.height(plane,[v[0],v[2]]))for v in tri)
    if error>1e-7:continue
    max_plane_error=max(max_plane_error,error)
    disjoint=g.common.subtract([q],claimed)
    if abs(sum(g.geo.polygon_area(p)for p in disjoint)-g.geo.polygon_area(q))>1e-7:raise ValueError('Overlapping residual dispositions')
    for q in disjoint:
     row['covered'].append(world(q));claimed.append(q);area=g.geo.polygon_area(q)
     if material==row['proposed_material']:existing+=area;continue
     rows.append((k,q));accepted+=area
   if not rows:continue
   cuts=[q for k,q in rows];rest=g.common.subtract([poly],cuts)
   plane=g.common.plane(tri);kept=[t for p in rest for t in g.fan_upward([[v[0],g.common.height(plane,v),v[1]]for v in world(p)])]
   before=g.geo.polygon_area(poly);after=sum(g.geo.polygon_area(p)for p in rest+cuts)
   if abs(before-after)>1e-7:
    # A material-only proposal must never damage an existing top to force a
    # boundary recolor. Preserve this complete source triangle byte-for-byte.
    requested=sum(g.geo.polygon_area(q)for _,q in rows);accepted-=requested;retained_area+=requested
    retained_boundary.append(dict(material=material,triangle_index=index,source_triangle_sha256=g.canonical_sha(tri),source_area_m2=before,requested_material_area_m2=requested,rejected_partition_error_m2=before-after,policy='KEEP_COMPLETE_EXISTING_TOP_AND_MATERIAL; functional source owner only; no target-color completion claim.'))
    continue
   changed[(material,index)]=kept
   for k,q in rows:
    target=pieces[k]['proposed_material'];append[target].extend(v for t in g.fan_upward([[v[0],g.common.height(plane,v),v[1]]for v in world(q)])for v in t)
   proof.append(dict(material=material,triangle_index=index,source_triangle_sha256=g.canonical_sha(tri),reclassified_area_m2=sum(g.geo.polygon_area(q)for _,q in rows),partition_error_m2=abs(before-after)))
 missing=[];source_area=0.
 for row in pieces:
  origin=row['polygon_xz_m'][0];local=lambda p:[[v[0]-origin[0],v[1]-origin[1]]for v in p];world=lambda p:[[v[0]+origin[0],v[1]+origin[1]]for v in p]
  remaining=[world(p)for p in g.common.subtract([local(row['polygon_xz_m'])],[local(p)for p in row['covered']])];area=sum(g.geo.polygon_area(p)for p in remaining);source_area+=g.geo.polygon_area(row['polygon_xz_m'])
  if area>1e-7:missing.append(dict(region_id=row['region_id'],material=row['material'],triangle_index=row['triangle_index'],missing_area_m2=area,polygons_xz_m=remaining))
 unapplied_area=sum(r['missing_area_m2']for r in missing)
 if unapplied_area>unpainted_color_budget_m2:raise ValueError('Residual use has no matching current same-plane source: '+str(missing[:8]))
 out=dict(scene);out['surfaces']={}
 for material,flat in scene['surfaces'].items():
  out['surfaces'][material]=[v for i in range(len(flat)//3)for t in changed.get((material,i),[flat[3*i:3*i+3]])for v in t]
 for material,flat in append.items():out['surfaces'].setdefault(material,[]).extend(flat)
 report=dict(schema='riverstone.r8.same_plane_residual_activation.v1',regions=len(plan['regions']),source_pieces=len(pieces),effective_area_m2=source_area,reclassified_area_m2=accepted,already_target_material_area_m2=existing,conservatively_retained_boundary_material_area_m2=retained_area,retained_complete_boundary_triangles=retained_boundary,unpainted_color_boundary_area_m2=unapplied_area,unpainted_color_boundaries=missing,unpainted_color_budget_m2=unpainted_color_budget_m2,source_triangle_edits=len(changed),maximum_plane_error_m=max_plane_error,source_partitions=proof,new_native_instances=0,new_ground_height=False,new_walkability_claim=False,missing_ground_filled=False,protected_surfaces_unchanged=all(out['surfaces'].get(m)==scene['surfaces'].get(m)for m in PROTECTED),seconds=time.monotonic()-start)
 assert report['protected_surfaces_unchanged'];return out,report

def apply_bound(scene,rows):
 reports=[]
 for ref in rows:
  plan=a.load(a.source_file(ref['path']),ref['sha256']);source=plan['actual_source_scene'];old=a.load(a.source_file(source['path']),source['sha256'])
  for region in plan['regions']:
   for row in region['same_plane_functional_ground']:
    tri=old['surfaces'][row['material']][3*row['triangle_index']:3*row['triangle_index']+3]
    if g.canonical_sha(tri)!=row['source_triangle_sha256']:raise ValueError('Changed disposition source triangle')
  del old
  excluded=[]
  for exclusion in ref.get('exact_exclusions',[]):
   j=a.load(a.source_file(exclusion['path']),exclusion['sha256']);excluded.extend(j['polygons_xz_m'])
  scene,report=apply(scene,plan,excluded,ref.get('unpainted_color_budget_m2',0.));report['source_plan']=ref;reports.append(report)
 return scene,reports
