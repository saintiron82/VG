"""Court equipment and route-cut enclosures, using unchanged native common grammar."""
import copy,itertools
from ..design import *
from ..access import ribbons
from world_city.runtime_city.parts.author import Source,extrusion,make_master as part_master
from world_city.runtime_city.checks import placement as geo
from voxel_character.common import core,coordinate_planes
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles
PARENT=HERE;HERE=PARENT/'court_phase01';PITCH=.125
R6=CITY/'evidence/visual_registered_common_r6_apron_r01/scene.json'
R6_HASH='6e441b9ca417db63dccbb0bbccd48aa59e6a2a62079cdeeb3e5440d78f654844'

def inv(poly,c):return [xform([p[0]-c['center'][0],p[1]-c['center'][1]],[0,0],-c['yaw'])for p in poly]
def transformed(polys,center,yaw):return [[xform(q,center,yaw)for q in p]for p in polys]
def count(m):
 resolved,_=coordinate_planes.resolve_master(m,{'pitch':PITCH})
 count=0;cs={c['id']:c for c in resolved['components']}
 for i in resolved['instances']:
  tr=core.transform(i.get('transform'))
  for o in cs[i['component']]['operations']:
   shp=core.prepare_shape(o['shape'],PITCH);lo,hi=core.shape_bounds(shp);t=core.compose(tr,core.transform(o.get('transform')));corners=[core.apply(t,q)for q in itertools.product(*zip(lo,hi))];a=[min(q[k]for q in corners)for k in range(3)];b=[max(q[k]for q in corners)for k in range(3)];count+=math.prod(math.ceil(y/PITCH-core.EPS)-math.floor(x/PITCH+core.EPS)for x,y in zip(a,b))
 return count

def source(id,lo,hi):return Source(id,lo,hi)
def finalize(a):
 m=a.finish();m['provenance'].update(court_phase_author=ref(Path(__file__)),range_pack=ref(PARENT/'resolved_placements.json'),policy='No paving plane, unit scale, unchanged common compiler. Equipment is fictional dimension-authored use, not character interaction or structural approval.');m['extensions']['status']='staged_court_equipment_and_boundaries';return m

def new_masters():
 a=source('court_domestic_wash_barrel',[-1.5,-.25,-.5],[1.25,1.125,.5]);a.box('wash_base',[-1.5,-.25,-.5],[0,.25,.5],'stone_dark')
 a.box('wash_basin',[-1.5,.125,-.5],[0,.875,.5],'stone_light');a.box('open_bowl',[-1.375,.25,-.375],[-.125,1,.375],action='cut')
 a.box('wash_board',[-1.25,.875,-.5],[-.25,1,-.375],'timber_light',component='wash_board')
 barrel=part_master('cargo_barrel')
 for c in barrel['components']:
  for o in c['operations']:
   a.op('barrel_'+o['id'],copy.deepcopy(o['shape']),o.get('material','timber'),component='barrel_'+c['id'],transform={'translation':[.75,0,0]},action=o['action'])
 a.support('basin_bottom',[-1.5,-.25,-.5],[0,-.125,.5],'Exact below-ground native basin base; finite R16 owner cut required.')
 a.support('barrel_base',[.4,0,-.35],[1.1,.125,.35],'Original +2.5 m court plane; no new water or drainage connection.')
 m=finalize(a);m['provenance']['barrel_source_factory']=ref(ROOT/'world_city/runtime_city/parts/author.py');m['extensions']['functional_scope']='Shared hand-filled wash vessel and closed water barrel. No pipe, discharge, pumping or drinkability claim.';yield 'domestic_wash_barrel',m
 a=source('court_dry_work_rack_store',[-1.5,-.25,-.25],[1.5,2.25,.75])
 for j,x in enumerate((-1.375,1.375)):a.box('rack_post_'+str(j),[x-.125,-.25,.375],[x+.125,2.25,.625],'timber_dark',component='rack')
 for j,y in enumerate((1.125,1.625,2.125)):a.box('rack_rail_'+str(j),[-1.5,y,.375],[1.5,y+.125,.625],'timber',component='rack')
 for j in range(4):a.box('stored_timber_'+str(j),[-1.25,1.25+j*.1875,.125],[1.25,1.375+j*.1875,.375],'timber_light'if j%2 else'timber',component='rack')
 a.box('lockable_store',[-.75,-.125,-.25],[.75,.625,.25],'timber',component='storage');a.box('store_hollow',[-.625,0,-.125],[.625,.5,.126],action='cut',component='storage');a.box('closed_store_front',[-.625,0,-.25],[.625,.5,-.125],'timber_light',component='storage');a.box('latch',[-.125,.25,-.3125],[.125,.375,-.125],'iron',component='storage')
 m=finalize(a);m['extensions']['functional_scope']='Shared timber rack and lockable tool chest below the separately reused 2.5 m workbench; source spatial fit preserves circulation.';yield 'dry_work_rack_store',m

