"""Read-only result localization against the exact tested triangle/native caches."""
import pathlib,json,hashlib,math,importlib.util,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prep',H/'prepare_batch.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);b=p.b;ROOT=p.ROOT

def sub(a,c):return [a[i]-c[i]for i in range(3)]
def dot(a,c):return sum(x*y for x,y in zip(a,c))
def cross(a,c):return [a[1]*c[2]-a[2]*c[1],a[2]*c[0]-a[0]*c[2],a[0]*c[1]-a[1]*c[0]]
def distance(point,t):
 a,c,e=t;ac=sub(c,a);ae=sub(e,a);ap=sub(point,a);n=cross(ac,ae);nn=dot(n,n)
 candidates=[]
 if nn>1e-20:
  proj=[point[i]-n[i]*dot(ap,n)/nn for i in range(3)];pp=sub(proj,a);aa=dot(ac,ac);ab=dot(ac,ae);bb=dot(ae,ae);pa=dot(pp,ac);pb=dot(pp,ae);det=aa*bb-ab*ab
  if det>1e-20:
   u=(pa*bb-pb*ab)/det;v=(pb*aa-pa*ab)/det
   if min(u,v,1-u-v)>=-1e-9:candidates.append(math.dist(point,proj))
 for a,c in zip(t,t[1:]+t[:1]):
  v=sub(c,a);vv=dot(v,v);f=max(0,min(1,dot(sub(point,a),v)/vv))if vv else 0;candidates.append(math.dist(point,[a[i]+f*v[i]for i in range(3)]))
 return min(candidates)
def main():
 data=b.read(H/'prepared_runtime.json');route_map={r['id']:r for r in data['routes']};log=H/'evidence/network_initial.log';report=H/'evidence/network_initial.json'
 if report.exists():
  rs=b.read(report)['routes'];metrics=H/'evidence/network_metrics.json';complete=len(rs)==len(data['routes']) and metrics.exists() and b.read(metrics).get('exit_code') is not None
 else:rs=[json.loads(l[len('ROUTE_RESULT '):])for l in log.read_text().splitlines()if l.startswith('ROUTE_RESULT ')];complete=False
 cache={};findings=[]
 for r in rs:
  if r['pass'] or not r['obstacle_contact_samples']:continue
  hit=r['obstacle_contact_samples'][0];pid=hit['collider_id'];place=data['placements'].get(pid)
  if not place:continue
  asset=data['assets'][place['asset_key']];path=ROOT/asset['render_path']
  if path not in cache:cache[path]=b.read(path)
  native=cache[path];poss=[];point=hit['position']
  if asset.get('collision_format')in ['actual_scene_triangles','source_grade_proxy_triangles']:
   iterable=[(i,t)for i,t in enumerate(native['triangles'])]
  else:iterable=[((gi,qi),[b.transform(q[j],place)for j in inds])for gi,g in enumerate(native['groups'])for qi,q in enumerate(g['quads'])for inds in [[0,2,1],[0,3,2]]]
  for ident,t in iterable:
   if any(point[j]<min(v[j]for v in t)-.02 or point[j]>max(v[j]for v in t)+.02 for j in range(3)):continue
   dist=distance(point,t)
   if dist>.02:continue
   n=cross(sub(t[1],t[0]),sub(t[2],t[0]));length=math.sqrt(dot(n,n));normal=[v/length for v in n]if length else [0,0,0]
   source=native.get('source_face_indices',[None]*len(native.get('triangles',[])))[ident]if isinstance(ident,int)else {'group_index':ident[0],'quad_index':ident[1]}
   poss.append({'source_face':source,'distance_to_actual_contact_m':dist,'triangle_godot_xyz_m':t,'mathematical_normal_xyz':normal,'absolute_grade':math.hypot(n[0],n[2])/abs(n[1])if abs(n[1])>1e-12 else None})
  findings.append({'route_id':r['id'],'status':r['status'],'actual_contact':hit,'collider_asset':asset,'candidate_faces_within_2cm':sorted(poss,key=lambda v:v['distance_to_actual_contact_m'])[:12]})
 out={'schema':'riverstone.primary_network_contact_localization.v1','status':'FINAL'if complete else 'PARTIAL','completed_cases':len(rs),'raw_passed_cases':sum(r['pass']for r in rs),'scene':data['sources']['scene'],'prepared':b.ref(H/'prepared_runtime.json'),'findings':findings,'unlocalized_blocked_route_ids':[r['id']for r in rs if r['status']=='blocked'and not r['obstacle_contact_samples']],'limits':['Triangle matches identify the exact contacted surfaces within2cm; they do not authorize geometry edits.','Legacy registered MAIN_BRIDGE vectors remain a hypothesis; authoritative native-axis continuation is separately named.']}
 path=H/'evidence'/(f'contact_localization_final_{len(rs):03}.json'if complete else f'contact_localization_partial_{len(rs):03}.json');b.write(path,out)
 print(json.dumps({'report':b.ref(path),'completed':len(rs),'passed':sum(r['pass']for r in rs),'localized':len(findings),'first_findings':[{'id':f['route_id'],'faces':[q['source_face']for q in f['candidate_faces_within_2cm'][:3]],'at':f['actual_contact']['position']}for f in findings[:8]]}))
if __name__=='__main__':main()
