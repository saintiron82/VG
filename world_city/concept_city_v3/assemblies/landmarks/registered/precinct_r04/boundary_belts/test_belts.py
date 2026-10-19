from author_belts import *
from voxel_character.common import coordinate_planes,render_data

def main():
 plan=load(BASE/'coverage_plan.json');prod=load(BASE/'productive_frames.json');routes=load(BASE/'exterior_access_proposal.json');pack=load(HERE/'resolved_placements.json');obstacles=[{'id':r['id'],'polygon_xz_m':r['polygon_xz_m']}for r in plan['reserved_records']]+[{'id':c['id'],'polygon_xz_m':c['requested_frame_xz_m']}for c in plan['compounds']]+[{'id':f['id'],'polygon_xz_m':f['polygon_xz_m']}for f in prod['frames']]
 for r in routes['routes']:
  for i,p in enumerate(r['ribbon_polygons_xz_m']+r['join_polygons_xz_m']):obstacles.append({'id':r['id']+':'+str(i),'polygon_xz_m':p})
 index=geo._SpatialIndex(16)
 for i,r in enumerate(obstacles):index.add(i,r['polygon_xz_m'])
 hits=[];measure=[]
 for asset,pose in zip(pack['assets'],pack['placements']):
  s=load(ROOT/asset['source']['path']);c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=600000,max_output_cells=150000);assert render_data.make_render_data(c)==load(ROOT/asset['cache']['path']);xz={(x,z)for x,y,z,*_ in c['cells']if 0<=(y+.5)*.5<2};origin=pose['position_m']
  for x,z in xz:
   p=[[origin[0]+x*.5,origin[2]+z*.5],[origin[0]+(x+1)*.5,origin[2]+z*.5],[origin[0]+(x+1)*.5,origin[2]+(z+1)*.5],[origin[0]+x*.5,origin[2]+(z+1)*.5]]
   for i in index.candidates(p):
    area=geo.intersection_area(p,obstacles[i]['polygon_xz_m'])
    if area>1e-7:hits.append({'asset_id':asset['id'],'cell_xz':[x,z],'obstacle_id':obstacles[i]['id'],'area_m2':area})
  measure.append({'asset_id':asset['id'],'native_walking_height_xz_cells':len(xz),'source_cache_replay':True})
 report={'pack':ref(HERE/'resolved_placements.json'),'measurements':measure,'native_obstacle_hits':hits,'pass':not hits,'scope':'Actual0.5m cell projections at walking height against preserved reservations, new grounds and exterior routes; no runtime controller claim.'};write(HERE/'evidence/native_reservation_audit.json',report);print('hits',len(hits),hits[:3]);assert not hits
if __name__=='__main__':main()
