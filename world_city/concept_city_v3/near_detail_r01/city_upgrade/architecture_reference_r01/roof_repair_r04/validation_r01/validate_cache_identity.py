#!/usr/bin/env python3
"""Prove old source caches concatenate exactly to the pinned old final render.
No geometry generation, sampling, or renderer. Per-material ordered quad hashes
are computed using streamed final JSON and one small cache at a time.
"""
from validate_render import *
OLD=ARCH/'roof_repair_r03';F=ARCH/'foundation_repair_r01'
FROZEN='c5354c21ca7a12589f6a8ee0bd73ca9046c120a43914b0502b1fc88d96c120ca'
def add(out,material,q):
 assert len(q)==4 and all(len(p)==3 for p in q)
 # All coordinates normalized to exact integer lattice; additionally prove
 # lossless roundtrip for each original coordinate, excluding numeric aliases.
 g=[[round(n/PITCH) for n in p] for p in q];assert all(g[i][j]*PITCH==q[i][j] for i in range(4) for j in range(3))
 state=out.setdefault(material,[0,hashlib.sha256()]);state[0]+=1;state[1].update(json.dumps(g,separators=(',',':')).encode()+b'\n')
def summarize(out):return {m:{'quads':v[0],'ordered_lattice_quads_sha256':v[1].hexdigest()} for m,v in sorted(out.items())}
def main():
 t=time.monotonic();source=OLD/'roof_repaired.render.json.gz';assert sha(source)==FROZEN;composition=read(OLD/'composition.json');cacheplan=read(R/'cache_plan.json');assert composition['render']['sha256']==FROZEN and composition['lower_original_quads_clipped_at_join']==0
 expected={};lower=0;data=stream_render(F/'foundation_repaired.render.json.gz')
 for g in data['groups']:
  q=g['quads'][0];ys=[p[1] for p in q];n=cross(sub(q[1],q[0]),sub(q[2],q[0]));below=(ys[0]<9.5 or (ys[0]==9.5 and n[1]>0)) if min(ys)==max(ys) else max(ys)<=9.5
  if below:add(expected,g['material'],q);lower+=1
 assert lower==27998==composition['lower_original_quads_kept'];union=sha(OLD/'upper_union_arrays.npz');mesher=cacheplan['common_mesher'];assert sha(ROOT/mesher['path'])==mesher['sha256'];cacheproof=[]
 for i,record in enumerate(composition['chunks']):
  plan=cacheplan['chunks'][i];path=OLD/f'mesh_cache/chunk_{i:03d}.json.gz';before=sha(path);assert plan['index']==i and plan['original_cache']==ref(path);c=read(path)
  assert c['upper_union_sha256']==union and c['mesher_sha256']==mesher['sha256'] and c['owned_z_cells']==record['owned_z_cells']==plan['owned_z_cells'] and c['record']==record
  count=0
  for g in c['groups']:
   for q in g['quads']:add(expected,g['material'],q);count+=1
  assert count==record['owned_quads'] and sha(path)==before;cacheproof.append({'index':i,'sha256':before,'quads':count,'owned_z_cells':c['owned_z_cells']});del c;gc.collect()
 actual={};actual_groups=[];final=stream_render(source)
 for g in final['groups']:
  m=g['material']
  if not actual_groups or actual_groups[-1]!=m:actual_groups.append(m)
  add(actual,m,g['quads'][0])
 assert actual_groups==sorted(expected);assert summarize(actual)==summarize(expected),'Ordered cache concatenation differs from frozen final render';assert sum(v[0] for v in actual.values())==189509==composition['quad_count'];assert sha(source)==FROZEN
 report={'schema':'riverstone.roof_r04.r03_cache_identity.v1','status':'PASS_EXACT_ORDERED_CACHE_IDENTITY','source_render':ref(source),'source_composition':ref(OLD/'composition.json'),'source_union':ref(OLD/'upper_union_arrays.npz'),'foundation_render':ref(F/'foundation_repaired.render.json.gz'),'common_mesher':mesher,'cache_identity_verified':True,'total_cached_quads':sum(x['quads'] for x in cacheproof),'lower_quads':lower,'cache_partitions':len(cacheproof),'total_quads':189509,'ordered_material_groups':actual_groups,'per_material_ordered_quads':summarize(actual),'caches':cacheproof,'exact_ordered_material_and_quad_concatenation':True,'coordinate_normalization_lossless':True,'all_source_files_unchanged':True,'sampling_calls':0,'mesher_calls':0,'address_space_limit_mib':256,'cpu_limit_seconds':60,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-t,'validator':ref(Path(__file__))}
 save(HERE/'cache_identity_proof.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['caches','per_material_ordered_quads']},sort_keys=True))
if __name__=='__main__':main()
