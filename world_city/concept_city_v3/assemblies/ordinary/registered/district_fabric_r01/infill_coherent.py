"""Count-independent residual native frontage infill to disclosed block targets."""
from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import config,nearest_road,PublicSamples
from scipy.signal import fftconvolve
import types,sys

def kernel(poly,yaw):
 c=g.point((g.NZ//2,g.NX//2));a=g.raster(g.transform([poly],c,yaw),True);z,x=g.cell(c);zz,xx=g.np.where(a);dz=max(z-int(zz.min()),int(zz.max())-z);dx=max(x-int(xx.min()),int(xx.max())-x);return a[z-dz:z+dz+1,x-dx:x+dx+1].astype(float)

def run():
 plan=g.CITY/'registered_integration/r8/coverage_plan';terr=g.CITY/'registered_topography/revisions/r17_district_batches';blocks={b['block_id']:b for b in g.load(plan/'baseline_blocks.json')['blocks']};scene=g.load(g.R7);samples=PublicSamples(scene);native=g.load(SOURCE/'native_local.json')['assets'];roads=g.load(g.CITY/'registered_source/plan.json')['roads'];base=g.np.load(plan/'baseline_masks.npz');allrows=g.load(terr/'all_blocks_r01/retirement_candidates.json')['rows'];projection={i['id']:i for i in g.load(plan/'native_projection.json')['instances']};special_parts=g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];results=[]
 for block_id in sys.argv[1:]:
  block=blocks[block_id];config(block);out=SOURCE/'coherent_regrade_r01'/block_id;g.HERE=out;layout=g.load(out/'selected_layout.json');rows=[r for r in allrows if r['block_id']==block_id];retired=set(layout['retired_source_ids']);target=max(layout['summary']['before_ordinary_roof_m2'],.35*block['ordinary_replanning_domain_m2']);before=g.copy.deepcopy(layout['summary']);x=((g.XS-float(base['bounds'][0]))/float(base['pitch'])).astype(int);z=((g.ZS-float(base['bounds'][1]))/float(base['pitch'])).astype(int);ms={k:base[k][g.np.ix_(z,x)]for k in base.files if base[k].ndim==2};hard=g.np.logical_or.reduce([ms[k]for k in['spaces','estates','water','wall','retained_native','retained_access']])|g.raster(special_parts,True);domain=g.raster(g.triangulate(block['polygon_xz_m']));eligible=domain&~hard&(g.ndimage.distance_transform_edt(~ms['water'])*g.GRID>4)&(g.ndimage.distance_transform_edt(~ms['road'])*g.GRID>2);hused=g.raster([h['holding_polygon_xz_m']for h in layout['holdings']],True);obstacles=g.raster([q for p in layout['placements']for q in p['native_walking_obstacles_xz_m']],True);lanes=g.raster([q for h in layout['holdings']for q in h['external_route_polygons_xz_m']],True);allowed=eligible&~hused&~lanes;roadset=[r for r in roads if r['id']in block['boundary_road_ids']or r.get('block_id')==block_id];network=ms['road']|lanes;distance=g.ndimage.distance_transform_edt(~network)*g.GRID;free=(domain|ms['road'])&~hard&~obstacles&~hused;candidates=[]
  families=[('working_r01_bank_joinery',g.rect(-15.75,-5.75,15.75,11)),('working_r01_market_lodging',g.rect(-12.75,-5.25,12.75,10)),('district_r01_compact_L',g.rect(-9.25,-10,9.25,13.5))]
  for ti,(key,hpoly)in enumerate(families):
   for degrees in range(0,360,15):
    yaw=g.math.radians(degrees);k=kernel(hpoly,yaw);valid=fftconvolve(allowed.astype(float),k[::-1,::-1],mode='same')>=k.sum()-.01;zz,xx=g.np.where(valid);gate=g.xform([0,max(q[1]for q in hpoly)],[0,0],yaw);gx=g.np.rint(xx+gate[0]/g.GRID).astype(int);gz=g.np.rint(zz+gate[1]/g.GRID).astype(int);ok=(gx>=0)&(gx<g.NX)&(gz>=0)&(gz<g.NZ);ii=g.np.where(ok)[0];ii=ii[(distance[gz[ii],gx[ii]]<=12)&(zz[ii]%4==0)&(xx[ii]%4==0)]
    for j in ii:candidates.append((native[key]['roof_area_m2']/g.geo.polygon_area(hpoly)-.007*distance[gz[j],gx[j]],ti,yaw,int(zz[j]),int(xx[j]),gate))
  candidates.sort(reverse=True);added=[];print('infill candidates',block_id,len(candidates),flush=True)
  for _,ti,yaw,z,x,gd in candidates:
   current=layout['summary']['before_ordinary_roof_m2']-sum(projection[i]['roof_area_m2']for i in retired)+sum(p['roof_area_m2']for p in layout['placements'])
   if current>=target:break
   key,hpoly=families[ti];c=g.point((z,x));hp=g.transform([hpoly],c,yaw)[0];hm=g.raster([hp],True)
   if g.np.any(hm&(hused|lanes)):continue
   if key=='working_r01_bank_joinery':key=['working_r01_bank_joinery','working_r01_bank_loft_store','working_r01_bank_craft_lodging'][len(added)%3]
   n=native[key];gate=[c[0]+gd[0],c[1]+gd[1]];dist,road,q=min(((nearest_road(gate,r)[0],r,nearest_road(gate,r)[3])for r in roadset),key=lambda a:a[0]);ev=samples.at(q);host=min(layout['holdings'],key=lambda h:g.math.dist(gate,h['gate_position_xz_m']));shared_host=host if g.math.dist(gate,host['gate_position_xz_m'])<dist else None;publicq=q
   if shared_host:
    q=host['gate_position_xz_m'];dist=g.math.dist(gate,q);ev=dict(y_m=host['floor_y_m'],point_xz_m=q,connection_holding_id=host['id'],public_anchor=host.get('public_target_evidence'));road=next(r for r in roadset if r['id']==host['public_road_id']);publicq=host['public_target_xz_m']
   if not ev:continue
   outward=g.xform([0,1],[0,0],yaw)
   if sum(outward[k]*(q[k]-gate[k])for k in[0,1])<.5*dist:continue
   width=min(2.4,road['width_m']);free=(domain|ms['road'])&~hard&~obstacles
   for oh in layout['holdings']:
    if abs(oh['floor_y_m']-ev['y_m'])>1e-6:free&=~g.raster([oh['holding_polygon_xz_m']],True)
   clear=g.ndimage.distance_transform_edt(free)*g.GRID>=width/2+.25;start=g.nearest(clear,gate,3);end=g.nearest(clear,q,2.5);goals=g.np.zeros(g.SHAPE,bool)
   if end:goals[end]=True
   direct=g.ribbons([gate,q],width);line=[gate,q]if not g.np.any(g.raster(direct,True)&~free)else(g.astar(clear,start,goals)if start and end else None)
   if not line:continue
   line=[gate]+line+[q]
   if shared_host:line+=host['external_route'][1:]
   rp=g.ribbons(line,width);rm=g.raster(rp,True);roof=g.transform(n['roof_local_polygons_xz_m'],c,yaw)
   if g.np.any(rm&g.raster(roof,True)):continue
   ids={r['source_id']for r in rows if g.geo.intersection_area(r['actual_native_outer_footprint_xz_m'],hp)>1e-7 or any(g.geo.intersection_area(r['actual_native_outer_footprint_xz_m'],p)>1e-7 for p in rp)}
   gain=n['roof_area_m2']-sum(projection[i]['roof_area_m2']for i in ids-retired)
   if gain<20:continue
   floor=ev['y_m'];hid=block_id+f':R8_I{1+sum(h["id"].startswith(block_id+":R8_I")for h in layout["holdings"]):03}';pid=hid+':FABRIC';cid=host['cluster_id']if shared_host else hid+':GRADE';foot=g.transform(n['foundation_local_polygons_xz_m'],c,yaw);walk=g.transform(n['walking_local_polygons_xz_m'],c,yaw);p=dict(id=pid,holding_id=hid,cluster_id=cid,block_id=block_id,asset_key=key,position_m=[c[0],floor-.5,c[1]],yaw_rad=yaw,scale=[1,1,1],finished_floor_y_m=floor,palette_id=n['asset']['native_metadata']['palette'],source_pack='district_fabric_coherent_r01',native_foundation_polygons_xz_m=foot,native_walking_obstacles_xz_m=walk,native_roof_polygons_xz_m=roof,actual_door_ids=[],roof_area_m2=n['roof_area_m2'],foundation_area_m2=n['foundation_area_m2'],role=n['asset']['native_metadata']['role'],implementation_tier='exterior_only');layout['placements'].append(p)
   for d0 in n['doors']:
    dv=g.copy.deepcopy(d0);v=dv['actual_local_xyz_m'];xz=g.xform([v[0],v[2]],c,yaw);dv.update(id=pid+':'+dv['id'],parcel_id=pid,holding_id=hid,actual_door_xyz_m=[xz[0],floor-.5+v[1],xz[1]],outward_xz=g.xform(dv['outward_local_xz'],[0,0],yaw),threshold_lip_xz_m=g.xform(dv['threshold_lip_local_xz_m'],c,yaw),render_sha256=n['asset']['render_sha256']);layout['actual_doors'].append(dv);p['actual_door_ids'].append(dv['id'])
   court=n['court_local_polygon_xz_m']or g.rect(-hpoly[2][0]+2,6,hpoly[2][0]-2,max(t[1]for t in hpoly)-1);datum=dict(floor_y_m=floor,chosen_public_anchor=dict(ev,public_road_id=road['id']),all_public_anchors=[ev]);h=dict(id=hid,parcel_id=pid,component_placement_ids=[pid],cluster_id=cid,floor_y_m=floor,holding_polygon_xz_m=hp,core_court_polygons_xz_m=g.transform([court],c,yaw),gate_position_xz_m=gate,external_width_m=width,external_route=line,external_route_polygons_xz_m=rp,public_road_id=road['id'],public_target_xz_m=publicq,public_target_evidence=host.get('public_target_evidence')if shared_host else ev,retired_source_ids=sorted(ids),native_roof_area_m2=n['roof_area_m2'],holding_area_m2=g.geo.polygon_area(hp),planned_role='shared_manual_work_and_domestic_court',ground_mode='bounded_cluster_regrade',court_datum_evidence=datum,design='Additional route-fronted fixed native holding selected by roofscape target, not source count');layout['holdings'].append(h);layout.setdefault('cluster_court_datums',{}).setdefault(cid,datum);added.append(hid);print('infill accepted',hid,round(gain,1),flush=True);retired|=ids;hused|=hm;lanes|=rm;free&=~hm
  layout['retired_source_ids']=sorted(retired);layout['retirement_records']=[r for r in rows if r['source_id']in retired];layout['retired_foundation_proxy_ids']=[i+':owned_foundation'for i in sorted(retired)];newroof=sum(p['roof_area_m2']for p in layout['placements']);removed=sum(projection[i]['roof_area_m2']for i in retired);s=layout['summary'];s.update(holdings=len(layout['holdings']),native_instances=len(layout['placements']),native_roof_m2=newroof,holding_area_m2=sum(h['holding_area_m2']for h in layout['holdings']),actual_exterior_doors=len(layout['actual_doors']),retired_ordinary_instances=len(retired),retired_ordinary_roof_m2=removed,after_ordinary_roof_m2=s['before_ordinary_roof_m2']-removed+newroof,net_ordinary_roof_gain_m2=newroof-removed,ordinary_domain_m2=block['ordinary_replanning_domain_m2'],ordinary_roof_fraction=(s['before_ordinary_roof_m2']-removed+newroof)/block['ordinary_replanning_domain_m2'],disclosed_roof_fraction_target=.35);g.write(out/'selected_layout.json',layout)
  for name in['access','furnish']:
   src=(SOURCE/(name+'.py')).read_text()
   if name=='access':src=src.replace('>=w/2+.2','>=w/2+.4')
   else:src=src.replace("holes=b['native_foundation_polygons_xz_m']+", "holes=[q for bp in layout['placements']if bp['holding_id']==h['id']for q in bp['native_foundation_polygons_xz_m']]+")
   mod=types.ModuleType(__package__+'.infill_'+name);mod.__package__=__package__;exec(compile(src,str(SOURCE/(name+'.py')),'exec'),mod.__dict__);mod.run()
  proposal=g.load(out/'ground_proposal.json');proposal.update(layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'),retirement_records=layout['retirement_records'],retired_foundation_proxy_ids=layout['retired_foundation_proxy_ids']);proposal['clusters']=[dict(id=cid,datum=datum,holding_ids=[h['id']for h in layout['holdings']if h['cluster_id']==cid],ground_owner_polygons_xz_m=[h['holding_polygon_xz_m']for h in layout['holdings']if h['cluster_id']==cid],entry_routes=[dict(id=h['id']+':ENTRY',width_m=h['external_width_m'],polyline_xz_m=h['external_route'],polygons_xz_m=h['external_route_polygons_xz_m'],public_road_id=h['public_road_id'],public_target=h.get('public_target_evidence'))for h in layout['holdings']if h['cluster_id']==cid])for cid,datum in layout['cluster_court_datums'].items()];g.write(out/'ground_proposal.json',proposal);results.append(dict(block_id=block_id,added_holding_ids=added,before=before,after=s,remaining_target_deficit_m2=max(0,target-s['after_ordinary_roof_m2'])));print('INFILL',block_id,len(added),s,flush=True)
 g.write(SOURCE/'coherent_regrade_r01/infill_report.json',dict(results=results,source=g.ref(SOURCE/'infill_coherent.py'),new_art_or_compiles=0))
if __name__=='__main__':run()
