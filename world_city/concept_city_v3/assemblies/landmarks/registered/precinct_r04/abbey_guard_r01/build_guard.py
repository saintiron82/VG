"""A bounded native rail outside the abbey orchard's retained pedestrian edge."""
import sys,math,time,resource,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'access_r02'))
from recovered_range_factory import Source,estimate_candidates,ROOT,ref,write
from author_access import load,geo,terrain,polygons
from inspect_abbey_shoulder import distance
from voxel_character.common import coordinate_planes,render_data,core

def main():
 start=time.monotonic();origin=[-149.45,8,224.5];a=Source('abbey_orchard_pedestrian_guard',[-.1,-1,-3],[.1,.9,3]);a.smoke_pitch=.1
 for i,z in enumerate([-2.9,-1,1,2.9]):
  a.box('embedded_post_'+str(i),[-.1,-1,z-.1],[.1,.9,z+.1],'timber',component='timber_guard');a.support('post_'+str(i),[-.1,-1,z-.1],[.1,-.8,z+.1],'Inherited shoulder; terrain remains under these embedded post feet.')
 for i,(lo,hi)in enumerate([(.1,.25),(.4,.55),(.75,.9)]):a.box('continuous_rail_'+str(i),[-.1,lo,-3],[.1,hi,3],'timber',component='timber_guard')
 a.clearance('full_pedestrian_strip',[-2.0,-.02,-3],[-.15,2,3],'Keep the declared 1.8 m travel ribbon west of the rail empty; tested against cached footprint.',assert_empty=False)
 s=a.finish();s['id']='registered_abbey_orchard_pedestrian_guard_r01';s['provenance'].update(addon_author=ref(Path(__file__)),fixed_edge_request=ref(BASE/'access_r02/abbey_shoulder_request.json'),revision02_prompt_status='Explicit reconstruction notice; original prompt unavailable.');s['extensions'].update(placement_origin_m=origin,exposed_retained_edge={'x_m':-149.6,'z_range_m':[222.167089675,226.969529341],'floor_y_m':8},finished_guard_top_y_m=8.9,travel_width_m=1.8,structural_certification=False,actual_placed=False,actual_viewed=False)
 sp=HERE/'masters'/f"{s['id']}.json";write(sp,s);estimate=estimate_candidates(s,.1);assert estimate['candidate_cells_exact_aabb_visits']<5000;write(HERE/'preflight.json',{'source':ref(sp),'estimate':estimate,'candidate_cap':5000,'output_cap':5000,'pitch_m':.1});print('PREFLIGHT',estimate['candidate_cells_exact_aabb_visits'],flush=True)
 c=coordinate_planes.compile_master(s,{'pitch':.1},max_candidate_cells=5000,max_output_cells=5000);assert c['valid'],c.get('constraints');m=render_data.make_render_data(c);cp=HERE/'cache'/f"{s['id']}.pitch_0.1.render.json";write(cp,m)
 bounds=m['bounds'];foot=geo.transformed_aabb_xz_m(bounds,origin,0);route=next(r for r in load(BASE/'access_r02/exterior_access_proposal.json')['routes']if r['gate_id']=='ABBEY_EAST_ORCHARD:main_gate');travelhits=[geo.intersection_area(foot,p)for p in route['ribbon_polygons_xz_m']+route['join_polygons_xz_m']];assert max(travelhits)==0
 regions=terrain.surface_domains([-154,218,-140,232],conform=False);roads=[r for r in regions if r['kind']=='road'];clear=min(distance(foot,r['polygon_xz_m'])for r in roads);assert clear>1
 bearings=[]
 for g in m['groups']:
  for q in g['quads']:
   if not all(abs(v[1]+1)<1e-8 for v in q):continue
   u=[q[1][i]-q[0][i]for i in range(3)];v=[q[2][i]-q[0][i]for i in range(3)]
   if u[2]*v[0]-u[0]*v[2]>=0:continue
   for x,y,z in q:
    wx,wy,wz=x+origin[0],y+origin[1],z+origin[2];h=terrain.land_height_at(wx,wz);bearings.append({'position_xyz_m':[wx,wy,wz],'inherited_land_y_m':h,'embed_m':h-wy});assert h>=wy
 cells={tuple(r[:3])for r in c['cells']};seen=set();todo=[next(iter(cells))]
 while todo:
  q=todo.pop()
  if q in seen:continue
  seen.add(q)
  for axis in range(3):
   for delta in(-1,1):
    r=list(q);r[axis]+=delta;r=tuple(r)
    if r in cells and r not in seen:todo.append(r)
 assert len(seen)==len(cells)
 row={'id':s['id'],'source':ref(sp),'cache':ref(cp),'master_hash':core.digest(s),'pitch_m':.1,'candidate_cells':c['candidate_cells'],'cell_count':len(cells),'quad_count':m['quad_count'],'bounds':bounds}
 pack={'schema':'riverstone.precinct.pedestrian_guard_addon.v1','assets':[row],'placements':[{'id':'ABBEY_EAST_ORCHARD:RETAINED_EDGE_GUARD','asset_key':s['id'],'position_m':origin,'yaw_rad':0,'scale':[1,1,1],'source':ref(sp),'cache':ref(cp),'footprint_xz_m':foot}],'owned_floors':[],'terrain_policy':'Embedded post feet only; retain the shoulder and R14 path support. No new ground-plane cut.','source_native_pack':ref(BASE/'resolved_placements.json'),'effective_access':ref(BASE/'access_r02/exterior_access_proposal.json'),'finite_shoulder_request':ref(BASE/'access_r02/abbey_shoulder_request.json'),'test_results':{'connected_cells':len(seen),'total_cells':len(cells),'travel_ribbon_hits':0,'minimum_native_guard_to_traffic_edge_m':clear,'bearing_vertices':bearings,'minimum_post_embed_m':min(r['embed_m']for r in bearings),'maximum_post_embed_m':max(r['embed_m']for r in bearings)},'compile_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_placed':False,'actual_viewed':False,'independent_acceptance':False,'limitations':['Geometric barrier only; structural and native character physics unverified.','Terrain R14 must supply the matching retained support.']};write(HERE/'resolved_placements.json',pack);print(ref(HERE/'resolved_placements.json'),len(cells),'clearance',clear,'seconds',pack['compile_seconds'])
if __name__=='__main__':main()
