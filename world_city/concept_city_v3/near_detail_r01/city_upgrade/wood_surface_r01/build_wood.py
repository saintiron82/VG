#!/usr/bin/env python3
"""Deterministic appearance-only wood UV sidecars. Never compiles or writes geometry.
Evaluate exact source predicates on every inward face-cell center, preserving
instance-local cuts, ordered paint, assembly cuts and final instance precedence.
"""
from __future__ import annotations
import argparse, collections, gzip, hashlib, itertools, json, math, sys
from pathlib import Path
from PIL import Image
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'voxel_character'))
from common import core
WOOD={'door','door_dark','timber','timber_dark','timber_light','endgrain'}
SCHEMA='riverstone.directional_wood_surface.v1'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def read(path):
 b=Path(path).read_bytes()
 return json.loads(gzip.decompress(b) if str(path).endswith('.gz') else b)
def write(path,data):Path(path).write_bytes(canonical(data)+b'\n')
def sub(a,b):return [x-y for x,y in zip(a,b)]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def normal(q):
 n=cross(sub(q[1],q[0]),sub(q[2],q[0]));m=math.sqrt(sum(x*x for x in n));return [x/m for x in n]
def stable_seed(s):return int(hashlib.sha256(s.encode()).hexdigest()[:8],16)

def textures():
 """Analytic continuous fibers + sparse tapered knots, no pixel noise wallpaper."""
 W,H=128,512; im=Image.new('L',(W,H));px=im.load()
 knots=[(.23,.24,.045,.058),(.73,.69,.035,.046),(.48,.91,.025,.040)]
 for y in range(H):
  v=(y+.5)/H
  for x in range(W):
   u=(x+.5)/W
   bend=.018*math.sin(v*math.tau)+.007*math.sin(v*math.tau*3+u*math.tau)
   knot_dark=0
   for ku,kv,kw,kh in knots:
    dx=(u-ku+.5)%1-.5;dy=(v-kv+.5)%1-.5
    envelope=math.exp(-((dy/kh)**2+(dx/(kw*2.4))**2))
    bend+=.025*math.tanh(dx/kw)*envelope
    rr=math.hypot(dx/kw,dy/kh)
    if rr<1.7:
     ring=max(0,1-abs(math.sin(rr*math.pi*2))/.25)
     knot_dark+=20*ring*(1-rr/1.7)+24*max(0,1-rr*2)
   p=u+bend
   fibers=(math.sin(p*math.tau*23)+.38*math.sin(p*math.tau*47+.8)+.19*math.sin(p*math.tau*79))
   latewood=max(0,1-abs(math.sin(p*math.pi*29))/.20)
   longtone=6*math.sin(p*math.tau*5)+3*math.sin(v*math.tau*2+p*math.tau*7)
   # Very sparse elongated soft worn fibers, never rectangular seams.
   wear=max(0,math.sin(p*math.tau*13+1.2)-.94)*120*(.5+.5*math.sin(v*math.tau*3))
   value=128+13*fibers-17*latewood+longtone-knot_dark+wear
   px[x,y]=int(max(72,min(180,round(value/3)*3)))
 im.save(HERE/'wood_fibers.png',optimize=True)
 rings=Image.new('L',(128,128));rp=rings.load()
 for y in range(128):
  for x in range(128):
   dx=(x+.5-64)/64;dy=(y+.5-64)/64
   a=math.atan2(dy,dx);r=math.hypot(dx*1.04,dy*.94)
   phase=r*13+.10*math.sin(a*3)+.04*math.sin(a*7)
   ring=max(0,1-abs(math.sin(phase*math.pi))/.20)
   value=132-27*ring+4*math.sin(phase*math.pi*2)
   rp[x,y]=int(round(value/3)*3)
 rings.save(HERE/'wood_endgrain.png',optimize=True)
 return {'wood_fibers.png':sha(HERE/'wood_fibers.png'),'wood_endgrain.png':sha(HERE/'wood_endgrain.png')}

