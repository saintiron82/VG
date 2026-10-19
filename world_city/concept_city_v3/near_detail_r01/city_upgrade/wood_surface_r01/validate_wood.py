#!/usr/bin/env python3
"""Source/determinism/ownership tests. GPU performance is deliberately unmeasured."""
import collections, copy, hashlib, json, math
from pathlib import Path
import build_wood as w
from PIL import Image

def box_quads(lo,hi):
 result=[]
 for axis in range(3):
  uv=[a for a in range(3) if a!=axis]
  for sign in [-1,1]:
   q=[]
   for a,b in [(0,0),(1,0),(1,1),(0,1)]:
    p=list(lo);p[axis]=lo[axis] if sign<0 else hi[axis];p[uv[0]]=[lo,hi][a][uv[0]];p[uv[1]]=[lo,hi][b][uv[1]];q.append(p)
   if w.normal(q)[axis]*sign<0:q.reverse()
   result.append(q)
 return result

def fixtures():
 specs=[('door','door',[-2.3,0,0],[-1.2,2.2,.15]),('post','timber',[-.75,0,0],[-.4,2.5,.35]),('beam','timber_light',[.2,1.6,0],[2.5,1.95,.35])]
 master={'schema':'riverstone.voxel.master.v1','id':'wood_surface_source_samples_r01','revision':1,'grid_origin':[0,0,0],'materials':{'door':'946b45','timber':'654631','timber_light':'896143'},'components':[],'instances':[]}
 groups=[]
 for name,mat,lo,hi in specs:
  master['components'].append({'id':name,'operations':[{'id':name,'part':'solid','action':'paint','material':mat,'shape':{'kind':'box','min':lo,'max':hi}}]});master['instances'].append({'id':name,'component':name});groups.append({'material':mat,'quads':box_quads(lo,hi)})
 data={'schema':'riverstone.voxel.render.v1','source_id':master['id'],'source_revision':1,'master_hash':w.core.digest(master),'pitch':.025,'grid_origin':[0,0,0],'materials':master['materials'],'bounds':{'min':[-2.3,0,0],'max':[2.5,2.5,.35]},'groups':groups,'quad_count':18,'metadata':{'purpose':'source-owned showcase fixtures; not added to city'}}
 w.write(w.HERE/'showcase_samples.master.json',master);w.write(w.HERE/'showcase_samples.render.json',data)
 w.build_sidecar(w.HERE/'showcase_samples.master.json',w.HERE/'showcase_samples.render.json',w.HERE/'showcase_samples.wood.json')
 return master,data

