"""Whole-city fixed-native source parcels on authorized coherent court planes.
Existing ordinary pads are retired within finite new owners; protected public,
water and special interfaces are preserved for R17's bounded grade transition.
"""
from . import geometry as g
from .design import HERE as SOURCE
import types,sys

def config(block):
 p=block['polygon_xz_m'];b=[g.math.floor(min(q[0]for q in p)/10)*10-20,g.math.floor(min(q[1]for q in p)/10)*10-20,g.math.ceil(max(q[0]for q in p)/10)*10+20,g.math.ceil(max(q[1]for q in p)/10)*10+20];g.BOUNDS=b;g.NX=round((b[2]-b[0])/g.GRID);g.NZ=round((b[3]-b[1])/g.GRID);g.SHAPE=(g.NZ,g.NX);g.XS=b[0]+(g.np.arange(g.NX)+.5)*g.GRID;g.ZS=b[1]+(g.np.arange(g.NZ)+.5)*g.GRID

def nearest_road(q,road):
 best=None
 for i,(a,b)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
  dx,dz=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((q[0]-a[0])*dx+(q[1]-a[1])*dz)/(dx*dx+dz*dz)));p=[a[0]+t*dx,a[1]+t*dz];v=(g.math.dist(q,p),i,t,p)
  if best is None or v[0]<best[0]:best=v
 return best

class PublicSamples:
 def __init__(self,scene):
  self.arrays={m:g.np.array(scene['surfaces'].get(m,[]),dtype=float).reshape(-1,3,3)for m in['road','alley']}
  self.bounds={m:(t[:,:,0].min(1),t[:,:,0].max(1),t[:,:,2].min(1),t[:,:,2].max(1))for m,t in self.arrays.items()}
 def at(self,q):
  for m,ts in self.arrays.items():
   x0,x1,z0,z1=self.bounds[m];ix=g.np.where((x0<=q[0]+1e-7)&(x1>=q[0]-1e-7)&(z0<=q[1]+1e-7)&(z1>=q[1]-1e-7))[0]
   for j in ix:
    t=ts[j];p=[[float(v[0]),float(v[2])]for v in t];den=(p[1][1]-p[2][1])*(p[0][0]-p[2][0])+(p[2][0]-p[1][0])*(p[0][1]-p[2][1])
    if abs(den)<1e-10:continue
    a=((p[1][1]-p[2][1])*(q[0]-p[2][0])+(p[2][0]-p[1][0])*(q[1]-p[2][1]))/den;b=((p[2][1]-p[0][1])*(q[0]-p[2][0])+(p[0][0]-p[2][0])*(q[1]-p[2][1]))/den;c=1-a-b
    if min(a,b,c)>=-1e-6:return dict(y_m=float(a*t[0,1]+b*t[1,1]+c*t[2,1]),material=m,triangle_index=int(j),vertices_xyz_m=t.tolist(),point_xz_m=q)
  return None

