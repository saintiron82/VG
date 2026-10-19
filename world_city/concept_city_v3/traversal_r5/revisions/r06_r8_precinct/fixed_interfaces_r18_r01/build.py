"""Copy exact accepted finite profiles and declared exclusions for R18 authoring.
No new road datum, footprint hull, coordinate interpolation or terrain edit.
"""
import collections,hashlib,json,math,pathlib,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));CITY=ROOT/'world_city/concept_city_v3'
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as common
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import landings
from world_city.runtime_city.checks import placement as geo
SOURCES={};REGIONS=[];SEGMENTS=[];EXCLUSIONS=[];OMISSIONS=[];LEDGER=[];SEEN=set()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(path,expected=None):
 p=path if isinstance(path,pathlib.Path)else CITY/path;h=sha(p)
 if expected:assert h==expected,(p,h,expected)
 SOURCES[str(p.relative_to(ROOT))]=h;return json.loads(p.read_bytes())
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def clean_exact(p):
 q=[]
 for v in p:
  if not q or v!=q[-1]:q.append(v)
 if len(q)>1 and q[0]==q[-1]:q.pop()
 assert len(q)>=3 and geo.polygon_area(q)>0
 return q

def add_region(id,p,plane,source,**kw):
 p=clean_exact(p);assert len(plane)==3 and all(math.isfinite(v)for v in plane)
 REGIONS.append(dict(id=id,polygon_xz_m=p,plane_y_xz_m=plane,source=source,**kw))
def add_segment(id,xyz,source,**kw):
 assert len(xyz)==2 and math.dist([xyz[0][0],xyz[0][2]],[xyz[1][0],xyz[1][2]])>1e-10
 SEGMENTS.append(dict(id=id,xyz_m=xyz,source=source,**kw))
