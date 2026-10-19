"""Read-only exact actual-R8 activation screen for the sealed backland pack.

No old source is rewritten, no geometry compiled, no scene or terrain changed.
All necessary panels in each deliberate enclosure are selected atomically.
"""
from . import geometry as g
from .design import HERE as SOURCE
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as ta,side_clearance
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import public_domain
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
from collections import Counter,defaultdict
import time,math

BASE=SOURCE/'backland_completion_r01';OUT=BASE/'activation_subset_r01'
SCENE=g.CITY/'evidence/r8_district_r04/scene.json'
R17=g.CITY/'registered_topography/revisions/r17_district_batches/contour_bulk_r01'
EXPECTED={'scene':'3c63a21f4490e1dada6be34428dc2d1ffacd326d8f34b2deee81e378ab6680d7','source':'511584b3ce587ac7559e499689787e851f64afcd0b0336ae403a9f585f4a3433','layout':'4b2ce5a6bdc5db51ef2e0cdaef88e265521f8aa0f44ce2b2ca4a0bd97e0accd1','physical':'0106cc825ebaf91e0fa03d2a3db431d3823846c0421a505679e0359bfee4d76a','public':'fcca52f49b1377478e604e2108cde1b0689d6d7f1e65a6df0a087b61941be15e'}
EPS=1e-7

def bind(path,expected=None):
 r=g.ref(path)
 if expected and r['sha256']!=expected:raise ValueError('Changed input '+str(path))
 return r
class MaskIndex:
 def __init__(self,rows):
  self.rows=rows;self.index=g.geo._SpatialIndex(16)
  for i,r in enumerate(rows):self.index.add(i,r['polygon_xz_m'])
 def hit(self,polys):
  out=[]
  for p in polys:
   for j in self.index.candidates(p):
    r=self.rows[j];q=ta.clip(p,r['polygon_xz_m']);area=g.geo.polygon_area(q)if q else 0
    if area>EPS:out.append(dict(id=r['id'],kind=r.get('kind'),area_m2=area,polygon_xz_m=q))
  return out
class ActualNative:
 def __init__(self,scene):
  self.scene=scene;self.rows=[];self.index=g.geo._SpatialIndex(16);self.cache={};self.slabs={};self.refs={}
  for p in scene['common_instances']:
   a=scene['common_assets'][p['asset_key']]
   if 'bounds'not in a:
    path=g.ROOT/a['render_path'];key=a['render_sha256'];self.refs[key]=bind(path,key);self.cache[key]=g.load(path);a=dict(a,bounds=self.cache[key]['bounds'])
   bb=a['bounds'];poly=transform(g.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),p)
   self.index.add(len(self.rows),poly);self.rows.append(dict(id=p['id'],placement=p,asset=a,polygon_xz_m=poly,min_y_m=p['position_m'][1]+bb['min'][1],max_y_m=p['position_m'][1]+bb['max'][1]))
  for p in scene['boxes']:
   x,y,z=p['size_m'];poly=transform(g.rect(-x/2,-z/2,x/2,z/2),p);self.index.add(len(self.rows),poly);self.rows.append(dict(id=p['id'],polygon_xz_m=poly,min_y_m=p['position_m'][1]-y/2,max_y_m=p['position_m'][1]+y/2,box=True))
 def hit(self,polys,low,high):
  out=[];candidateids={i for p in polys for i in self.index.candidates(p)}
  for j in sorted(candidateids):
   r=self.rows[j]
   if r['max_y_m']<=low+1e-8 or r['min_y_m']>=high-1e-8:continue
   if not any(g.geo.intersection_area(p,r['polygon_xz_m'])>EPS for p in polys):continue
   if r.get('box'):parts=[r['polygon_xz_m']]
   else:
    p=r['placement'];a=r['asset'];path=g.ROOT/a['render_path'];key=a['render_sha256']
    if key not in self.cache:
     self.refs[key]=bind(path,key);self.cache[key]=g.load(path)
    lo=low-p['position_m'][1];hi=high-p['position_m'][1];sk=(key,lo,hi)
    if sk not in self.slabs:self.slabs[sk]=slab_rectangles(self.cache[key],lo,hi)
    parts=[transform(q,p)for q in self.slabs[sk]]
   hits=[dict(area_m2=g.geo.intersection_area(p,q),polygon_xz_m=ta.clip(p,q))for p in polys for q in parts if g.geo.intersection_area(p,q)>EPS]
   if hits:out.append(dict(id=r['id'],kind='actual_scene_box'if r.get('box')else'actual_scene_native_solid',low_y_m=low,high_y_m=high,contacts=hits))
  return out

