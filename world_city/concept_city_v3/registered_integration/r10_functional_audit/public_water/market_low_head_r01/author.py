"""Independent low-head market draw candidate. Never edits frozen two-site pack."""
import copy,json,math
from pathlib import Path
from voxel_character.common import coordinate_planes,render_data
from ..author import B,R,S,SHA,ref,load,sha,box,component,fan
from ..select_sites import trans,rect
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.runtime_city.checks import placement as g
H=Path(__file__).resolve().parent;KEY='r10_market_low_head_draw'
def write(name,d):
 p=H/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def build():
 src=H.parent/'frozen_r01/masters/aboveground_drawhouse.json';m=load(src);m.update(id=KEY,revision=1)
 # Common receiving-basin, masonry box and hollow spout grammar, kept separate
 # from the original fountain; no tall storage tank or deep shaft is reused.
 basin=component('shallow_receiving_basin',[box('masonry_basin',[-.55,0,-.15],[.55,.4,.65],'stone_light'),box('open_receiving_volume',[-.4,.15,0],[.4,.5,.5],action='cut')])
 pillar=component('covered_feed_pillar',[box('protected_feed_marker',[-.25,0,-.8],[.25,1.1,-.3],'stone'),box('slate_cap',[-.3,1.1,-.85],[.3,1.2,-.25],'slate'),box('manual_stop_handle',[-.1,.65,-.35],[.1,.9,-.15],'iron_light')])
 spout=component('low_direct_outlet',[dict(id='hollow_spout_shell',action='paint',material='iron',part='solid',shape=dict(kind='tube',points=[[0,.45,-.35],[0,.45,.3]],radius=.12,minimum_radius_cells=0)),dict(id='open_mouth_bore',action='cut',part='solid',shape=dict(kind='tube',points=[[0,.45,-.35],[0,.45,.4]],radius=.075,minimum_radius_cells=0))])
 waste=component('separate_waste_receiver',[box('separate_receiver',[-1,0,.1],[-.65,.3,.6],'stone_dark'),box('receiver_clear',[-.93,.1,.17],[-.72,.4,.53],action='cut')])
 m['components']=[basin,pillar,spout,waste];m['instances']=[dict(id=c['id'],component=c['id'])for c in m['components']];m['constraints']=[dict(id=c['id']+'_present',kind='nonempty',selector={'component':c['id']})for c in m['components']]+[dict(id='front_standing_clear',kind='empty_region',selector={},shape=dict(kind='box',min=[-1,.05,.75],max=[1,2.2,1.5]))]
 m['extensions']=dict(status='independent_market_low_head_candidate',datum='Y0=actual market floorY4. No below-floor geometry.',local_bounds_m=dict(min=[-1,0,-.85],max=[.55,1.2,.65]),supply_head_world_y_m=4.6,low_outlet_local_y_m=.45,receiving_water_local_y_m=.3,maximum_receiving_water_local_y_m=.4,storage_role='Shallow open receiver, not a pressure tank. Masonry feed marker height does not imply a water level.',supply_relationship='Direct protected branch to low outlet. Receiver does not lift water to the outlet.',original_fountain='All original fountain native geometry, position, colors and upper static water remain untouched; no gravity-operation claim for its upper bowls.',water_quality_certified=False,hydraulic_simulation=False,runtime_interaction=False)
 m['provenance']=dict(source_common_family=ref(src),adaptation='Reuse the common low-basin, masonry and hollow-spout grammar with explicit low-head dimensions; no tall cistern reuse.',base_scene=ref(S),original_fountain_unchanged=True)
 write('masters/low_head_draw.json',m);c=coordinate_planes.compile_master(m,{'pitch':.05},max_candidate_cells=150000,max_output_cells=50000);assert c['valid'];render=render_data.make_render_data(c);write('cache/low_head_draw.render.json',render)
 audit=load(H/'source_audit.json');assert audit['status']=='PASS_SELECTED_FINITE_CANDIDATE';r=audit['results'][-1];q=r['candidate'];p=q['position_m'];yaw=q['yaw_rad'];scene=load(S);assert sha(S)==SHA
 edits={};paint=[]
 for key in ['ground','access']:
  for piece in r[key]['source_pieces']:
   if piece['material']in ['road','alley']:continue
   edits.setdefault((piece['material'],piece['triangle_index']),[]).append(piece['polygon_xz_m'])
 rows=[]
 for (mat,j),polys in sorted(edits.items()):
  tri=scene['surfaces'][mat][3*j:3*j+3];plane=a.common.plane(tri);orig=[[v[0],v[2]]for v in tri];remain=a.common.subtract([orig],polys);done=[]
  for poly in polys:
   for part in a.common.subtract([poly],done):paint.extend(v for t in fan(part,plane)for v in t)
   done.append(poly)
  rows.append(dict(material=mat,triangle_index=j,source_triangle_sha256=a.canonical_sha(tri),source_triangle_xyz_m=tri,replacement_triangles_xyz_m=[t for part in remain for t in fan(part,plane)]))
 waterpoly=trans(rect(-.38,.02,.38,.48),p,yaw);water=[v for t in fan(waterpoly,[0,0,4.3])for v in t]
 patch=dict(schema='riverstone.frozen_scene.local_surface_patch.v1',id='R10_MARKET_LOW_HEAD_DRAW_CANDIDATE',base_scene_sha256=SHA,source_surface_hashes={mat:a.canonical_sha(scene['surfaces'][mat])for mat in sorted({k[0]for k in edits}|{'water'})},surface_edits=rows,appended_surfaces={'ground_stone':paint,'water':water},removed_foundation_proxy_ids=[],ownership=[dict(id='R10_MARKET_LOW_DRAW',kind='public_market_draw_pocket',polygon_xz_m=q['footprint_xz_m'],floor_y_m=4,source_owner='Existing public market space, no registered private plot overlap'),dict(id='R10_MARKET_LOW_DRAW:BRANCH',kind='public_2m_branch',polygon_xz_m=q['branch_polygon_xz_m'],floor_y_m=4)],summary=dict(pocket_area_m2=9,branch_width_m=2,branch_length_m=q['branch_length_m'],source_triangles_edited=len(rows),road_triangles_edited=0,existing_fountain_changed=False,existing_stalls_moved=0,excavation_depth_m=0))
 write('surface_patch.json',patch)
 asset=dict(master_path=str((H/'masters/low_head_draw.json').relative_to(R)),master_sha256=sha(H/'masters/low_head_draw.json'),render_path=str((H/'cache/low_head_draw.render.json').relative_to(R)),render_sha256=sha(H/'cache/low_head_draw.render.json'),bounds=render['bounds'],pitch_m=.05,quad_count=render['quad_count'])
 target=trans([[0,1.05]],p,yaw)[0];points=q['branch_points_xyz_m']+[[target[0],4,target[1]]];camera=trans([[5,8]],p,yaw)[0]
 write('pack.json',dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=SHA,common_assets={KEY:asset},add_instances=[dict(id='R10_MARKET_LOW_DRAW',asset_key=KEY,position_m=p,yaw_rad=yaw,scale=[1,1,1],palette_id='slate_gray',palette_override={},source_pack='r10_market_low_head_candidate')],remove_instance_ids=[],replace_instances=[],inspection_cameras={'r10_market_low_draw':dict(position_m=[camera[0],9,camera[1]],target_m=[p[0],4.5,p[2]],ortho_size_m=19,render_size_px=[1536,1024])},local_surface_patch=ref(H/'surface_patch.json'),status='INDEPENDENT_CANDIDATE_NOT_INCLUDED_IN_TWO_SITE_FROZEN_PACK'))
 write('routes.json',dict(base_scene_sha256=SHA,status='NOT_REPLAYED',routes=[dict(id='R10_MARKET_LOW_DRAW:PUBLIC_APPROACH',group='market_low_head',public_road_id=q['public_road_id'],source_road_ids=[q['public_road_id']],points=points,points_xyz_m=points,width_m=2,clear_width_m=2,placement_ids=['R10_MARKET_LOW_DRAW'],bidirectional=True,source_supported_floor_y_m=4,source_station_xyz_m=q['public_station_xyz_m'])]))
 write('design_ledger.json',dict(status='AUTHORED_NATIVE_AND_FINITE_SURFACE_CANDIDATE',native_compile=dict(valid=True,pitch_m=.05,candidate_cells=c['candidate_cells'],output_cells=len(c['cells']),quad_count=render['quad_count'],bounds=render['bounds']),supply_head_y_m=4.6,direct_outlet_y_m=4.45,nominal_receiving_surface_y_m=4.3,maximum_receiving_surface_y_m=4.4,static_head_margin_to_outlet_m=.15,receiver_continuous_nominal_volume_m3=.8*.5*(.3-.15),design_residents=6000,supply_scope='Direct protected feed interface only; receiver volume is not source delivery or city capacity.',implemented=['Common native shallow receiving basin','Low hollow outlet and static manual stop marker','Separate waste cup','Finite same-height public pocket and2m branch','Original fountain and66market stalls retained'],concept_only=['Protected replenishment branch and connection to existingY4.6 source','Manual valve function, cleaning and emptying waste cup'],missing=['Hydraulic losses and flow','Potability and source yield','Runtime/visual validation','6,000-resident demand sufficiency'],limits=['No gravity feed to existing upper bowls is asserted.','The0.15m ideal static head margin may be consumed by losses; operation is not certified.','Independent proposed candidate, not activated or counted in the first two draw stations.']))
 print('MARKET CANDIDATE',len(c['cells']),render['quad_count'],'source faces',len(rows))
if __name__=='__main__':build()