class SourceQuery:
 def __init__(self,master,pitch):
  self.master,self.pitch=master,pitch;self.ops=[];self.bins=collections.defaultdict(list);self.cache={}
  comps={c['id']:c for c in master['components']};inst={i['id']:i for i in master['instances']};trans={}
  def wt(k):
   if k not in trans:
    t=core.transform(inst[k].get('transform'));trans[k]=core.compose(wt(inst[k]['parent']),t) if inst[k].get('parent') else t
   return trans[k]
  for layer,i in enumerate(inst.values()):
   for o in comps[i['component']]['operations']:
    t=core.compose(wt(i['id']),core.transform(o.get('transform')))
    shape=core.prepare_shape(o['shape'],pitch)
    record={'id':len(self.ops),'layer':layer,'instance':i['id'],'component':i['component'],'part':o['part'],'feature':o['id'],'material':o.get('material'),'action':o['action'],'selector':o.get('selector',{}),'shape':shape,'transform':t,'metadata':o.get('metadata',{}),'pitch':pitch,'operation_transform':core.transform(o.get('transform'))}
    self._add(record)
  for o in master.get('assembly_cuts',[]):
   self._add({'id':len(self.ops),'layer':-1,'action':'assembly_cut','selector':o.get('selector',{}),'shape':core.prepare_shape(o['shape'],pitch),'transform':core.transform(o.get('transform'))})
 def _add(self,r):
  lo,hi=core.shape_bounds(r['shape']);cs=[core.apply(r['transform'],p) for p in itertools.product(*zip(lo,hi))]
  r['lo']=[min(p[i] for p in cs) for i in range(3)];r['hi']=[max(p[i] for p in cs) for i in range(3)]
  self.ops.append(r)
  # Half-metre spatial bins accelerate read-only source point queries.
  for b in itertools.product(*(range(math.floor(x*2)-1,math.floor(y*2)+2) for x,y in zip(r['lo'],r['hi']))):self.bins[b].append(r['id'])
 def owner(self,p):
  # p is a voxel center; exact integer index provides deterministic caching.
  key=tuple(round((p[i]-self.master.get('grid_origin',[0,0,0])[i])/self.pitch-.5) for i in range(3))
  if key in self.cache:return self.cache[key]
  layers={}
  for oi in self.bins.get(tuple(math.floor(v*2) for v in p),[]):
   r=self.ops[oi]
   if any(n<a-1e-8 or n>b+1e-8 for a,n,b in zip(r['lo'],p,r['hi'])):continue
   if not core.contains(r['shape'],core.inverse(r['transform'],p),epsilon=self.pitch*core.EPS):continue
   if r['action']=='assembly_cut':
    layers={k:v for k,v in layers.items() if not core.selector_matches(r['selector'],v)}
   elif r['action']=='paint':layers[r['layer']]=r
   elif r['layer'] in layers and core.selector_matches(r['selector'],layers[r['layer']]):del layers[r['layer']]
  result=layers[max(layers)]['id'] if layers else None
  self.cache[key]=result;return result
 def quad_owner(self,q,material):
  n=normal(q);face_axis=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3) if i!=face_axis]
  if abs(n[face_axis])<.999999:return None,'non_grid_face'
  lo=[min(p[i] for p in q) for i in range(3)];hi=[max(p[i] for p in q) for i in range(3)]
  counts=[round((hi[i]-lo[i])/self.pitch) for i in axes]
  owner=None
  for a,b in itertools.product(*(range(c) for c in counts)):
   p=[(x+y)*.5 for x,y in zip(lo,hi)];p[face_axis]-=n[face_axis]*self.pitch*.5
   for axis,k in zip(axes,[a,b]):p[axis]=lo[axis]+(k+.5)*self.pitch
   oi=self.owner(p)
   if oi is None:return None,'unowned_source_cell'
   if self.ops[oi]['material']!=material:return None,'source_material_mismatch'
   if owner is None:owner=oi
   elif owner!=oi:return None,'merged_source_operations'
  return owner,None if owner is not None else 'empty_face'

def unit(a):
 n=math.sqrt(core.dot(a,a));return [v/n for v in a]
