"""Exact private-append predecessor accounting for explicitly reviewed finite retirements.

The immutable producer review authorizes the finite cut. This checker preserves every
unaffected ordered triangle, checks changed-row hashes and projected area, and admits
new vertical sides only when their exact coordinates occur in a bound contract.
"""
import collections,hashlib,json,math

def sha(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def key(t):return tuple(tuple(p)for p in t)
def triangles(vs):
 assert len(vs)%3==0
 return collections.Counter(key(vs[i:i+3])for i in range(0,len(vs),3))
def area(t):
 a,b,c=t;return abs((b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0]))*.5

def validate(previous,current,review,extra_triangles_by_material=None):
 assert not review.get('walking_geometry_changed',True),'Walking geometry change is not a finite nonwalking retirement'
 assert not review.get('native_geometry_changed',True),'Native geometry changed'
 assert previous['base_scene_sha256']==current['base_scene_sha256']
 old={k:triangles(v)for k,v in previous['appended_surfaces'].items()};new={k:triangles(v)for k,v in current['appended_surfaces'].items()}
 selected=collections.defaultdict(collections.Counter);removed_area=collections.Counter();seen=set()
 for row in review['source_rows']:
  mat=row['material'];i=row['appended_triangle_index'];assert (mat,i)not in seen;seen.add((mat,i))
  vs=previous['appended_surfaces'][mat];assert 0<=i<len(vs)//3
  t=vs[i*3:i*3+3];assert sha(t)==row['source_triangle_sha256'],'Changed predecessor triangle hash mismatch'
  selected[mat][key(t)]+=1;assert row['removed_area_m2']>=0;removed_area[mat]+=row['removed_area_m2']
 extras={mat:collections.Counter(key(t)for t in ts)for mat,ts in(extra_triangles_by_material or{}).items()};unchanged={};retired={};stats={}
 for mat in sorted(set(old)|set(new)):
  a=old.get(mat,collections.Counter());b=new.get(mat,collections.Counter());declared=selected[mat];unaffected=a-declared
  assert not(unaffected-b),'Unaffected private appended triangle changed: '+mat
  assert not((a-b)-declared),'Undeclared predecessor retirement: '+mat
  assert not (declared&a&b),'Declared retired triangle remains verbatim: '+mat
  additions=b-unaffected
  if mat not in removed_area:
   assert additions==extras.get(mat,collections.Counter()),'Unapproved additional private/side triangles: '+mat
  else:
   assert not (extras.get(mat,collections.Counter())-additions),'Declared side triangles missing'
   top_additions=additions-extras.get(mat,collections.Counter())
   # Triangles are emitted per old source face by the producer; retain that boundedness.
   for t,count in top_additions.items():
    assert all(math.isfinite(x)for p in t for x in p)
    assert any(on_triangle(t,source)for source in declared),'New top outside all declared retired predecessor faces'
   oldarea=math.fsum(area(t)*n for t,n in declared.items());newarea=math.fsum(area(t)*n for t,n in top_additions.items())
   assert abs(oldarea-newarea-removed_area[mat])<=max(1e-9,oldarea*1e-10),'Projected retirement area differs from immutable review'
  unchanged[mat]=unaffected;retired[mat]=a-b;stats[mat]=dict(unchanged_triangle_instances=sum(unaffected.values()),retired_triangle_instances=sum((a-b).values()),current_triangle_instances=sum(b.values()),declared_removed_projected_area_m2=removed_area[mat],exact_added_side_triangle_instances=sum(extras.get(mat,{}).values()))
 return dict(unchanged=unchanged,retired=retired,summary=stats)

def on_triangle(candidate,source):
 a,b,c=source;ux=b[0]-a[0];uz=b[2]-a[2];vx=c[0]-a[0];vz=c[2]-a[2];den=ux*vz-uz*vx
 if abs(den)<1e-18:return False
 for p in candidate:
  x=p[0]-a[0];z=p[2]-a[2];u=(x*vz-z*vx)/den;v=(ux*z-uz*x)/den
  if min(u,v,1-u-v)<-1e-7:return False
  y=a[1]+u*(b[1]-a[1])+v*(c[1]-a[1])
  if abs(p[1]-y)>1e-8:return False
 return True
