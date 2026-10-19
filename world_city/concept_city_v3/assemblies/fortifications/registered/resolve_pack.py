"""Native repeated curtain modules with bounded closures and exact source binding.

No source-plan edits, no scale, no whole-wall compile, and no new gate openings.
"""
import copy,json,math,resource,sys,time
from pathlib import Path
from author_fixtures import HERE,ROOT,ref,write,estimate_candidates,Source,make_master
from voxel_character.common import core,coordinate_planes,render_data
from world_city.concept_city_v3.registered_topography.revisions.r04_assembly_ownership import author as terrain
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.assemblies.landmarks.registered.build_audit import pose,camera_functions

OUT=HERE/'placement_r01'

def main():
 planpath=ROOT/'world_city/concept_city_v3/registered_source/plan.json';plan=json.loads(planpath.read_text());manifest=json.loads((HERE/'fixture_manifest.json').read_text());assets={x['id']:copy.deepcopy(x) for x in manifest['sources']};places=[];supports=[];added=[];gates=[];fit=[]
 def compile_source(s):
  key=s['id'];sp=OUT/'masters'/f'{key}.json';s.setdefault('provenance',{})['placement_author']=ref(Path(__file__));write(sp,s);est=estimate_candidates(s,.5)['candidate_cells_exact_aabb_visits'];assert est<400000;start=time.monotonic();c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=400000,max_output_cells=200000);assert c['valid'];r=render_data.make_render_data(c);cp=OUT/'cache'/f'{key}.pitch_0.5.render.json';write(cp,r)
  row={'id':key,'source':ref(sp),'cache':ref(cp),'master_hash':core.digest(s),'valid':True,'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'quads':r['quad_count'],'bounds':r['bounds'],'seconds':round(time.monotonic()-start,3),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};assets[key]=row;added.append(row);print(json.dumps({k:row[k] for k in ('id','candidate_cells','output_cells','seconds')}),flush=True);return key
 def add(id,key,pos,yaw,role,**extra):
  a=assets[key];b=a['bounds'];poly=[]
  for x,z in ((b['min'][0],b['min'][2]),(b['max'][0],b['min'][2]),(b['max'][0],b['max'][2]),(b['min'][0],b['max'][2])):
   p=pose([x,0,z],pos,yaw);poly.append([p[0],p[2]])
  row={'id':id,'asset_key':key,'source_id':key,'source':a['source'],'cache':a['cache'],'master_hash':a['master_hash'],'position_m':pos,'position_xyz_m':pos,'yaw_rad':math.radians(yaw),'yaw_degrees':yaw,'scale':[1,1,1],'scale_xyz':[1,1,1],'semantic_role':role,'actual_cached_bounds_local_m':b,'outer_footprint_xz_m':poly,'world_y_range_m':[pos[1]+b['min'][1],pos[1]+b['max'][1]],**extra};places.append(row);return row
 def samples(center,yaw,width,depth):
  out=[]
  for x in (-width/2,-width/4,0,width/4,width/2):
   for z in (-depth/2,0,depth/2):
    p=pose([x,0,z],[center[0],0,center[1]],yaw);out.append([p[0],terrain.height_at(p[0],p[2]),p[2]])
  return out
 def base_and_depth(values):
  ys=[p[1] for p in values];base=math.ceil(max(ys)*2-1e-9)/2;depth=math.ceil((base-min(ys)+.5)*2)/2
  return base,max(.5,depth)
 points=plan['boundary_xz_m'];edges=[]
 for edge,(a,b) in enumerate(zip(points,points[1:]+points[:1])):
  length=math.dist(a,b);u=[(b[j]-a[j])/length for j in (0,1)];yaw=math.degrees(math.atan2(-u[1],u[0]));h=22 if edge in (17,22) else 18 if edge in (16,18,19,20,21,23,24) else 14
  intervals=[];cuts=[]
  for g in plan['gates']:
   if g['wall_edge_index']==edge:
    t=sum((g['position_xz_m'][j]-a[j])*u[j] for j in (0,1));cuts.append([t-g['opening_width_m']/2,t+g['opening_width_m']/2])
  cursor=0
  for lo,hi in sorted(cuts):intervals.append([cursor,lo]);cursor=hi
  intervals.append([cursor,length]);segments=[]
  for run,(lo,hi) in enumerate(intervals):
   x=lo;chunk=0
   while x<hi-1e-7:
    width=min(16,hi-x);mid=x+width/2;center=[a[j]+u[j]*mid for j in (0,1)];values=samples(center,yaw,width,4);base,depth=base_and_depth(values);id=f'FORT_CURTAIN_{edge:02d}_{run}_{chunk:02d}'
    if width>=16-1e-7:
     key=f'registered_curtain16_h{h}';add(id,key,[center[0],base,center[1]],yaw,'curtain',wall_edge_index=edge)
     z=0
     while z<depth-1e-9:
      step=min(1,depth-z);keyfoot='registered_fort_footing_16x1' if step==1 else 'registered_fort_footing_16x0.5';add(id+f':FOOTING:{z:g}',keyfoot,[center[0],base-z,center[1]],yaw,'native_foundation',support_owner_id=id);z+=step
    else:
     s=make_master({'kind':'wall_panel','width_m':width,'depth_m':3,'height_m':h,'battlements':True,'battlement_height_m':1,'battlement_spacing_m':2});s['id']=f'registered_curtain_closure_{edge:02d}_{run}';s['components'].append({'id':'bearing','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':[{'id':'footing','part':'solid','action':'paint','material':'stone_dark','shape':{'kind':'box','min':[-width/2,-depth,-2],'max':[width/2,0,2]}}]});s['instances'].append({'id':'bearing','component':'bearing'});key=compile_source(s);add(id,key,[center[0],base,center[1]],yaw,'curtain_with_native_foundation',wall_edge_index=edge)
    supports.append({'placement_id':id,'footprint_samples_xyz_m':values,'sample_spacing_max_m':max(width/4,2),'body_base_y_m':base,'foundation_bottom_y_m':base-depth,'minimum_sampled_embed_m':min(v[1] for v in values)-(base-depth),'all_samples_reached':base-depth<=min(v[1] for v in values)-.499999,'scope':'finite15-point support sampling, not structural engineering or continuous terrain proof'})
    segments.append({'id':id,'station_range_m':[x,x+width],'width_m':width,'body_height_m':h,'base_y_m':base});x+=width;chunk+=1
  edges.append({'edge_index':edge,'endpoints_xz_m':[a,b],'length_m':length,'curtain_height_m':h,'height_basis':'local paired-face sample' if edge in (17,22) else 'conservative regional image-fit candidate; inferred','gate_cuts_station_m':cuts,'segments':segments})
 # Six actually observed paired-face tower positions, with source-anchor residuals preserved.
 pre=json.loads((HERE/'preflight.json').read_text());controls=json.loads((ROOT/'world_city/concept_city_v3/image_registration/controls.json').read_text());project,*_=camera_functions(controls)
 for obs in pre['observations']:
  if obs['kind']!='tower':continue
  anchor=obs['nearest_current_wall_ground_projection'];edge=anchor['edge_index'];a,b=points[edge],points[(edge+1)%len(points)];yaw=math.degrees(math.atan2(-(b[1]-a[1]),b[0]-a[0]));center=[anchor['world_xyz_m'][0],anchor['world_xyz_m'][2]];w,h=(10,34) if obs['id'].startswith('south_') else (12,42);values=samples(center,yaw,w,w);base,depth=base_and_depth(values);id='FORT_TOWER:'+obs['id'];add(id,f'registered_fort_tower_{w}x{h}',[center[0],base,center[1]],yaw,'observed_wall_tower',observation_id=obs['id'])
  s=Source('tower_footing_'+obs['id'],[-w/2,-depth,-w/2],[w/2,0,w/2]);s.box('bearing',[-w/2,-depth,-w/2],[w/2,0,w/2],'stone_dark');src=s.finish();src['id']='registered_'+s.kind;key=compile_source(src);add(id+':FOOTING',key,[center[0],base,center[1]],yaw,'native_foundation',support_owner_id=id)
  supports.append({'placement_id':id,'footprint_samples_xyz_m':values,'body_base_y_m':base,'foundation_bottom_y_m':base-depth,'minimum_sampled_embed_m':min(v[1] for v in values)-(base-depth),'all_samples_reached':True,'scope':'finite15-point sampled support; full footprint terrain and structure review remain'})
  # A pyramid apex is a point, not the four top corners of the full tower box.
  pts=[pose([x,y,z],[center[0],base,center[1]],yaw) for y in (0,h-7) for x in (-w/2,w/2) for z in (-w/2,w/2)]+[[center[0],base+h,center[1]]]
  fit.append({'placement_id':id,'observation':obs,'projected_source_points_pixel_xy':[project(p) for p in pts],'projected_apex_pixel_xy':project(pts[-1]),'source_height_m':h,'actual_coarse_tip_local_y_m':assets[f'registered_fort_tower_{w}x{h}']['bounds']['max'][1],'uncertainty_decision':'Keep the frozen wall trace and authored terrain support; record the residual rather than move the city boundary or raise all walls. Candidate awaits actual silhouette review.'})
 for g in plan['gates']:
  edge=g['wall_edge_index'];a,b=points[edge],points[(edge+1)%len(points)];yaw=math.degrees(math.atan2(-(b[1]-a[1]),b[0]-a[0]));center=g['position_xz_m'];y=terrain.road_height_at(g['road_id'],*center);key='registered_main_gate_header' if g['road_id']=='MAIN_BRIDGE' else 'registered_service_gate_header';p=add('FORT_GATE:'+g['id'],key,[center[0],y,center[1]],yaw,'native_gate_header',source_gate_id=g['id'],road_id=g['road_id']);src=json.loads((ROOT/assets[key]['source']['path']).read_text());dim=src['extensions']['design_dimensions_m'];gates.append({'placement_id':p['id'],'source_gate':g,'floor_y_m_at_crossing':y,'floor_owner':g['road_id'],'floor_api':'registered_topography.revisions.r04_assembly_ownership.author.road_height_at','flat_floor_added':False,'native_clear_width_m':dim['clear_width'],'total_travel_corridor_m':7 if g['road_id']=='MAIN_BRIDGE' else 3,'main_gate_function':'4m cart band and1.5m pedestrian margins each merge into short shared7m throat' if g['road_id']=='MAIN_BRIDGE' else '3m service road','added_opening':False,'actual_capsule_clearance_status':'pending compiled cell/ribbon audit'})
 # Enumerate actual frozen proxy IDs; do not apply a wildcard to unknown content.
 scenepath=ROOT/'world_city/concept_city_v3/evidence/visual_registered_common_r1_cached/scene.json';scene=json.loads(scenepath.read_text());proxy_ids=[x['id'] for x in scene['boxes'] if x['id'].startswith('wall:')];assert len(proxy_ids)==722
 assert len(added)<=38,len(added)
 used={p['asset_key'] for p in places};final_assets=[assets[k] for k in sorted(used)]
 overlay={'schema':'riverstone.city.fortification_supersession_overlay.v1','source_plan':ref(planpath),'proxy_evidence_scene':ref(scenepath),'remove_box_ids':proxy_ids,'remove_count':len(proxy_ids),'source_wall_boundary_unchanged':True,'source_gate_openings_unchanged':True,'new_gate_count':0,'road_xz_changes':[],'gate_floor_policy':'Road and bridge retain their exact graded floors; headers add no floor surface.','bridge_pack':ref(ROOT/'world_city/concept_city_v3/assemblies/waterworks/registered_bridge/resolved_placements.json'),'bridge_overlay':ref(ROOT/'world_city/concept_city_v3/assemblies/waterworks/registered_bridge/continuous_deck_overlay.json')};write(OUT/'supersession_overlay.json',overlay)
 report={'schema':'riverstone.city.native_fortification_compile_report.v1','status':'pass','new_sources':added,'reused_fixture_manifest':ref(HERE/'fixture_manifest.json'),'budget':{'new_unique_sources_cap':38,'actual_new_unique_sources':len(added),'candidate_cap_each':400000,'output_cap_each':200000,'pitch_m':.5,'sequential_only':True,'whole_wall_compile':False},'peak_candidate_cells':max(x['candidate_cells'] for x in added),'peak_rss_kib':max(x['peak_rss_kib'] for x in added)};write(OUT/'compile_report.json',report)
 pack={'schema':'riverstone.city.registered_common_fortifications.v1','status':'resolved_candidate_pending_independent_access_and_visual_review','source_plan':ref(planpath),'terrain_author':ref(Path(terrain.__file__)),'terrain_contract':ref(terrain.HERE/'contract.json'),'preflight':ref(HERE/'preflight.json'),'replacement_overlay':ref(OUT/'supersession_overlay.json'),'compile_report':ref(OUT/'compile_report.json'),'assets':final_assets,'placements':places,'owned_floors':[],'support_evidence':supports,'wall_edge_contracts':edges,'gates':gates,'tower_silhouette_candidates':fit,'completion_claims':{'source_authored':True,'caches_compiled':True,'resolved_placements':True,'actual_scene_loaded':False,'actual_visual_review':False,'navigation_validated':False,'structure_engineered':False},'missing':['Independent native road/gate clearance audit','Tower wall-walk entrances, stairs and detailed interiors','Additional concept-visible watchtower anchors beyond the six paired-face samples','First actual native fortification silhouette review','Continuous support-footprint validation between finite samples']};write(OUT/'resolved_placements.json',pack);print(json.dumps({'placements':len(places),'unique_assets':len(final_assets),'new_caches':len(added),'curtains':sum(len(e['segments']) for e in edges),'towers':len(fit),'gates':len(gates),'proxy_replacements':len(proxy_ids),'peak_candidates':report['peak_candidate_cells']},indent=2))

if __name__=='__main__':main()
