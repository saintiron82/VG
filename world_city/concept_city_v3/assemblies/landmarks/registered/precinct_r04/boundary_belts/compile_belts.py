"""Two bounded native hedge unions with source-bound replay and support samples."""
import time,resource
from author_belts import *
from voxel_character.common import coordinate_planes,render_data,core
from world_city.concept_city_v3.registered_topography import author as terrain

def main():
 p=load(HERE/'preflight.json');rows=[];placements=[];support=[];t=time.monotonic()
 for r in p['sources']:
  start=time.monotonic();s=load(ROOT/r['source']['path']);c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=600000,max_output_cells=150000);assert c['valid'];mesh=render_data.make_render_data(c);cp=HERE/'cache'/f"{s['id']}.pitch_0.5.render.json";write(cp,mesh);asset={'id':s['id'],'source':r['source'],'cache':ref(cp),'master_hash':core.digest(s),'pitch_m':.5,'candidate_cells':c['candidate_cells'],'cell_count':len(c['cells']),'quad_count':mesh['quad_count'],'bounds':mesh['bounds'],'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};rows.append(asset);placements.append({'id':r['site_id']+':LOW_BOUNDARY_BELT','asset_key':s['id'],'position_m':r['position_m'],'yaw_rad':0,'scale':[1,1,1],'source':r['source'],'cache':ref(cp),'source_module_count':r['native_modules'],'role':'continuous_low_green_precinct_edge_with_reserved_access_gaps'})
  for g in mesh['groups']:
   for q in g['quads']:
    if not all(abs(v[1]+.5)<1e-7 for v in q):continue
    u=[q[1][i]-q[0][i]for i in range(3)];v=[q[2][i]-q[0][i]for i in range(3)]
    if u[2]*v[0]-u[0]*v[2]>=0:continue
    for x,y,z in q:
     wx,wz=x+r['position_m'][0],z+r['position_m'][2];land=terrain.land_height_at(wx,wz);bottom=y+r['position_m'][1];support.append({'position_xyz_m':[wx,bottom,wz],'land_y_m':land,'gap_m':max(0,bottom-land)})
  print(r['site_id'],len(c['cells']),asset['seconds'],flush=True)
 pack={'schema':'riverstone.city.precinct_boundary_belt_addon.v1','status':'native_resolved_addon_pending_actual_view','base_precinct_pack':ref(BASE/'resolved_placements.json'),'preflight':ref(HERE/'preflight.json'),'assets':rows,'placements':placements,'native_module_footprints':p['native_modules'],'owned_floors':[],'terrain_policy':'Native planted-root embeds only; preserve underlying ground, all road/access surfaces and existing grounds.','support_vertex_samples':support,'maximum_bearing_vertex_gap_m':max(x['gap_m']for x in support),'compile_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_fields_preserved':True,'actual_placed':False,'actual_viewed':False,'missing':['Independent native traffic/entrance overlap audit.','Actual scene composition review.','Remaining source-program service/green spaces are not all built.']};write(HERE/'resolved_placements.json',pack);print(ref(HERE/'resolved_placements.json'),pack['maximum_bearing_vertex_gap_m'])
if __name__=='__main__':main()