def fence(c,protected):
 w,d=c['dimensions'];a=source('court_boundary_'+c['short'],[-w/2,-.25,-d/2],[w/2,1.25,d/2]);segments=[];openings=[]
 for edge,(axis,station,lo,hi)in enumerate([(0,-d/2+.125,-w/2+.25,w/2-.25),(0,d/2-.125,-w/2+.25,w/2-.25),(1,-w/2+.125,-d/2+.25,d/2-.25),(1,w/2-.125,-d/2+.25,d/2-.25)]):
  ticks=[lo+i*.25 for i in range(round((hi-lo)/.25)+1)];states=[]
  for l,r in zip(ticks,ticks[1:]):
   poly=rect(l-.125,station-.25,r+.125,station+.25)if axis==0 else rect(station-.25,l-.125,station+.25,r+.125)
   states.append(not any(geo.intersection_area(poly,p)>1e-9 for p in protected))
  runs=[];start=0
  for j in range(1,len(states)+1):
   if j==len(states)or states[j]!=states[start]:runs.append((ticks[start],ticks[j],states[start]));start=j
  for ri,(l,r,free)in enumerate(runs):
   if not free or r-l<.5:
    openings.append(dict(edge=edge,axis=axis,station=station,start=l,end=r,clear_width_m=r-l,role='protected_route_opening'if not free else'short_unbuilt_boundary_fragment',native_leaf='none: deliberate open portal, no animated gate'))
    continue
   def lohi(l,r,y0,y1,thick=.125):return ([l,y0,station-thick],[r,y1,station+thick])if axis==0 else([station-thick,y0,l],[station+thick,y1,r])
   for rail,y0,y1 in [('lower',.375,.625),('upper',1,1.25)]:a.box(f'e{edge}_r{ri}_{rail}',*lohi(l,r,y0,y1),'timber',component='boundary')
   n=max(1,math.ceil((r-l)/1.5));posts=[l+.125+(r-l-.25)*j/n for j in range(n+1)]
   for j,t in enumerate(posts):a.box(f'e{edge}_r{ri}_post{j}',*lohi(t-.125,t+.125,-.25,1.25),'timber_dark',component='boundary')
   segments.append(dict(edge=edge,start=l,end=r,station=station,axis=axis,native_endpoint_posts_local_xz_m=[[l+.125,station],[r-.125,station]]if axis==0 else[[station,l+.125],[station,r-.125]],length_m=r-l))
 m=finalize(a);m['extensions'].update(boundary_segments=segments,opening_intervals=openings,no_floor_geometry=True,design='Low shared-yard enclosure with source-tested open portals at every reserved approach crossing. Endpoint posts form actual opening jambs; no fence blocks an access ribbon.');return m

