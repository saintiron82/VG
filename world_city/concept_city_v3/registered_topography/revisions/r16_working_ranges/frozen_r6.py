"""Finite queries and edits bound to the corrected, sealed R6 scene."""
import hashlib,json,math
from . import author as a

SCENE_PATH=a.CITY/'evidence/visual_registered_common_r6_apron_r01/scene.json'
SCENE_SHA256='6e441b9ca417db63dccbb0bbccd48aa59e6a2a62079cdeeb3e5440d78f654844'
COLLAR_BOUNDS=[209.9,132.,228.,151.]

def canonical_sha(value):return hashlib.sha256(json.dumps(value,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load_scene():
 raw=SCENE_PATH.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=SCENE_SHA256:raise ValueError('Changed corrected R6 scene')
 return json.loads(raw)
def bounds(p):return [min(q[0] for q in p),min(q[1] for q in p),max(q[0] for q in p),max(q[1] for q in p)]
def overlap(b,c):return b[0]<=c[2]+1e-9 and c[0]<=b[2]+1e-9 and b[1]<=c[3]+1e-9 and c[1]<=b[3]+1e-9
def normal_y(t):
 p,q,r=t;return (q[2]-p[2])*(r[0]-p[0])-(q[0]-p[0])*(r[2]-p[2])
def upward(t):return [t[0],t[2],t[1]] if normal_y(t)<0 else t
def fan_upward(vs):
 for i in range(1,len(vs)-1):
  t=[vs[0],vs[i],vs[i+1]]
  if abs(normal_y(t))>1e-10:yield upward(t)
def lift(poly,plane):return [[p[0],a.height(plane,p),p[1]] for p in poly]
def default_windows():
 rows=a.native_holes()+a.court_regions()+a.terminal_domains()+a.walk_reservations()
 out=[bounds(r['polygon_xz_m']) for r in rows]
 out.append(COLLAR_BOUNDS);return out

class SurfaceIndex:
 def __init__(self,scene,windows=None,margin=1.):
  windows=default_windows() if windows is None else windows
  boxes=[[b[0]-margin,b[1]-margin,b[2]+margin,b[3]+margin] for b in windows]
  wi=a.geo._SpatialIndex(16)
  for i,b in enumerate(boxes):wi.add(i,[[b[0],b[1]],[b[2],b[3]]])
  self.records=[];self.index=a.geo._SpatialIndex(8);self.source_triangle_count=0
  for material,vertices in scene['surfaces'].items():
   self.source_triangle_count+=len(vertices)//3
   if material in ('water','bank'):continue
   for j in range(0,len(vertices),3):
    tri=vertices[j:j+3]
    if normal_y(tri)<=1e-10:continue
    p=[[v[0],v[2]] for v in tri];ids=wi.candidates(p)
    if not ids or not any(overlap(bounds(p),boxes[i]) for i in ids):continue
    row=dict(material=material,triangle_index=j//3,source_triangle_sha256=canonical_sha(tri),vertices_xyz_m=tri,polygon_xz_m=p,plane_y_xz_m=a.plane(tri))
    self.index.add(len(self.records),p);self.records.append(row)
 def intersecting(self,p):
  for i in sorted(self.index.candidates(p)):
   r=self.records[i]
   if a.clean(a.geo.convex_intersection(p,r['polygon_xz_m'])):yield r
 def at(self,x,z,tolerance=1e-8):
  return [self.records[i] for i in sorted(self.index.candidates([[x,z]])) if a.geo.point_in_convex_polygon([x,z],self.records[i]['polygon_xz_m'],tolerance)]
 def height(self,row,x,z):return a.height(row['plane_y_xz_m'],[x,z])
 def cover(self,p):
  return [dict(r,intersection_polygon_xz_m=q) for r in self.intersecting(p) if(q:=a.clean(a.geo.convex_intersection(p,r['polygon_xz_m'])))]

def apply_edits(scene,patch):
 """Pure source-index application; unchanged numeric triangles keep their order."""
 if patch['base_scene_sha256']!=SCENE_SHA256:raise ValueError('Wrong R16 base')
 original=scene['surfaces'];surfaces=dict(original);groups={};ledger=[]
 for e in patch['surface_edits']:
  m,i=e['material'],e['triangle_index']
  if not isinstance(i,int) or m not in original or not 0<=i<len(original[m])//3:raise ValueError('Invalid source triangle index')
  if i in groups.setdefault(m,{}):raise ValueError('Duplicate source index requires geometric composition')
  groups[m][i]=e
 for m,edits in groups.items():
  if canonical_sha(original[m])!=patch['source_surface_hashes'][m]:raise ValueError('Changed source array')
  result=[];unchanged=[]
  for start in range(0,len(original[m]),3):
   i=start//3;t=original[m][start:start+3]
   if i in edits:
    e=edits[i]
    if canonical_sha(t)!=e['source_triangle_sha256']:raise ValueError('Changed source triangle')
    result.extend(v for q in e['replacement_triangles_xyz_m'] for v in q)
   else:result.extend(t);unchanged.append(t)
  surfaces[m]=result;ledger.append(dict(material=m,count=len(unchanged),sequence_sha256=canonical_sha(unchanged)))
 for m,vs in patch.get('appended_surfaces',{}).items():surfaces[m]=surfaces.get(m,[])+vs
 if patch.get('removed_foundation_proxy_ids'):raise ValueError('R16 has no retired native or proxy owners')
 out=dict(scene,surfaces=surfaces)
 return out