def run():
 plan=g.CITY/'registered_integration/r8/coverage_plan';terr=g.CITY/'registered_topography/revisions/r17_district_batches';bulk=g.load(plan/'fixed_family_bulk_contract.json');sources=g.load(plan/'parcel_candidates.json');by_source={h['id']:h for h in sources['holdings']};blocks={b['block_id']:b for b in g.load(plan/'baseline_blocks.json')['blocks']};base=g.np.load(plan/'baseline_masks.npz');scene=g.load(g.R7);native=g.load(SOURCE/'native_local.json')['assets'];roads={r['id']:r for r in g.load(g.CITY/'registered_source/plan.json')['roads']};samples=PublicSamples(scene);retire=g.load(terr/'all_blocks_r01/retirement_candidates.json')['rows'];projection={i['id']:i for i in g.load(plan/'native_projection.json')['instances']};special_parts=g.load(SOURCE/'owner_route_source_snapshot.json')['special_reserved_polygon_parts_xz_m'];clusters={c['id']:c for c in bulk['frontage_clusters']};cluster_of={h:c['id']for c in clusters.values()for h in c['holding_ids']};datums={};failed=[];allresults=[]
 for cid,c in clusters.items():
  evidence=[]
  for hid in c['holding_ids']:
   h=by_source[hid];road=roads.get(h['street_road_id'])
   if not road:continue
   q=nearest_road(h['street_connection_polyline_xz_m'][-1],road)[3];ev=samples.at(q)
   if ev:ev.update(source_holding_id=hid,public_road_id=road['id']);evidence.append(ev)
  if evidence:
   ev=sorted(evidence,key=lambda x:x['y_m'])[len(evidence)//2];datums[cid]=dict(floor_y_m=ev['y_m'],chosen_public_anchor=ev,all_public_anchors=evidence,policy='One coherent court datum selected from an actual protected public frontage triangle; finite entry profiles preserve every other road-edge value.')
 for block_id in dict.fromkeys(h['block_id']for h in bulk['non_B15_source_holdings']):
  if len(sys.argv)>1 and block_id not in sys.argv[1:]:continue
  config(blocks[block_id]);out=SOURCE/'coherent_regrade_r01'/block_id;out.mkdir(parents=True,exist_ok=True);g.HERE=out;x=((g.XS-float(base['bounds'][0]))/float(base['pitch'])).astype(int);z=((g.ZS-float(base['bounds'][1]))/float(base['pitch'])).astype(int);ms={k:base[k][g.np.ix_(z,x)]for k in base.files if base[k].ndim==2};special=g.raster(special_parts,True);hard=g.np.logical_or.reduce([ms[k]for k in['spaces','estates','water','wall','retained_native','retained_access']])|special;water_clear=g.ndimage.distance_transform_edt(~ms['water'])*g.GRID>4;domain=g.raster([t for t in g.triangulate(blocks[block_id]['polygon_xz_m'])]);allowed=domain&~hard&water_clear;placements=[];holdings=[];doors=[];used=g.np.zeros(g.SHAPE,bool);rows=[r for r in retire if r['block_id']==block_id]
  for hspec in [h for h in bulk['non_B15_source_holdings']if h['block_id']==block_id]:
   hs=by_source[hspec['source_holding_id']];cid=cluster_of[hs['id']]
   if cid not in datums:failed.append(dict(id=hs['id'],reason='No actual public source triangle found for the named frontage cluster'));continue
   floor=datums[cid]['floor_y_m'];center=hs['origin_xz_m'];yaw=hs['yaw_rad'];w,d=hs['holding_dimensions_m'];hp=hs['holding_polygon_xz_m'];hm=g.raster([hp]);grammar=hs['grammar_id'];hid=hs['id'].replace(':R8_P',':R8_C');components=[]
   if 'DOUBLE_RANGE' in grammar:
    variants=['working_r01_bank_joinery','working_r01_bank_loft_store','working_r01_bank_craft_lodging'];i=len(holdings);components=[(variants[i%3],[0,-8.5],0),(variants[(i+1)%3],[0,8.5],g.math.pi)];court=g.rect(-14.5,-3.25,14.5,3.25);target=hs['street_connection_polyline_xz_m'][-1];gates=[g.xform([sgn*w/2,0],center,yaw)for sgn in[-1,1]];gate=min(gates,key=lambda q:g.math.dist(q,target));entry_width=2.
   else:
    if 'CRAFT_U'in grammar:key='district_r01_craft_U';offset=[0,.5]
    elif 'DOMESTIC_L'in grammar:key='district_r01_domestic_L';offset=[0,.25]
    elif 'COMPACT_L'in grammar:key='district_r01_compact_L';offset=[0,-1.]
    else:key='working_r01_market_lodging';offset=[0,-2.]
    components=[(key,offset,0)];court=native[key]['court_local_polygon_xz_m']or g.rect(-10,5.5,10,d/2-1);court=[[q[0]+offset[0],q[1]+offset[1]]for q in court];gate=g.xform([0,d/2],center,yaw);entry_width=2.4 if roads[hs['street_road_id']]['width_m']<3.5 else 3.5
   pending=[];pd=[]
   for ci,(key,offset,ryaw)in enumerate(components):
    n=native[key];c=g.xform(offset,center,yaw);pyaw=yaw+ryaw;pid=hid+f':FABRIC:{ci+1}';foot=g.transform(n['foundation_local_polygons_xz_m'],c,pyaw);walk=g.transform(n['walking_local_polygons_xz_m'],c,pyaw);roof=g.transform(n['roof_local_polygons_xz_m'],c,pyaw)
    p=dict(id=pid,holding_id=hid,block_id=block_id,cluster_id=cid,asset_key=key,position_m=[c[0],floor-.5,c[1]],yaw_rad=pyaw,scale=[1,1,1],finished_floor_y_m=floor,palette_id=n['asset']['native_metadata']['palette'],source_pack='district_fabric_coherent_r01',native_foundation_polygons_xz_m=foot,native_walking_obstacles_xz_m=walk,native_roof_polygons_xz_m=roof,actual_door_ids=[],roof_area_m2=n['roof_area_m2'],foundation_area_m2=n['foundation_area_m2'],role=n['asset']['native_metadata']['role'],implementation_tier='exterior_only',activation_status='Coherent finite ground proposal; exact R17 regrade and integrated view pending')
    for d0 in n['doors']:
     dv=g.copy.deepcopy(d0);q=dv['actual_local_xyz_m'];wxz=g.xform([q[0],q[2]],c,pyaw);dv.update(id=pid+':'+dv['id'],parcel_id=pid,holding_id=hid,actual_door_xyz_m=[wxz[0],floor-.5+q[1],wxz[1]],outward_xz=g.xform(dv['outward_local_xz'],[0,0],pyaw),threshold_lip_xz_m=g.xform(dv['threshold_lip_local_xz_m'],c,pyaw),render_sha256=n['asset']['render_sha256'],exterior_route_width_m=min(2.,dv['exterior_route_width_m'])if len(components)>1 else dv['exterior_route_width_m']);pd.append(dv);p['actual_door_ids'].append(dv['id'])
    pending.append(p)
   exact_inside=all(abs(g.geo.intersection_area(q,hp)-g.geo.polygon_area(q))<1e-6 for p in pending for q in p['native_roof_polygons_xz_m'])
   if not exact_inside or g.np.any(hm&used)or g.np.any(g.raster([q for p in pending for q in p['native_roof_polygons_xz_m']],True)&(~allowed|ms['road'])):
    failed.append(dict(id=hs['id'],reason='Native fixed family would cross source holding, retained ownership, canonical road or previously allocated holding',native_inside=exact_inside));continue
   ids=[r['source_id']for r in rows if g.geo.intersection_area(r['actual_native_outer_footprint_xz_m'],hp)>1e-7]
   holdings.append(dict(id=hid,parcel_id=pending[0]['id'],component_placement_ids=[p['id']for p in pending],source_holding_id=hs['id'],cluster_id=cid,floor_y_m=floor,holding_polygon_xz_m=hp,core_court_polygons_xz_m=g.transform([court],center,yaw),gate_position_xz_m=gate,external_width_m=entry_width,public_road_id=hs['street_road_id'],public_target_xz_m=nearest_road(hs['street_connection_polyline_xz_m'][-1],roads[hs['street_road_id']])[3],retired_source_ids=ids,native_roof_area_m2=sum(p['roof_area_m2']for p in pending),holding_area_m2=g.geo.polygon_area(hp),planned_role=hs['role'],design='Coherent finite regraded shared court with fixed native attached frontages',ground_mode='bounded_cluster_regrade',court_datum_evidence=datums[cid]))
   placements+=pending;doors+=pd;used|=hm
  # All roofs precede external route search. Shared cluster lanes may use a
  # neighbour's same-datum court only with that explicit common ownership.
  obstacles=g.raster([q for p in placements for q in p['native_walking_obstacles_xz_m']],True);route_free=(domain|ms['road'])&~hard&~obstacles;route_fail=[]
  for h in holdings:
   w=h['external_width_m'];clear=g.ndimage.distance_transform_edt(route_free)*g.GRID>=w/2+.18;start=g.nearest(clear,h['gate_position_xz_m'],3);target=h['public_target_xz_m'];end=g.nearest(clear,target,2.5);goals=g.np.zeros(g.SHAPE,bool)
   if end:goals[end]=True
   line=g.astar(clear,start,goals)if start and end else None
   if not line:route_fail.append(dict(id=h['id'],reason='No full-width protected-owner-clear route to actual named public strip'));h.update(external_route=[],external_route_polygons_xz_m=[]);continue
   line=[h['gate_position_xz_m']]+line+[target];polys=g.ribbons(line,w);h.update(external_route=line,external_route_polygons_xz_m=polys,public_target_evidence=samples.at(target),public_join_status='Exact R17 source-road seam and <=12% graded profile pending')
   for r in rows:
    if any(g.geo.intersection_area(r['actual_native_outer_footprint_xz_m'],q)>1e-7 for q in polys):h['retired_source_ids'].append(r['source_id'])
   h['retired_source_ids']=sorted(set(h['retired_source_ids']))
  retired=sorted({i for h in holdings for i in h['retired_source_ids']});oldroof=sum(projection[r['source_id']]['roof_area_m2']for r in rows);removed=sum(projection[i]['roof_area_m2']for i in retired);newroof=sum(p['roof_area_m2']for p in placements)
  layout=dict(schema='riverstone.district_fabric.coherent_layout.v1',base_scene=g.ref(g.R7),source_plan=g.ref(plan/'fixed_family_bulk_contract.json'),native_local=g.ref(SOURCE/'native_local.json'),shared_private_routes=[],holdings=holdings,placements=placements,actual_doors=doors,retired_source_ids=retired,retirement_records=[r for r in rows if r['source_id']in retired],retired_foundation_proxy_ids=[i+':owned_foundation'for i in retired],ground_mode='bounded_cluster_regrade',cluster_court_datums={k:v for k,v in datums.items()if any(h['cluster_id']==k for h in holdings)},unresolved_external_routes=route_fail,summary=dict(holdings=len(holdings),native_instances=len(placements),native_roof_m2=newroof,holding_area_m2=sum(h['holding_area_m2']for h in holdings),actual_exterior_doors=len(doors),retired_ordinary_instances=len(retired),before_ordinary_roof_m2=oldroof,retired_ordinary_roof_m2=removed,after_ordinary_roof_m2=oldroof-removed+newroof,net_ordinary_roof_gain_m2=newroof-removed,shared_private_routes=0,unresolved_external_routes=len(route_fail)))
  g.write(out/'selected_layout.json',layout)
  for name in['native_local.json','compile_report.json']:(out/name).write_bytes((SOURCE/name).read_bytes())
  for name in['access','furnish']:
   src=(SOURCE/(name+'.py')).read_text()
   if name=='furnish':src=src.replace("holes=b['native_foundation_polygons_xz_m']+", "holes=[q for bp in layout['placements']if bp['holding_id']==h['id']for q in bp['native_foundation_polygons_xz_m']]+")
   mod=types.ModuleType(__package__+'.coherent_'+name);mod.__package__=__package__;exec(compile(src,str(SOURCE/(name+'.py')),'exec'),mod.__dict__);mod.run()
  g.write(out/'ground_proposal.json',dict(schema='riverstone.district_fabric.coherent_ground_proposal.v1',base_scene=g.ref(g.R7),layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'),clusters=[dict(id=cid,datum=datums[cid],holding_ids=[h['id']for h in holdings if h['cluster_id']==cid],ground_owner_polygons_xz_m=[h['holding_polygon_xz_m']for h in holdings if h['cluster_id']==cid],entry_routes=[dict(id=h['id']+':ENTRY',width_m=h['external_width_m'],polyline_xz_m=h['external_route'],polygons_xz_m=h['external_route_polygons_xz_m'],public_road_id=h['public_road_id'],public_target=h.get('public_target_evidence'))for h in holdings if h['cluster_id']==cid])for cid in datums if any(h['cluster_id']==cid for h in holdings)],retirement_records=layout['retirement_records'],retired_foundation_proxy_ids=layout['retired_foundation_proxy_ids'],policy='Atomic finite cluster regrade: remove only owned obsolete ordinary pads/banks, preserve protected public/water/special/native interfaces; support actual new native bottoms, keep full-width entrances <=12%, explicit nonwalking retaining edges at remaining discontinuities. No blanket block pad.',status='FINITE_NATIVE_SOURCE_REQUIRING_R17_GRADE_ACCEPTANCE'))
  allresults.append(dict(block_id=block_id,summary=layout['summary'],layout=g.ref(out/'selected_layout.json'),ground_proposal=g.ref(out/'ground_proposal.json')));print('COHERENT',block_id,layout['summary'],flush=True)
 index_path=SOURCE/'coherent_regrade_r01/bulk_index.json'
 if index_path.exists():
  prior=g.load(index_path);done={r['block_id']for r in allresults};allresults=[r for r in prior.get('districts',[])if r['block_id']not in done]+allresults
 g.write(index_path,dict(schema='riverstone.district_fabric.coherent_bulk_index.v1',source=g.ref(plan/'fixed_family_bulk_contract.json'),native_local=g.ref(SOURCE/'native_local.json'),districts=allresults,unfitted_source_holdings=failed,new_compiles=0,status='FINITE_NATIVE_SOURCE_REQUIRING_R17_GRADE_ACCEPTANCE'))
if __name__=='__main__':run()
