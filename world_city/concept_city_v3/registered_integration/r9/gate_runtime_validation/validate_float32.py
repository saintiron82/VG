#!/usr/bin/env python3
"""Read-only preflight of finite patch triangles before expensive scene loading."""
import argparse,json,pathlib,hashlib,numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--patch',required=True,type=pathlib.Path);p.add_argument('--report',required=True,type=pathlib.Path);a=p.parse_args();d=json.loads(a.patch.read_bytes());bad=[];counts={'appended':0,'replacement':0}
 def check(t,where,source=None):
  f=np.asarray(t,dtype=np.float32);n=np.cross(f[1]-f[0],f[2]-f[0]);reason=None
  if not np.all(np.isfinite(f))or not np.all(np.isfinite(n)):reason='nonfinite float32'
  elif np.dot(n,n)==0:reason='float32 zero face'
  elif source is not None:
   o=np.asarray(source,dtype=np.float32);normal=np.cross(o[1]-o[0],o[2]-o[0])
   if np.dot(normal,n)<=0:reason='float32 replacement winding rejected by renderer'
  elif where['material']!='bank'and n[1]<=0:reason='float32 appended top winding rejected by renderer'
  if reason:bad.append(dict(where,reason=reason,source_xyz_m=t,float32_xyz_m=f.tolist()))
 for row in d['surface_edits']:
  for i,t in enumerate(row['replacement_triangles_xyz_m']):counts['replacement']+=1;check(t,{'kind':'replacement','material':row['material'],'source_triangle_index':row['triangle_index'],'replacement_index':i},row['source_triangle_xyz_m'])
 for mat,verts in d['appended_surfaces'].items():
  for i in range(0,len(verts),3):counts['appended']+=1;check(verts[i:i+3],{'kind':'appended','material':mat,'appended_triangle_index':i//3})
 report={'status':'PASS_PREFLIGHT_ONLY'if not bad else'REJECTED_BEFORE_RUNTIME','patch_path':str(a.patch),'patch_sha256':hashlib.sha256(a.patch.read_bytes()).hexdigest(),'triangles_checked':counts,'failures':bad,'geometry_modified':False,'capsule_executed':False,'cart_executed':False}
 with a.report.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'status':report['status'],'triangles_checked':counts,'failures':len(bad)}));return 1 if bad else 0
if __name__=='__main__':raise SystemExit(main())