def main():
 manifest=w.read(w.HERE/'manifest.json');baseline={}
 for name,row in manifest['assets'].items():
  s=w.read(w.HERE/row['sidecar'])
  for path in [s['source_master']['path'],s['render']['path']]:baseline[path]=w.sha(w.ROOT/path)
 textures1={n:w.sha(w.HERE/n) for n in ['wood_fibers.png','wood_endgrain.png']};w.textures();assert textures1=={n:w.sha(w.HERE/n) for n in textures1}
 tests={'texture_bytes_deterministic':True,'texture_sizes_small':True,'assets':{}}
 for n in textures1:
  im=Image.open(w.HERE/n);assert im.mode=='L' and im.width<=128 and im.height<=512
 fibers=Image.open(w.HERE/'wood_fibers.png');p=fibers.load()
 dx=sum(abs(p[x+1,y]-p[x,y]) for y in range(fibers.height) for x in range(fibers.width-1)) / ((fibers.width-1)*fibers.height)
 dy=sum(abs(p[x,y+1]-p[x,y]) for y in range(fibers.height-1) for x in range(fibers.width)) / (fibers.width*(fibers.height-1))
 assert dx>dy*3,'Fibers must actually vary transversely more than lengthwise'
 tests['fiber_directionality']={'transverse_mean_delta':dx,'lengthwise_mean_delta':dy,'ratio':dx/dy}
 for name,row in manifest['assets'].items():
  path=w.HERE/row['sidecar'];old=path.read_bytes();s=w.read(path);render=w.read(w.ROOT/s['render']['path']);master=w.read(w.ROOT/s['source_master']['path']);geometry_before=copy.deepcopy(render)
  s2=w.build_sidecar(w.ROOT/s['source_master']['path'],w.ROOT/s['render']['path'],path)
  assert path.read_bytes()==old,'Sidecar bytes nondeterministic'
  assert render==geometry_before
  assert w.core.digest(master)==render['master_hash'],'Render not generated from bound master'
  mapped={(x['group'],x['quad']) for x in s['quads']};fallback={(x[0],x[1]) for x in s['fallback_quads']}
  expected={(gi,qi) for gi,g in enumerate(render['groups']) if g['material'] in w.WOOD for qi in range(len(g['quads']))}
  assert mapped.isdisjoint(fallback) and mapped|fallback==expected
  assert len(mapped)==len(s['quads'])
  assert all(render['groups'][x['group']]['material'] in w.WOOD for x in s['quads'])
  for part in s['parts'].values():assert abs(w.core.dot(part['axis_asset_local'],part['axis_asset_local'])-1)<1e-8
  for record in s['quads']:
   if s['parts'][record['part']]['source_shape_kind']=='extrusion':assert record['mode']==1,'Voxel stair facets misclassified as cross-sections'
  tests['assets'][name]={'repeat_bytes_equal':True,'source_binding_verified':True,'source_render_bounds_palette_unchanged':True,'all_wood_quads_mapped_or_explicit_fallback':True,'nonwood_including_iron_unchanged':True,'stats':s['stats']}
 master,data=fixtures();side=w.read(w.HERE/'showcase_samples.wood.json')
 assert side['stats']['mapped_quads']==18 and side['stats']['cross_section_rings']==6
 parts=side['parts'];assert {tuple(v['axis_asset_local']) for v in parts.values()}=={(1,0,0),(0,1,0)}
 # UV orientation survives a complete asset rotation, including operation axes.
 rotation=w.core.transform({'basis':[[0,0,1],[0,1,0],[-1,0,0]],'translation':[10,0,4]})
 query=w.SourceQuery(master,data['pitch']);r=query.ops[0];axis,_=w.direction(r,{})
 q=data['groups'][0]['quads'][0];uv,mode,_=w.uv_for(q,r,axis,123)
 rotated=copy.deepcopy(r);rotated['transform']=w.core.compose(rotation,r['transform']);rq=[w.core.apply(rotation,p) for p in q]
 uv2,mode2,_=w.uv_for(rq,rotated,axis,123);assert uv2==uv and mode==mode2
 tests['rotated_asset_keeps_source_grain']=True
 # Verify local cuts reveal earlier instance layers, rather than cutting globally.
 layered=copy.deepcopy(master);layered['components']=[{'id':'base','operations':[{'id':'base','part':'solid','material':'timber','action':'paint','shape':{'kind':'box','min':[0,0,0],'max':[1,1,1]}}]},{'id':'top','operations':[{'id':'top','part':'solid','material':'door','action':'paint','shape':{'kind':'box','min':[0,0,0],'max':[1,1,1]}},{'id':'hole','part':'solid','action':'cut','shape':{'kind':'box','min':[0,0,0],'max':[.5,1,1]}}]}];layered['instances']=[{'id':'base','component':'base'},{'id':'top','component':'top'}]
 query=w.SourceQuery(layered,.1);assert query.ops[query.owner([.25,.25,.25])]['material']=='timber';assert query.ops[query.owner([.75,.25,.25])]['material']=='door'
 tests['instance_local_cut_precedence']=True
 assert all(w.sha(w.ROOT/path)==digest for path,digest in baseline.items());tests['input_files_byte_identical_after_generation']=True
 tests['collision']='No collision file, shape, body, source or reference is changed or emitted by this layer; native mesh-only adapter is additionally checked headlessly.'
 tests['performance']='No GPU benchmark measured. Only source/data and headless runtime checks are claimed.'
 w.write(w.HERE/'validation_python.json',tests);print(json.dumps(tests,indent=2))
if __name__=='__main__':main()
