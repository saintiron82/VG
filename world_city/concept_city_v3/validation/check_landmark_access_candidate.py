"""Reconstructed bounded native mesh cross-section helpers (2026-10-18).

The former complete landmark audit is not reconstructed by this file. Only its
public helper interface is supplied, with fresh algorithm tests. Axis-aligned,
closed, outward-oriented common voxel render quads are required. This is a
read-only audit of an existing mesh, not a mesher or collision approximation.
"""
import math
EPS=1e-9

def _merge_intervals(intervals):
 out=[]
 for lo,hi in sorted(intervals):
  if hi<=lo+EPS:continue
  if out and lo<=out[-1][1]+EPS:out[-1][1]=max(out[-1][1],hi)
  else:out.append([lo,hi])
 return out

def _union_rectangles(rects):
 """Exact rectilinear union with disjoint interiors; coordinates are not snapped."""
 zs=sorted({z for x0,z0,x1,z1 in rects for z in (z0,z1)})
 completed=[];active={}
 for z0,z1 in zip(zs,zs[1:]):
  mid=(z0+z1)/2
  runs=_merge_intervals((x0,x1) for x0,a,x1,b in rects if a<mid<b)
  nxt={}
  for x0,x1 in runs:
   key=(x0,x1)
   if key in active and abs(active[key][3]-z0)<EPS:r=active.pop(key);r[3]=z1
   else:r=[x0,z0,x1,z1]
   nxt[key]=r
  completed.extend(active.values());active=nxt
 completed.extend(active.values())
 return [[[x0,z0],[x1,z0],[x1,z1],[x0,z1]] for x0,z0,x1,z1 in completed]

def slab_rectangles(render,low_y,high_y):
 """Projection of solid occupancy in the open vertical slab (low_y, high_y).

 All mesh Y breakpoints partition the slab. Each interval is reconstructed via
 exact oriented X-plane crossings for every Z interval. Consequently an empty
 doorway below its lintel stays empty, and hollow courts aren't filled. A solid
 face merely touching the lower/upper slab boundary is excluded. Non-orthogonal,
 open, reversed or multiply covered boundary meshes fail explicitly.
 """
 if not math.isfinite(low_y) or not math.isfinite(high_y) or high_y<=low_y:raise ValueError('invalid finite slab')
 faces=[];ys={low_y,high_y}
 for group in render['groups']:
  for q in group['quads']:
   if len(q)!=4 or any(len(p)!=3 or any(not math.isfinite(v) for v in p) for p in q):raise ValueError('malformed quad')
   lo=[min(p[i] for p in q) for i in range(3)];hi=[max(p[i] for p in q) for i in range(3)]
   flat=[i for i in range(3) if abs(hi[i]-lo[i])<EPS]
   if len(flat)!=1:raise ValueError('quad is not a nondegenerate orthogonal face')
   u=[q[1][i]-q[0][i] for i in range(3)];v=[q[2][i]-q[1][i] for i in range(3)]
   n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
   axis=flat[0]
   if abs(n[axis])<EPS or any(abs(n[i])>EPS for i in range(3) if i!=axis):raise ValueError('bad quad winding')
   for y in (lo[1],hi[1]):
    if low_y<y<high_y:ys.add(y)
   if axis==0 and hi[1]>low_y and lo[1]<high_y:faces.append((lo[0],lo[1],hi[1],lo[2],hi[2],1 if n[0]>0 else -1))
 rects=[];ys=sorted(ys)
 for y0,y1 in zip(ys,ys[1:]):
  y=(y0+y1)/2;active=[f for f in faces if f[1]<y<f[2]]
  zs=sorted({z for f in active for z in (f[3],f[4])})
  for z0,z1 in zip(zs,zs[1:]):
   z=(z0+z1)/2;events={}
   for x,_,__,a,b,sign in active:
    if a<z<b:events[x]=events.get(x,0)-sign
   winding=0;start=None
   for x,delta in sorted(events.items()):
    before=winding;winding+=delta
    if winding not in (0,1):raise ValueError('non-union or reversed native boundary')
    if before==0 and winding==1:start=x
    if before==1 and winding==0:rects.append([start,z0,x,z1])
   if winding:raise ValueError('open native boundary in requested slab')
 return _union_rectangles(rects)

def transform(poly,placement):
 """Rigid upright placement using the existing native yaw convention."""
 if any(abs(v-1)>EPS for v in placement.get('scale',[1,1,1])):raise ValueError('audit requires native unit scale')
 pos=placement['position_m'];yaw=placement.get('yaw_rad',0);c=math.cos(yaw);s=math.sin(yaw)
 return [[pos[0]+c*p[0]+s*p[1],pos[2]-s*p[0]+c*p[1]] for p in poly]
