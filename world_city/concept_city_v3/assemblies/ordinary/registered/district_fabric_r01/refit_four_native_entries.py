"""Bounded private-only source entry search; exact finite grade proof is R17/R18.

Sealed sources are read-only. Candidate ribbons carry their complete public
intersection planes and explicit gate changes. No house scaling or compilation.
"""
from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import config
from .activate_backlands_subset import MaskIndex,ActualNative
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as ta
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import public_domain
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
import math,time,heapq,sys

OUT=SOURCE/'hard_core_native_refit_r01/entry_candidates';R17=g.CITY/'registered_topography/revisions/r17_district_batches';R18=g.CITY/'registered_topography/revisions/public_corridors_r18'
IDS=['BLOCK_001:R8_C003','BLOCK_001:R8_C004','BLOCK_003:R8_C003','BLOCK_004:R8_C004']

def rows(polys,kind):return[dict(id=kind+':'+str(i),kind=kind,polygon_xz_m=p)for i,p in enumerate(polys)]
def simplify(line,clear):
 # Exact clearance is tested after this conservative grid line simplification.
 out=[line[0]];i=0
 while i<len(line)-1:
  selected=i+1
  for j in range(len(line)-1,i+1,-1):
   a,b=line[i],line[j];n=max(2,int(math.ceil(math.dist(a,b)/.2)));ok=True
   for t in g.np.linspace(0,1,n):
    z,x=g.cell([a[k]+float(t)*(b[k]-a[k])for k in[0,1]])
    if not(0<=z<g.NZ and 0<=x<g.NX and clear[z,x]):ok=False;break
   if ok:selected=j;break
  out.append(line[selected]);i=selected
 return out

def station_bounds(line,poly):
 out=[];station=0.
 for a,b in zip(line,line[1:]):
  length=math.dist(a,b)
  if length<1e-9:continue
  strip=g.geo.road_ribbon(a,b,20.)
  q=ta.clip(poly,strip)
  if q:
   dd=[((p[0]-a[0])*(b[0]-a[0])+(p[1]-a[1])*(b[1]-a[1]))/length for p in q]
   lo=max(0.,min(dd));hi=min(length,max(dd))
   if hi>=lo:out.append([station+lo,station+hi])
  station+=length
 return out

def route_intervals(line,width,masks):
 result=[];station=0.
 for si,(a,b)in enumerate(zip(line,line[1:])):
  length=math.dist(a,b)
  if length<1e-9:continue
  for r in masks.hit([g.geo.road_ribbon(a,b,width)]):
   ds=[((p[0]-a[0])*(b[0]-a[0])+(p[1]-a[1])*(b[1]-a[1]))/length for p in r['polygon_xz_m']]
   result.append(dict(r,segment_index=si,station_range_m=[station+min(ds),station+max(ds)]))
  station+=length
 return result

class PublicField:
 def __init__(self,records):
  self.records=records;self.index=g.geo._SpatialIndex(8)
  for i,r in enumerate(records):self.index.add(i,r['polygon_xz_m'])
 def at(self,p):
  hits=[self.records[i]for i in self.index.candidates([p])if g.geo.point_in_convex_polygon(p,self.records[i]['polygon_xz_m'],1e-8)]
  if not hits:return None
  ys=[ta.common.height(r['plane_y_xz_m'],p)for r in hits]
  if max(ys)-min(ys)>1e-6:return None
  return dict(point_xz_m=p,y_m=ys[0],source_ids=[r['id']for r in hits],source_planes=[r['plane_y_xz_m']for r in hits])
 def intersection(self,ps):
  out=[]
  for p in ps:
   for i in self.index.candidates(p):
    r=self.records[i];q=ta.clip(p,r['polygon_xz_m'])
    if q and g.geo.polygon_area(q)>1e-8:out.append(dict(r,polygon_xz_m=q))
  return out

