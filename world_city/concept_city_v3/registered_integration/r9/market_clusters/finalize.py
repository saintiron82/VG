"""Compact integration and replay handoff, without changing any shared consumer."""
import collections,copy,math
from .author import *
from .route_links import path_clear

def build():
 ctx=Context();pack=load(HERE/'pack.json');layout=load(HERE/'layout.json');assert layout['status']=='STATIC_LINKS_PASS'
 for p in pack['add_instances']:ctx.solids.append(dict(id=p['id'],polygon=p['footprint_xz_m'],y_min=3.5,y_max=p['native_top_y_m'],source='candidate'))
 ctx.reindex();checks=[]
 for name,cid in [('r9_market_grain_court_eye','GRAIN_WEST'),('r9_market_textile_court_eye','TEXTILE_SOUTH')]:
  r=next(r for r in layout['routes'] if r['cluster_id']==cid and r['route_type']=='customer' and ':02L:' in r['id']);p=next(p for p in pack['add_instances'] if p['id']==r['stall_id']);x,_,z=r['points_xyz_m'][0]
  eye=[x,5.65,z];target=local(p,0,-2,2.6);hits=ctx.blocked(square(x,z,.3),4,5.8);assert not hits
  pack['inspection_cameras'][name]=dict(position_m=eye,target_m=target,eye_height_m=1.65,source_route=r['id'],purpose='New statically clear customer eye; post-integration visual review required.')
  checks.append(dict(id=name,route_id=r['id'],standing_clear=True,ground_support=ctx.height(x,z)))
 # The frozen cargo pack has one historical customer-eye camera. Its pose stays clear,
 # but its old source-link attribution is retired in this candidate.
 cargo=load(HERE.parent/'port_market/pack_r02.json')
 for name,c in cargo.get('inspection_cameras',{}).items():
  if 'market' not in name or 'eye' not in name:continue
  x,y,z=c['position_m'];hits=ctx.blocked(square(x,z,.3),4,5.8)
  checks.append(dict(id=name,position_m=c['position_m'],standing_clear=not hits,solid_hits=hits,source_link_status='Historic old104 attribution retired. Use new cluster-eye cameras for new-link evidence.'))
 write('pack.json',pack);write('camera_checks.json',dict(cameras=checks))
 runtime=[]
 for r in layout['routes']:
  runtime.append(dict(id=r['id'],kind='market_cluster_customer' if r['route_type']=='customer' else 'market_cluster_service',points=r['points_xyz_m'],source_width_m=r['width_m'],minimum_allowed_feet_y_m=3.7,bidirectional=True,source_road_ids=[r['entrance_target']['source_road_id']],placement_ids=[r['stall_id']],group=r['cluster_id'],test_scope='New local market link, at actual sampled Y=4; pedestrian capsule only unless a separate cart test is implemented.',activation_condition='Apply market_clusters/pack.json in place of canopy-only pack. Never replay these links against r01 market geometry.'))
 selected=[]
 for g in layout['clusters']:
  for typ in ['customer','service']:
   chosen=max((r for r in layout['routes'] if r['cluster_id']==g['id'] and r['route_type']==typ),key=lambda r:r['length_m']);selected.append(chosen['id'])
 write('runtime_routes.json',dict(schema='riverstone.market.cluster_runtime_candidates.v1',status='NOT_REPLAYED',base_scene_sha256=BASE_SHA,pack=ref(HERE/'pack.json'),routes=runtime,unique_routes=132,directional_cases_if_expanded=264,recommended_first_pass_route_ids=selected,recommended_first_pass_directional_cases=28,unchanged_certified_493_source=next(r for r in ctx.c['source_refs'] if 'selected_all493_bound' in r['path'])))
 ledger=[];used={p['source_original_instance_id']:p for p in pack['add_instances']}
 for old in ctx.c['old_stalls']:
  p=used.get(old['id']);ledger.append(dict(source_id=old['id'],source_asset=old['asset_key'],source_position_m=old['position_m'],source_yaw_rad=old['yaw_rad'],candidate_id=p['id'] if p else None,disposition='Relocated rigid native stall with canopy variant' if p else 'Retired to open circulation and loading space',candidate_position_m=p['position_m'] if p else None,candidate_yaw_rad=p['yaw_rad'] if p else None))
 write('source_instance_ledger.json',dict(base_scene_sha256=BASE_SHA,old_stall_count=104,new_stall_count=66,retired_without_relocation=38,source_id_reuse_under_add_instances=False,ledger=ledger))
 report=dict(schema='riverstone.market.cluster_static_review.v1',status='PASS_STATIC_ONLY',source_refs=ctx.c['source_refs'],context=ref(HERE/'source_context.json'),pack=ref(HERE/'pack.json'),cluster_count=7,old_stalls_removed=104,new_stalls_added=66,old_customer_links_retired=104,new_customer_links=66,new_service_links=66,source_public_catalog_unique_routes=254,exact_certified_directional_paths_preserved_by_static_exclusion=493,public_route_geometry_changed=False,fountain_gathering_radius_m=10,base_fountain_pose_changed=False,frozen_cargo_changed=False,native_asset_count=9,new_native_compiles=0,native_scale=[1,1,1],stall_footprint_support_samples=594,local_route_support_samples=sum(r['support_sample_count'] for r in layout['routes']),new_geometry_route_conflicts=0,new_geometry_solid_conflicts=0,new_local_link_solid_conflicts=0,grounding='All new stalls use original Y=4 native datum; native foot extension occupies Y=3.5 to4, same 0.5m embed as the original stalls. No terrain or road changes.',limits=['All 66 stall poses and their occupied world low geometry move. Canopy-only pose/low-volume invariance does not apply to this candidate.','The old104 per-stall paths are retired, not preserved. The separate certified493 route geometry is preserved by exact exclusions.','Customer/service definitions are sidecar data. The current renderer consumes the visual pack only; the parent must explicitly select runtime_routes.json for physical replay and update any future NPC path consumer.','3m rear-service clearance is a static corridor check, not a wheeled-cart turning, loading, dispatch or economy simulation. No native cart asset was added.','Actual integrated root visual review and new physics replay remain pending; old r01 screenshot and runtime certification are not new-candidate approval.'])
 write('static_clearance_report.json',report)
 print('finalized',report['new_stalls_added'],'stalls',len(runtime),'routes')
if __name__=='__main__':build()
