"""Read-only exact native deck/tread survey; no collider or geometry mutation."""
import json,pathlib,hashlib,math,numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());BASE=H.parent
P=BASE/'north_approach_r03/cache/registered_north_approach_r03_recessed_fixed.render.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def survey():
 d=json.loads(P.read_bytes()); xs=np.arange(-64.,64.001,.25);zs=np.arange(-4.,4.001,.25); floor=np.full((len(xs)-1,len(zs)-1),np.nan); owners={}
 for gi,g in enumerate(d['groups']):
  for qi,q in enumerate(g['quads']):
   a,b,c=np.array(q[:3]);n=np.cross(b-a,c-a)
   if n[1]<=0 or abs(n[0])+abs(n[2])>1e-10:continue
   y=q[0][1]
   if y<1. or y>4.1:continue
   xx=[v[0]for v in q];zz=[v[2]for v in q]
   ii=np.where((xs[:-1]+.125>=min(xx))&(xs[:-1]+.125<=max(xx)))[0];jj=np.where((zs[:-1]+.125>=min(zz))&(zs[:-1]+.125<=max(zz)))[0]
   for i in ii:
    if abs(xs[i]+.125)<7:continue
    for j in jj:
     if math.isnan(floor[i,j])or floor[i,j]<y:floor[i,j]=y;owners[f'{i}:{j}']=[gi,qi]
 result=[]
 for lo,hi in [(-64,-7),(7,64)]:
  ids=[i for i in range(len(xs)-1)if lo<=xs[i]<hi];rows=[]
  for i in ids:
   a=floor[i];rows.append(dict(x_interval=[float(xs[i]),float(xs[i+1])],minimum_y_m=None if np.isnan(a).all()else float(np.nanmin(a)),maximum_y_m=None if np.isnan(a).all()else float(np.nanmax(a)),missing_cells=int(np.isnan(a).sum())))
  result.append(dict(x_interval=[lo,hi],rows=rows,missing_cells=sum(r['missing_cells']for r in rows),maximum_transverse_native_step_m=max((r['maximum_y_m']-r['minimum_y_m'])for r in rows if r['maximum_y_m']is not None)))
 out=dict(schema='riverstone.fixed_bridge_native_tread_survey.v1',native_render=ref(P),source_id=d['source_id'],pitch_m=d['pitch'],lateral_interval_m=[-4,4],cell_grid_x=xs.tolist(),cell_grid_z=zs.tolist(),cell_top_heights=[[None if math.isnan(v)else v for v in row]for row in floor.tolist()],native_top_face_indices=owners,spans=result)
 target=H/'native_tread_survey.json'
 with target.open('x')as f:json.dump(out,f,separators=(',',':'));f.write('\n')
 print(json.dumps(dict(source=ref(target),spans=[{k:v for k,v in r.items()if k!='rows'}for r in result]),indent=2))
if __name__=='__main__':survey()
