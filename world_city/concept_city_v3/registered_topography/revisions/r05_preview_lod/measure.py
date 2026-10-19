import json,time,math
from . import review as r
from world_city.concept_city_v3.review_geometry import prune_collinear_xyz
POINTS=[(-520,-480),(-400,-430),(-250,-400),(-80,-420),(180,-400),(400,-370),(500,-200),(-480,-220),(-400,-100),(-300,0),(-280,100),(-320,250),(-400,350),(-250,360),(-150,340),(0,300),(200,330),(350,300),(420,160),(350,50),(210,-50),(100,30),(0,-80),(-120,120),(-180,-250),(110,433),(125,450),(220,-230),(-80,-320),(20,-230),(100,180),(470,550)]
def run():
 r.prior._owners();rows=[];max_error=0;sample_count=0
 for x,z in POINTS:
  x=math.floor(x/8)*8;z=math.floor(z/8)*8;bounds=[x,z,x+8,z+8];entry=dict(bounds_xz_m=bounds)
  for label,m in [('previous',r.prior),('lod',r)]:
   t=time.perf_counter();ds=m.surface_domains(bounds);verts=triangles=0
   for d in ds:
    if not d['render_land']:continue
    ps=prune_collinear_xyz([[p[0],m.surface_height_at(d,*p),p[1]] for p in d['polygon_xz_m']]);verts+=len(ps);triangles+=max(0,len(ps)-2)
    if label=='lod':
     for i in range(1,len(ps)-1):
      tri=[ps[0],ps[i],ps[i+1]]
      for w in [(1/3,1/3,1/3),(.5,.25,.25),(.25,.5,.25),(.25,.25,.5)]:
       p=[sum(w[j]*tri[j][k] for j in range(3)) for k in range(3)]
       analytic=r.source_surface_height_at(d,p[0],p[2]);max_error=max(max_error,abs(p[1]-analytic));sample_count+=1
   entry[label]=dict(vertices_after_exact_xyz_prune=verts,fan_triangle_count=triangles,seconds=time.perf_counter()-t)
  rows.append(entry)
 seam=0
 for x,z in [(-504,-472),(-296,0),(-120,120),(104,432),(96,32)]:
  for i in range(65):
   p=[x,z+i/8];owner=r.owner_at(*p)
   a=r.surface_height_at(dict(owner,review_tile_bounds_xz_m=[x-8,z,x,z+8]),*p)
   b=r.surface_height_at(dict(owner,review_tile_bounds_xz_m=[x,z,x+8,z+8]),*p);seam=max(seam,abs(a-b))
 totals={k:{metric:sum(v[k][metric] for v in rows) for metric in ('vertices_after_exact_xyz_prune','fan_triangle_count','seconds')} for k in ('previous','lod')}
 result=dict(source_plan_sha256=r.prior.old.SOURCE_SHA,author_sha256=r.prior.sha(r.HERE/'review.py'),tile_count=len(rows),rows=rows,totals=totals,
  max_sampled_fan_departure_from_source_m=max_error,interior_error_sample_count=sample_count,max_shared_edge_height_difference_m=seam,
  error_scope='Convex boundary-fan triangles after exact XYZ collinear pruning;4barycentric samples per triangle across32representative8m tiles. Measured bound is not a global proof.',
  first_use_limit='Do not treat the spatial proxy as continuous collision. Coarse inactive edge interpolation has an independent<=.12m bound;8m fan interior error is measured here.')
 (r.HERE/'metrics.json').write_text(json.dumps(result,indent=2)+'\n');(r.HERE/'contract.json').write_text(json.dumps(r.build_contract(),indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('rows',)},indent=2))
if __name__=='__main__':run()
