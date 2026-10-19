"""Two reversible public draw pockets, shared common master and native RenderData.
All outputs are local to this package. Source scene/plan are immutable.
"""
from __future__ import annotations
import copy,json,math,hashlib,sys
from pathlib import Path
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import frozen_r6 as f
from world_city.runtime_city.checks import placement as g
from .select_sites import H,R,B,N,S,SHA,load,trans,rect
KEY='r10_public_aboveground_drawhouse'
def write(name,d):
 p=H/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(R)),sha256=sha(p))
def fan(poly,plane):return f.fan_upward(f.lift(poly,plane))
def box(id,lo,hi,material='stone',action='paint'):return dict(id=id,action=action,part='solid',**({'material':material}if action=='paint'else{}),shape=dict(kind='box',min=lo,max=hi))
def component(id,ops):return dict(id=id,parts=[dict(id='solid',pivot=[0,0,0])],operations=ops)
def native_master():
 source=B/'assemblies/waterworks/masters/covered_wellhouse.json';base=load(source);parts={c['id']:c for c in base['components']};m=copy.deepcopy(base)
 m.update(id=KEY,revision=1)
 # The common lining, four posts, and slate roof remain the grammar. No shaft.
 shell=copy.deepcopy(parts['shaft']);shell['id']='sealed_tank';op=shell['operations'][0];op['id']='aboveground_lined_cistern';op['shape'].update(inner_radius=.6,outer_radius=.9,y_min=.2,y_max=1.8);op['transform']={'translation':[0,0,-.9]}
 shell['operations'] += [dict(id='closed_bottom',action='paint',material='stone_dark',part='solid',shape=dict(kind='annulus',inner_radius=0,outer_radius=.9,y_min=0,y_max=.3),transform={'translation':[0,0,-.9]}),dict(id='sealed_lid',action='paint',material='stone_light',part='solid',shape=dict(kind='annulus',inner_radius=0,outer_radius=1.,y_min=1.8,y_max=2),transform={'translation':[0,0,-.9]}),box('inspection_cap',[-.25,2,-1.15],[.25,2.15,-.65],'iron')]
 bowl=component('low_receiving_basin',[box('basin_body',[-.5,0,0],[.5,.6,.6],'stone_light'),box('basin_clear',[-.3,.2,.1],[.3,.7,.5],action='cut')])
 # A fixed low draw socket and visible hand lever. No pretend running jet.
 spout=component('low_draw_spout',[dict(id='outlet',action='paint',material='iron',part='solid',shape=dict(kind='tube',points=[[0,.9,-.1],[0,.9,.3],[0,.8,.3]],radius=.18,minimum_radius_cells=0)),dict(id='open_spout_bore',action='cut',part='solid',shape=dict(kind='tube',points=[[0,.9,-.1],[0,.9,.3],[0,.7,.3]],radius=.1,minimum_radius_cells=0)),box('manual_lever',[-.1,.95,-.15],[.1,1.25,.05],'iron_light')])
 drain=component('separate_waste_receiver',[box('waste_cup',[-1.1,0,0],[-.6,.4,.6],'stone_dark'),box('waste_cup_clear',[-1,.15,.1],[-.7,.5,.5],action='cut'),dict(id='basin_drain_socket',action='paint',material='iron',part='solid',shape=dict(kind='tube',points=[[-.4,.3,.3],[-.65,.3,.3]],radius=.1,minimum_radius_cells=0))])
 inlet=component('covered_inlet',[box('covered_supply_socket',[-.2,1.2,-2],[.2,1.6,-1.7],'stone_dark'),box('inlet_cap',[-.2,1.6,-2],[.2,1.8,-1.7],'iron')])
 m['components']=[shell,copy.deepcopy(parts['frame']),copy.deepcopy(parts['roof']),bowl,spout,drain,inlet];m['instances']=[dict(id=c['id'],component=c['id'])for c in m['components']]
 m['constraints']=[dict(id=c['id']+'_present',kind='nonempty',selector={'component':c['id']})for c in m['components']]+[dict(id='standing_queue_clear',kind='empty_region',selector={},shape=dict(kind='box',min=[-1,.1,.7],max=[1,2.2,1.9]))]
 m['extensions']=dict(status='r10_aboveground_candidate',datum='Y=0 actual dry ground; no material below Y=0; public stone floor is a finite flush terrain owner, not a buried platform.',local_bounds_m={'min':[-2,0,-2],'max':[2,4.2,2]},footprint_xz_m=rect(-2,-2,2,2),nominal_storage_water_local_y_m=1.4,low_outlet_local_y_m=.8,receiving_bowl_water_local_y_m=.35,queue_clear_local_polygon_xz_m=rect(-1,.7,1,2),reused_components=['covered_wellhouse.frame unchanged','covered_wellhouse.roof unchanged','covered_wellhouse.shaft annular lining shortened and raised, closed floor and lid'],omitted_source_components=['subsurface shaft','windlass','buried platform'],network='protected_supply_concept_only',sockets=[dict(id='covered_replenishment',position_m=[0,1.4,-2],role='Separate covered supply branch candidate, no flow claim'),dict(id='low_draw',position_m=[0,.8,.3],role='Open-mouthed low spout; stationary closed valve interface, no running fluid'),dict(id='waste_receiver',position_m=[-.85,.3,.3],role='Separate removable waste receiver, never connected to protected inlet')],fluid_surface_owner='Two finite non-colliding water surfaces per location; internal storage plane hidden by lid, small bowl surface exposed.',actual_placed=False,visually_reviewed=False,hydraulic_simulation=False,potable_certification=False)
 m['provenance']=dict(reused_source=ref(source),reuse='Unchanged common frame and slate roof; source annulus grammar adapted into an entirely aboveground closed tank. Added common box/tube bowl, cap, low spout and separate waste receiver.',new_mesher=False,new_engine=False,source_plan=ref(B/'registered_source/plan.json'),limits=['Static candidate; operation, source delivery, cleaning and drain disposal are design responsibilities, not runtime systems.'])
 write('masters/aboveground_drawhouse.json',m)
 c=coordinate_planes.compile_master(m,{'pitch':.1},max_candidate_cells=250000,max_output_cells=100000);assert c['valid'],c.get('constraint_results');r=render_data.make_render_data(c);write('cache/aboveground_drawhouse.render.json',r)
 occupied={tuple(row[:3])for row in c['cells']};p=.1;origin=c['grid_origin'];nominal_void=0;max_void=0
 for ix in range(-6,6):
  for iz in range(-15,-3):
   x,z=origin[0]+(ix+.5)*p,origin[2]+(iz+.5)*p
   if x*x+(z+.9)**2>=.6**2:continue
   for iy in range(3,18):
    if (ix,iy,iz)not in occupied:
     max_void+=1
     if iy<14:nominal_void+=1
 write('storage_geometry.json',dict(local_inner_radius_m=.6,bottom_inner_surface_y_m=.3,nominal_water_y_m=1.4,maximum_internal_ceiling_y_m=1.8,continuous_nominal_storage_m3=math.pi*.6**2*(1.4-.3),continuous_full_internal_cavity_m3=math.pi*.6**2*(1.8-.3),native_nominal_empty_cells=nominal_void,native_nominal_storage_m3=nominal_void*p**3,native_full_internal_empty_cells=max_void,native_full_internal_cavity_m3=max_void*p**3,method='Count empty 0.1m common cells in the sealed cylindrical interior between bottom and target water plane. Exterior, basin, wall and pipe cells excluded. Useful operation, turnover and replenishment capacity are not inferred.',resident_count_design=6000,capacity_claim='Local intermediate storage only; no autonomy, daily demand, source yield, supply flow or city adequacy claim.'))
 write('compile_report.json',dict(status='PASS',compiler='voxel_character.common.coordinate_planes.compile_master + render_data.make_render_data',pitch_m=.1,candidate_cells=c['candidate_cells'],output_cells=len(c['cells']),quad_count=r['quad_count'],bounds=r['bounds'],minimum_native_y_m=r['bounds']['min'][1],source=ref(H/'masters/aboveground_drawhouse.json'),cache=ref(H/'cache/aboveground_drawhouse.render.json'),queue_clear_constraint='PASS',material_below_ground=False))
 return m,r