def run():
 started=time.monotonic();OUT.mkdir(exist_ok=True)
 refs=dict(base_scene=bind(SCENE,EXPECTED['scene']),sealed_source_pack=bind(BASE/'resolved_placements.json',EXPECTED['source']),private_layout=bind(R17/'effective_source_layout_r03.json',EXPECTED['layout']),private_physical_reservations=bind(R17/'physical_owner_handoff_r01.json',EXPECTED['physical']),exact_public_intersections=bind(R17/'exact_public_reservations.json',EXPECTED['public']),boundary_source=bind(BASE/'boundary_continuity.json'),terrain_source=bind(BASE/'terrain_handoff.json'),public_domain_sources=public_domain.source_refs(),screen_author=bind(__file__))
 scene=g.load(SCENE);pack=g.load(BASE/'resolved_placements.json');boundary=g.load(BASE/'boundary_continuity.json');terrain=g.load(BASE/'terrain_handoff.json');physical=g.load(R17/'physical_owner_handoff_r01.json');reserved=physical['all_candidate_reservations'];assert len(reserved)==78
 masks=[]
 for r in reserved:
  for kind,polys in [('pending_private_holding',[r['holding_polygon_xz_m']]),('pending_private_entry',r['external_route_polygons_xz_m'])]:
   masks.extend(dict(id=r['id'],kind=kind,polygon_xz_m=p)for p in polys)
 masks += [dict(r,kind='canonical_R18_public')for r in public_domain.records()]
 masks += [dict(id='ACTUAL_WATER:'+str(j//3),kind='actual_water',polygon_xz_m=[[v[0],v[2]]for v in scene['surfaces']['water'][j:j+3]])for j in range(0,len(scene['surfaces']['water']),3)]
 mi=MaskIndex(masks);native=ActualNative(scene);source=pack['placements'];assert len(source)==903
 # The source native masks are also rebound to their existing exact caches.
 for a in pack['assets'].values():bind(g.ROOT/a['render_path'],a['render_sha256'])
 footprints=[q for p in source for q in p['native_foundation_polygons_xz_m']];gates=[q for e in boundary['complete_gated_subyards']for q in e['full_width_gate_access']['polygons_xz_m']];windows=footprints+gates+[q for p in source for q in p['native_walking_obstacles_xz_m']]
 print('Index actual R8 terrain',flush=True);index=ta.TriangleIndex(scene,windows);sides=side_clearance.SideIndex(scene,windows);results=[];kept=[]
 for n,p in enumerate(source):
  a=pack['assets'][p['asset_key']];lo=p['position_m'][1]+a['bounds']['min'][1];hi=p['position_m'][1]+a['bounds']['max'][1];ps=p['native_walking_obstacles_xz_m'];foot=p['native_foundation_polygons_xz_m'];reasons=[]
  maskhit=mi.hit(ps+foot)
  if maskhit:reasons.append('RESERVED_PRIVATE_PUBLIC_OR_WATER_DOMAIN')
  checks=[ta.audit_polygon(index,q,None,grade_limit=math.inf)for q in foot];pieces=[r for c in checks for r in c['source_pieces']];missing=sum(c['missing_area_m2']for c in checks);excess=sum(c['excess_area_m2']for c in checks);mn=min((r['min_y_m']for r in pieces),default=None);mx=max((r['max_y_m']for r in pieces),default=None)
  supported=bool(pieces)and missing<=EPS and excess<=EPS and mn>=lo-EPS and mx<=p['position_m'][1]+EPS
  if not supported:reasons.append('ACTUAL_R8_NATIVE_BEARING_NOT_SUPPORTED_AT_SEALED_POSE')
  contacts=native.hit(ps,lo+1e-5,hi-1e-5)
  if contacts:reasons.append('ACTUAL_R8_NATIVE_OR_FOUNDATION_CONTACT')
  sc=sides.audit([dict(id=p['id'],polygon_xz_m=q,floor_y_m=p['position_m'][1],headroom_m=a['bounds']['max'][1])for q in ps])
  if sc['contacts']:reasons.append('ACTUAL_R8_RETAINED_SIDE_CONTACT')
  row=dict(id=p['id'],ground_owner_id=p['ground_owner_id'],holding_id=p['holding_id'],asset_key=p['asset_key'],status='ACCEPTED_PHYSICAL_NATIVE_SUBSET'if not reasons else'DEFERRED',reasons=reasons,reservation_contacts=maskhit,native_contacts=contacts,retained_side_contacts=sc['contacts'],support=dict(missing_area_m2=missing,excess_area_m2=excess,actual_min_y_m=mn,actual_max_y_m=mx,native_bottom_y_m=lo,ground_datum_y_m=p['position_m'][1],source_pieces=pieces,passes=supported));results.append(row)
  if not reasons:kept.append(p)
  if n%100==0:print(n,'candidate pass',len(kept),flush=True)
 # A court perimeter is never partially promoted. Its full gate stays supported
 # on current actual planes and clear of all later ground/public reservations.
 rowsby={r['id']:r for r in results};keptids={p['id']for p in kept};enclosures=[];remove=set()
 for e in boundary['complete_gated_subyards']:
  gp=e['full_width_gate_access']['polygons_xz_m'];missing=[pid for pid in e['boundary_ids']if pid not in keptids];maskhit=mi.hit(gp);checks=[ta.audit_polygon(index,q,None)for q in gp];pieces=[r for c in checks for r in c['source_pieces']];contacts=[]
  for r in pieces:contacts+=native.hit([r['polygon_xz_m']],r['min_y_m']+.01,r['max_y_m']+2.2)
  sc=sides.audit([dict(id=e['id'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'])for r in pieces]);jumps=[]
  for r in pieces:
   for p in r['polygon_xz_m']:
    ys=[ta.common.height(v['plane_y_xz_m'],p)for v in pieces if g.geo.point_in_convex_polygon(p,v['polygon_xz_m'],1e-7)]
    if ys and max(ys)-min(ys)>.15+1e-7:jumps.append(dict(point_xz_m=p,jump_m=max(ys)-min(ys)))
  ok=not(missing or maskhit or contacts or sc['contacts']or jumps)and all(c['passes_existing_surface']for c in checks)
  row=dict(id=e['id'],ground_owner_id=e['ground_owner_id'],status='COMPLETE_GATED_SUBYARD_NATIVE_ACTIVATION'if ok else'DEFERRED_WHOLE_ENCLOSURE',source=e,missing_boundary_ids=missing,reservation_contacts=maskhit,native_contacts=contacts,side_contacts=sc['contacts'],gate_top_checks=checks,gate_jump_failures=jumps)
  enclosures.append(row)
  if not ok:
   remove.update(e['boundary_ids'])
   for pid in e['boundary_ids']:
    r=rowsby[pid]
    if 'WHOLE_ENCLOSURE_DEPENDENCY'not in r['reasons']:r['reasons'].append('WHOLE_ENCLOSURE_DEPENDENCY')
    r['status']='DEFERRED'
 kept=[p for p in kept if p['id']not in remove];keptids={p['id']for p in kept};deferred=[r for r in results if r['id']not in keptids];complete=[r for r in enclosures if r['status']=='COMPLETE_GATED_SUBYARD_NATIVE_ACTIVATION'];ownerids={p['ground_owner_id']for p in kept};functional={p['holding_id']for p in kept};counts=Counter(p['asset_key']for p in kept);byblock=defaultdict(Counter)
 for p in kept:byblock[p['id'].split(':')[0]][p['asset_key']]+=1
 summary=dict(source_native_placements=len(source),selected_native_placements=len(kept),deferred_native_placements=len(deferred),ground_owners_with_native_use=len(ownerids),named_holdings_with_native_use=len(functional),selected_by_asset=dict(counts),selected_by_block={k:dict(v)for k,v in byblock.items()},complete_gated_subyards=len(complete),deferred_whole_enclosures=len(enclosures)-len(complete),partial_enclosure_panels=0,fully_enclosed_outer_holdings=0,private_holding_reservations=78,public_reservation_records=sum(r['kind']=='canonical_R18_public'for r in masks),new_compilations=0,seconds=time.monotonic()-started)
 g.write(OUT/'reservation_snapshot.json',dict(source_references=refs,reservations=masks,policy='Every current selected or held private source reservation is excluded. Canonical R18 original traffic and fixed retained junction extensions are excluded.'))
 report=dict(schema='riverstone.backland.actual_r8_native_activation_audit.v1',source_references=refs,native_cache_references=list(native.refs.values()),checks=dict(source_ids_partition_exactly=len(kept)+len(deferred)==len(source)and set(r['id']for r in results)=={p['id']for p in source},selected_poses_unchanged=all(p==next(r for r in source if r['id']==p['id'])for p in kept),all_selected_actual_support_and_clear=all(not rowsby[p['id']]['reasons']for p in kept),complete_enclosures_atomic=all(all(pid in keptids for pid in e['source']['boundary_ids'])for e in complete),no_partial_enclosure_rails=all(all(pid in keptids for pid in e['source']['boundary_ids'])or all(pid not in keptids for pid in e['source']['boundary_ids'])for e in enclosures),unit_native_scales=all(p['scale']==[1,1,1]for p in kept)),placements=results,enclosures=enclosures,summary=summary,limits=['This accepts native support/clearance at the sealed poses on actual r8_district_r04. It does not activate pending named holdings or claim their routes have passed.','Parent owns the same-plane ground material/hole composition and integrated runtime review. No new ground floor or terrain edit is emitted here.','Open functional yards remain open; no analytic fragment perimeter panel is promoted.']);report['passed']=all(report['checks'].values());g.write(OUT/'actual_scene_audit.json',report)
 g.write(OUT/'deferred_ledger.json',dict(source=refs['sealed_source_pack'],base_scene=refs['base_scene'],deferred_placements=deferred,deferred_enclosures=[e for e in enclosures if e not in complete],reason_counts=dict(Counter(reason for r in deferred for reason in r['reasons'])),policy='All excluded source placements remain explicitly deferred at unchanged IDs/poses. No source candidate was deleted or silently dropped.'))
 grounds={o['id']:o for o in terrain['material_owners']};selectedground=[]
 for oid in sorted(ownerids):
  o=grounds[oid];selectedground.append(dict(id=oid,named_owner=o['named_owner'],block_id=o['block_id'],planned_function=o['planned_function'],selected_native_ids=[p['id']for p in kept if p['ground_owner_id']==oid],finite_owner_polygons_xz_m=o['finite_owner_polygons_xz_m'],ground_activation_status='PARENT_SAME_PLANE_COMPOSITION_REQUIRED',named_holding_may_remain_pending=True))
 g.write(OUT/'terrain_handoff.json',dict(schema='riverstone.backland.selected_native_ground_dependency.v1',base_scene=refs['base_scene'],source_terrain=refs['terrain_source'],reservation_snapshot=g.ref(OUT/'reservation_snapshot.json'),native_placements=kept,native_footings=[dict(id=p['id'],ground_owner_id=p['ground_owner_id'],polygons_xz_m=p['native_foundation_polygons_xz_m'],bottom_y_m=p['native_bottom_y_m'],ground_datum_y_m=p['position_m'][1])for p in kept],functional_ground_owners=selectedground,complete_gated_subyards=[e['source']for e in complete],retired_native_ids=[],ground_policy='Compose materials on the actual source planes once and subtract selected occupied bottoms. Do not append duplicate floors. The explicit public/private reservations have priority. Terrain material activation remains parent-owned.',implementation_tier='exterior_only'))
 outpack=dict(schema='riverstone.backland.actual_r8_native_activation_subpack.v1',status='SUPPORTED_CLEAR_NATIVE_SUBSET_READY_FOR_PARENT_TERRAIN_INTEGRATION',base_scene=refs['base_scene'],sealed_source=refs['sealed_source_pack'],assets={k:v for k,v in pack['assets'].items()if k in counts},placements=kept,audit=g.ref(OUT/'actual_scene_audit.json'),deferred_ledger=g.ref(OUT/'deferred_ledger.json'),terrain_handoff=g.ref(OUT/'terrain_handoff.json'),reservation_snapshot=g.ref(OUT/'reservation_snapshot.json'),complete_gated_subyards=[e['source']for e in complete],summary=summary,implementation_tier='exterior_only',new_compilations=0,retired_native_ids=[],integration_rules=report['limits']);g.write(OUT/'resolved_placements.json',outpack);g.write(OUT/'manifest.json',dict(pack=g.ref(OUT/'resolved_placements.json'),terrain=g.ref(OUT/'terrain_handoff.json'),audit=g.ref(OUT/'actual_scene_audit.json'),deferred=g.ref(OUT/'deferred_ledger.json'),reservations=g.ref(OUT/'reservation_snapshot.json'),summary=summary));print(summary,flush=True);print(g.ref(OUT/'resolved_placements.json'),flush=True)
if __name__=='__main__':run()
