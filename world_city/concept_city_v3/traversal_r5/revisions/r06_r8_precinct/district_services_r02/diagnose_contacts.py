"""Read-only nearest actual triangle provenance for the two failed northern cases."""
import pathlib,json,math
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def segment(p,a,b):
 d=[b[k]-a[k]for k in(0,1)];L=sum(x*x for x in d);t=max(0,min(1,sum((p[k]-a[k])*d[k]for k in(0,1))/L))if L>1e-20 else 0;return math.dist(p,[a[k]+t*d[k]for k in(0,1)])
def distance(p,t):
 signs=[]
 for a,b in zip(t,t[1:]+t[:1]):signs.append((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
 if (min(signs)>=-1e-10 or max(signs)<=1e-10)and abs(sum(t[i][0]*t[(i+1)%3][1]-t[(i+1)%3][0]*t[i][1]for i in range(3)))>1e-12:return 0.
 return min(segment(p,a,b)for a,b in zip(t,t[1:]+t[:1]))
def main():
 d=json.loads((H/'prepared_runtime.json').read_bytes());s=json.loads(pathlib.Path(d['sources']['scene']['path']).read_bytes());r=json.loads((H/'evidence/services_replay.json').read_bytes());out=[]
 for a in r['routes']:
  if not a['id'].startswith('NORTH_TWO'):continue
  pos=a['end_position'];p=[pos[0],pos[2]];rows=[]
  for mat,v in s['surfaces'].items():
   if mat=='water':continue
   for i in range(0,len(v),3):
    t=v[i:i+3]
    if min(x[1]for x in t)>17.5 or max(x[1]for x in t)<15.59:continue
    xz=[[x[0],x[2]]for x in t];dist=distance(p,xz)
    if dist<.32:rows.append(dict(material=mat,triangle_index=i//3,distance_xz=dist,vertices=t,area_xz=abs(sum(xz[i][0]*xz[(i+1)%3][1]-xz[(i+1)%3][0]*xz[i][1]for i in range(3)))/2))
  out.append(dict(case=a['id'],end=pos,near_faces=rows));print(a['id'],'nearfaces',len(rows));print(json.dumps(rows,indent=1))
 with(H/'evidence/north_contact_faces.json').open('x')as f:json.dump(dict(scene=d['sources']['scene'],cases=out),f,indent=2)
if __name__=='__main__':main()