def parcel_overlay(selected):
 plan=load(B/'registered_source/plan.json');parcel=next(p for p in plan['plots']if p['id']=='P_REG_0668');poly=parcel['polygon_xz_m'];masks=[];newdomains=[]
 for row in selected['sites']:
  for kind,key in [('pocket','footprint_xz_m'),('branch','branch_polygon_xz_m')]:
   mask=row[key];masks.append(mask);newdomains.append(dict(id='R10_PUBLIC_DRAW:'+str(row['site'])+':'+kind,polygon_xz_m=mask,area_m2=g.polygon_area(mask),source_parcel_intersection_m2=g.polygon_area(g.convex_intersection(poly,mask))))
 remaining=a.common.subtract([poly],masks);area_before=g.polygon_area(poly);area_after=sum(g.polygon_area(p)for p in remaining);front=parcel['frontage_reservation_polygon_xz_m'];front_area=g.polygon_area(front)
 gate_ribbon=g.road_ribbon(parcel['gate_position_xz_m'],parcel['gate_connection_xz_m'],2)
 gate_body_intersections=[g.polygon_area(g.convex_intersection(gate_ribbon,row['footprint_xz_m']))for row in selected['sites']]
 assert max(gate_body_intersections)==0
 write('parcel_ownership_overlay.json',dict(schema='riverstone.finite_parcel_public_carveout.v1',source_plan=ref(B/'registered_source/plan.json'),status='AUTHORED_REVERSIBLE_BOUNDARY_AND_SURFACE_CHANGE',original_parcel=parcel,replace_parcel_geometry=[dict(id='P_REG_0668',before_polygon_xz_m=poly,after_disjoint_polygons_xz_m=remaining,before_area_m2=area_before,after_area_m2=area_after,public_carveout_area_m2=area_before-area_after)],new_public_domains=newdomains,original_frontage=dict(polygon_xz_m=front,area_m2=front_area,shared_flush_public_branch_area_m2=sum(g.polygon_area(g.convex_intersection(front,row['branch_polygon_xz_m']))for row in selected['sites']),retained_world_height_m=1,gate_position_xz_m=parcel['gate_position_xz_m'],gate_connection_xz_m=parcel['gate_connection_xz_m'],gate_body_intersections_m2=gate_body_intersections,walkable_geometry_policy='Old frontage remains a same-height traversable surface. The branch changes finish/ownership only; no blocker, wall, step or gate is inserted across it.'),physical_boundary_implementation='The new public polygon is paved by surface_patch.json with its exact finite boundary. No wall/fence intersects either new body or branch under complete native bounds screening, so no fictional wall opening is claimed.',building_support_policy='No building moved/removed; source support heights and existing holes unchanged. Surface repaint is flush, and body/branch do not intersect existing native volumes.',reversal='Drop this overlay, surface patch, native pack and water extension; source plan and source scene were never overwritten.'))