def direction(r,axes):
 explicit=axes.get((r['component'],r['feature']))
 if explicit:
  a=explicit['grain_axis_component_local']
  a=core.mv(core.transpose(r['operation_transform']['basis']),a)
  if abs(core.dot(a,a)-1)>1e-6:return None,'invalid_explicit_axis'
  return a,'explicit_axis_sidecar'
 s=r['shape']
 if s['kind']=='lathe':return [0,1,0],'lathe_staves_y'
 if s['kind']=='extrusion':
  p=s['polygon']
  if len(p)!=4:return None,'unsupported_source_shape'
  e=[sub(p[(i+1)%4],p[i]) for i in range(4)]
  if any(abs(e[0][j]+e[2][j])>1e-6 or abs(e[1][j]+e[3][j])>1e-6 for j in range(2)):return None,'non_parallelogram_profile'
  lengths=[math.hypot(*v) for v in e[:2]];i=0 if lengths[0]>lengths[1] else 1
  if lengths[i]<lengths[1-i]*1.25:return None,'ambiguous_profile_axis'
  return unit(e[i]+[0]),'source_parallelogram_long_edge'
 if s['kind']!='box':return None,'unsupported_source_shape'
 ext=[b-a for a,b in zip(s['min'],s['max'])];rank=sorted(range(3),key=lambda a:ext[a],reverse=True)
 if ext[rank[0]]<ext[rank[1]]*1.25:return None,'ambiguous_long_axis'
 a=[0,0,0];a[rank[0]]=1
 return a,'source_box_unique_long_axis'

def uv_for(q,r,axis,seed):
 local=[core.inverse(r['transform'],p) for p in q]
 ln=core.mv(core.transpose(r['transform']['basis']),normal(q))
 end=abs(core.dot(ln,axis))>.95
 offset=[(seed%128)/128,((seed>>8)%512)/512]
 if r['shape']['kind']=='lathe':
  bottom=min(p[1] for p in r['shape']['profile']);top=max(p[1] for p in r['shape']['profile'])
  cap_band=r['pitch']*2+1e-8
  cap=end and (min(p[1] for p in local)>=top-cap_band or max(p[1] for p in local)<=bottom+1e-8)
  if cap:
   # Authored cap seams run along Z. Lid boards have side-grain, not trunk rings.
   return [[round(p[0]/1.6+offset[0],7),round(p[2]/6.4+offset[1],7)] for p in local],1,'cap_boards_z'
  theta=[math.atan2(p[2],p[0]) for p in local];ref=theta[0]
  theta=[ref+(t-ref+math.pi)%math.tau-math.pi for t in theta]
  return [[round(t*.4/1.6+offset[0],7),round(p[1]/6.4+offset[1],7)] for t,p in zip(theta,local)],1,'staves_y'
 # Diagonal voxel staircase facets are not cut ends. Until a precise end-plane
 # sidecar exists, retain side fibers on all diagonal faces rather than invent rings.
 if r['shape']['kind']=='extrusion':end=False
 # Construct a stable source-local orthonormal cross-section frame. Projection
 # follows diagonal source braces rather than their voxel stair-step normals.
 helper=[0,0,1] if abs(axis[2])<.9 else [1,0,0]
 transverse=unit(cross(axis,helper));other=unit(cross(axis,transverse))
 if end:
  lo,hi=core.shape_bounds(r['shape']);center=[(a+b)*.5 for a,b in zip(lo,hi)]
  corners=list(itertools.product(*zip(lo,hi)))
  span=lambda v:max(core.dot(p,v) for p in corners)-min(core.dot(p,v) for p in corners)
  size=max(span(transverse),span(other))*1.2
  return [[round(core.dot(sub(p,center),transverse)/size+.5,7),round(core.dot(sub(p,center),other)/size+.5,7)] for p in local],2,'cross_section_rings'
 if abs(core.dot(ln,transverse))>abs(core.dot(ln,other)):transverse=other
 return [[round(core.dot(p,transverse)/1.6+offset[0],7),round(core.dot(p,axis)/6.4+offset[1],7)] for p in local],1,'lengthwise_fibers'

