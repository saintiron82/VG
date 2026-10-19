"""Seven accepted finite interfaces; never consumes external_gate_links proposals."""
import pathlib,json,hashlib,sys,math,copy
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5';R15=CITY/'registered_topography/revisions/r15_merchant_local_patch';sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo
read=lambda p:json.loads(pathlib.Path(p).read_bytes())
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(pathlib.Path(p).resolve()),'sha256':sha(p)}
def write(p,d):
 with p.open('x') as f:json.dump(d,f,separators=(',',':'),allow_nan=False);f.write('\n')
def tri_y(t,x,z):
 a,b,c=t;dx1,dz1=b[0]-a[0],b[2]-a[2];dx2,dz2=c[0]-a[0],c[2]-a[2];den=dx1*dz2-dx2*dz1;u=((x-a[0])*dz2-(z-a[2])*dx2)/den;v=(dx1*(z-a[2])-dz1*(x-a[0]))/den
 return a[1]+u*(b[1]-a[1])+v*(c[1]-a[1])
def main():
 seal=read(R15/'subset_07/freeze_manifest.json')
 for r in seal['files']:assert sha(ROOT/r['path'])==r['sha256'],r['path']
 manifest=read(R15/'public_interfaces/accepted_subset_manifest.json');profiles=read(R15/'public_interfaces/accepted_public_profiles.json')['profiles'];pack=read(R15/'subset_07/merchant_pack.json');accept=read(R15/'subset_07/acceptance_report.json');assert len(profiles)==7 and len(pack['actual_doors'])==46
 for r in manifest['profiles']:assert sha(R15/'public_interfaces'/r['path'])==r['sha256']
 assert set(r['property_id'] for r in profiles)==set(accept['accepted_property_ids']);doors={r['id']:r for r in pack['actual_doors']};routes=[];selected=[]
 for p in profiles:
  prop=p['property_id'];candidates=[r for r in pack['access_proposals'] if r['property_id']==prop and 'goods_store' in r['id']];assert candidates,prop
  private=next((r for r in candidates if ':DOOR:0:' in r['id']),sorted(candidates,key=lambda r:r['id'])[0]);court=next(r for r in pack['courts'] if r['id']==prop+':SERVICE_COURT');door=doors[private['actual_door_id']]
  assert math.dist(private['polyline_xz_m'][0],door['threshold_lip_xz_m'])<1e-8
  gate=p['gate_polygon_xz_m'];inner=[(gate[0][i]+gate[1][i])/2 for i in range(2)];outer=[(gate[2][i]+gate[3][i])/2 for i in range(2)]
  assert math.dist(inner,private['polyline_xz_m'][-1])<1e-8
  heights=[tri_y(r['vertices_xyz_m'],*outer) for r in p['triangles'] if geo.point_in_convex_polygon(outer,r['polygon_xz_m'],1e-8)];assert heights and max(heights)-min(heights)<1e-6,(prop,heights)
  points=[[outer[0],sum(heights)/len(heights),outer[1]]]+[[x,p['property_floor_y_m'],z] for x,z in reversed(private['polyline_xz_m'])]
  inside=sum(geo.point_in_convex_polygon([v[0],v[2]],court['polygon_xz_m'],1e-8) for v in points);assert inside,prop
  r={'id':f'MERCHANT_{p["index"]:02d}_PUBLIC_TO_GOODS_DOOR_LIP','kind':'actual_scene_public_route','property_id':prop,'accepted_profile_index':p['index'],'points':points,'length_m':sum(math.dist(a,b) for a,b in zip(points,points[1:])),'source_road_ids':[p['road_id'],p['gate_id'],private['id'],court['id']],'actual_door_id':door['id'],'test_scope':'Accepted finite public interface, genuine private goods-store/court chain, exact exterior standing lip. Closed native leaf/interior not traversed.','minimum_allowed_feet_y_m':p['property_floor_y_m']-2,'placement_ids':[],'building_ids':[]};routes.append(r);routes.append(dict(copy.deepcopy(r),id=r['id']+'_REVERSE',points=list(reversed(points))))
  selected.append({'property_id':prop,'accepted_profile_index':p['index'],'gate_id':p['gate_id'],'private_route_id':private['id'],'actual_door_id':door['id'],'door_surface_world':door['actual_door_xyz_m'],'standing_lip_world':points[-1],'standing_lip_distance_from_native_leaf_m':math.dist(door['actual_door_xyz_m'],points[-1]),'source_waypoints_inside_court':inside,'native_threshold_status':door['threshold_status']})
 r02=read(BASE/'revisions/r02/prepared.json')
 for r in r02['routes'][:2]:
  r=copy.deepcopy(r);r['placement_ids']=[];r['building_ids']=[];routes.append(r)
 routes+=copy.deepcopy(r02['routes'][-2:])
 sources={name:ref(p) for name,p in {'subset_seal':R15/'subset_07/freeze_manifest.json','subset_acceptance':R15/'subset_07/acceptance_report.json','merchant_pack':R15/'subset_07/merchant_pack.json','merchant_patch':R15/'subset_07/scene_patch.json','accepted_interfaces':R15/'public_interfaces/accepted_public_profiles.json','accepted_interface_manifest':R15/'public_interfaces/accepted_subset_manifest.json','southern_seal':BASE/'revisions/r02/freeze_manifest.json','southern_profile':CITY/'assemblies/waterworks/registered_bridge/south_approach_r02/profile.json','southern_normalized_pack':CITY/'assemblies/waterworks/registered_bridge/south_approach_r02/normalized_resolved_placements.json'}.items()}
 write(H/'route_plan.json',{'schema':'riverstone.r6.merchant_subset_route_plan.v1','status':'source_plan_only_awaiting_parent_scene_hash','sources':sources,'routes':routes,'selected_private_chains':selected,'coverage':{'active_properties':7,'inactive_properties':12,'actual_door_branches':46,'tested_exterior_door_chains':7,'untested_door_branches':39,'merchant_positive_directions':14,'southern_regression_directions':2,'negative_controls':2,'total_cases':18},'limits':['No proposal-only external_gate_links data used. Accepted public profile geometry supplies start height only; composed actual-scene triangles will supply walking collision.','Each closed native door is approached to its exact exterior standing lip; no interior or door opening behavior is claimed.','Central leaves/hinges and the closed barrier 0.5 m gap are separate pending tests.','Do not run before parent supplies final composed scene hash and GUI release.']})
 print(json.dumps({'cases':len(routes),'coverage':{'merchant_directions':14,'southern_directions':2,'controls':2},'total_positive_length_m':sum(r['length_m'] for r in routes if 'expected_failure' not in r),'source_plan':ref(H/'route_plan.json')}))
if __name__=='__main__':main()