def run():
 assert ref(R6)['sha256']==R6_HASH;courts=load(PARENT/'court_plan.json')['courts'];paths=load(PARENT/'access_handoff.json');cs=[]
 for j,c in enumerate(courts):
  center=[sum(q[k]for q in c['polygon_xz_m'])/4 for k in(0,1)];q=dict(source=c,id=c['id'],center=center,yaw=math.radians(-48),dimensions=[8,5]if j==0 else[10,7],short='domestic'if j==0 else'work');q['protected_local_polygons']=[]
  for r in paths['internal_routes']+paths['external_routes']+[c['access_link']]:
   if r.get('holding_id',c['holding_id'])!=c['holding_id']:continue
   q['protected_local_polygons'] += [inv(p,q) for p in r['ribbon_and_join_polygons_xz_m']]
  if j==1: q['protected_local_polygons'] += [inv(p,q) for p in ribbons([[234.75,180.75],[235.25,181.75]],2)]
  cs.append(q)
 variants={}
 for key,m in list(new_masters())+[(c['short']+'_boundary',fence(c,c['protected_local_polygons']))for c in cs]:
  p=HERE/'masters'/f'{key}.json';write(p,m);cost=count(m);assert cost<200000;variants[key]=dict(master=ref(p),predicted_candidate_visits=cost,candidate_cap=200000,output_cap=60000,pitch_m=PITCH)
 prior=load(CITY/'assemblies/property/registered/b13_workyards_r1/resolved_placements.json')['assets'];reuse={'drying_frame':prior['b13_workyard_drying_frame']};cache=load(ROOT/'world_city/runtime_city/generated/r2/fabric_cache/uf_workbench_4d91d514c111fd.json');reuse['workbench']={k:cache[k]for k in ('master_path','master_sha256','render_path','render_sha256','bounds','pitch_m','quad_count')}
 for a in reuse.values():
  for k in('master','render'):assert ref(ROOT/a[k+'_path'])['sha256']==a[k+'_sha256']
 placements=[dict(id='DOMESTIC_BOUNDARY',court_id=cs[0]['id'],asset_key='domestic_boundary',local_center_xz_m=[0,0],local_yaw_rad=0),dict(id='DOMESTIC_DRYING_FRAME',court_id=cs[0]['id'],asset_key='drying_frame',local_center_xz_m=[-.5,1.5],local_yaw_rad=0),dict(id='DOMESTIC_WASH_BARREL',court_id=cs[0]['id'],asset_key='domestic_wash_barrel',local_center_xz_m=[-2,-1.25],local_yaw_rad=0),dict(id='WORK_BOUNDARY',court_id=cs[1]['id'],asset_key='work_boundary',local_center_xz_m=[0,0],local_yaw_rad=0),dict(id='SHARED_WORKBENCH',court_id=cs[1]['id'],asset_key='workbench',local_center_xz_m=[-.75,2.5],local_yaw_rad=0),dict(id='TIMBER_RACK_AND_STORE',court_id=cs[1]['id'],asset_key='dry_work_rack_store',local_center_xz_m=[-.75,2.5],local_yaw_rad=0)]
 out=dict(schema='riverstone.court_phase01.source_plan.v1',source=ref(Path(__file__)),sealed_parent_pack=ref(PARENT/'resolved_placements.json'),sealed_parent_manifest=ref(PARENT/'freeze_manifest.json'),corrected_r6=ref(R6),source_courts=ref(PARENT/'court_plan.json'),source_access=ref(PARENT/'access_handoff.json'),courts=cs,placements=placements,reused_assets=reuse,no_native_paving=True,terrain_owner='R16 original +2.5 m corrected-R6 court triangles, stone material only; exact native bearing masks supplied after compile',unimplemented=['Animated gates and props','Water fill, wash drainage, clean-water pipe or supply connection','NPC/character interaction and navigation'])
 write(HERE/'source_plan.json',out);b=dict(schema='riverstone.court_phase01.compile_budget.v1',source_plan=ref(HERE/'source_plan.json'),variants=variants,summary=dict(new_sources=len(variants),reused_native_assets=len(reuse),total_candidate_visits=sum(v['predicted_candidate_visits']for v in variants.values()),largest_candidate_visits=max(v['predicted_candidate_visits']for v in variants.values()),pitch_m=PITCH,no_new_paving=True,sequential=True));write(HERE/'compile_budget.json',b);print(json.dumps(b['summary'],indent=2));return b
if __name__=='__main__':run()