def run():
 started=time.monotonic();OUT.mkdir(parents=True,exist_ok=True);budgets={b['id']:b for b in g.load(SOURCE/'hard_core_native_refit_r01/required_core_budget.json')['rows']};extra_retire={'BLOCK_003:R8_C003':{'B_REG_0224','B_REG_0231'}}
 layout=g.load(SOURCE/'hard_core_native_refit_r01/selected_layout_candidate.json');prepared=g.load(R17/'contour_bulk_r01/effective_prepared_parcels_r03.json');manifest=g.load(SOURCE/'effective_city_manifest_r01.json');nextpack=g.load(SOURCE/'coherent_datum_addendum_r01/atomic_datum_addendum.json');back=g.load(SOURCE/'backland_completion_r01/phase02_ownership_correction_r01/resolved_placements_r02.json');scene=g.load(g.CITY/'evidence/r8_district_r04/scene.json');field=PublicField(g.load(R18/'finite_field_candidate_r04_common.json')['records']);sourceplan=g.load(g.CITY/'registered_source/plan.json');roads=sourceplan['roads'];blocks={b['block_id']:b for b in g.load(g.CITY/'registered_integration/r8/coverage_plan/baseline_blocks.json')['blocks']};proj={p['id']:p for p in g.load(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json')['instances']};special=g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];native=ActualNative(scene);allretired=set(manifest['replaced_placement_ids']);publicrows=[dict(r,kind='R18_PUBLIC')for r in public_domain.records()];publicrows+=rows([g.geo.road_ribbon(a,b,r['width_m'])for r in roads for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])],'CANONICAL_TRAFFIC');pub=MaskIndex(publicrows);water=rows([[[v[0],v[2]]for v in scene['surfaces']['water'][i:i+3]]for i in range(0,len(scene['surfaces']['water']),3)],'WATER');refs=dict(layout=g.ref(SOURCE/'hard_core_native_refit_r01/selected_layout_candidate.json'),public_field=g.ref(R18/'finite_field_candidate_r04_common.json'),public_seal=g.ref(R18/'finite_candidate_active23_seal_r01.json'),actual_scene=g.ref(g.CITY/'evidence/r8_district_r04/scene.json'),backlands=g.ref(SOURCE/'backland_completion_r01/phase02_ownership_correction_r01/resolved_placements_r02.json'),next18=g.ref(SOURCE/'coherent_datum_addendum_r01/atomic_datum_addendum.json'),author=g.ref(__file__));result=[]
 # Rebind every other holding to the sealed next18/20 external reservations.
 for ap in ['coherent_datum_addendum_r01/atomic_datum_addendum.json','next20_source_addendum_r01/atomic_source_addendum.json']:
  for rr in g.load(SOURCE/ap)['records']:
   if rr['holding_id']not in IDS:
    for hh in layout['holdings']:
     if hh['id']==rr['holding_id']:hh.update(rr['replacement_holding'])
 for hid in IDS:
  if len(sys.argv)>1 and hid not in sys.argv[1:]:continue
  t0=time.monotonic();h=next(h for h in layout['holdings']if h['id']==hid);hp=h['holding_polygon_xz_m'];floor=h['floor_y_m'];w=h['external_width_m'];block=blocks[hid.split(':')[0]];config(dict(polygon_xz_m=[[min(v[0]for v in hp)-65,min(v[1]for v in hp)-65],[max(v[0]for v in hp)+65,max(v[1]for v in hp)+65]]));window=g.rect(*g.BOUNDS);ownretired=set(h['retired_source_ids']);additional=extra_retire.get(hid,set());oldfloor=floor;budgetrow=budgets[hid];floor_interval=[oldfloor+budgetrow['maximum_required_core_cut_m']-2.5,oldfloor-budgetrow['maximum_required_core_fill_m']+2.5];allowedretired=allretired|additional;readyretired=set(g.load(R17/'contour_bulk_r01/native_pack_ready_r02.json')['replaced_placement_ids']) if False else set()
  # Other planned holdings are hard ownership boundaries. Old ordinary bodies
  # selected for any current district are hypothetically retired only where an
  # explicit new owner/route will be emitted; every encountered ID is recorded.
  hardrows=[]
  for j in native.index.candidates(window):
   r=native.rows[j];pid=r['id']
   if pid.split(':owned_foundation')[0]in allowedretired:continue
   if pid in proj:ps=proj[pid]['native_owner_parts_xz_m']
   elif r.get('box'):ps=[r['polygon_xz_m']]
   else:
    a=r['asset'];key=a['render_sha256']
    if key not in native.cache:native.cache[key]=g.load(g.ROOT/a['render_path'])
    ps=[transform(p,r['placement'])for p in slab_rectangles(native.cache[key],r['asset']['bounds']['min'][1],r['asset']['bounds']['max'][1])]
   hardrows +=[dict(id=pid,kind='RETAINED_NATIVE',polygon_xz_m=p)for p in ps]
  for other in layout['holdings']:
   if other['id']!=hid:hardrows +=[dict(id=other['id'],kind='OTHER_PRIVATE_HOLDING',polygon_xz_m=other['holding_polygon_xz_m'])]
  hardrows+=rows([q for p in layout['placements']for q in p['native_walking_obstacles_xz_m']],'NEW_NATIVE')
  hardrows+=rows([q for p in back['placements']for q in p['native_walking_obstacles_xz_m']],'ACTIVE_BACKLAND_NATIVE')
  hardrows+=rows(special,'SPECIAL_OWNER')+water
  hardrows +=[dict(id=r['id'],kind='PROTECTED_PRECINCT_OR_ESTATE',polygon_xz_m=p)for r in sourceplan['spaces']+[q for q in sourceplan['plots']if q['land_use']=='enclosed_noble_compound']for p in g.triangulate(r['polygon_xz_m'])]
  wall=sourceplan['wall_registration']['polygon_xz_m'];hardrows+=rows(g.ribbons(wall+[wall[0]],24.),'PROTECTED_WALL_SERVICE')
  hardrows +=[dict(id=oh['id'],kind='OTHER_RESERVED_PRIVATE_ENTRY',polygon_xz_m=p)for oh in layout['holdings']if oh['id']not in IDS for p in oh['external_route_polygons_xz_m']]
  hardrows=[r for r in hardrows if g.geo.intersection_area(r['polygon_xz_m'],window)>1e-8]
  hard=MaskIndex(hardrows);hardmask=g.raster([r['polygon_xz_m']for r in hardrows],True);publicmask=g.raster([r['polygon_xz_m']for r in publicrows],True);domain=g.raster(g.triangulate(block['polygon_xz_m']));free=domain&~hardmask&~publicmask;clear=g.ndimage.distance_transform_edt(free)*g.GRID>=w/2+.22
  # Court-connected openings on the finite owner perimeter, including existing gate.
  internal=g.raster([hp])&~hardmask&~publicmask;iclear=g.ndimage.distance_transform_edt(~hardmask&~publicmask)*g.GRID>=w/2+.15
  anchor=g.np.mean(h['core_court_polygons_xz_m'][0],axis=0).tolist();aroot=g.nearest(iclear&internal,anchor,8);labs,n=g.ndimage.label(iclear&internal);lab=labs[aroot]if aroot else 0;court_connected=labs==lab if lab else g.np.zeros(g.SHAPE,bool);gates=[h['gate_position_xz_m']]
  for a,b in zip(hp,hp[1:]+hp[:1]):
   for t in g.np.linspace(.08,.92,max(3,int(math.dist(a,b)/3))):
    q=[a[k]+float(t)*(b[k]-a[k])for k in[0,1]]
    if not hard.hit(g.ribbons([q],w)) and not pub.hit(g.ribbons([q],w)) and g.nearest(court_connected,q,2.5):gates.append(q)
  gates=[q for i,q in enumerate(gates)if not any(math.dist(q,p)<2 for p in gates[:i])]
  anchors=[]
  for road in roads:
   for si,(a,b)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
    if not(g.geo.intersection_area(g.geo.road_ribbon(a,b,road['width_m']+4),window)>0):continue
    ll=math.dist(a,b)
    for tt in g.np.linspace(0,1,max(2,int(math.ceil(ll/2.5))+1)):
     q=[a[k]+float(tt)*(b[k]-a[k])for k in[0,1]];ev=field.at(q)
     if not ev or math.dist(q,anchor)>85:continue
     for sign in[-1,1]:
      end=[q[0]+sign*(b[1]-a[1])/ll*(road['width_m']/2+w/2+1),q[1]-sign*(b[0]-a[0])/ll*(road['width_m']/2+w/2+1)];cell=g.nearest(clear,end,1)
      if cell is None:continue
      end=g.point(cell);tail=g.ribbons([end,q],w)
      if hard.hit(tail):continue
      anchors.append(dict(q=q,end=end,cell=cell,evidence=ev,road_id=road['id'],segment=si))
  anchors.sort(key=lambda r:math.dist(r['end'],anchor)+abs(floor-r['evidence']['y_m'])*8)
  selected=[];diagnostic=dict(gates=len(gates),anchors=len(anchors),attempted=0,reason_counts={})
  def reject(reason):diagnostic['reason_counts'][reason]=diagnostic['reason_counts'].get(reason,0)+1
  for gate in gates[:16]:
   start=g.nearest(clear,gate,1.)
   if start is None:continue
   # Preserve a real internal route from this opening to the existing core.
   goals=g.np.zeros(g.SHAPE,bool);inside=g.nearest(court_connected,gate,2.5)
   if inside:goals[inside]=True
   iline=g.astar(iclear&internal,aroot,goals)if aroot and inside else None
   if not iline:continue
   iline=[anchor]+iline+[gate];iline=simplify(iline,iclear)
   if hard.hit(g.ribbons(iline,w))or pub.hit(g.ribbons(iline,w)):continue
   for an in anchors[:80]:
    diagnostic['attempted']+=1;goals=g.np.zeros(g.SHAPE,bool);goals[an['cell']]=True;ll=g.astar(clear,start,goals)
    if not ll:reject('private_grid_disconnected');continue
    ll=simplify(ll,clear);ll=[gate]+ll+[an['q']];ll=[v for i,v in enumerate(ll)if not i or math.dist(v,ll[i-1])>1e-7];polys=g.ribbons(ll,w)
    if hard.hit(polys):reject('exact_native_owner_clearance');continue
    early=g.ribbons(ll[:-1],w)
    if pub.hit(early):reject('preterminal_public_contact');continue
    pi=route_intervals(ll,w,pub);ci=route_intervals(ll,w,MaskIndex([dict(id=hid,polygon_xz_m=hp)]));first=min((r['station_range_m'][0]for r in pi),default=None);last=max((r['station_range_m'][1]for r in ci),default=0.);budget=first-last if first is not None else 0.
    if budget<1:reject('no_private_grade_length');continue
    fixed=field.intersection(polys);yvalues=[ta.common.height(r['plane_y_xz_m'],p)for r in fixed for p in r['polygon_xz_m']];floor=max(floor_interval[0],min(floor_interval[1],(min(yvalues)+max(yvalues))/2)) if yvalues else oldfloor;rise=max((abs(y-floor)for y in yvalues),default=math.inf);screen=rise/budget
    if screen>.105:reject('bounded_private_rise_budget');continue
    # Retire only explicitly intersected current old bodies, with exact source ledger.
    oldhits=[p['id']for p in proj.values()if p['id']in allowedretired and any(g.geo.intersection_area(q,r)>1e-7 for q in polys for r in p['native_owner_parts_xz_m'])]
    proposal=dict(holding_id=hid,candidate_index=len(selected),original_floor_y_m=oldfloor,required_core_floor_interval_m=floor_interval,proposed_rigid_y_delta_m=floor-oldfloor,additional_retirement_ids=sorted(set(oldhits)&additional),floor_y_m=floor,width_m=w,original_gate_xz_m=h['gate_position_xz_m'],gate_xz_m=gate,gate_changed=math.dist(gate,h['gate_position_xz_m'])>1e-7,internal_court_link_xz_m=iline,internal_court_link_polygons_xz_m=g.ribbons(iline,w),polyline_xz_m=ll,polygons_xz_m=polys,public_road_id=an['road_id'],public_segment=an['segment'],public_target_evidence=an['evidence'],fixed_public_regions=fixed,first_full_width_public_station_m=first,last_fixed_holding_station_m=last,strict_private_rise_length_m=budget,maximum_terminal_height_delta_m=rise,source_average_rise_screen=screen,preterminal_public_overlap_m2=0.,new_native_and_reserved_owner_overlap_m2=0.,encountered_old_retirement_ids=oldhits,status='PRIVATE_ONLY_SOURCE_CANDIDATE_REQUIRES_FINITE_R17_R18_PROFILE')
    if all(math.dist(an['q'],p['public_target_evidence']['point_xz_m'])>4 or math.dist(gate,p['gate_xz_m'])>4 for p in selected):selected.append(proposal);print('CANDIDATE',hid,len(selected),'rise',round(screen,3),'private',round(budget,2),'gate',proposal['gate_changed'],flush=True)
    if len(selected)>=4:break
   if len(selected)>=4:break
  row=dict(holding_id=hid,candidates=selected,diagnostic=diagnostic,seconds=time.monotonic()-t0,status='CANDIDATES_FOR_FINITE_PROFILE'if selected else'HELD_REQUIRES_NATIVE_CORE_OR_COURT_REFIT');g.write(OUT/(hid.replace(':','_')+'.json'),row);result.append(row);print('DONE',hid,row['status'],diagnostic,'seconds',round(row['seconds'],2),flush=True)
 # Run results are accumulated without changing prior district source bytes.
 paths=sorted(OUT.glob('BLOCK_*.json'));rr=[g.load(p)for p in paths];g.write(OUT/'source_candidate_batch.json',dict(schema='riverstone.ordinary.private_entry_source_refit.v1',source_references=refs,requested_holding_ids=IDS,holdings=rr,summary=dict(requested=len(IDS),searched=len(rr),with_source_candidates=sum(bool(r['candidates'])for r in rr),held=sum(not r['candidates']for r in rr),source_candidates=sum(len(r['candidates'])for r in rr),new_compiles=0),limits=['Candidate routes are source proposals; actual finite gradients, public seams, ground-owner topology and retained sides are not accepted here.','Gate changes require atomically regenerated native boundary panels and internal actual-door route chains before activation.','No extra length inside public traffic or fixed flat holding is counted toward private rise.','Original native geometry, caches and every sealed pack remain unchanged. Candidate datums require an atomic native/door/internal-route/bearing addendum after finite acceptance.'],activation=False));print(g.ref(OUT/'source_candidate_batch.json'),flush=True)
if __name__=='__main__':run()
