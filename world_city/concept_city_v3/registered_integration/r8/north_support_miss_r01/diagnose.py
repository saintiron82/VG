import json,pathlib,struct,hashlib,math
ROOT=next(p for p in pathlib.Path(__file__).resolve().parents if(p/'voxel_character').is_dir());H=pathlib.Path(__file__).resolve().parent
P=ROOT/'world_city/concept_city_v3/traversal_r5/revisions/r06_r8_precinct/public_network_r18_runtime_r01/geometry/f9623b7fd90da9b4.json';j=json.loads(P.read_bytes());q=[62.7274894714355,-281.014770507812]
f=lambda x:struct.unpack('f',struct.pack('f',x))[0]
def sample(tri):
 a,b,c=[[v[0]-q[0],v[2]-q[1]]for v in tri];cross=lambda u,v:u[0]*v[1]-u[1]*v[0];v=[b[0]-a[0],b[1]-a[1]];w=[c[0]-a[0],c[1]-a[1]];den=cross(v,w)
 if den==0:return {'contains':False,'degenerate_xz':True}
 beta=cross([-a[0],-a[1]],w)/den;gamma=cross(v,[-a[0],-a[1]])/den;weights=[1-beta-gamma,beta,gamma];n=[v[1]*(tri[2][1]-tri[0][1])-(tri[1][1]-tri[0][1])*w[1],-den,(tri[1][1]-tri[0][1])*w[0]-v[0]*(tri[2][1]-tri[0][1])];ln=math.sqrt(sum(x*x for x in n));normal=[x/ln for x in n]if ln else[]
 return dict(contains=min(weights)>=-1e-12,barycentric=weights,height_y=sum(t[1]*s for t,s in zip(tri,weights)),normal_xyz=normal,xz_double_area=abs(den))
rows=[]
for i,t in enumerate(j['triangles']):
 if max(v[1]for v in t)<15.3 or min(v[1]for v in t)>16.7:continue
 if not(min(v[0]for v in t)-.01<=q[0]<=max(v[0]for v in t)+.01 and min(v[2]for v in t)-.01<=q[1]<=max(v[2]for v in t)+.01):continue
 rows.append(dict(face_index=i,source_face=j['source_face_indices'][i],triangle=t,double=sample(t),float32=sample([[f(v)for v in p]for p in t])))
report=dict(query_xz=q,geometry=dict(path=str(P.relative_to(ROOT)),sha256=hashlib.sha256(P.read_bytes()).hexdigest()),nearby=rows,contains_double=[r['source_face']for r in rows if r['double']['contains']],contains_float32=[r['source_face']for r in rows if r['float32']['contains']]);(H/'point_support.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
