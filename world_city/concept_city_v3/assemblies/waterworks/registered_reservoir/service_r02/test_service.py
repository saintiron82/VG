"""Bounded recovered service walk replay; no whole-city compiler."""
import collections,json,math,resource,time
from author_service import *
from voxel_character.common import coordinate_planes,render_data

def main():
 t=time.monotonic();pack=json.loads((HERE/'resolved_placements.json').read_text());service=pack['placements'][-1];cistern=next(p for p in pack['placements']if p['id']=='RESERVOIR_DRAWPOINT');floor=set();obstacles=set();replay=[];grid=json.loads((ROOT/service['source']['path']).read_text())['grid_origin'];origin=[ORIGIN[0],18,ORIGIN[2]+grid[2]]
 for p in (service,cistern):
  source=json.loads((ROOT/p['source']['path']).read_text());c=coordinate_planes.compile_master(source,{'pitch':.2},max_candidate_cells=600000,max_output_cells=200000);r=render_data.make_render_data(c);assert r==json.loads((ROOT/p['cache']['path']).read_text());replay.append({'id':p['id'],'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells'])});cells={tuple(x[:3])for x in c['cells']};g=c['grid_origin'];o=p['position_m']
  for x,y,z in cells:
   wy=o[1]+g[1]+(y+.5)*.2;ix=round((o[0]+g[0]+x*.2-origin[0])/.2);iz=round((o[2]+g[2]+z*.2-origin[2])/.2)
   if abs(wy-17.9)<1e-6 and (x,y+1,z)not in cells:floor.add((ix,iz))
   if 18.01<wy<19.8:obstacles.add((ix,iz))
 # Conservative native 0.4m capsule erosion, all cell-centre offsets within radius.
 offsets=[(x,z)for x in range(-2,3)for z in range(-2,3)if x*x+z*z<=4]
 walk={q for q in floor if all((q[0]+dx,q[1]+dz)in floor and (q[0]+dx,q[1]+dz)not in obstacles for dx,dz in offsets)}
 def nearest(p):return min(walk,key=lambda q:math.hypot(origin[0]+(q[0]+.5)*.2-p[0],origin[2]+(q[1]+.5)*.2-p[1]))
 start=nearest([-33.4,-335.7167708839214]);seen={start};queue=collections.deque(seen)
 while queue:
  x,z=queue.popleft()
  for q in [(x-1,z),(x+1,z),(x,z-1),(x,z+1)]:
   if q in walk and q not in seen:seen.add(q);queue.append(q)
 targets=[{'id':b['id'],'xz':[b['center_xyz_m'][0],b['center_xyz_m'][2]]}for b in BRIDGES]+[{'id':'ring_corner_'+str(i),'xz':q}for i,q in enumerate(offset(BASIN['polygon_xz_m'],-1.5))];result=[]
 for target in targets:
  q=nearest(target['xz']);result.append({**target,'nearest_native_center_xz_m':[origin[0]+(q[0]+.5)*.2,origin[2]+(q[1]+.5)*.2],'reachable':q in seen})
 report={'schema':'riverstone.city.recovered_service_native_walk_test.v1','pack':ref(HERE/'resolved_placements.json'),'replay':replay,'capsule_radius_m':.4,'walk_cells':len(walk),'reachable_cells':len(seen),'unreachable_cells':len(walk-seen),'required_targets':result,'required_targets_reachable':all(x['reachable']for x in result),'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'scope':'Two cached solids replayed on their actual aligned grid; 4-neighbour floor walk. Separate bank/sluice cross-pack collisions and terrain/public handoff remain independently unapproved.'};write(HERE/'evidence/native_walk_replay.json',report);print(json.dumps(report,indent=2));assert report['required_targets_reachable']
if __name__=='__main__':main()
