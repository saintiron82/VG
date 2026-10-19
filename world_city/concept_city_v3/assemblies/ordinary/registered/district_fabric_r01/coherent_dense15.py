"""Count-independent B15 native district fit with two public-anchored court zones.
Paired-range search masks are temporary planning groups; final outputs contain
only the already compiled individual native assets at unit scale.
"""
from . import geometry as g
from .design import HERE as SOURCE
from . import dense as frozen
import types

def run():
 out=SOURCE/'coherent_regrade_r01/BLOCK_015';out.mkdir(parents=True,exist_ok=True);g.HERE=out;plan=g.CITY/'registered_integration/r8/coverage_plan';terr=g.CITY/'registered_topography/revisions/r17_district_batches';scene=g.load(g.R7);source_native=g.load(SOURCE/'native_local.json');native=g.copy.deepcopy(source_native['assets']);pairkey='PLAN_ONLY_PAIRED_NATIVE_RANGES';specs=[('working_r01_bank_joinery',[0,-8.5],0),('working_r01_bank_craft_lodging',[0,8.5],g.math.pi)]
 pair=dict(asset={'native_metadata':{'palette':'wood_brown','role':'Paired existing native frontages around a shared manual-working court'},'render_sha256':'PLANNING_GROUP_EXPANDED_BEFORE_EXPORT'},foundation_local_polygons_xz_m=[],walking_local_polygons_xz_m=[],roof_local_polygons_xz_m=[],court_local_polygon_xz_m=g.rect(-14.5,-3.25,14.5,3.25),doors=[],roof_area_m2=0,foundation_area_m2=0)
 for ci,(key,c,yaw)in enumerate(specs):
  n=native[key]
  for field in['foundation_local_polygons_xz_m','walking_local_polygons_xz_m','roof_local_polygons_xz_m']:pair[field]+=g.transform(n[field],c,yaw)
  pair['roof_area_m2']+=n['roof_area_m2'];pair['foundation_area_m2']+=n['foundation_area_m2']
  for d0 in n['doors']:
   d=g.copy.deepcopy(d0);q=d['actual_local_xyz_m'];xz=g.xform([q[0],q[2]],c,yaw);d.update(id=f'COMPONENT{ci}:'+d['id'],actual_local_xyz_m=[xz[0],q[1],xz[1]],outward_local_xz=g.xform(d['outward_local_xz'],[0,0],yaw),threshold_lip_local_xz_m=g.xform(d['threshold_lip_local_xz_m'],c,yaw));pair['doors'].append(d)
 native[pairkey]=pair;g.write(out/'native_local.json',dict(source_native,assets=native,planning_group_policy='Temporary composed masks only. No runtime asset or compiler output; expanded into exact existing cache instances before export.'))
 m0=g.np.load(SOURCE/'planning_masks.npz');m={k:m0[k]for k in m0.files};base=g.np.load(plan/'baseline_masks.npz');x=((g.XS-float(base['bounds'][0]))/float(base['pitch'])).astype(int);z=((g.ZS-float(base['bounds'][1]))/float(base['pitch'])).astype(int);public={f:frozen.world_scene_floor(scene,f,{'road','alley'})&base['road'][g.np.ix_(z,x)]for f in[2.5,1.]};dist={f:g.ndimage.distance_transform_edt(~public[f])*g.GRID for f in public};m['nonmatching_native']=g.np.zeros(g.SHAPE,bool)
 for f in public:
  tag=str(f).replace('.','_');other=1. if f==2.5 else 2.5;zone=(m['domain']&(dist[f]<=dist[other]))|public[f];m['regrade_'+tag]=zone;m['floor_'+tag]=zone;m['restorable_'+tag]=g.np.zeros(g.SHAPE,bool)
 g.np.savez_compressed(out/'planning_masks.npz',**m);rows=[r for r in g.load(terr/'all_blocks_r01/retirement_candidates.json')['rows']if r['block_id']=='BLOCK_015'];inp=g.load(SOURCE/'input.json');inp.update(restorable_candidates=rows,ground_mode='bounded_cluster_regrade',policy='Synthetic planning zones are nearest preserved +1/+2.5 public frontages, not existing flat floor evidence. Every accepted finite holding/lane requires R17 grading.');g.write(out/'input.json',inp);(out/'owner_route_source_snapshot.json').write_bytes((SOURCE/'owner_route_source_snapshot.json').read_bytes())
 text=(SOURCE/'dense.py').read_text();text=text.replace("actual=world_scene_floor(scene,floor);public=world_scene_floor(scene,floor,{'road','alley'});band=(actual|oldholes)&~hard", "actual=m['regrade_'+str(floor).replace('.','_')];public=world_scene_floor(scene,floor,{'road','alley'})&old['road'][np.ix_(z,x)];band=(actual|oldholes)&~hard").replace("nearroad=ndimage.distance_transform_edt(~public)*GRID<3", "nearroad=ndimage.distance_transform_edt(~public)*GRID<1.5").replace("range(10)","range(10)").replace("safe_ids={r['source_id']for r in load(TERR/'retired_body_boundary_audit.json')['rows']if r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'}", "safe_ids={r['source_id']for r in load(TERR/'all_blocks_r01/retirement_candidates.json')['rows']if r['block_id']=='BLOCK_015'}")
 text=text.replace("TYPES=[", "TYPES=[('PLAN_ONLY_PAIRED_NATIVE_RANGES',rect(-17,-14,17,14)),")
 text=text.replace("gate=xform([0,max(q[1]for q in hpoly)],[0,0],yaw)","gate=xform([17,0]if key=='PLAN_ONLY_PAIRED_NATIVE_RANGES'else[0,max(q[1]for q in hpoly)],[0,0],yaw)")
 text=text.replace("'Bulk native candidate; exact terrain, routes and actual view pending'","'Coherent bounded regrade proposal, not existing-level proof'")
 text=text.replace('allowed=eligible&bands[floor]&~lanes','allowed=eligible&bands[floor]')
 text=text.replace('distance[gz[ii],gx[ii]]<=8','distance[gz[ii],gx[ii]]<=18')
 text=text.replace('free=clear[floor]&~used;goals=network[floor]&free;line=astar(free,start,goals)','free=clear[floor]&(ndimage.distance_transform_edt(bands[floor]&~used)*GRID>=2.2);goals=network[floor]&free;start=nearest(free,gate,4);line=astar(free,start,goals)')
 text=text.replace('placements.append(p);used|=hm|rm;obstacle|=raster(roof,True)','network[floor]|=rm;placements.append(p);used|=hm|rm;obstacle|=raster(roof,True)')

 text=text.replace('if np.any(hm&used):continue','if False:continue')
 text=text.replace('candidates.sort(reverse=True,key=lambda q:q[0]);obstacle=np.zeros(SHAPE,bool)','candidates.sort(reverse=True,key=lambda q:q[0]);obstacle=np.zeros(SHAPE,bool);court_reserved=np.zeros(SHAPE,bool)')
 text=text.replace('if np.any(rm&raster(roof,True))or np.any(rm&used):continue',"roofmask=raster(roof,True);courttest=transform([n['court_local_polygon_xz_m']or rect(-10,6,10,10)],center,yaw);courtmask=raster(courttest,True)\n  if np.any(roofmask&(used|lanes|court_reserved))or np.any(courtmask&used)or np.any(rm&roofmask)or np.any(rm&used):continue")
 text=text.replace('placements.append(p);used|=hm|rm;obstacle|=raster(roof,True)','placements.append(p);used|=roofmask;lanes|=rm;court_reserved|=courtmask;obstacle|=roofmask\n  if sum(q["roof_area_m2"]for q in placements)>=18000:break')
 text=text.replace('n=native[key];gate=',"n=native[key];earlyroof=raster(transform(n['roof_local_polygons_xz_m'],center,yaw),True);earlycourt=raster(transform([n['court_local_polygon_xz_m']or rect(-10,6,10,10)],center,yaw),True)\n  if np.any(earlyroof&(used|lanes|court_reserved))or np.any(earlycourt&used):continue\n  gate=")


 (out/'producer_source.py').write_text(text);engine=types.ModuleType(__package__+'.coherent_dense_engine');engine.__package__=__package__;exec(compile(text,str(out/'producer_source.py'),'exec'),engine.__dict__);layout=engine.run();placements=[];doors=[]
 for p0 in layout['placements']:
  if p0['asset_key']==pairkey:components=specs
  else:components=[(p0['asset_key'],[0,0],0)]
  basecenter=[p0['position_m'][0],p0['position_m'][2]];floor=p0['finished_floor_y_m'];pyaw=p0['yaw_rad'];ids=[]
  for ci,(key,offset,ryaw)in enumerate(components):
   n=source_native['assets'][key];c=g.xform(offset,basecenter,pyaw);yaw=pyaw+ryaw;p=g.copy.deepcopy(p0);p.update(id=p0['id']+(f':PART{ci+1}'if len(components)>1 else''),asset_key=key,position_m=[c[0],floor-.5,c[1]],yaw_rad=yaw,palette_id=n['asset']['native_metadata']['palette'],native_foundation_polygons_xz_m=g.transform(n['foundation_local_polygons_xz_m'],c,yaw),native_walking_obstacles_xz_m=g.transform(n['walking_local_polygons_xz_m'],c,yaw),native_roof_polygons_xz_m=g.transform(n['roof_local_polygons_xz_m'],c,yaw),actual_door_ids=[],roof_area_m2=n['roof_area_m2'],foundation_area_m2=n['foundation_area_m2'],role=n['asset']['native_metadata']['role'],implementation_tier='exterior_only');placements.append(p);ids.append(p['id'])
   for d0 in n['doors']:
    d=g.copy.deepcopy(d0);q=d['actual_local_xyz_m'];xz=g.xform([q[0],q[2]],c,yaw);d.update(id=p['id']+':'+d['id'],parcel_id=p['id'],holding_id=p['holding_id'],actual_door_xyz_m=[xz[0],floor-.5+q[1],xz[1]],outward_xz=g.xform(d['outward_local_xz'],[0,0],yaw),threshold_lip_xz_m=g.xform(d['threshold_lip_local_xz_m'],c,yaw),render_sha256=n['asset']['render_sha256'],exterior_route_width_m=min(2.,d['exterior_route_width_m'])if len(components)>1 else d['exterior_route_width_m']);doors.append(d);p['actual_door_ids'].append(d['id'])
  h=next(h for h in layout['holdings']if h['id']==p0['holding_id']);h.update(parcel_id=ids[0],component_placement_ids=ids,cluster_id='B15_COURT_ZONE_'+str(floor).replace('.','_'),ground_mode='bounded_cluster_regrade')
 layout.update(placements=placements,actual_doors=doors,ground_mode='bounded_cluster_regrade',native_local=g.ref(SOURCE/'native_local.json'));layout['summary'].update(native_instances=len(placements),actual_exterior_doors=len(doors));g.write(out/'selected_layout.json',layout);(out/'native_local.json').write_bytes((SOURCE/'native_local.json').read_bytes());(out/'compile_report.json').write_bytes((SOURCE/'compile_report.json').read_bytes())
 for name in['access','furnish']:
  src=(SOURCE/(name+'.py')).read_text()
  if name=='furnish':src=src.replace("holes=b['native_foundation_polygons_xz_m']+", "holes=[q for bp in layout['placements']if bp['holding_id']==h['id']for q in bp['native_foundation_polygons_xz_m']]+")
  mod=types.ModuleType(__package__+'.b15_'+name);mod.__package__=__package__;exec(compile(src,str(SOURCE/(name+'.py')),'exec'),mod.__dict__);mod.run()
 g.write(out/'ground_proposal.json',dict(schema='riverstone.district_fabric.coherent_ground_proposal.v1',base_scene=g.ref(g.R7),layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'),clusters=[dict(id='B15_COURT_ZONE_'+str(f).replace('.','_'),floor_y_m=f,datum_policy='Nearest retained public road band with exact actual R7 floor '+str(f),holding_ids=[h['id']for h in layout['holdings']if h['floor_y_m']==f],ground_owner_polygons_xz_m=[h['holding_polygon_xz_m']for h in layout['holdings']if h['floor_y_m']==f],shared_routes=[r for r in layout['shared_private_routes']if r['floor_y_m']==f])for f in[2.5,1.]],retirement_records=layout['retirement_records'],retired_foundation_proxy_ids=layout['retired_foundation_proxy_ids'],policy='Union overlapping same-level holding envelopes into one finite shared-court ground owner, subtract every new native hole, and partition materials once. Private building owners remain distinct. Finite holding and private-lane grading only. Planning zones are not blanket terrain owners. Public road/water/special/native interfaces stay fixed; R17 composes <=12% entries and explicit retaining sides.',supersedes_safe_B15_only_after_acceptance=g.ref(SOURCE/'selected_layout.json'),status='NATIVE_SOURCE_PENDING_COHERENT_GRADE_ACCEPTANCE'));print('COHERENT B15',layout['summary'])
if __name__=='__main__':run()
