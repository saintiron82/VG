"""Seven functional trade courts, native cached assets only. All writes are pack-local."""
from __future__ import annotations
import collections,copy,hashlib,heapq,json,math,time
from pathlib import Path
import numpy as np
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_integration.r9.port_market.author import ring,local,overlap,square,sha,BASE_SHA
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]

def load(p):return json.loads(Path(p).read_bytes())
def write(name,d):
 p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def circ(x,z,r):
 r=r/math.cos(math.pi/32)
 return [[x+r*math.cos((i+.5)*math.pi/16),z+r*math.sin((i+.5)*math.pi/16)] for i in range(32)]
def corridor(points,width):
 return [geo.road_ribbon(a,b,width) for a,b in zip(points,points[1:]) if math.dist(a,b)>1e-9]+[circ(*p,width/2) for p in points]

class Context:
 def __init__(self):
  self.c=load(HERE/'source_context.json');self.site=self.c['site']['polygon_xz_m'];self.assets=self.c['canopy_assets'];self.solids=copy.deepcopy(self.c['solids']);self.res=self.c['reservations'];self.reindex()
  self.ridx=geo._SpatialIndex(10)
  for i,r in enumerate(self.res):self.ridx.add(i,r['polygon'])
  self.tidx=geo._SpatialIndex(4);self.tris=self.c['triangles']
  for i,t in enumerate(self.tris):self.tidx.add(i,[[p[0],p[2]] for p in t['vertices']])
  self.ground_cache={}
 def reindex(self):
  self.sidx=geo._SpatialIndex(8)
  for i,s in enumerate(self.solids):self.sidx.add(i,s['polygon'])
 def blocked(self,poly,lo=3.5,hi=9):
  return sorted({s['id'] for i in self.sidx.candidates(poly) for s in [self.solids[i]] if s['y_max']>lo+.04 and s['y_min']<hi-.04 and overlap(poly,s['polygon'])})
 def reserved(self,poly):return sorted({self.res[i]['id'] for i in self.ridx.candidates(poly) if overlap(poly,self.res[i]['polygon'])})
 def height(self,x,z):
  key=(round(x,6),round(z,6))
  if key in self.ground_cache:return self.ground_cache[key]
  out=None
  for i in self.tidx.candidates(square(x,z,.00001)):
   t=self.tris[i];v=t['vertices'];poly=[[p[0],p[2]] for p in v]
   if not geo.point_in_convex_polygon([x,z],poly,1e-7):continue
   a,b,c=v;den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
   if abs(den)<1e-12:continue
   u=((b[2]-c[2])*(x-c[0])+(c[2]-b[2])*(z-c[2]))/den;w=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den
   h=u*a[1]+w*b[1]+(1-u-w)*c[1]
   if abs(h-4)<.025:out=dict(xz_m=[x,z],world_y_m=h,surface_key=t['key'],context_triangle_index=i);break
  self.ground_cache[key]=out;return out
 def support(self,poly):
  pts=poly+[[sum(p[k] for p in poly)/len(poly) for k in (0,1)]]+[[ (a[k]+b[k])/2 for k in (0,1)]for a,b in zip(poly,poly[1:]+poly[:1])]
  samples=[self.height(*p) for p in pts]
  return samples if all(samples) else None

# Each court is deliberately short and oriented to its local plaza edge.
# Axis endpoints are authored choices, not random scatter or density optimization.
GROUPS=[
 dict(id='GRAIN_WEST',label='Grain cart court',trade='grain',axis=[[38,8],[42,24],[48,40]],label_xz_m=[41,25],n=5,road='MARKET_WEST_EDGE',function='Bulk grain customers face an inner court; western rear loading connects to the established edge road and existing grain crates.'),
 dict(id='PRODUCE_CIVIC',label='Civic produce',trade='produce',axis=[[75,3],[76,18],[78,33]],label_xz_m=[76,16],n=5,road='MARKET_PROCESSION',function='Daily produce beside the civic approach, opening toward the clear fountain procession bypass.'),
 dict(id='GRAIN_SOUTHWEST',label='Grain weigh court',trade='grain',axis=[[51,52],[57,67],[64,82]],label_xz_m=[57,67],n=5,road='MARKET_WEST_EDGE',function='A second bulk court follows the southwestern edge and leaves a through loading gap to the first grain court.'),
 dict(id='TEXTILE_WEST',label='Linen court',trade='textile',axis=[[79,47],[82,63],[83,79]],label_xz_m=[82,63],n=5,road='MARKET_PROCESSION',function='Linen sellers face a narrow browsing court adjacent to the civic route, with the original southern cloth rack retained.'),
 dict(id='PRODUCE_EAST',label='Orchard produce',trade='produce',axis=[[117,16],[130,21],[143,26]],label_xz_m=[131,22],n=4,road='MARKET_EAST_EDGE',function='A short angled produce court follows the northeastern plaza edge and leaves the fountain gathering island open.'),
 dict(id='TEXTILE_EAST',label='Dyers court',trade='textile',axis=[[147,39],[148,51],[149,63]],label_xz_m=[149,51],n=4,road='MARKET_EAST_EDGE',function='Dyers and cloth merchants follow the eastern edge near existing casks, with open heads for loading access.'),
 dict(id='TEXTILE_SOUTH',label='Cloth exchange',trade='textile',axis=[[116,47],[121,64],[126,81]],label_xz_m=[121,64],n=5,road='MARKET_PROCESSION',function='Cloth exchange runs diagonally toward the south entry and keeps a clear service gap beside the eastern court.')]