def build():
 m,r=native_master();print('native',r['cell_count'],r['quad_count'],flush=True)
 selected=load(H/'selected_sites.json');assert selected['status']in ['PASS_TWO_FINITE_POCKETS','PASS_FINITE_POCKETS'];scene=load(S);assert sha(S)==SHA
 asset=dict(master_path=str((H/'masters/aboveground_drawhouse.json').relative_to(R)),master_sha256=sha(H/'masters/aboveground_drawhouse.json'),render_path=str((H/'cache/aboveground_drawhouse.render.json').relative_to(R)),render_sha256=sha(H/'cache/aboveground_drawhouse.render.json'),bounds=r['bounds'],pitch_m=.1,source_pack='r10_public_water')
 edits={};add=[];owners=[];placements=[];cameras={};water=[];routes=[];head=[]
 for row in selected['sites']:
  sid='R10_PUBLIC_DRAW:'+str(row['site']);p=row['position_m'];yaw=row['yaw_rad'];placements.append(dict(id=sid,asset_key=KEY,position_m=p,yaw_rad=yaw,scale=[1,1,1],palette_id='slate_gray',palette_override={},source_pack='r10_public_water',function='public_aboveground_closed_storage_low_manual_draw',access_policy='Public open frontage; no institution gate crossing'))
  masks=[row['footprint_xz_m'],row['branch_polygon_xz_m']];owners.append(dict(id=sid,kind='public_draw_pocket',polygon_xz_m=row['footprint_xz_m'],floor_y_m=p[1],queue_polygon_xz_m=row['queue_polygon_xz_m'],existing_plot_ids=row['boundary_ownership']['footprint_existing_plot_ids'],ownership_policy='Explicit finite P_REG_0668 corner subtraction where present; all other plots and every actual road surface triangle retained.'))
  owners.append(dict(id=sid+':BRANCH',kind='public_2m_branch',polygon_xz_m=row['branch_polygon_xz_m'],floor_y_m=p[1],road_id=row['road']))
  # Source polygons are repainted once only on non-road material. Native foot
  # contacts sit on the retained height, so no excavation or elevated threshold.
  for key in ['ground','access']:
   for piece in row[key]['source_pieces']:
    if piece['material'] in ['road','alley']:continue
    k=(piece['material'],piece['triangle_index']);edits.setdefault(k,[]).append(piece['polygon_xz_m'])
  local_queue=[0,1.0];q=trans([local_queue],p,yaw)[0];route=row['branch_points_xyz_m']+[[q[0],p[1],q[1]]];routes.append(dict(id=sid+':PUBLIC_APPROACH',public_road_id=row['road'],station_xyz_m=row['station_xyz_m'],points_xyz_m=route,width_m=2,clear_queue_width_m=2,clear_queue_area_m2=2.6,implementation='finite source-supported branch and standing area; controller replay pending'))
  for poly,y in [(trans([[.55*math.cos(i*math.pi/8),-.9+.55*math.sin(i*math.pi/8)]for i in range(16)],p,yaw),p[1]+1.4),(trans(rect(-.28,.12,.28,.48),p,yaw),p[1]+.35)]:water.extend(v for t in fan(poly,[0,0,y])for v in t)
  camera=trans([[9,12]],p,yaw)[0];cameras['r10_public_draw_'+str(row['site'])]=dict(position_m=[camera[0],p[1]+9,camera[1]],target_m=[p[0],p[1]+1,p[2]],ortho_size_m=23,render_size_px=[1536,1024])
  head.append(dict(id=sid,position_m=p,upstream_node='COVERED_CISTERN',upstream_head_y_m=15.5,local_storage_water_y_m=p[1]+1.4,head_margin_m=15.5-(p[1]+1.4),low_draw_y_m=p[1]+.8,receiving_bowl_y_m=p[1]+.35,implemented_geometry=['closed tank and lid','covered inlet socket','low outlet and receiving bowl','physically separate waste receiver'],concept_only=['covered branch from source node to inlet','manual replenishment stop and cleaning regime','emptying waste receiver away from source and public approach'],missing=['real source branch construction','flow and pressure loss','water quality and storage turnover','runtime valve interaction'],drain_policy='Waste receiver is disconnected from the protected inlet. No outfall to process canal, road or groundwater is asserted. Manual emptying remains an operational requirement.'))
 outedits=[]
 for (material,j),polys in sorted(edits.items()):
  t=scene['surfaces'][material][3*j:3*j+3];plane=a.common.plane(t);orig=[[v[0],v[2]]for v in t];remain=a.common.subtract([orig],polys);done=[]
  for poly in polys:
   for part in a.common.subtract([poly],done):add.extend(v for tri in fan(part,plane)for v in tri)
   done.append(poly)
  outedits.append(dict(material=material,triangle_index=j,source_triangle_sha256=a.canonical_sha(t),source_triangle_xyz_m=t,replacement_triangles_xyz_m=[tri for part in remain for tri in fan(part,plane)]))
 patch=dict(schema='riverstone.frozen_scene.local_surface_patch.v1',id='R10_PUBLIC_DRAW_POCKETS',base_scene_sha256=SHA,source_surface_hashes={key:a.canonical_sha(scene['surfaces'][key])for key in sorted({key for key,j in edits}|{'water'})},surface_edits=outedits,appended_surfaces={'ground_stone':add,'water':water},removed_foundation_proxy_ids=[],ownership=owners,summary=dict(facility_count=len(placements),flush_pocket_area_m2=16*len(placements),queue_area_m2=2.6*len(placements),source_triangles_edited=len(outedits),existing_road_triangles_edited=0,existing_plot_boundaries_changed=1,excavation_depth_m=0,source_heights_changed=False))
 write('surface_patch.json',patch);parcel_overlay(selected);write('water_extension.json',dict(base_water_sha256=a.canonical_sha(scene['surfaces']['water']),append_vertices_xyz_m=water,owner_ids=[p['id']for p in placements],collision=False,already_included_in_surface_patch=True,apply_separately=False,policy='Finite static local storage and receiving-bowl surfaces only; no opaque water voxels and no running flow.'))
 write('pack.json',dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=SHA,common_assets={KEY:asset},remove_instance_ids=[],replace_instances=[],add_instances=placements,inspection_cameras=cameras,local_surface_patch=ref(H/'surface_patch.json'),water_extension=ref(H/'water_extension.json'),parcel_ownership_overlay=ref(H/'parcel_ownership_overlay.json'),integration_requirements=['Apply finite surface patch (includes water vertices) as well as native instances. water_extension.json is the water ledger and must not be appended a second time.','Source-index conflicts with other patches must be composed geometrically.']))
 write('routes.json',dict(schema='riverstone.public_draw_routes.v1',base_scene_sha256=SHA,routes=routes,activation='SOURCE_STATIC_PASS_RUNTIME_REPLAY_PENDING'))
 write('service_head_ledger.json',dict(sites=head,source_graph=ref(B/'assemblies/waterworks/registered_water_completion_r01/head_graph_and_asset_associations.json'),source_head_semantics='15.5m is the protected conceptual source head, not an exposed water surface or guarantee of capacity. Positive static head margin alone does not certify operation.',market_fountain_correction='Existing upper bowl Y6.1 remains above its stated inletY4.6. Keep upper bowl dry/manual-fill, or author a distinct lower receiving surface no higher thanY4.4; no new pressure head is invented.'))
 print('pack ready',len(placements),'edits',len(outedits),'appended triangles',len(add)//3,flush=True)
if __name__=='__main__':
 if '--master-only' in sys.argv:native_master()
 else:build()
