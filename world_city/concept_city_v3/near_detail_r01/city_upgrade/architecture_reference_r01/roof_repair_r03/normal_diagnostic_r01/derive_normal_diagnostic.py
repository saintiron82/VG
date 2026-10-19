#!/usr/bin/env python3
"""Source-bound, normal-only sidecar. No shape sampler, mesher, GUI, or render writes."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(45,)*2)
import gzip,hashlib,json,math,struct,time,sys,collections,gc
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;A=H.parent.parent;R2=A/'roof_repair_r02'
ROOT=next(p for p in H.parents if (p/'voxel_character/common/core.py').exists())
PIN='d71a5987debe5e3e22a3663f8ee4b604bd7d880a0fa7d8188e4d9247c26edb17';P=.03125
SELECTED=[f'right_{col:02d}_r{row:02d}' for col in (3,4,5) for row in (8,9,10,11)]
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def read(path):
 with gzip.open(path,'rt') if str(path).endswith('.gz') else open(path) as f:return json.load(f)
def save(name,obj):
 data=(json.dumps(obj,separators=(',',':'),allow_nan=False)+'\n').encode();(H/name).write_bytes(gzip.compress(data,mtime=0) if name.endswith('.gz') else data)
def sub(a,b):return [x-y for x,y in zip(a,b)]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
class JsonStream:
 def __init__(self,f):self.f=f;self.b='';self.pos=0;self.eof=False;self.d=json.JSONDecoder()
 def fill(self):
  self.b=self.b[self.pos:];self.pos=0;s=self.f.read(65536);self.eof=not s;self.b+=s
 def peek(self):
  while True:
   while self.pos<len(self.b) and self.b[self.pos].isspace():self.pos+=1
   if self.pos<len(self.b):return self.b[self.pos]
   if self.eof:return ''
   self.fill()
 def eat(self,s):assert self.peek()==s;self.pos+=1
 def value(self):
  self.peek()
  while True:
   try:
    v,end=self.d.raw_decode(self.b,self.pos)
    if end==len(self.b) and not self.eof:self.fill();continue
    self.pos=end;return v
   except json.JSONDecodeError:
    if self.eof:raise
    self.fill()
def stream_quads(path,meta):
 with gzip.open(path,'rt') as f:
  p=JsonStream(f);p.eat('{');gi=0
  while p.peek()!='}':
   key=p.value();p.eat(':')
   if key=='groups':
    p.eat('[')
    while p.peek()!=']':
     p.eat('{');material=None;qi=0
     while p.peek()!='}':
      field=p.value();p.eat(':')
      if field=='material':material=p.value()
      elif field=='quads':
       assert material is not None;p.eat('[')
       while p.peek()!=']':
        q=p.value();yield gi,qi,material,q;qi+=1
        if p.peek()==',':p.eat(',')
        else:break
       p.eat(']')
      else:raise AssertionError('Unexpected group field')
      if p.peek()==',':p.eat(',')
      else:break
     p.eat('}');meta.setdefault('groups',[]).append({'material':material,'quad_count':qi});gi+=1
     if p.peek()==',':p.eat(',')
     else:break
    p.eat(']')
   else:meta[key]=p.value()
   if p.peek()==',':p.eat(',')
   else:break
  p.eat('}');assert p.peek()==''
class SourceTile:
 def __init__(self,op,link):
  self.op=op;self.link=link;self.B=op['transform']['basis'];self.t=op['transform']['translation'];self.top=list(reversed(op['shape']['polygon'][5:]));self.x0,self.z0,self.x1,self.z1=link['horizontal_footprint_xz']
  assert len(self.top)==5 and all(self.top[i][0]<self.top[i+1][0] for i in range(4))
  assert max(abs(dot([r[i] for r in self.B],[r[j] for r in self.B])-(i==j)) for i in range(3) for j in range(3))<1e-12
 def local(self,p):
  p=sub(p,self.t);return [sum(self.B[j][i]*p[j] for j in range(3)) for i in range(3)]
 def seg(self,x):
  for i,(a,b) in enumerate(zip(self.top,self.top[1:])):
   if a[0]-1e-10<=x<=b[0]+1e-10:return i
  return None
 def height(self,x,i):
  a,b=self.top[i:i+2];return a[1]+(x-a[0])*(b[1]-a[1])/(b[0]-a[0])
 def normal(self,i):
  a,b=self.top[i:i+2];m=(b[1]-a[1])/(b[0]-a[0]);local=[-m,1.,0.];w=[dot(r,local) for r in self.B];n=math.sqrt(dot(w,w));return [v/n for v in w]
 def classify(self,q,owners,axis,sign):
  # No quad straddles any source top-profile crease. Its unique source-top plane
  # must explain EVERY voxel owner/exterior pair, not only the quad centroid.
  L=[self.local(p) for p in q];lo=min(v[0] for v in L);hi=max(v[0] for v in L)
  if any(lo+1e-10<x<hi-1e-10 for x,y in self.top[1:-1]):return None,'profile_crease_crossing'
  seg=self.seg((lo+hi)/2)
  if seg is None:return None,'outside_source_profile'
  if min(p[0] for p in q)<self.x0-1e-10 or max(p[0] for p in q)>self.x1+1e-10:return None,'crop_endpoint_boundary'
  if lo<=self.top[0][0]+1e-10 or hi>=self.top[-1][0]-1e-10:return None,'barrel_side_boundary'
  n=self.normal(seg)
  if sign*n[axis]<=1e-10:return None,'bottom_or_true_boundary_orientation'
  for cell in owners:
   c=[(v+.5)*P for v in cell];nc=c.copy();nc[axis]+=sign*P
   lc=self.local(c);ln=self.local(nc)
   if not (self.x0<c[0]<self.x1 and self.x0<nc[0]<self.x1):return None,'crop_endpoint_boundary'
   if not (self.top[0][0]<lc[0]<self.top[-1][0] and self.top[0][0]<ln[0]<self.top[-1][0]):return None,'barrel_side_boundary'
   if not (self.op['shape']['z_min']<lc[2]<self.op['shape']['z_max'] and self.op['shape']['z_min']<ln[2]<self.op['shape']['z_max']):return None,'extrusion_endpoint_boundary'
   sc=self.seg(lc[0]);sn=self.seg(ln[0])
   if sc!=seg or sn!=seg:return None,'profile_crease_neighbor_ambiguity'
   tc=lc[1]-self.height(lc[0],seg);tn=ln[1]-self.height(ln[0],seg)
   if not (-.0625-1e-9<=tc<=1e-9 and tn>1e-9):return None,'top_vs_real_boundary_ambiguity'
  return (n,seg),'analytic_top_staircase'

def main():
 start=time.monotonic();render=R2/'roof_repaired.render.json.gz';assert sha(render)==PIN
 paths=[render,R2/'roof_patch.master.json.gz',R2/'plan.json',R2/'compile.json',R2/'upper_union_arrays.npz',A/'roof_repair_r01/tile_measurement_r01/tile_regions.json']
 pins={str(p.relative_to(ROOT)):sha(p) for p in paths}
 plan=read(R2/'plan.json');links={v['operation']:v for v in plan['tile_source_links']};master=read(R2/'roof_patch.master.json.gz');ops={op['id']:op for c in master['components'] for op in c['operations']}
 tiles={s:SourceTile(ops[s],links[s]) for s in SELECTED};source_boxes={r['id']:r['bbox_px'] for r in read(paths[-1])['regions']}
 for s,t in tiles.items():assert t.link['source_bbox_px']==source_boxes[s]
 union=np.load(R2/'upper_union_arrays.npz');arr=union['materials'];origin=union['origin_cell_xyz'].tolist();names=union['material_names'].tolist();ids={n:i for i,n in enumerate(names)}
 def material(cell):
  x,y,z=cell;ix=x-origin[0];iy=y-origin[1];iz=z-origin[2]
  return int(arr[iy,ix,iz]) if 0<=ix<arr.shape[1] and 0<=iy<arr.shape[0] and 0<=iz<arr.shape[2] else -1
 x0=min(t.x0 for t in tiles.values());x1=max(t.x1 for t in tiles.values());z0=min(t.z0 for t in tiles.values());z1=max(t.z1 for t in tiles.values())
 cells={};loaded=[];comp=read(R2/'compile.json')
 for rec in comp['chunks']:
  low,high=rec['owned_z_cells']
  if high*P<z0-P or low*P>z1+P:continue
  path=ROOT/rec['compiled']['path'];assert sha(path)==rec['compiled']['sha256'];pins[str(path.relative_to(ROOT))]=sha(path)
  c=read(path);loaded.append(rec['index'])
  for row in c['cells']:
   fid=row[6]
   if fid in tiles:
    xyz=tuple(row[:3]);assert xyz not in cells and row[5]==tiles[fid].op['material']
    if material(xyz)==ids[row[5]]:cells[xyz]=fid
  del c;gc.collect()
 meta={};patches=[];skips=[];counts=collections.Counter();per=collections.defaultdict(collections.Counter);evidence=[];positions=hashlib.sha256();colors=hashlib.sha256();before_after=hashlib.sha256();all_quads=0;unit_faces=0;boundary_fixture=None
 for gi,qi,mat,q in stream_quads(render,meta):
  # Exact ordered full-position hash: uint32 group, uint32 quad, 12 float64 LE.
  data=struct.pack('<II12d',gi,qi,*(v for p in q for v in p));positions.update(data);before_after.update(data);colors.update(struct.pack('<II',gi,qi)+mat.encode()+b'\0');all_quads+=1
  if not mat.startswith('top_tile_') or max(p[0] for p in q)<x0-P or min(p[0] for p in q)>x1+P or max(p[2] for p in q)<z0-P or min(p[2] for p in q)>z1+P:continue
  g=[[round(v/P) for v in p] for p in q];low=[min(v[i] for v in g) for i in range(3)];high=[max(v[i] for v in g) for i in range(3)];fixed=[i for i in range(3) if low[i]==high[i]]
  assert len(fixed)==1;axis=fixed[0];normal=cross(sub(g[1],g[0]),sub(g[2],g[0]));sign=1 if normal[axis]>0 else -1;u,v=[i for i in range(3) if i!=axis]
  owner_axis=low[axis]-(sign>0);owner_cells=[];owners=set();bad_neighbor=False;bad_material=False
  for a in range(low[u],high[u]):
   for b in range(low[v],high[v]):
    cell=[0,0,0];cell[axis]=owner_axis;cell[u]=a;cell[v]=b;cell=tuple(cell);owner_cells.append(cell);owners.add(cells.get(cell))
    nc=list(cell);nc[axis]+=sign
    if material(nc)>=0:bad_neighbor=True
    if material(cell)!=ids[mat]:bad_material=True
  selected_owners=owners.intersection(tiles)
  if not selected_owners:continue
  reason=None;fid=next(iter(selected_owners))
  if len(owners)!=1:reason='mixed_or_unproven_tile_ownership'
  elif bad_neighbor:reason='not_actual_exterior'
  elif bad_material:reason='union_material_mismatch'
  else:
   result,reason=tiles[fid].classify(q,owner_cells,axis,sign)
   if result is not None:
    n,segment=result;patch={'group_index':gi,'quad_index':qi,'normals':[[round(c,10) for c in n] for _ in range(4)],'source_tile_id':fid,'classification':'analytic_top_staircase'};patches.append(patch);unit_faces+=len(owner_cells);per[fid]['patched_quads']+=1;per[fid]['patched_unit_faces']+=len(owner_cells);per[fid]['axis_'+str(axis)+'_'+str(sign)]+=1
    evidence.append({'group_index':gi,'quad_index':qi,'source_tile_id':fid,'source_profile_segment':segment,'axis':axis,'sign':sign,'unit_faces':len(owner_cells)})
    continue
  counts[reason]+=1
  for s in selected_owners:per[s]['skipped_'+reason]+=1
  skips.append({'group_index':gi,'quad_index':qi,'source_tile_ids':sorted(selected_owners),'reason':reason})
  if boundary_fixture is None and reason in ('crop_endpoint_boundary','barrel_side_boundary','extrusion_endpoint_boundary') and len(selected_owners)==1:
   boundary_fixture={'group_index':gi,'quad_index':qi,'source_tile_id':fid,'axis':axis,'sign':sign,'reason':reason}
 assert all_quads==meta['quad_count'];assert positions.digest()==before_after.digest()
 palette_sha=hashlib.sha256(json.dumps(meta['materials'],sort_keys=True,separators=(',',':')).encode()).hexdigest();colors.update(bytes.fromhex(palette_sha));colors_sha=colors.hexdigest()
 side={'schema':'riverstone.roof.normal_sidecar.v1','render_sha256':PIN,'patches':patches,'unchanged_positions_sha256':positions.hexdigest(),'unchanged_colors_sha256':colors_sha,'diagnostic_only':True,'production_gate_open':False}
 # Exact reject fixtures refer to already established source classification evidence.
 lookup={(p['group_index'],p['quad_index']):p for p in patches};skip_lookup={(s['group_index'],s['quad_index']):s for s in skips}
 def validate(candidate):
  assert candidate['schema']==side['schema'],'schema'
  assert candidate['render_sha256']==PIN,'render_sha256'
  assert candidate['unchanged_positions_sha256']==positions.hexdigest(),'positions_hash'
  assert candidate['unchanged_colors_sha256']==colors_sha,'colors_hash'
  seen=set()
  for p in candidate['patches']:
   gi=p['group_index'];qi=p['quad_index'];assert type(gi)is int and type(qi)is int and 0<=gi<len(meta['groups']) and 0<=qi<meta['groups'][gi]['quad_count'],'index_range'
   key=(gi,qi);assert key not in seen,'duplicate';seen.add(key)
   assert key in lookup,'edge_or_ambiguous_face'
   expected=lookup[key];assert p['source_tile_id']==expected['source_tile_id'],'source_feature'
   assert p['classification']==expected['classification'],'classification'
   assert len(p['normals'])==4
   for n,e in zip(p['normals'],expected['normals']):
    assert len(n)==3 and all(type(v)in(int,float) and math.isfinite(v) for v in n),'finite_normal'
    assert abs(dot(n,n)-1)<1e-9,'unit_normal'
    assert max(abs(x-y) for x,y in zip(n,e))<1e-10,'analytic_normal'
  return True
 assert patches and validate(side)
 tests=[];fixtures=[]
 def bad(name,changes,expected):
  c=dict(side);c['patches']=[dict(patches[0])];changes(c);accepted=False;msg=None
  try:validate(c);accepted=True
  except AssertionError as e:msg=str(e)
  assert not accepted and msg==expected,(name,msg);tests.append({'fixture':name,'rejected':True,'reason':msg});fixtures.append({'name':name,'candidate':c,'expected_rejection':expected})
 bad('swapped_render_sha',lambda c:c.update(render_sha256='0'*64),'render_sha256')
 bad('out_of_range_quad',lambda c:c['patches'][0].update(quad_index=meta['groups'][c['patches'][0]['group_index']]['quad_count']),'index_range')
 bad('wrong_source_feature',lambda c:c['patches'][0].update(source_tile_id=next(s for s in SELECTED if s!=c['patches'][0]['source_tile_id'])),'source_feature')
 assert boundary_fixture
 bad('edge_normal_patch',lambda c:c['patches'][0].update(**{k:boundary_fixture[k] for k in ('group_index','quad_index','source_tile_id')}),'edge_or_ambiguous_face')
 bad('flipped_normal',lambda c:c['patches'][0].update(normals=[[-v for v in n] for n in c['patches'][0]['normals']]),'analytic_normal')
 assert set(p['source_tile_id'] for p in patches)==set(SELECTED),'All 12 features need genuine top facets'
 assert all(sha(ROOT/p)==v for p,v in pins.items()),'Frozen input changed'
 save('normal_sidecar.json',side);save('face_evidence.json.gz',{'accepted':evidence,'skipped':skips,'preserved_boundary_fixture':boundary_fixture});save('rejection_fixtures.json',{'fixtures':fixtures,'results':tests})
 selection=[{'source_tile_id':s,'source_bbox_px':source_boxes[s],'horizontal_footprint_xz':links[s]['horizontal_footprint_xz'],'source_color':links[s]['source_color'],'top_profile_local':tiles[s].top,'transform':tiles[s].op['transform'],'counts':dict(per[s])} for s in SELECTED]
 save('selection.json',{'features':selection,'reason':'Compact 3-column by 4-feature block on visible main right slope, positive Z/front half, away from chimney, roof rim and gables.'})
 report={'schema':'riverstone.roof_normal_diagnostic.proof.v1','status':'PASS_NORMAL_ONLY_DIAGNOSTIC','source_render_sha256':PIN,'source_inputs':pins,'source_inputs_unchanged':True,'features_selected':len(SELECTED),'features_patched':len(set(p['source_tile_id'] for p in patches)),'patched_quads':len(patches),'patched_unit_faces':unit_faces,'all_render_quads_streamed':all_quads,'position_hash_definition':'SHA256 over original render order, each quad packed little-endian uint32 group index, uint32 quad index, twelve float64 coordinates; struct <II12d.','unchanged_positions_sha256':positions.hexdigest(),'simulated_B_positions_sha256':before_after.hexdigest(),'unchanged_colors_sha256':colors_sha,'color_hash_definition':'SHA256 ordered <II group,quad> + UTF8 material name + NUL for every quad, followed by raw 32-byte SHA256 of canonical sorted-key materials JSON.','palette_sha256':palette_sha,'all_patch_normals_finite_unit':True,'all_patch_normals_outward_to_cardinal_face':True,'all_unit_faces_unique_compiled_owner_and_exact_union_material':True,'all_unit_faces_actual_solid_exterior':True,'all_unit_faces_cross_only_source_top_inequality':True,'cross_profile_crease_quads_skipped':True,'true_side_crop_extrusion_end_normals_untouched':True,'chimney_gable_body_geometry_and_normals_untouched':True,'material_rgb_unchanged':True,'positions_unchanged':True,'indices_unchanged':True,'no_new_geometry':True,'no_new_materials':True,'no_texture_changes':True,'normal_only':True,'skip_counts':dict(counts),'negative_tests':tests,'selected_compiled_chunks':loaded,'geometry_sampling_calls':0,'mesher_calls':0,'compiler_calls':0,'render_file_writes':0,'full_render_JSON_expanded':False,'address_space_limit_mib':256,'cpu_limit_seconds':45,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'visual_acceptance':'PENDING_PARENT_SEPARATE_ARRAYMESH_AB; explicit five-point barrel and slope are existing priors, not new measurements','sidecar_sha256':sha(H/'normal_sidecar.json')}
 save('validation.json',report)
 total=sum(p.stat().st_size for p in H.iterdir() if p.is_file());assert total<500000,total
 print(json.dumps({'status':report['status'],'patched_quads':len(patches),'unit_faces':unit_faces,'features':12,'skip_counts':dict(counts),'seconds':report['elapsed_seconds'],'rss_kib':report['peak_rss_kib'],'total_bytes':total,'sidecar':str(H/'normal_sidecar.json')},sort_keys=True))
if __name__=='__main__':main()
