"""Cross-pack conservative native-envelope SAT. Not replacement physics."""
import json, math, hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[4]; H=Path(__file__).resolve().parent

def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def envelope(a,p):
 b=a['bounds'];x,y,z=p['position_m'];t=p.get('yaw_rad',0);co,si=math.cos(t),math.sin(t)
 q=[(x+co*u+si*v,z-si*u+co*v)for u,v in [(b['min'][0],b['min'][2]),(b['max'][0],b['min'][2]),(b['max'][0],b['max'][2]),(b['min'][0],b['max'][2])]]
 return q,(y+b['min'][1],y+b['max'][1])
def hit(a,b):
 pa,ya=a;pb,yb=b
 if min(ya[1],yb[1])-max(ya[0],yb[0])<=.001:return False
 for poly in (pa,pb):
  for i,p in enumerate(poly):
   q=poly[(i+1)%4];n=(-(q[1]-p[1]),q[0]-p[0]);aa=[x*n[0]+z*n[1]for x,z in pa];bb=[x*n[0]+z*n[1]for x,z in pb]
   if min(max(aa),max(bb))-max(min(aa),min(bb))<=.001:return False
 return True

def main():
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument("--integration",default="integration_r01");args=parser.parse_args();out=H/args.integration
 index=json.load(open(out/'index.json'));rows=[];refs=[];retired=set()
 for ref in index['packs']:
  p=json.load(open(R/ref['path']));assert sha(R/ref['path'])==ref['sha256'];refs.append(ref);retired.update(p.get('remove_instance_ids',[]))
  for row in p.get('add_instances',[]):rows.append((ref['path'],row,envelope(p['common_assets'][row['asset_key']],row)))
  for replacement in p.get('replace_instances',[]):
   row=dict(replacement,position_m=replacement['expected_position_m'],yaw_rad=replacement.get('expected_yaw_rad',0))
   rows.append((ref['path'],row,envelope(p['common_assets'][row['asset_key']],row)))
 rows=[r for r in rows if r[1]["id"]not in retired]
 hits=[];tested=0
 for i,(pa,a,ea)in enumerate(rows):
  for pb,b,eb in rows[i+1:]:
   if pa==pb:continue
   tested+=1
   if hit(ea,eb):hits.append({'a':a['id'],'b':b['id'],'pack_a':pa,'pack_b':pb})
 report={'status':'PASS'if not hits else 'REVIEW_REQUIRED','method':'3D height band and yaw rectangle SAT using native render bounds; excludes within-pack intentional support/stacking already audited separately. No physics replay.','index_sha256':sha(out/'index.json'),'cross_pack_pairs':tested,'intersections':hits,'pack_refs':refs}
 (out/'cross_pack_bounds.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
