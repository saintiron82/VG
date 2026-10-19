"""Independent finite sliver diagnosis and new native/private-domain screen."""
from . import geometry as g
from .activate_backlands_subset import ActualNative,MaskIndex
from world_city.concept_city_v3.registered_integration.r8 import compose_finite_patches as c
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
import copy,time

OUT=g.HERE/'backland_completion_r01/joint_source_review_r02'
def run():
 started=time.monotonic();OUT.mkdir(exist_ok=True);bp=g.CITY/'registered_integration/r8/joint_producer_preflight_r02.json';binding=g.load(bp);base=g.load(g.R7)
 jp=g.CITY/'registered_integration/r8/joint_shared_source_audit_r02.json';errors=[r for r in g.load(jp)['errors']if 'R8_NOBLE_SEVEN_FINE_ENTRY_R01'not in r['patch_ids']];wanted={(r['material'],r['triangle_index'])for r in errors};groups={k:[]for k in wanted}
 for ref in binding['patches']:
  assert g.ref(g.ROOT/ref['path'])==ref;patch=g.load(g.ROOT/ref['path'])
  for row in patch['surface_edits']:
   key=(row['material'],row['triangle_index'])
   if key in wanted:groups[key].append((patch['id'],row))
 diagnostics=[]
 for key,rows in sorted(groups.items()):
  source=base['surfaces'][key[0]][key[1]*3:key[1]*3+3];n,length,d,project,unproject=c.project_frame(source);bad=[];clean=copy.deepcopy(rows)
  for pi,(pid,row)in enumerate(rows):
   keep=[]
   for ti,tr in enumerate(row['replacement_triangles_xyz_m']):
    nn=c.cross(c.sub(tr[1],tr[0]),c.sub(tr[2],tr[0]));sign=c.dot(nn,n)
    if sign<=0:
     ar=g.geo.polygon_area([project(v)for v in tr]);bad.append(dict(patch_id=pid,replacement_index=ti,vertices_xyz_m=tr,normal_dot_source=sign,projected_area_m2=ar,area_3d_m2=c.dot(nn,nn)**.5/2,classification='EXACT_ZERO_AREA_REDUNDANT_FACE'if c.dot(nn,nn)==0 else'NUMERIC_COLLAPSE_OR_REVERSED_REQUIRES_PRODUCER_REVIEW'))
    else:keep.append(tr)
   clean[pi][1]['replacement_triangles_xyz_m']=keep
  try:
   normalized,proof=c.compound_row(base,key,clean);error=None
  except Exception as e:proof=None;error=str(e)
  diagnostics.append(dict(material=key[0],triangle_index=key[1],source_triangle_xyz_m=source,invalid_replacement_faces=bad,after_only_invalid_face_removal_passes=error is None,remaining_composition_error=error,composition_proof=proof))
 g.write(OUT/'shared_source_diagnosis.json',dict(binding=g.ref(bp),source_audit=g.ref(jp),source_scene=g.ref(g.R7),author=g.ref(__file__),rows=diagnostics,policy='Read-only diagnosis. No source bytes or compositor acceptance rules changed. Any nonzero-area reversed face remains a producer correction, not an ignored error.'))
 nativepack=g.HERE/'backland_completion_r01/phase02_ownership_correction_r01/resolved_placements_r02.json';pk=g.load(nativepack);newscene=dict(common_assets={},common_instances=[],boxes=[]);packrefs=[]
 extra_path=g.CITY/'registered_topography/revisions/r17_district_batches/coherent_batch20_r01/native_pack_ready_r02.json'
 for r in binding['packs']+[dict(g.ref(extra_path),name='private20')]:
  if r['name']not in ['private23','private18','private20','seven_noble_entries_r01']:continue
  q=g.load(g.ROOT/r['path']);packrefs.append(r)
  if isinstance(q['assets'],list):
   for asset in q['assets']:
    ca=asset['cache'];assert g.ref(g.ROOT/ca['path'])==ca;newscene['common_assets'][asset['id']]=dict(render_path=ca['path'],render_sha256=ca['sha256'])
  else:newscene['common_assets'].update(q['assets'])
  newscene['common_instances']+=q['placements']
 ni=ActualNative(newscene);masks=[];domainrefs=[]
 for sub in ['contour_bulk_r01','coherent_batch18_r01','coherent_batch20_r01']:
  path=g.CITY/'registered_topography/revisions/r17_district_batches'/sub/'physical_owner_handoff_r02.json';q=g.load(path);domainrefs.append(g.ref(path))
  masks +=[dict(id=r['id'],kind=sub+':PHYSICAL_EARTH',polygon_xz_m=r['polygon_xz_m'])for r in q['physical_earth_owners']]
  masks +=[dict(id=r['id'],kind=sub+':BEARING',polygon_xz_m=r['polygon_xz_m'])for r in q['native_earth_bearings']]
 mi=MaskIndex(masks);results=[]
 for i,p in enumerate(pk['placements']):
  aa=pk['assets'][p['asset_key']];lo=p['native_bottom_y_m'];hi=p['position_m'][1]+aa['bounds']['max'][1];ps=p['native_foundation_polygons_xz_m']+p['native_walking_obstacles_xz_m'];nc=ni.hit(ps,lo+1e-7,hi-1e-7);dc=mi.hit(ps);results.append(dict(id=p['id'],native_contacts=nc,physical_private_domain_contacts=dc,passed=not nc and not dc))
  if i%100==0:print('new native',i,'failed',sum(not r['passed']for r in results),flush=True)
 # Adjacent enclosure corners intentionally share their square end posts.
 prior=MaskIndex([]);joints=[]
 for p in pk['placements']:
  for hit in prior.hit(p['native_foundation_polygons_xz_m']):joints.append(dict(id=p['id'],other_id=hit['id'],area_m2=hit['area_m2'],polygon_xz_m=hit['polygon_xz_m'],same_enclosure=p['id'].split(':ENCLOSURE:')[0]==hit['id'].split(':ENCLOSURE:')[0]))
  for poly in p['native_foundation_polygons_xz_m']:
   prior.index.add(len(prior.rows),poly);prior.rows.append(dict(id=p['id'],polygon_xz_m=poly))
 report=dict(source_pack=g.ref(nativepack),integration_binding=g.ref(bp),new_native_packs=packrefs,physical_private_domains=domainrefs,native_cache_references=list(ni.refs.values()),rows=results,intentional_corner_joints=joints,summary=dict(checked_native_instances=len(results),new_native_instances=len(newscene['common_instances']),private_domain_regions=len(masks),native_contact_instances=sum(bool(r['native_contacts'])for r in results),private_domain_contact_instances=sum(bool(r['physical_private_domain_contacts'])for r in results),corner_joints=len(joints),corner_overlap_m2=sum(r['area_m2']for r in joints),seconds=time.monotonic()-started),passed=all(r['passed']for r in results)and all(r['same_enclosure']and abs(r['area_m2']-.015625)<1e-9 for r in joints),policy='Exact native-cache vertical-slab screen plus full physical private earth/bearing reservations. Native support on actual R04 is separately bound; whole composite runtime remains an integration gate.');g.write(OUT/'new_noble_private_native_audit.json',report);print(report['summary'],flush=True);print('PASSED',report['passed'],flush=True);print(g.ref(OUT/'shared_source_diagnosis.json'));print(g.ref(OUT/'new_noble_private_native_audit.json'))
if __name__=='__main__':run()
