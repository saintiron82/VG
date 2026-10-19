"""A finite seven-holding B07 contour refit using only existing native caches."""
from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import config,PublicSamples
from .finalize_coherent import overlap
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as ta
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.bulk_grade_budget import height_part
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as tc
import types

def run():
 src=SOURCE/'coherent_regrade_r01/BLOCK_007';out=SOURCE/'b07_terrace_refit_r01/BLOCK_007';out.mkdir(parents=True,exist_ok=True);g.HERE=out;plan=g.CITY/'registered_integration/r8/coverage_plan';block=next(b for b in g.load(plan/'baseline_blocks.json')['blocks']if b['block_id']=='BLOCK_007');config(block);scene=g.load(g.R7);reg=g.load(SOURCE/'contour_revision_r01/BLOCK_006/native_local.json');native=reg['assets'];l=g.load(src/'selected_layout.json');l['supersedes_source']=g.ref(src/'selected_layout.json');specs={};r3=g.load(SOURCE/'b07_terrace_refit_r01/native_fit_search_r03.json')['rows'];r2=g.load(SOURCE/'b07_terrace_refit_r01/native_fit_search_r02.json')['rows'];specs['BLOCK_007:R8_C001']=next(r for r in r3 if r['description']['rear_shift_m']==3.5 and r['floor_y_m']==9.25);specs['BLOCK_007:R8_C005']=next(r for r in r2 if r['holding_id'].endswith('C005')and r['description']['range_local_z_m']==-8.25 and r['floor_y_m']==8);floors={'BLOCK_007:R8_C001':9.25,'BLOCK_007:R8_C005':8.,'BLOCK_007:R8_C006':5.,'BLOCK_007:R8_C007':3.75};newps=[];newds=[];checks=[];idx=ta.TriangleIndex(scene,[h['holding_polygon_xz_m']for h in l['holdings']]);oldrows=g.load(g.CITY/'registered_topography/revisions/r17_district_batches/all_blocks_r01/retirement_candidates.json')['rows'];retrows=[r for r in oldrows if r['source_id']in l['retired_source_ids']]
 for h in l['holdings']:
  hid=h['id'];floor=floors.get(hid,h['floor_y_m']);oldps=[p for p in l['placements']if p['holding_id']==hid];old=oldps[0];center=list(g.np.mean(h['holding_polygon_xz_m'],axis=0));yaw=old['yaw_rad'];pending=[];doors=[]
  if hid in specs:
   spec=specs[hid];h['core_court_polygons_xz_m']=spec['core_court_polygons_xz_m'];placements=spec['native_placements'];h['gate_position_xz_m']=g.xform([-17,-1.75]if hid.endswith('C001')else[9.5,-8.25],center,yaw);h['design']='Upper contour native frontage and bounded shared workcourt, with lower terrain retained at its actual source planes.'
  else:placements=[dict(asset_key=p['asset_key'],center_xz_m=[p['position_m'][0],p['position_m'][2]],yaw_rad=p['yaw_rad'])for p in oldps]
  for i,sp in enumerate(placements,1):
   key=sp['asset_key'];n=native[key];c=sp['center_xz_m'];pyaw=sp['yaw_rad'];p=g.copy.deepcopy(old);p.update(id=hid+f':FABRIC:{i}',asset_key=key,position_m=[c[0],floor-.5,c[1]],yaw_rad=pyaw,finished_floor_y_m=floor,cluster_id=hid+':TERRACE',palette_id=n['asset']['native_metadata']['palette'],native_foundation_polygons_xz_m=g.transform(n['foundation_local_polygons_xz_m'],c,pyaw),native_walking_obstacles_xz_m=g.transform(n['walking_local_polygons_xz_m'],c,pyaw),native_roof_polygons_xz_m=g.transform(n['roof_local_polygons_xz_m'],c,pyaw),actual_door_ids=[],roof_area_m2=n['roof_area_m2'],foundation_area_m2=n['foundation_area_m2'],role=n['asset']['native_metadata']['role']);pending.append(p)
   for d0 in n['doors']:
    d=g.copy.deepcopy(d0);q=d['actual_local_xyz_m'];xz=g.xform([q[0],q[2]],c,pyaw);d.update(id=p['id']+':'+d['id'],parcel_id=p['id'],holding_id=hid,actual_door_xyz_m=[xz[0],floor-.5+q[1],xz[1]],outward_xz=g.xform(d['outward_local_xz'],[0,0],pyaw),threshold_lip_xz_m=g.xform(d['threshold_lip_local_xz_m'],c,pyaw),render_sha256=n['asset']['render_sha256'],exterior_route_width_m=min(2.,d['exterior_route_width_m']));doors.append(d);p['actual_door_ids'].append(d['id'])
  margins=[]
  for r in idx.covering(h['holding_polygon_xz_m']):
   for kind,kw in[('cut',dict(low=floor+2.5+1e-7)),('fill',dict(high=floor-2.5-1e-7))]:
    q=height_part(r['intersection_polygon_xz_m'],r['plane_y_xz_m'],**kw)
    if q:margins.append(dict(kind=kind,polygon_xz_m=q,source_material=r['material'],source_triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],plane_y_xz_m=r['plane_y_xz_m'],classification='retained_existing_level_margin'))
  req=[q for p in pending for q in p['native_foundation_polygons_xz_m']]+h['core_court_polygons_xz_m'];excess=overlap(req,[r['polygon_xz_m']for r in margins]);oldholeexcess=sum(overlap(req,[r['old_terrain_body_hole_polygon_xz_m']])for r in retrows if abs(r['existing_finished_floor_y_m']-floor)>2.5+1e-7);nativepairs=sum(overlap(p['native_walking_obstacles_xz_m'],q['native_walking_obstacles_xz_m'])for i,p in enumerate(pending)for q in pending[:i]);inside=all(abs(g.geo.intersection_area(q,h['holding_polygon_xz_m'])-g.geo.polygon_area(q))<1e-7 for p in pending for q in p['native_roof_polygons_xz_m']);checks.append(dict(holding_id=hid,visible_core_excess_m2=excess,old_hole_core_excess_m2=oldholeexcess,new_native_pair_overlap_m2=nativepairs,native_roof_inside_holding=inside));print(checks[-1],flush=True);assert excess<1e-6 and nativepairs<1e-6 and inside
  h.update(floor_y_m=floor,cluster_id=hid+':TERRACE',component_placement_ids=[p['id']for p in pending],parcel_id=pending[0]['id'],native_roof_area_m2=sum(p['roof_area_m2']for p in pending),ground_owner_polygons_xz_m=tc.subtract([h['holding_polygon_xz_m']],[r['polygon_xz_m']for r in margins]),nonwalking_slope_verges=margins,external_width_m=2. if hid in floors else h['external_width_m'],court_datum_evidence=dict(floor_y_m=floor,policy='Actual visible-terrain required core remains within 2.5 m. Any old cached-body-floor excess is separately held for R17 obsolete-pad boundary reconstruction; it is not silently treated as surviving terrain. Excluded margins retain existing planes.'),native_refit_provenance=dict(source_layout=g.ref(src/'selected_layout.json'),new_compilation=False,replacement_asset_keys=[p['asset_key']for p in pending]));newps+=pending;newds+=doors
 l['placements']=newps;l['actual_doors']=newds;g.write(out/'native_local.json',reg);l['native_local']=g.ref(out/'native_local.json');projection=g.load(plan/'native_projection.json')['instances'];manifest=g.load(SOURCE/'effective_city_manifest_r01.json');retired=set(l['retired_source_ids'])|set(manifest['replaced_placement_ids']);retained=[q for r in projection if r['id']not in retired for q in r['native_owner_parts_xz_m']];special=g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];mill=g.load(SOURCE/'coherent_regrade_r01/mill_reservation_check.json')['protected_regions'];protected=special+[r['polygon']for r in mill];vs=scene['surfaces']['water'];water=[[[v[0],v[2]]for v in vs[i:i+3]]for i in range(0,len(vs),3)];newnative=[q for p in newps for q in p['native_walking_obstacles_xz_m']];base=g.np.load(plan/'baseline_masks.npz');x=((g.XS-float(base['bounds'][0]))/float(base['pitch'])).astype(int);z=((g.ZS-float(base['bounds'][1]))/float(base['pitch'])).astype(int);ms={k:base[k][g.np.ix_(z,x)]for k in base.files if base[k].ndim==2};domain=g.raster(g.triangulate(block['polygon_xz_m']));hard=g.raster(retained+protected+water+newnative,True)|ms['spaces']|ms['estates']|ms['wall'];samples=PublicSamples(scene);roadpoints=[]
 for road in g.load(g.CITY/'registered_source/plan.json')['roads']:
  for si,(a,b)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   if min(g.math.dist(a,[315,-25]),g.math.dist(b,[315,-25]))>150:continue
   for t in g.np.linspace(0,1,max(2,int(g.math.ceil(g.math.dist(a,b)/2))+1)):
    q=[a[k]+float(t)*(b[k]-a[k])for k in[0,1]];e=samples.at(q)
    if e:roadpoints.append((q,e,road,si))
 unresolved=[]
 for h in l['holdings']:
  if h['id']not in floors:continue
  gate=h['gate_position_xz_m'];width=h['external_width_m'];floor=h['floor_y_m'];free=(domain|ms['road'])&~hard
  for oh in l['holdings']:
   if oh['id']!=h['id']:free &=~g.raster([oh['holding_polygon_xz_m']],True)
  clear=g.ndimage.distance_transform_edt(free)*g.GRID>=width/2+.15;start=g.nearest(clear,gate,3);choices=[]
  for q,e,road,si in roadpoints:
   dist=g.math.dist(gate,q);dy=abs(floor-e['y_m'])
   if not 5<dist<100 or road['width_m']<width or dy>dist*.105:continue
   choices.append((dist+.8*dy,q,e,road,si))
  choices.sort(key=lambda x:x[0]);found=None
  for _,q,e,road,si in choices[:120]:
   end=g.nearest(clear,q,2.);goals=g.np.zeros(g.SHAPE,bool)
   if end:goals[end]=True
   ll=g.astar(clear,start,goals)if start and end else None
   if not ll:continue
   ll=[gate]+ll+[q];ll=[p for i,p in enumerate(ll)if not i or g.math.dist(p,ll[i-1])>1e-7];ps=g.ribbons(ll,width);length=sum(g.math.dist(a,b)for a,b in zip(ll,ll[1:]));grade=abs(floor-e['y_m'])/max(1,length-width)
   if grade>.105:continue
   checks2={k:overlap(ps,ss)for k,ss in [('retained',retained),('protected',protected),('water',water),('new_native',newnative)]}
   if any(v>1e-7 for v in checks2.values()):continue
   found=(ll,ps,q,e,road,si,length,grade,checks2);break
  if not found:unresolved.append(dict(id=h['id'],reason='No native-clear bounded higher-road approach yet'));h.update(external_route=[],external_route_polygons_xz_m=[]);print('ENTRY_HELD',h['id'],flush=True);continue
  ll,ps,q,e,road,si,length,grade,cc=found;h.update(external_route=ll,external_route_polygons_xz_m=ps,public_target_xz_m=q,public_target_evidence=e,public_road_id=road['id'],public_join_status='Exact full transverse R17/R18 profile pending');h['court_datum_evidence'].update(chosen_public_anchor=dict(e,public_road_id=road['id'],segment=si),profile_centerline_grade=grade);print('ENTRY',h['id'],road['id'],length,grade,flush=True)
 l['unresolved_external_routes']=unresolved;s=l['summary'];s.update(native_instances=len(newps),native_roof_m2=sum(p['roof_area_m2']for p in newps),actual_exterior_doors=len(newds),unresolved_external_routes=len(unresolved));s.update(after_ordinary_roof_m2=s['before_ordinary_roof_m2']-s['retired_ordinary_roof_m2']+s['native_roof_m2'],net_ordinary_roof_gain_m2=s['native_roof_m2']-s['retired_ordinary_roof_m2']);g.write(out/'selected_layout.json',l);g.write(out/'core_refit_audit.json',dict(checks=checks,source_layout=g.ref(src/'selected_layout.json'),summary=s,status='Exact native and visible-core screen passed; explicit old-body-floor exceptions and full entry/side composition remain pending'))
 for name in ['compile_report.json','owner_route_source_snapshot.json']:(out/name).write_bytes((src/name).read_bytes())
 for name in ['access','furnish']:
  text=(SOURCE/(name+'.py')).read_text()
  if name=='access':text=text.replace("allowed=raster([h['holding_polygon_xz_m']]+", "allowed=raster(h.get('ground_owner_polygons_xz_m',[h['holding_polygon_xz_m']])+")
  else:text=text.replace("holes=b['native_foundation_polygons_xz_m']+", "holes=[q for bp in layout['placements']if bp['holding_id']==h['id']for q in bp['native_foundation_polygons_xz_m']]+")
  mod=types.ModuleType(__package__+'.b07_'+name);mod.__package__=__package__;exec(compile(text,str(SOURCE/(name+'.py')),'exec'),mod.__dict__);mod.run()
 proposal=g.load(src/'ground_proposal.json');proposal.update(layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'));proposal['clusters']=[dict(id=h['cluster_id'],datum=h['court_datum_evidence'],holding_ids=[h['id']],ground_owner_polygons_xz_m=h['ground_owner_polygons_xz_m'],entry_routes=[dict(id=h['id']+':ENTRY',width_m=h['external_width_m'],polyline_xz_m=h['external_route'],polygons_xz_m=h['external_route_polygons_xz_m'],public_road_id=h['public_road_id'],public_target=h.get('public_target_evidence'))])for h in l['holdings']];proposal['retained_nonwalking_margin_verges']=[dict(holding_id=h['id'],**q)for h in l['holdings']for q in h.get('nonwalking_slope_verges',[])];g.write(out/'ground_proposal.json',proposal);print(s,flush=True)
if __name__=='__main__':run()