def sample_axis(points,t):
 lengths=[math.dist(a,b) for a,b in zip(points,points[1:])];d=t*sum(lengths)
 for i,L in enumerate(lengths):
  if d<=L or i==len(lengths)-1:
   a,b=points[i:i+2];u=d/L;return [a[k]+u*(b[k]-a[k]) for k in (0,1)],[(b[k]-a[k])/L for k in (0,1)]
  d-=L

def placements(ctx):
 sources=collections.defaultdict(list)
 for p in ctx.c['old_stalls']:sources[p['asset_key']].append(p)
 pool={k:list(v) for k,v in sources.items()};out=[];groups=[];errors=[]
 for g in GROUPS:
  group=copy.deepcopy(g);group['stall_ids']=[]
  for j in range(g['n']):
   center,tangent=sample_axis(g['axis'],j/(g['n']-1));normal=[tangent[1],-tangent[0]]
   for side in [-1,1]:
    # Width-eight stalls are the middle anchors only, preserving a real source identity.
    suffix='cloth8' if j==2 and g['id']!='TEXTILE_EAST' else ('timber6' if j in (0,g['n']-1) and side==-1 else 'cloth6')
    oldkey='market_r3_'+suffix
    if not pool[oldkey]:oldkey='market_r3_cloth6';suffix='cloth6'
    src=pool[oldkey].pop(0);key=f"r9_canopy_{g['trade']}_{suffix}"
    pos=[center[0]+side*4.7*normal[0],4,center[1]+side*4.7*normal[1]]
    face=[-side*normal[0],-side*normal[1]];yaw=math.atan2(face[0],face[1])
    p=dict(id=f"R9_CLUSTER_{g['id']}:{j:02d}{'L' if side==-1 else 'R'}",asset_key=key,position_m=pos,yaw_rad=yaw,scale=[1,1,1],palette_id=f"r9_market_{g['trade']}",palette_override={},source_pack='r9_market_clusters',cluster_id=g['id'],trade_family=g['trade'],source_original_instance_id=src['id'],source_original_asset_key=src['asset_key'],source_original_position_m=src['position_m'],source_original_yaw_rad=src['yaw_rad'])
    poly=ring(ctx.assets[key]['bounds'],p);support=ctx.support(poly)
    fail=[]
    if not geo.convex_polygon_contains(ctx.site,poly,0):fail.append('outside_site')
    fail+=['reserved:'+x for x in ctx.reserved(poly)];fail+=['solid:'+x for x in ctx.blocked(poly)]
    if not support:fail.append('unsupported_ground')
    if fail:errors.append(dict(id=p['id'],reasons=fail))
    p.update(footprint_xz_m=poly,native_bottom_y_m=3.5,native_top_y_m=4+ctx.assets[key]['bounds']['max'][1],support_floor_y_m=4,support_samples=support or [],grounding_policy='Original native stall pose convention: local Y=0 at plaza Y=4; the -0.5 m native foot extension remains embedded, not floating.')
    out.append(p);group['stall_ids'].append(p['id']);ctx.solids.append(dict(id=p['id'],polygon=poly,y_min=3.5,y_max=p['native_top_y_m'],source='candidate'));ctx.reindex()
  groups.append(group)
 return out,groups,errors

def build():
 ctx=Context();out,groups,errors=placements(ctx)
 pack=dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=BASE_SHA,common_assets=ctx.assets,remove_instance_ids=[p['id'] for p in ctx.c['old_stalls']],add_instances=out,replace_instances=[],inspection_cameras={'r9_market_cluster_overview':dict(position_m=[108,78,160],target_m=[100,4,43],ortho_size_m=132,render_size_px=[1536,1024])})
 layout=dict(schema='riverstone.market.trade_courts.v1',clusters=groups,routes=[],status='PLACEMENT_DRAFT' if errors else 'PLACEMENT_CHECKS_PASS',placement_errors=errors)
 write('pack.json',pack);write('layout.json',layout);print(len(out),'stalls',len(errors),'placement errors');print(json.dumps(errors,indent=2))
 from .plan_view import draw
 draw(pack,layout,'candidate_plan.png')
if __name__=='__main__':build()