def exclude(id,p,source,**kw):EXCLUSIONS.append(dict(id=id,polygon_xz_m=clean_exact(p),source=source,**kw))
def source(path,pointer):return {'path':path,'json_pointer':pointer}
def count(kind):return {'kind':kind,'regions':len(REGIONS),'segments':len(SEGMENTS),'exclusions':len(EXCLUSIONS)}
def main():
 northpath='assemblies/waterworks/registered_bridge/north_approach_r03/profile.json';north=read(northpath);seam=north['sections_world_xyz_m'][0];assert len(seam)==34
 for i,(a,b)in enumerate(zip(seam,seam[1:])):add_segment('NORTH_ACCEPTED_PUBLIC_SEAM:'+str(i),[a,b],source(northpath,f'/sections_world_xyz_m/0/{i}..{i+1}'),kind='accepted_north_native_seam')
 nrpath='assemblies/waterworks/registered_bridge/north_approach_r03/ownership_review.json';nr=read(nrpath)
 for i,p in enumerate(nr['exact_native_footprint_masks_xz_m']):exclude('NORTH_NATIVE:'+str(i),p,source(nrpath,f'/exact_native_footprint_masks_xz_m/{i}'),kind='accepted_native_domain')
 # The exact connector physical domain itself is retained, including the road seam.
 ncpath='assemblies/waterworks/registered_bridge/north_approach_r03/collision_r04/collision_contract.json';nc=read(ncpath)
 for i,t in enumerate(nc['add_triangles_world_xyz_m']):exclude('NORTH_ACCEPTED_PROFILE:'+str(i),[[v[0],v[2]]for v in t],source(ncpath,f'/add_triangles_world_xyz_m/{i}'),kind='retained_collision_profile')
 LEDGER.append(count('north'))
 # Only the seven scene-promoted merchant profiles, never the twelve inactive proposals.
 manifestpath='registered_topography/revisions/r15_merchant_local_patch/public_interfaces/accepted_subset_manifest.json';man=read(manifestpath);assert man['accepted_profile_indices']==[3,11,12,13,15,16,18]
 arp='registered_topography/revisions/r15_merchant_local_patch/subset_07/acceptance_report.json';acc=read(arp)
 for m in man['profiles']:
  path='registered_topography/revisions/r15_merchant_local_patch/public_interfaces/'+m['path'];p=read(path,m['sha256']);assert p['property_id']in acc['accepted_property_ids']
  for i,t in enumerate(p['triangles']):add_region('MERCHANT:'+t['id'],t['polygon_xz_m'],t['plane_y_xz_m'],source(path,f'/triangles/{i}'),kind='accepted_merchant_public_profile',property_id=p['property_id'],triangle_xyz_m=t['vertices_xyz_m'])
  for i,q in enumerate(p['ownership_masks']):exclude('MERCHANT_PROFILE:'+q['id'],q['polygon_xz_m'],source(path,f'/ownership_masks/{i}'),kind='retained_finite_public_profile')
  for i,q in enumerate(p['boundary']):
   if q['kind'].startswith('nonwalkable'):continue
   add_segment('MERCHANT:'+str(p['index'])+':BOUNDARY:'+str(i),q['vertices_xyz_m'],source(path,f'/boundary/{i}'),kind='accepted_merchant_profile_boundary',boundary_kind=q['kind'])
 packpath='registered_topography/revisions/r15_merchant_local_patch/subset_07/merchant_pack.json';pack=read(packpath)
 for i,q in enumerate(pack['ownership_masks']):
  for j,p in enumerate(q['terrain_exclusion_regions_xz_m']):exclude('MERCHANT_NATIVE:'+q['owner_id']+':'+str(j),p,source(packpath,f'/ownership_masks/{i}/terrain_exclusion_regions_xz_m/{j}'),kind='actual_native_foundation',property_id=q['property_id'])
 LEDGER.append(count('merchant'))
 # Both moved working-range public tails are exact existing +2.5 planes.
 wp='registered_topography/revisions/r16_working_ranges/public_interfaces/r6_candidate/level_profile_handoff.json';w=read(wp,'b83e38d8505e9e90c1e7dea2d59163e5771c9f05b65b1c7829ec528f5c916304')
 assert all(t['plane_y_xz_m']==[-0.,-0.,2.5]and all(v[1]==2.5 for v in t['vertices_xyz_m'])for t in w['triangles'])
 for i,q in enumerate(w['regions']):
  add_region(q['id'],q['polygon_xz_m'],[0.,0.,2.5],source(wp,f'/regions/{i}'),kind='accepted_working_range_public_profile',plane_provenance='All1344 exact bound source triangles have this identical plane.')
  exclude('WORKING_PROFILE:'+q['id'],q['polygon_xz_m'],source(wp,f'/regions/{i}'),kind='retained_finite_public_profile')
 for i,r in enumerate(w['full_width_profiles']):
  for j,q in enumerate(r['public_road_terminal']['pieces']):add_segment('WORKING_TERMINAL:'+str(i)+':'+str(j),q['vertices_xyz_m'],source(wp,f'/full_width_profiles/{i}/public_road_terminal/pieces/{j}'),kind='accepted_working_range_public_terminal')
 wcpath='registered_topography/revisions/r16_working_ranges/contract.json';wc=read(wcpath)
 for field in ['native_range_footing_holes','court_native_bearing_cuts']:
  for i,q in enumerate(wc[field]):exclude('WORKING_NATIVE:'+q['id'],q['polygon_xz_m'],source(wcpath,f'/{field}/{i}'),kind='actual_native_bearing')
 LEDGER.append(count('working_ranges'))
 # Recovered actual institutional landing boundary triangles and exact linear edges.
 lp='validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json';ld=read(lp)
 lmod=pathlib.Path(landings.__file__);SOURCES[str(lmod.relative_to(ROOT))]=sha(lmod)
 boundaries=landings.boundary_segments();tri_by_edge={}
 for i,t in enumerate(ld['landings']['triangles']):
  xyz=t['triangle_xyz_m']
  for a,b in zip(xyz,xyz[1:]+xyz[:1]):tri_by_edge.setdefault(tuple(sorted([tuple(a),tuple(b)])),[]).append((i,t))
 picked={}
 for i,b in enumerate(boundaries):
  xyz=[b['a_xyz_m'],b['b_xyz_m']];key=tuple(sorted([tuple(v)for v in xyz]));assert key in tri_by_edge
  ti,t=tri_by_edge[key][0];picked[ti]=t
  add_segment('INSTITUTION_BOUNDARY:'+str(i),xyz,source(lp,f'/landings/triangles/{ti}'),kind='recovered_actual_landing_boundary',group_id=b['group_id'],derivation='Existing sealed recovery_support.landings.boundary_segments; endpoints copied verbatim from actual recovered triangle.')
 for i,t in sorted(picked.items()):add_region('INSTITUTION_TERMINAL:'+t['owner_id'],t['polygon_xz_m'],common.plane(t['triangle_xyz_m']),source(lp,f'/landings/triangles/{i}'),kind='recovered_actual_boundary_triangle',group_id=t['group_id'],triangle_xyz_m=t['triangle_xyz_m'],support_status=t.get('support_status'))
 # Exact rendered triangle footprints avoid widening a recovered broad mask into a missing sliver.
 for i,t in enumerate(ld['landings']['triangles']):exclude('INSTITUTION_LANDING:'+t['owner_id'],t['polygon_xz_m'],source(lp,f'/landings/triangles/{i}'),kind='retained_actual_public_landing')
 # Approaches use the already recovered exact-union convex mask decomposition.
 for i,q in enumerate(ld['approaches']['masks']):exclude('INSTITUTION_APPROACH:'+str(i),q['polygon_xz_m'],source(lp,f'/approaches/masks/{i}'),kind='retained_actual_institutional_approach',group_id=q['group_id'])
 LEDGER.append(count('institutional'))
 # Ready static precinct entries. Preserve the failed park endpoint separately.
 pp='assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/public_entry_interfaces_r18.json';pd=read(pp,'c990aa71f46150801740fb93ca04631f63328bc90baf9f21487343be35c5e171')
 for i,q in enumerate(pd['interfaces']):
  if q['status'].startswith('FAILED'):
   OMISSIONS.append(dict(id=q['id'],source=source(pp,f'/interfaces/{i}'),reason=q['status'],data=q));continue
  for j,r in enumerate(q.get('terminal_actual_regions',[])):add_region('PRECINCT:'+q['id']+':TERMINAL:'+str(j),r['polygon_xz_m'],r['plane_y_xz_m'],source(pp,f'/interfaces/{i}/terminal_actual_regions/{j}'),kind='accepted_static_precinct_terminal',status=q['status'])
  if q.get('continuation_last_actual_triangle'):
   r=q['continuation_last_actual_triangle'];add_region('PRECINCT:'+q['id']+':CONTINUATION',r['polygon_xz_m'],r['plane_y_xz_m'],source(pp,f'/interfaces/{i}/continuation_last_actual_triangle'),kind='accepted_static_precinct_public_continuation',status=q['status'])
  if q.get('terminal_polygon_xz_m'):add_region('PRECINCT:'+q['id'],q['terminal_polygon_xz_m'],[0.,0.,q['floor_y_m']],source(pp,f'/interfaces/{i}'),kind='static_training_terminal_controller_pending',status=q['status'])
 LEDGER.append(count('precinct'))
 # Hash-bind existing executable proof, not stale producer active:false flags.
 for path in [H.parent/'north_connector_r02/freeze_manifest.json',CITY/'traversal_r5/revisions/r04_r6_apron_replay/freeze_manifest.json',CITY/'traversal_r5/revisions/r05_r7_working_ranges/freeze_manifest.json']:
  if path.exists():SOURCES[str(path.relative_to(ROOT))]=sha(path)
 ids=[q['id']for q in REGIONS+SEGMENTS+EXCLUSIONS];assert len(ids)==len(set(ids)),'Duplicate interface ID'
 for path,h in SOURCES.items():assert sha(ROOT/path)==h,'Source changed during extraction'
 slopes=[dict(id=r['id'],grade=math.hypot(*r['plane_y_xz_m'][:2]))for r in REGIONS]
 slopes+= [dict(id=r['id'],grade=abs(r['xyz_m'][1][1]-r['xyz_m'][0][1])/math.dist([r['xyz_m'][0][0],r['xyz_m'][0][2]],[r['xyz_m'][1][0],r['xyz_m'][1][2]]))for r in SEGMENTS]
 out=dict(schema='riverstone.r18.exact_fixed_interfaces.v1',status='EXACT_FIXED_INPUTS_PENDING_R18_COMPATIBILITY_AND_COMPOSITION',regions=REGIONS,segments=SEGMENTS,exclusions=EXCLUSIONS,sources=[dict(path=p,sha256=h)for p,h in sorted(SOURCES.items())],group_counts_cumulative=LEDGER,north_seam_knots_world_xyz_m=seam,omitted_unaccepted_profiles=OMISSIONS,fixed_gradient_review=dict(maximum=max(v['grade']for v in slopes),above_11_percent=[r for r in slopes if r['grade']>.11+1e-8],above_12_percent=[r for r in slopes if r['grade']>.12+1e-7]),limits=['Exact static constraints, not a new traversal claim.','Current B15 and noble anchors are already bound separately by parent; not duplicated here.','Known explicit native exclusions include north connector, seven merchant foundations and working-range/court bearings. Other retained native holes must still be preserved from the composed actual scene.','Recovered institutional exclusions reserve actual rendered domains; support_status remains unverified_visible_top_only where recorded.','The failed park/common endpoint is omitted from accepted regions and preserved as a pending repair record.','Existing source coordinates and planes copied; only exact duplicate consecutive/closing polygon vertices removed. No rounded hulls, resampled heights or invented route points.','Do not enforce an11% limit on accepted fixed12% planes; report incompatibilities and choose an explicit local bound.'])
 with(H/'fixed_interfaces.json').open('x')as f:json.dump(out,f,separators=(',',':'),allow_nan=False);f.write('\n')
 print(json.dumps({'output':ref(H/'fixed_interfaces.json'),'regions':len(REGIONS),'segments':len(SEGMENTS),'exclusions':len(EXCLUSIONS),'sources':len(SOURCES),'maximum_fixed_grade':out['fixed_gradient_review']['maximum'],'over_11':len(out['fixed_gradient_review']['above_11_percent']),'over_12':len(out['fixed_gradient_review']['above_12_percent']),'omitted':[q['id']for q in OMISSIONS]}))
if __name__=='__main__':main()
