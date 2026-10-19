"""One batch of contour-aware private court datums and bounded public approaches."""
from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import config,PublicSamples
import types,shutil

def run():
 plan=g.CITY/'registered_integration/r8/coverage_plan';terr=g.CITY/'registered_topography/revisions/r17_district_batches';budget=g.load(terr/'city_coherent_budget_r01/terrain_budget.json');blocks={b['block_id']:b for b in g.load(plan/'baseline_blocks.json')['blocks']};base=g.np.load(plan/'baseline_masks.npz');scene=g.load(g.R7);samples=PublicSamples(scene);roads=g.load(g.CITY/'registered_source/plan.json')['roads'];special=g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];mill=g.load(SOURCE/'coherent_regrade_r01/mill_reservation_check.json')['protected_regions'];oldrows=g.load(terr/'all_blocks_r01/retirement_candidates.json')['rows'];projection={i['id']:i for i in g.load(plan/'native_projection.json')['instances']};results=[];roadpoints=[]
 for road in roads:
  for si,(a,b)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   length=g.math.dist(a,b)
   for t in g.np.linspace(0,1,max(2,int(g.math.ceil(length/3))+1)):
    q=[a[k]+float(t)*(b[k]-a[k])for k in[0,1]];ev=samples.at(q)
    if ev:roadpoints.append((q,ev,road,si))
 for bid in sorted({r['block_id']for r in budget['rows']if r['status']!='MODEST_FINITE_REGRADE_SOURCE_CANDIDATE'and r['block_id']!='BLOCK_007'}):
  config(blocks[bid]);original=SOURCE/'coherent_regrade_r01'/bid;out=SOURCE/'contour_revision_r01'/bid;out.mkdir(parents=True,exist_ok=True);g.HERE=out
  for name in['native_local.json','compile_report.json','owner_route_source_snapshot.json']:(out/name).write_bytes((original/name).read_bytes())
  l=g.load(original/'selected_layout.json');l['supersedes_source']=g.ref(original/'selected_layout.json');l['native_local']=g.ref(out/'native_local.json');x=((g.XS-float(base['bounds'][0]))/float(base['pitch'])).astype(int);z=((g.ZS-float(base['bounds'][1]))/float(base['pitch'])).astype(int);ms={k:base[k][g.np.ix_(z,x)]for k in base.files if base[k].ndim==2};domain=g.raster(g.triangulate(blocks[bid]['polygon_xz_m']));hard=g.np.logical_or.reduce([ms[k]for k in['spaces','estates','water','wall','retained_native','retained_access']])|g.raster(special+[v['polygon']for v in mill],True);obstacles=g.raster([q for p in l['placements']for q in p['native_walking_obstacles_xz_m']],True);rows=[r for r in oldrows if r['block_id']==bid];updates=[]
  for r in[r for r in budget['rows']if r['block_id']==bid and r['status']!='MODEST_FINITE_REGRADE_SOURCE_CANDIDATE']:
   h=next(h for h in l['holdings']if h['id']==r['id']);gate=h['gate_position_xz_m'];low=r['actual_source_min_y_m'];high=r['actual_source_max_y_m'];median=r['weighted_centroid_height_quantiles_m']['0.5'];width=h['external_width_m'];free=(domain|ms['road'])&~hard&~obstacles
   for oh in l['holdings']:
    if oh['id']!=h['id']:free&=~g.raster([oh['holding_polygon_xz_m']],True)
   clear=g.ndimage.distance_transform_edt(free)*g.GRID>=width/2+.3;start=g.nearest(clear,gate,3);choices=[]
   for q,ev,road,si in roadpoints:
    dist=g.math.dist(gate,q)
    if dist>65 or road['width_m']+1e-6<width:continue
    # Prefer the local terrain band; exact public target carries its own retained
    # height. A bounded private profile is needed whenever these differ.
    target=max(low+min(2.5,(high-low)/2),min(high-min(2.5,(high-low)/2),median))if high-low>5 else max(high-2.5,min(low+2.5,ev['y_m']))
    dy=abs(target-ev['y_m'])
    if dy>max(1.,dist*.10):continue
    score=3*abs(target-median)+max(high-target,target-low)+.06*dist+dy*2
    choices.append((score,q,ev,road,si,target))
   choices.sort(key=lambda v:v[0]);accepted=None
   for score,q,ev,road,si,floor in choices[:45]:
    end=g.nearest(clear,q,2.5);goals=g.np.zeros(g.SHAPE,bool)
    if end:goals[end]=True
    direct=g.ribbons([gate,q],width);line=[gate,q]if not g.np.any(g.raster(direct,True)&~free)else(g.astar(clear,start,goals)if start and end else None)
    if not line:continue
    line=[gate]+line+[q];line=[q for i,q in enumerate(line)if not i or g.math.dist(q,line[i-1])>1e-7];length=sum(g.math.dist(a,b)for a,b in zip(line,line[1:]));grade=abs(floor-ev['y_m'])/max(.001,length-width)
    if grade>.105:continue
    rp=g.ribbons(line,width)
    if any(g.geo.intersection_area(p,q)>1e-6 for p in rp for pp in l['placements']for q in pp['native_walking_obstacles_xz_m']):continue
    ids={rr['source_id']for rr in rows if any(g.geo.intersection_area(rr['actual_native_outer_footprint_xz_m'],p)>1e-7 for p in rp)};newids=ids-set(l['retired_source_ids']);newretire=sum(projection[i]['roof_area_m2']for i in newids)
    if newretire>l['summary']['net_ordinary_roof_gain_m2']*.5+1e-6:continue
    accepted=(floor,line,rp,road,ev,si,length,grade,ids);break
   if not accepted:updates.append(dict(id=h['id'],status='NEEDS_OWNED_LONGER_APPROACH_OR_NATIVE_REFIT',old_budget=r));continue
   floor,line,rp,road,ev,si,length,grade,ids=accepted;oldfloor=h['floor_y_m'];delta=floor-oldfloor;h.update(floor_y_m=floor,external_route=line,external_route_polygons_xz_m=rp,public_road_id=road['id'],public_target_xz_m=ev['point_xz_m'],public_target_evidence=ev,cluster_id=h['id']+':CONTOUR',retired_source_ids=sorted(set(h['retired_source_ids'])|ids),court_datum_evidence=dict(floor_y_m=floor,terrain_height_budget=r,chosen_public_anchor=dict(ev,public_road_id=road['id'],segment=si),profile_centerline_grade=grade,policy='Preserve concept hill through a local court terrace and bounded owned approach. Exact full-width profile and all remaining retaining edges require R17.'),public_join_status='Contour-aware finite source profile pending R17')
   for p in l['placements']:
    if p['holding_id']==h['id']:p['position_m'][1]+=delta;p['finished_floor_y_m']=floor;p['cluster_id']=h['cluster_id']
   for d in l['actual_doors']:
    if d['holding_id']==h['id']:d['actual_door_xyz_m'][1]+=delta
   updates.append(dict(id=h['id'],status='CONTOUR_ENTRY_SOURCE_CANDIDATE',previous_floor_y_m=oldfloor,proposed_floor_y_m=floor,maximum_cut_m=max(0,high-floor),maximum_fill_m=max(0,floor-low),public_road_id=road['id'],public_target=ev,entry_length_m=length,minimum_centerline_grade=grade,remaining_over_2_5m_design_review=max(high-floor,floor-low)>2.5+1e-6));print('CONTOUR',bid,h['id'],round(oldfloor,2),'to',round(floor,2),road['id'],round(grade,3),flush=True)
  retired=sorted({i for h in l['holdings']for i in h['retired_source_ids']});l.update(retired_source_ids=retired,retirement_records=[r for r in rows if r['source_id']in retired],retired_foundation_proxy_ids=[i+':owned_foundation'for i in retired]);removed=sum(projection[i]['roof_area_m2']for i in retired);s=l['summary'];s.update(retired_ordinary_instances=len(retired),retired_ordinary_roof_m2=removed,after_ordinary_roof_m2=s['before_ordinary_roof_m2']-removed+s['native_roof_m2'],net_ordinary_roof_gain_m2=s['native_roof_m2']-removed);g.write(out/'selected_layout.json',l)
  for name in['access','furnish']:
   src=(SOURCE/(name+'.py')).read_text()
   if name=='furnish':src=src.replace("holes=b['native_foundation_polygons_xz_m']+", "holes=[q for bp in layout['placements']if bp['holding_id']==h['id']for q in bp['native_foundation_polygons_xz_m']]+")
   mod=types.ModuleType(__package__+'.contour_'+name);mod.__package__=__package__;exec(compile(src,str(SOURCE/(name+'.py')),'exec'),mod.__dict__);mod.run()
  proposal=g.load(original/'ground_proposal.json');proposal.update(layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'),retirement_records=l['retirement_records'],retired_foundation_proxy_ids=l['retired_foundation_proxy_ids'],contour_reassignment=updates);proposal['clusters']=[dict(id=h['cluster_id'],datum=h.get('court_datum_evidence'),holding_ids=[h['id']],ground_owner_polygons_xz_m=[h['holding_polygon_xz_m']],entry_routes=[dict(id=h['id']+':ENTRY',width_m=h['external_width_m'],polyline_xz_m=h['external_route'],polygons_xz_m=h['external_route_polygons_xz_m'],public_road_id=h['public_road_id'],public_target=h.get('public_target_evidence'))])for h in l['holdings']];proposal.pop('exact_nonoverlapping_ground_owners',None);proposal.pop('route_graph',None);g.write(out/'ground_proposal.json',proposal);results+=updates
 g.write(SOURCE/'contour_revision_r01/contour_report.json',dict(budget=g.ref(terr/'city_coherent_budget_r01/terrain_budget.json'),results=results,accepted=sum(r['status']=='CONTOUR_ENTRY_SOURCE_CANDIDATE'for r in results),unresolved=[r for r in results if r['status']!='CONTOUR_ENTRY_SOURCE_CANDIDATE'],status='SOURCE_CANDIDATES_REQUIRING_EXACT_R17_FULL_WIDTH_PROFILE_AND_TERRAIN_PROOF'))
if __name__=='__main__':run()
