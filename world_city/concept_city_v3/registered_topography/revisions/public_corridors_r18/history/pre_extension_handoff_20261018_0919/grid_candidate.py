"""Bounded shared public-road tessellation screen; no scene activation."""
import json,math,time
from .height_field import HeightField,fixed_sources,HERE
from .survey import ROAD_IDS
from ..r17_district_batches import author as a

def grade(tri):return math.hypot(*a.common.plane(tri)[:2])
def lift(p,h):return [[x,h.value(x,z),z]for x,z in p]
def variants(v):
 return [([v[0],v[2],v[1]],[v[0],v[3],v[2]]),([v[0],v[3],v[1]],[v[1],v[3],v[2]])]
def build():
 started=time.monotonic();regions,segments,refs=fixed_sources();field=HeightField(regions,segments);plan=json.loads(a.PLAN_PATH.read_bytes());windows=[]
 for r in plan['roads']:
  if r['id']not in ROAD_IDS:continue
  for u,v in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):windows.append(a.geo.road_ribbon(u,v,r['width_m']+2))
 cells=set();step=4.
 for p in windows:
  lo=a.bounds(p)
  for x in range(math.floor(lo[0]/step),math.floor(lo[2]/step)+1):
   for z in range(math.floor(lo[1]/step),math.floor(lo[3]/step)+1):
    q=[[x*step,z*step],[(x+1)*step,z*step],[(x+1)*step,(z+1)*step],[x*step,(z+1)*step]]
    if a.clip(p,q):cells.add((x,z))
 queue=[(x*step,z*step,step)for x,z in sorted(cells)];accepted=[];held=[];processed=0
 while queue:
  x,z,s=queue.pop();poly=[[x,z],[x+s,z],[x+s,z+s],[x,z+s]];v=lift(poly,field);pairs=variants(v);best=min(pairs,key=lambda ts:max(grade(t)for t in ts));g=max(grade(t)for t in best)
  if g>.12+1e-8 and s>.25:
   half=s/2;queue.extend((x+dx,z+dz,half)for dx in(0,half)for dz in(0,half))
  elif g>.12+1e-8:held.append(dict(origin_xz_m=[x,z],size_m=s,max_grade=g,vertices=v))
  else:accepted.append(dict(origin_xz_m=[x,z],size_m=s,max_grade=g,triangles_xyz_m=best))
  processed+=1
  if processed%500==0:print('processed',processed,'remaining',len(queue),'held',len(held),'seconds',round(time.monotonic()-started,2),flush=True)
 out=dict(schema='riverstone.r18.public_grid_screen.v1',base_scene_sha256=a.SCENE_SHA256,source_refs=refs,cells=accepted,held_cells=held,processed_cells=processed,elapsed_s=time.monotonic()-started,activation=False,limits=['Grid is not yet clipped to finite public ownership or fixed profile boundaries.','Nonconforming adaptive grid edges must be stitched before scene composition.'])
 (HERE/'grid_screen.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print('DONE',processed,len(accepted),len(held),out['elapsed_s'],flush=True)
if __name__=='__main__':build()
