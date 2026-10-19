"""Bounded mmap source extraction; never decode the complete 203MB scene."""
import mmap,json,hashlib
from pathlib import Path
from world_city.runtime_city.checks import placement as g
H=Path(__file__).resolve().parent;R=H.parents[4];B=R/'world_city/concept_city_v3/evidence/r8_final110_runtime_r01/scene.json'
def canon(x):return json.dumps(x,separators=(',',':'),ensure_ascii=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def run():
 out=[];refs={};rectangle=[[90,-11],[126,-11],[126,12],[90,12]]
 with B.open('rb')as f:
  m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);base_hash=sha(m);assert base_hash=='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2';start=m.find(b'"surfaces":{')
  for key in ['road','space_civic','bank','ground_earth','land_D_MIXED']:
   a=m.find(('"'+key+'":[').encode(),start)+len(key)+3;b=m.find(b']],"',a)+2
   # Material-local decode, released immediately. No native assets or scene load.
   verts=json.loads(m[a:b]);refs[key]=sha(canon(verts));count=0
   for i in range(0,len(verts),3):
    t=verts[i:i+3]
    if max(p[0]for p in t)<90 or min(p[0]for p in t)>126 or max(p[2]for p in t)<-11 or min(p[2]for p in t)>12:continue
    out.append(dict(material=key,triangle_index=i//3,source_triangle_xyz_m=t,source_triangle_sha256=sha(canon(t))));count+=1
   print(key,len(verts)//3,'triangles;',count,'selected',flush=True);del verts
  m.close()
 d=dict(schema='riverstone.r10.market_delivery.source_excerpt.v1',base_scene=dict(path=str(B.relative_to(R)),sha256=base_hash),bounds_xz_m=[90,-11,126,12],source_surface_hashes=refs,source_faces=out,method='mmap readonly material-by-material JSON extraction, original global triangle indices and canonical SHA256; no source mutation')
 (H/'source_excerpt.json').write_text(json.dumps(d,separators=(',',':'))+'\n');print(len(out),'source faces')
if __name__=='__main__':run()
