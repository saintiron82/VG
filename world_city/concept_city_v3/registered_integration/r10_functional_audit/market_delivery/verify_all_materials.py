"""Read-only independent full-material negative check, streamed one array at a time."""
import mmap,json,hashlib
from pathlib import Path
from .author import H,R,C,Source,geometry,canon
from world_city.runtime_city.checks import placement as g
import numpy as np

def main():
 source=Source();known=set(source.data['source_surface_hashes']);extras=[];refs={};counts={}
 base=C/'evidence/r8_final110_runtime_r01/scene.json'
 with base.open('rb')as f:
  m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);a=m.find(b'"surfaces":{')+12
  while m[a:a+1]==b'"':
   b=m.find(b'":',a);key=m[a+1:b].decode();s=b+2;e=m.find(b']]',s)+2;a=e+1
   if key in known:continue
   verts=json.loads(m[s:e]);refs[key]=hashlib.sha256(canon(verts)).hexdigest();counts[key]=0
   for i in range(0,len(verts),3):
    t=verts[i:i+3]
    if max(p[0]for p in t)<90 or min(p[0]for p in t)>126 or max(p[2]for p in t)<-11 or min(p[2]for p in t)>12:continue
    poly=[[v[0],v[2]]for v in t]
    if g.polygon_area(poly)<1e-10:continue
    extras.append(dict(material=key,triangle_index=i//3,source_triangle_xyz_m=t,source_triangle_sha256=hashlib.sha256(canon(t)).hexdigest(),polygon=poly,plane=np.linalg.solve([[v[0],v[2],1]for v in t],[v[1]for v in t]).tolist()));counts[key]+=1
   del verts
  m.close()
 for row in extras:source.idx.add(len(source.rows),row['polygon']);source.rows.append(row)
 route=load(H/'candidate_r01/routes.json');errors=[];checks=0
 for r in route['routes']:
  for p in r['points']:
   q=source.at(p[0],p[2]);checks+=1
   if abs(q['xyz_m'][1]-p[1])>1e-6:errors.append(dict(route=r['id'],stored=p,actual=q))
 old=load(H/'candidate_r01/source_grade_samples.json')
 for p in old['cross_section_samples']+[q for s in old['four_wheel_samples']for q in s['points']]:
  v=p['xyz_m'];q=source.at(v[0],v[2]);checks+=1
  if abs(q['xyz_m'][1]-v[1])>1e-6:errors.append(dict(stored=v,actual=q))
 out=dict(status='PASS_ALL_SOURCE_MATERIALS'if not errors else'FAIL',base_scene_sha256=source.data['base_scene']['sha256'],supplemental_material_hashes=refs,supplemental_local_face_counts=counts,exact_top_face_checks=checks,height_disagreements=errors,water_policy='Water is included for detection but would not be accepted as cart-bearing ground; no water face covers this site.',supplemental_source_faces=extras)
 p=H/'all_materials_verification.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items()if k not in ['supplemental_source_faces','supplemental_material_hashes']});assert not errors

def load(p):return json.loads(p.read_bytes())
if __name__=='__main__':main()
