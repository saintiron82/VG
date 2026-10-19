"""Read-only conservative cross-pack positive-volume AABB comparison."""
import math
from author import HERE,load,write,ref

def bounds(p,a):
 b=a['bounds'];c,s=math.cos(p['yaw_rad']),math.sin(p['yaw_rad']);v=p['position_m']
 q=[[v[0]+c*x+s*z,v[1]+y,v[2]-s*x+c*z]for x in (b['min'][0],b['max'][0])for y in(b['min'][1],b['max'][1])for z in(b['min'][2],b['max'][2])]
 return [min(p[i]for p in q)for i in range(3)],[max(p[i]for p in q)for i in range(3)]
def main():
 a=load(HERE/'pack.json');rows=[];sources=[ref(HERE/'pack.json')]
 for name in ('landmarks','port_market'):
  path=HERE.parent/name/'pack.json';b=load(path);sources.append(ref(path))
  for p in a['add_instances']:
   lo,hi=bounds(p,a['common_assets'][p['asset_key']])
   for q in b['add_instances']:
    l,h=bounds(q,b['common_assets'][q['asset_key']])
    if all(min(hi[i],h[i])-max(lo[i],l[i])>1e-7 for i in range(3)):rows.append(dict(planting=p['id'],other=q['id'],pack=name))
 report=dict(status='PASS'if not rows else 'REVIEW',method='Conservative full transformed native AABBs in all three axes; touching is not positive-volume overlap.',crosspack_positive_volume_overlaps=rows,source_refs=sources)
 write(HERE/'crosspack_bounds_review.json',report);print(report['status'],len(rows),'positive-volume overlaps')
 assert not rows
if __name__=='__main__':main()
