"""Repair only three recorded thin-triangle overlays with 60-digit arithmetic.

Input doubles are preserved exactly; the inherited 1 nm mask-normalization
contract is unchanged. Completed emission is reused rather than rerun.
"""
import copy,json,math,time
from decimal import Decimal,localcontext
from . import author_direct_tops as a,finite_geometry_r03 as g,public_domain as d

def D(x):return Decimal.from_float(float(x))
def clean(p):
 out=[]
 for v in p:
  if not out or out[-1]!=v:out.append(v)
 if len(out)>1 and out[0]==out[-1]:out.pop()
 return out if len(out)>=3 and area(out)>Decimal('1e-40') else[]
def signed(p):
 if len(p)<3:return Decimal(0)
 o=p[0]
 return sum(((u[0]-o[0])*(v[1]-o[1])-(u[1]-o[1])*(v[0]-o[0])for u,v in zip(p,p[1:]+p[:1])),Decimal(0))/2
def area(p):return abs(signed(p))
def cross(a,b,p):return(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
def half(p,a,b,sign,inside):
 if not p:return[]
 out=[];u=p[-1];du=sign*cross(a,b,u);iu=du>=0 if inside else du<=0
 for v in p:
  dv=sign*cross(a,b,v);iv=dv>=0 if inside else dv<=0
  if iu!=iv:
   t=du/(du-dv);out.append([u[k]+t*(v[k]-u[k])for k in(0,1)])
  if iv:out.append(v)
  u,du,iu=v,dv,iv
 return clean(out)
def clip(p,q):
 sign=1 if signed(q)>0 else-1
 for u,v in zip(q,q[1:]+q[:1]):
  p=half(p,u,v,sign,True)
  if not p:break
 return p
def difference(p,q):
 sign=1 if signed(q)>0 else-1;out=[]
 for u,v in zip(q,q[1:]+q[:1]):
  part=half(p,u,v,sign,False)
  if part:out.append(part)
  p=half(p,u,v,sign,True)
  if not p:break
 return out
def subtract(ps,masks):
 for mask in masks:
  ps=[q for p in ps for q in(difference(p,mask)if clip(p,mask)else[p])]
  if not ps:break
 return ps
def union(ps):
 out=[]
 for p in ps:out+=subtract([p],out)
 return out
def dec(p):return [[D(v)for v in row]for row in g.normalize_mask(p)]

def main():
 start=time.monotonic();src=a.HERE/'public_top_r01';out=a.HERE/'public_top_r02_partitionfix';out.mkdir(exist_ok=True);assert not(out/'surface_patch.json').exists()
 patch=json.loads((src/'surface_patch.json').read_bytes());review=json.loads((src/'top_review.json').read_bytes());candidate=json.loads((a.HERE/'finite_field_candidate_r04_common.json').read_bytes());cache=json.loads((a.HERE/'boundary_ownership_inputs_r03.json').read_bytes());scene=a.a.load_scene()
 traffic=d.polygons();masks=[r['polygon_xz_m']for r in cache['masks']]+[r['polygon_xz_m']for r in candidate['report']['common_cap_transition']['supplemental_native_exclusions']];ti=a.index(traffic);mi=a.index(masks)
 failures=[r for r in review['failures']if r['kind']=='source_partition'];assert[(r['material'],r['triangle_index'])for r in failures]==[('road',5995),('road',6077),('road',35463)]
 fixes=[]
 with localcontext()as ctx:
  ctx.prec=60
  for fail in failures:
   material,i=fail['material'],fail['triangle_index'];tri=scene['surfaces'][material][i*3:i*3+3];poly=[[v[0],v[2]]for v in tri];p=dec(poly)
   cuts=union([q for j in sorted(ti.candidates(poly))if(q:=clip(p,dec(traffic[j])))]);cuts=subtract(cuts,[dec(masks[j])for j in sorted(mi.candidates(poly))if len(dec(masks[j]))>=3]);rest=subtract([p],cuts)
   error=abs(area(p)-sum(map(area,cuts),Decimal(0))-sum(map(area,rest),Decimal(0)));assert error<Decimal('1e-40'),str(error)
   plane=a.a.common.plane(tri);floatrest=[[[float(v)for v in xy]for xy in q]for q in rest];ts=[t for q in floatrest for t in a.fan(q,plane)];newarea=math.fsum(g.area([[v[0],v[2]]for v in t])for t in ts);floaterr=abs(g.area(poly)-float(sum(map(area,cuts),Decimal(0)))-newarea);assert floaterr<1e-10
   row=next(r for r in patch['surface_edits']if r['material']==material and r['triangle_index']==i);row['replacement_triangles_xyz_m']=ts
   fixes.append(dict(material=material,triangle_index=i,old_area_error_m2=fail['area_error_m2'],decimal_partition_error_m2=str(error),emitted_float_partition_error_m2=floaterr,retained_triangles=len(ts),retained_area_m2=newarea,removed_area_m2=float(sum(map(area,cuts),Decimal(0)))))
   for proof in review['partitions']:
    if proof['material']==material and proof['triangle_index']==i:proof.update(partition_error_m2=floaterr,removed_area_m2=fixes[-1]['removed_area_m2'])
   print(fixes[-1],flush=True)
 refs=[a.ref(src/'surface_patch.json'),a.ref(src/'top_review.json'),a.ref(a.HERE/'repair_direct_partitions.py')]
 patch['id']='R18_DIRECT_CANONICAL_PUBLIC_TOPS_PARTITION_R02';patch['source_references']+=refs
 review['failures']=[r for r in review['failures']if r['kind']!='source_partition'];review['status']='HELD_SOURCE_HOLE_CLASSIFICATION';review['source_refs']+=refs;review['max_partition_error_m2']=max(r['partition_error_m2']for r in review['partitions']);review['local_partition_repair']=fixes;review['repair_elapsed_s']=time.monotonic()-start
 for n,v in [('surface_patch.json',patch),('top_review.json',review)]: (out/n).write_text(json.dumps(v,separators=(',',':'),allow_nan=False)+'\n')
 print('repaired',len(fixes),'remaining holds',len(review['failures']),'seconds',time.monotonic()-start,flush=True)
if __name__=='__main__':main()