def build_sidecar(master_path,render_path,out,axis_path=None):
 master=read(master_path);data=read(render_path);query=SourceQuery(master,data['pitch']);axis_data=read(axis_path) if axis_path else {};axes={}
 if axis_data:
  if axis_data.get('authored_master_sha256',axis_data.get('source_master_sha256'))!=sha(master_path):raise ValueError('Axis sidecar does not bind selected master')
  axes={(o['component_id'],o['operation_id']):o for o in axis_data['operations']}
 records=[];fallback=[];parts={};stats=collections.Counter();baseline=canonical(data)
 for gi,g in enumerate(data['groups']):
  if g['material'] not in WOOD:continue
  for qi,q in enumerate(g['quads']):
   stats['wood_quads']+=1;oi,why=query.quad_owner(q,g['material'])
   if oi is None:fallback.append([gi,qi,why]);stats[why]+=1;continue
   r=query.ops[oi];axis,reason=direction(r,axes)
   if axis is None:fallback.append([gi,qi,reason]);stats[reason]+=1;continue
   identity='/'.join([master['id'],r['instance'],r['part'],r['feature']]);seed=stable_seed(identity)
   uv,mode,kind=uv_for(q,r,axis,seed)
   records.append({'group':gi,'quad':qi,'part':str(oi),'uv':uv,'mode':mode,'wear':0.025})
   stats['mapped_quads']+=1;stats[kind]+=1
   if str(oi) not in parts:
    a=axis
    parts[str(oi)]={'instance_id':r['instance'],'component_id':r['component'],'operation_id':r['feature'],'part_id':r['part'],'material':r['material'],'source_shape_kind':r['shape']['kind'],'axis_operation_local':a,'axis_asset_local':core.mv(r['transform']['basis'],a),'axis_basis':reason,'seed':seed,'transform':r['transform']}
 assert baseline==canonical(data),'Geometry changed during sidecar generation'
 result={'schema':SCHEMA,'source_master':{'path':str(Path(master_path).relative_to(ROOT)),'sha256':sha(master_path)},'render':{'path':str(Path(render_path).relative_to(ROOT)),'sha256':sha(render_path),'source_id':data['source_id'],'payload_hash':data.get('payload_hash'),'quad_count':data['quad_count']},'geometry_fingerprint':hashlib.sha256(canonical({'groups':data['groups'],'bounds':data['bounds'],'materials':data['materials']})).hexdigest(),'policy':{'geometry':'unchanged vertices, normals, winding, bounds','collision':'not read, generated, replaced or altered','unknown_ownership':'unchanged base material','pixel_metres':0.0125,'mipmaps':True,'grain_fade_metres':[10,28],'random_noise':False,'source_cell_query':'all inward face-cell centers; source ordered operations; no volume compilation'},'parts':parts,'quads':records,'fallback_quads':fallback,'stats':dict(stats),'axis_override':{'path':str(Path(axis_path).relative_to(ROOT)),'sha256':sha(axis_path)} if axis_path else None}
 write(out,result);return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--master');p.add_argument('--render');p.add_argument('--out');p.add_argument('--axes');a=p.parse_args()
 hashes=textures()
 if a.master:
  result=build_sidecar(Path(a.master).resolve(),Path(a.render).resolve(),a.out,a.axes);print(json.dumps(result['stats']));return
 definitions=[('house_r04',ROOT/'world_city/concept_city_v3/near_detail_r01/source/house.r04.master.json',ROOT/'world_city/concept_city_v3/near_detail_r01/generated/house_near_r04.render.json'),('barrel_r01',HERE.parent/'prop_detail_r01/barrel_r01/master.json',HERE.parent/'prop_detail_r01/barrel_r01/render.json.gz')]
 manifest={'schema':'riverstone.wood_material_prototype.v1','textures':hashes,'assets':{},'gpu_benchmark':'not measured','reference':'User architectural photos inspected; restricted lengthwise tone, sparse knots, shallow wear; people/signage excluded.'}
 for name,m,r in definitions:
  result=build_sidecar(m,r,HERE/(name+'.wood.json'));manifest['assets'][name]={'sidecar':name+'.wood.json','sha256':sha(HERE/(name+'.wood.json')),'stats':result['stats']};print(name,result['stats'],flush=True)
 manifest['resources']={n:sha(HERE/n) for n in ['WoodSurface.gd','directional_wood.gdshader','build_wood.py'] if (HERE/n).exists()}
 write(HERE/'manifest.json',manifest)
if __name__=='__main__':main()
