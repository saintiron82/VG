"""Four finite common-grid quay unions from the unchanged module operations."""
import copy,json,math,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;REGISTERED=HERE.parent;sys.path.insert(0,str(REGISTERED))
from build_audit import ROOT,ref,write,pose,source_bounds,estimate_candidates
from voxel_character.common import core,coordinate_planes,render_data
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean,DomainCut
from world_city.concept_city_v3.registered_topography.revisions.r04_assembly_ownership import author as terrain
from world_city.concept_city_v3.registered_topography.revisions.r04_assembly_ownership import port_tie

def main():
 start=time.monotonic();base=REGISTERED/'port_r01/resolved_placements.json';p=json.loads(base.read_text());old=copy.deepcopy(p);remove=[];new=[];assets=[];floors=[];reports=[];joins=[]
 for run in range(4):
  original=sorted([x for x in p['placements'] if x['id'].startswith(f'PORT_QUAY_{run}_')],key=lambda x:int(x['id'].split('_')[-1]));sample=original[0];source=json.loads((ROOT/sample['source']['path']).read_text());width=source['extensions']['local_bounds_m']['max'][0]*2;length=width*len(original);center=[(original[0]['position_m'][i]+original[-1]['position_m'][i])/2 for i in range(3)];yaw=sample['yaw_degrees'];s=copy.deepcopy(source);s['id']=f'registered_port_quay_run_{run}_union_r03';s['revision']=3;s['grid_origin']=[-length/2,0,0];s['instances']=[]
  for j in range(len(original)):
   dx=(j+.5)*width-length/2
   for c in source['components']:s['instances'].append({'id':f"segment_{j}_{c['id']}",'component':c['id'],'transform':{'translation':[dx,0,0]}})
  s['provenance'].update(quay_union_author=ref(Path(__file__)),original_module=sample['source'],original_port_pack=ref(base),repair_reason='Independently sampled local module grids left physical end gaps; union all instances on one shared source grid before meshing.')
  s['extensions'].update(local_bounds_m=source_bounds(s),status='finite_common_grid_run_union_candidate',assembled_module_count=len(original),assembled_run_length_m=length,existing_operations_unchanged=True,actual_visual_review=False)
  sp=HERE/'masters'/f"{s['id']}.json";write(sp,s);estimate=estimate_candidates(s,.5)['candidate_cells_exact_aabb_visits'];assert estimate<400000;t=time.monotonic();c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=400000,max_output_cells=200000);assert c['valid'];assert c['candidate_cells']==estimate;r=render_data.make_render_data(c);cp=HERE/'cache'/f"{s['id']}.pitch_0.5.render.json";write(cp,r)
  occupied={tuple(row[:3]) for row in c['cells']};xs=[row[0] for row in c['cells'] if row[1]==-1 and -24<=row[2]<0];xmin,xmax=min(xs),max(xs);missing=[(x,-1,z) for x in range(xmin,xmax+1) for z in range(-24,0) if (x,-1,z) not in occupied];assert not missing
  # Every shared-X neighbour in the apron exists, so there is no segment-end crack.
  joins_test=[]
  for j in range(1,len(original)):
   boundary=j*width;cidx=math.floor(boundary/.5);tests=[]
   for z in range(-24,0):tests.extend([(cidx-1,-1,z) in occupied,(cidx,-1,z) in occupied])
   assert all(tests);joins_test.append({'old_joint_index':j,'source_x_m':-length/2+boundary,'tested_neighbour_cells':len(tests),'all_occupied':True})
  a={'id':s['id'],'source':ref(sp),'cache':ref(cp),'master_hash':core.digest(s),'valid':True,'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'quad_count':r['quad_count'],'pitch_m':.5};assets.append(a)
  # Dry floor is the actually sampled solid section to localZ0. The coping's
  # half-metre water-edge projection is retaining structure, not reclaimed land.
  lo=c['grid_origin'][0]+xmin*.5;hi=c['grid_origin'][0]+(xmax+1)*.5;poly=[]
  for x,z in ((lo,-12),(hi,-12),(hi,0),(lo,0)):
   q=pose([x,0,z],center,yaw);poly.append([q[0],q[2]])
  id=f'PORT_QUAY_RUN_{run}';placement={'id':id,'asset_key':s['id'],'source_id':s['id'],'source':a['source'],'cache':a['cache'],'master_hash':a['master_hash'],'position_m':center,'position_xyz_m':center,'yaw_degrees':yaw,'yaw_rad':math.radians(yaw),'scale':[1,1,1],'scale_xyz':[1,1,1],'datum':'finite_shore_apron','actual_cached_bounds_local_m':r['bounds'],'outer_footprint_xz_m':poly,'world_y_range_m':[center[1]+r['bounds']['min'][1],center[1]+r['bounds']['max'][1]],'replaces_placement_ids':[x['id'] for x in original]};new.append(placement);remove.extend(placement['replaces_placement_ids'])
  wet=terrain.finite_water_polygons();dryparts=DomainCut(wet).subtract(poly);wet_overlap=sum(geo.polygon_area(q) for w in wet if(q:=clean(geo.convex_intersection(poly,w['polygon_xz_m']))))
  for part,polygon in enumerate(dryparts):
   floors.append({'id':id+':floor'+(':'+str(part) if len(dryparts)>1 else ''),'placement_id':id,'polygon_xz_m':polygon,'floor_y_m':2.2,'support_bottom_y_m':-4.8,'priority':'shared common apron owns matching flat visible top; road semantics retained','datum':'finite_shore_apron','footprint_basis':'exact occupied voxel section clipped only to finite dry ownership; native water-edge lip does not reclaim river','source_continuous_length_m':length,'sampled_floor_length_m':hi-lo,'endpoint_quantization_m':[lo+length/2,hi-length/2],'native_section_polygon_xz_m':poly,'wet_masonry_lip_area_excluded_from_dry_ownership_m2':wet_overlap})
  report={'run':run,'source':a['source'],'cache':a['cache'],'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'quad_count':r['quad_count'],'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_module_count':len(original),'former_internal_joints':joins_test,'missing_floor_cells':missing,'actual_continuous_floor_area_m2':(hi-lo)*12,'source_continuous_floor_area_m2':length*12,'source_run_length_m':length,'sampled_run_length_m':hi-lo,'grid_origin':c['grid_origin']};reports.append(report);print(json.dumps({k:report[k] for k in ('run','candidate_cells','output_cells','quad_count','source_module_count','source_run_length_m','sampled_run_length_m')}),flush=True)
 p['placements']=[x for x in p['placements'] if x['id'] not in remove]+new;p['owned_floors']=[x for x in p['owned_floors'] if x['placement_id'] not in remove]+floors;used={x['asset_key'] for x in p['placements']};p['assets']=[x for x in p['assets'] if x['id'] in used]+assets;p['base_pack']=ref(base);p['status']='native_quay_run_unions_pending_independent_scene_review';p['support_evidence']=[x for x in p['support_evidence'] if x['id'] not in remove]
 for x in new:p['support_evidence'].append({'id':x['id'],'retaining_bottom_y_m':-4.8,'inherited_support_module_ids':x['replaces_placement_ids'],'support_rule':'Same continuous retaining face and elevation as the existing modules; sampling grid is unified. Exact shoreline corner/edge and support audit remain.'})
 p['completion_claims'].update(actual_scene_loaded=False,actual_visual_review=False);p['missing'].append('Finite joins between the four differently oriented run unions need actual closeup review; internal repeated-piece seams are closed numerically.')
 report={'schema':'riverstone.city.port_quay_union_compile.v1','base_pack':ref(base),'observed_native_gap_report':ref(ROOT/'world_city/concept_city_v3/validation/port_market/native_floor_section_report.json'),'requests':reports,'total_wall_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'budget':{'candidate_cap_each':400000,'output_cap_each':200000,'pitch_m':.5,'requests':4,'sequential':True,'whole_city_compile':False},'source_module_operations_changed':False,'sampled_cell_edits':False,'internal_joints_closed':sum(len(r['former_internal_joints']) for r in reports),'status':'pass'};write(HERE/'compile_report.json',report)
 overlay={'schema':'riverstone.city.port_quay_run_replacement.v1','base_pack':ref(base),'remove_placement_ids':remove,'remove_floor_ids':[x+':floor' for x in remove],'add_placement_ids':[x['id'] for x in new],'add_floor_ids':[x['id'] for x in floors],'warehouse_boat_crane_transforms_changed':False,'compile_report':ref(HERE/'compile_report.json'),'road_geometry_changed':False,'coownership_policy':'Use regenerated exact sampled floors and r04 matching-height proof; do not reuse old per-module floor masks.'};write(HERE/'replacement_overlay.json',overlay);p['quay_union_overlay']=ref(HERE/'replacement_overlay.json');write(HERE/'resolved_placements.json',p)
 # Rebind the tie certificate to the new run's actual floor. Preserve all old evidence.
 f=next(x for x in floors if x['placement_id']=='PORT_QUAY_RUN_3');contract=json.loads((port_tie.HERE/'port_tie_contract.json').read_text());raw=[];proof=[]
 for i,poly in enumerate(contract['owned_polygons_xz_m']):
  q=clean(geo.convex_intersection(f['polygon_xz_m'],poly))
  if q:raw.append({'id':f'PORT_QUAY_RUN_3:TIE_SHARED:{i}','polygon_xz_m':q})
 for i,poly in enumerate(contract['profile_piece_polygons_xz_m']):
  q=clean(geo.convex_intersection(f['polygon_xz_m'],poly))
  if q:
   ys=[port_tie.height_at(*v) for v in q];assert all(abs(y-2.2)<1e-9 for y in ys);proof.append({'polygon_xz_m':q,'vertex_height_m':ys})
 area=sum(geo.polygon_area(x['polygon_xz_m']) for x in raw);area2=sum(geo.polygon_area(x['polygon_xz_m']) for x in proof);assert abs(area-area2)<1e-6
 co={'schema':'riverstone.city.port_finite_coownership_addendum.v1','source_pack':ref(HERE/'resolved_placements.json'),'base_coownership_evidence':ref(REGISTERED/'port_r02_ownership/finite_coownership_addendum.json'),'terrain_tie_contract':ref(port_tie.HERE/'port_tie_contract.json'),'placement_id':'PORT_QUAY_RUN_3','shared_regions':raw,'proof_regions':proof,'proof':{'whole_field_flat':True,'floor_y_m':2.2,'method':'Exact sampled floor intersected with every linear bridge profile piece; max(2.2,linear field) equals2.2 at all vertices and throughout each convex polygon.','area_m2':area,'coverage_error_m2':abs(area-area2)},'ownership_rule':{'visible_solid_and_top_owner':'PORT_QUAY_RUN_3','traversal_semantics_owner':'PORT_BRIDGE_TIE','suppress_duplicate_terrain_or_road_top_only_inside_shared_regions':True,'rising_tie_outside_shared_regions':'Preserve exact r04 profile.'},'actual_scene_applied':False};write(HERE/'finite_coownership_addendum.json',co)
 print(json.dumps({'placements':len(p['placements']),'assets':len(p['assets']),'floors':len(p['owned_floors']),'closed_internal_joints':report['internal_joints_closed'],'tie_shared_area_m2':area,'total_wall_seconds':report['total_wall_seconds']},indent=2))
if __name__=='__main__':main()
