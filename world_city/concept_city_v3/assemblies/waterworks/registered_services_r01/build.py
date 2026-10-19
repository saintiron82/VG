"""Three source-bound protected draw cisterns using the existing common wellhouse."""
import copy,json,math
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a,side_clearance
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import frozen_r6 as f
from .select_drawhouses import HERE,CITY
ROOT=CITY.parents[1]
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':'),allow_nan=False)+'\n')
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=a.sha(p))
def fan(poly,plane):return f.fan_upward(f.lift(poly,plane))
def run():
 print('load',flush=True);scene=a.load_scene();locations=json.loads((HERE/'retained_entry_location_candidates.json').read_text());proof=json.loads((HERE/'public_continuation.json').read_text());proofs={r['fixture_id']:r for r in proof['fixtures']};assert len(proofs)==3 and all(r['status']=='PASS'for r in proofs.values())
 for r in locations['drawhouses']:
  r['public_continuation']=proofs[r['id']];r['public_road_id']='RETAINED_LANDMARK_ENTRY:'+proofs[r['id']]['group_id'];r['public_road_ids']=proofs[r['id']]['named_public_road_ids']
 locations['status']='THREE_NAMED_ENTRY_CONNECTED_SOURCE_CANDIDATES';locations['limits']=['Whole-width local fixture approach proven against actual R7 ground and retained banks.','Retained named entry continuation is proved by positive-length actual XYZ top edges to public landing.','Runtime character replay and potable/hydraulic certification are not claimed.'];write(HERE/'locations.json',locations);valid=locations['drawhouses']
 master=copy.deepcopy(json.loads((HERE.parent/'masters/covered_wellhouse.json').read_text()));master['id']='registered_services_closed_cistern';master['revision']=1
 master['components'].append(dict(id='cistern_bottom',parts=[dict(id='solid',pivot=[0,0,0])],operations=[dict(id='cistern_bed',action='paint',material='stone_dark',part='solid',shape=dict(kind='box',min=[-1.1,-2.6,-1.1],max=[1.1,-2.4,1.1]))]));master['instances'].append(dict(id='cistern_bottom',component='cistern_bottom'))
 master['extensions'].update(status='finite_registered_cistern_source_candidate',fluid_surface_owner='Separate finite water polygon in local scene patch; no opaque water cells.',actual_placed=False);master['extensions']['local_bounds_m']['min'][1]=-2.6
 master['provenance']['registered_adaptation']=dict(source=ref(HERE.parent/'masters/covered_wellhouse.json'),change='Add only a closed masonry cistern bed; existing wellhouse geometry and material family reused.',head='Stored water is 2m below dry ground; manual bucket draw. Network pressure head is not exposed groundwater.')
 mp=HERE/'masters/closed_cistern.json';write(mp,master);c=coordinate_planes.compile_master(master,{'pitch':.2},max_candidate_cells=400000,max_output_cells=120000);assert c['valid'];render=render_data.make_render_data(c);rp=HERE/'cache/closed_cistern.render.json';write(rp,render)
 print('compiled',len(c['cells']),flush=True);windows=[r['footprint_xz_m']for r in valid]+[p for r in valid for p in r['walk_polygons_xz_m']];si=side_clearance.SideIndex(scene,windows);owners=[]
 for row in valid:
  for k in ('ground','access'):owners += [dict(id=row['id']+':'+k+':'+str(i),polygon_xz_m=p['polygon_xz_m'],plane_y_xz_m=p['plane_y_xz_m'])for i,p in enumerate(row[k]['source_pieces'])]
 print('bank audit',len(owners),flush=True);side=si.audit(owners);write(HERE/'vertical_clearance.json',side);assert side['status']=='PASS',side['contacts'][:3]
 print('bank pass',flush=True);edited={};placements=[];water=[];walk_masks=[];platform_masks=[]
 for row in valid:
  x,y,z=row['position_m'];placements.append(dict(id='REGISTERED_SERVICES:'+row['id'],asset_key=master['id'],position_m=[x,y,z],yaw_rad=0,palette_id='slate_gray',scale=[1,1,1],function='protected_stored_water_manual_draw',implementation_tier='exterior_only',draw_point_xyz_m=[x,y+1.1,z],water_head_y_m=y-2,external_access=row['walk_centerline_xz_m'],public_entry=row['public_road_id'],public_road_ids=row['public_road_ids']));platform_masks.append(row['footprint_xz_m']);walk_masks.extend(row['walk_polygons_xz_m'])
  for key in ('ground','access'):
   for piece in row[key]['source_pieces']:
    k=(piece['material'],piece['triangle_index']);edited.setdefault(k,dict(cuts=[],walks=[]))
    if key=='ground':edited[k]['cuts'].append(row['footprint_xz_m'])
    elif piece['material']not in ('road','alley'):edited[k]['walks'].append(piece['polygon_xz_m'])
  poly=[[x+.55*math.cos(2*math.pi*i/16),z+.55*math.sin(2*math.pi*i/16)]for i in range(16)];water += [v for t in fan(poly,[0,0,y-2])for v in t]
 print('assembled',len(edited),flush=True);edits=[];path_vertices=[]
 for (material,j),masks in edited.items():
  if not masks['cuts'] and not masks['walks']:continue
  print('edit',material,j,len(masks['cuts']),len(masks['walks']),flush=True);tri=scene['surfaces'][material][3*j:3*j+3];plane=a.common.plane(tri);poly=[[p[0],p[2]]for p in tri]
  pieces=a.common.subtract([poly],masks['cuts']+masks['walks']);edits.append(dict(material=material,triangle_index=j,source_triangle_sha256=a.canonical_sha(tri),replacement_triangles_xyz_m=[t for p in pieces for t in fan(p,plane)]))
  done=[]
  for walk in masks['walks']:
   chunks=a.common.subtract([walk],masks['cuts']+done);done.append(walk)
   for p in chunks:path_vertices += [v for t in fan(p,plane)for v in t]
 patch=dict(schema='riverstone.frozen_scene.local_surface_patch.v1',id='R8_REGISTERED_DRAW_CISTERNS',base_scene_sha256=a.SCENE_SHA256,source_surface_hashes={m:a.canonical_sha(scene['surfaces'][m])for m in set(k[0]for k in edited)},surface_edits=edits,appended_surfaces={'ground_stone':path_vertices},removed_foundation_proxy_ids=[],summary=dict(native_platform_owned_m2=16*len(valid),source_triangles=len(edits),existing_water_changed=False),limits=['Existing native wellhouse is static; bucket interaction remains unimplemented.'])
 write(HERE/'surface_patch.json',patch);write(HERE/'water_extension.json',dict(base_water_sha256=a.canonical_sha(scene['surfaces']['water']),append_vertices_xyz_m=water,owner_ids=[p['id']for p in placements],collision=False,policy='Append finite local stored-water disks only; all existing water vertices remain byte-identical.'))
 asset=dict(id=master['id'],source=ref(mp),cache=ref(rp),pitch_m=.2,candidate_cells=c['candidate_cells'],output_cells=len(c['cells']),quad_count=render['quad_count'])
 pack=dict(schema='riverstone.r8.registered_water_services.v1',base_scene=ref(a.SCENE_PATH),assets=[asset],placements=placements,source_refs=[ref(HERE/'locations.json'),ref(HERE/'public_continuation.json'),ref(CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json')],replaced_placement_ids=[],owned_floors=[dict(placement_id=p['id'],polygon_xz_m=r['footprint_xz_m'],floor_y_m=r['position_m'][1],shaft_hole_owned_by_native_walls=True)for p,r in zip(placements,valid)],limits=['Subsurface supply branch is a connected head graph, not visible or fluid-simulated pipe geometry.','No potable quality, interaction or whole city completion claim.'])
 write(HERE/'resolved_placements.json',pack)
 write(HERE/'review.json',dict(status='SOURCE_TESTS_PASS_NOT_ACTUAL_VIEWED',native_reuse='Existing common covered wellhouse plus one closed-bottom component',assets=[asset],placement_count=len(placements),bank_contacts=side['contacts'],ground_cut_m2=16*len(valid),new_stored_water_area_m2=len(valid)*math.pi*.55**2,named_entry_proof=ref(HERE/'public_continuation.json'),source_graph_connections=[dict(draw_id=r['id'],upstream_head_m=r['upstream_source_head_m'],stored_head_m=r['local_stored_head_m'],offset_xz_m=r['offset_from_head_node_m'])for r in valid]));print(json.dumps(dict(placements=len(placements),cells=len(c['cells']),quads=render['quad_count'],bank_contacts=len(side['contacts']),terrain_edits=len(edits),painted_walk_triangles=len(path_vertices)//3)))
if __name__=='__main__':run()
