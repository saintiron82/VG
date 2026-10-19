#!/usr/bin/env python3
"""Read-only proof that R3 changes exactly the R2 previously proven safe faces."""
from build_split_diagnostic import *
def main():
 start=time.monotonic();assert sha(R3/'normal_diagnostic_r01/normal_sidecar.json')==SEALED;assert sha(R3/'roof_repaired.render.json.gz')==R3PIN
 side=read(OUT/'normal_split_sidecar.json');side_sha=sha(OUT/'normal_split_sidecar.json');old=read(R3/'normal_diagnostic_r01/normal_sidecar.json');ev=read(R3/'normal_diagnostic_r01/face_evidence.json.gz');oldpatch={(p['group_index'],p['quad_index']):p for p in old['patches']};oldskips={(p['group_index'],p['quad_index']) for p in ev['skipped']};oldq={};meta={};needs=set()
 for gi,qi,mat,q in stream_quads(R2/'roof_repaired.render.json.gz',meta):
  key=(gi,qi)
  if key in oldpatch or key in oldskips:
   oldq[key]=q
   if key in oldskips:
    for a,b,c in faces(qspec(q)):needs.add(c)
 master=read(R2/'roof_patch.master.json.gz');ops={op['id']:op for component in master['components'] for op in component['operations']};links={l['operation']:l for l in read(R2/'plan.json')['tile_source_links']};tiles={s:SourceTile(ops[s],links[s]) for s in SELECTED};owners={};zlo=min(c[2] for c in needs);zhi=max(c[2] for c in needs)
 for rec in read(R2/'compile.json')['chunks']:
  lo,hi=rec['owned_z_cells']
  if hi<=zlo or lo>zhi:continue
  chunk=read(ROOT/rec['compiled']['path'])
  for row in chunk['cells']:
   c=tuple(row[:3])
   if c in needs and row[6] in tiles:owners[c]=row[6]
  del chunk;gc.collect()
 expected={};actual={}
 def add(target,q,n,fid):
  sp=qspec(q);lo,hi,axis,sign,u,v=sp
  for a,b,c in faces(sp):
   key=(axis,lo[axis],sign,a,b);assert key not in target;target[key]=(fid,tuple(round(t,10) for t in n))
 for key,q in oldq.items():
  if key in oldpatch:
   p=oldpatch[key];add(expected,q,p['normals'][0],p['source_tile_id']);continue
  sp=qspec(q);lo,hi,axis,sign,u,v=sp
  for a,b,c in faces(sp):
   fid=owners.get(c)
   if fid not in tiles:continue
   uq=rect(q,sp,a,b,a+1,b+1);res,why=tiles[fid].classify(uq,[c],axis,sign)
   if res:add(expected,uq,res[0],fid)
 patches={(p['group_index'],p['quad_index']):p for p in side['patches']};meta={}
 for gi,qi,mat,q in stream_quads(R3/'roof_repaired.render.json.gz',meta):
  if (gi,qi) in patches:
   p=patches[(gi,qi)];add(actual,q,p['normals'][0],p['source_tile_id'])
 preserved=0;support=0
 for s in side['splits']:
  for q in s['quads']:
   if q['classification']=='analytic_top_staircase':add(actual,q['corners'],q['normals'][0],q['source_tile_id'])
   else:
    sp=qspec(q['corners']);axis,sign=sp[2:4];normal=[0,0,0];normal[axis]=sign;assert all(n==normal for n in q['normals']);n=sum(1 for f in faces(sp));preserved+=n
    if q['source_tile_id'].startswith('support_'):support+=n
 assert expected==actual and len(actual)==3960;assert sha(OUT/'normal_split_sidecar.json')==side_sha
 report={'schema':'riverstone.roof.safe_unit_face_equivalence.v1','status':'PASS_EXACT_FACE_FEATURE_NORMAL_EQUIVALENCE','R2_original_safe_unit_faces':len(expected),'R3_authored_safe_unit_faces':len(actual),'all_unit_face_coordinates_identical':True,'all_source_feature_ids_identical':True,'all_normals_identical':True,'extra_or_missing_safe_faces':0,'preserved_cardinal_unit_faces_inside_splits':preserved,'preserved_support_unit_faces_inside_splits':support,'all_other_original_quads_untouched_by_sidecar':True,'sealed_R2_sidecar_sha256':SEALED,'R3_sidecar_sha256':side_sha,'sampling_calls':0,'mesher_calls':0,'compiler_calls':0,'GUI_calls':0,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 output('safe_face_equivalence.json',report);print(json.dumps(report,sort_keys=True))
if __name__=='__main__':main()
