"""Read-only bounded context extraction from the frozen scene and current addenda."""
import json,hashlib,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent; ROOT=H.parents[4];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
from world_city.concept_city_v3.registered_integration.r9.landward_gates.build_corridors import Ground,plane,ph
C=ROOT/'world_city/concept_city_v3';BASE=C/'evidence/r8_final110_runtime_r01/scene.json'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(n,x):(H/n).write_text(json.dumps(x,separators=(',',':'))+'\n')
def rect(a,b,c,d):return [[a,b],[c,b],[c,d],[a,d]]

def main():
 s=read(BASE);assets=s['common_assets'];inst={i['id']:i for i in s['common_instances']}
 for pr in read(C/'registered_integration/r9/integration_r02_camera/index.json')['packs']:
  p=read(ROOT/pr['path']);assets.update(p.get('common_assets',{}))
  for i in p.get('remove_instance_ids',[]):inst.pop(i,None)
  inst.update({i['id']:i for i in p.get('add_instances',[])})
 windows={'abbey':rect(-342,-32,-235,20),'clergy':rect(159,-209,221,-102)};data={}
 for name,w in windows.items():
  floor=8 if name=='abbey' else 14;bodies=[];floors=[];seen=[]
  for i in inst.values():
   a=assets[i['asset_key']];b=a.get('bounds');p=ROOT/a.get('render_path',a.get('cache',{}).get('path',''))
   if not b:
    if abs(i['position_m'][0]-w[0][0])>180 or abs(i['position_m'][2]-w[0][1])>180:continue
    mesh=read(p);b=mesh['bounds']
   poly=transform(rect(b['min'][0],b['min'][2],b['max'][0],b['max'][2]),i)
   if geo.intersection_area(poly,w)<1e-8:continue
   mesh=read(p);seen.append(dict(instance=i,asset=a))
   if b['min'][1]+i['position_m'][1]<floor+2.2 and b['max'][1]+i['position_m'][1]>floor+.01:
    for q in slab_rectangles(mesh,floor-i['position_m'][1]+.01,floor-i['position_m'][1]+2.2):
     q=transform(q,i)
     if geo.intersection_area(q,w)>1e-8:bodies.append(dict(id=i['id'],polygon_xz_m=q))
   for gr in mesh['groups']:
    for q in gr['quads']:
     if max(v[1]for v in q)-min(v[1]for v in q)>1e-7 or abs(q[0][1]+i['position_m'][1]-floor)>1e-7:continue
     a0,b0,c0=q[:3];ny=(b0[2]-a0[2])*(c0[0]-a0[0])-(b0[0]-a0[0])*(c0[2]-a0[2])
     if ny>0:
      pp=transform([[v[0],v[2]]for v in q],i)
      if geo.intersection_area(pp,w)>1e-8:floors.append(dict(id=i['id'],polygon_xz_m=pp))
  rows=[]
  for m,vs in s['surfaces'].items():
   for k in range(0,len(vs),3):
    t=vs[k:k+3];p=[[v[0],v[2]]for v in t]
    if max(v[0]for v in p)<w[0][0] or min(v[0]for v in p)>w[2][0] or max(v[1]for v in p)<w[0][1] or min(v[1]for v in p)>w[2][1]:continue
    rows.append(dict(material=m,triangle_index=k//3,triangle=t))
  data[name]=dict(window=w,floor_y_m=floor,bodies=bodies,floors=floors,instances=seen,surface_rows=rows)
 write('context.json',dict(base_scene=ref(BASE),sites=data))
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Polygon
 fig,axs=plt.subplots(1,2,figsize=(17,10))
 for ax,(name,d) in zip(axs,data.items()):
  for r in d['surface_rows']:
   if r['material']=='road':ax.add_patch(Polygon([[v[0],v[2]]for v in r['triangle']],color='tan',alpha=.5))
  for r in d['floors']:ax.add_patch(Polygon(r['polygon_xz_m'],color='lightgray',alpha=.3))
  for r in d['bodies']:ax.add_patch(Polygon(r['polygon_xz_m'],color='black',alpha=.8))
  w=d['window'];ax.set(xlim=(w[0][0],w[2][0]),ylim=(w[2][1],w[0][1]),title=name);ax.set_aspect('equal');ax.grid(True)
  if name=='abbey':ax.plot([-247.491,-259,-292,-298,-307,-314,-324,-324],[-7.333,-7.824,-7.824,-8,-8,-8,-8,-17],color='red',marker='o')
  else:ax.plot([172.928,185,190,199,205.872],[-198.194,-180,-162,-140,-130.957],color='red',marker='o')
 fig.savefig(H/'context_plan.png',dpi=130)
 print({k:dict(instances=len(v['instances']),bodies=len(v['bodies']),floors=len(v['floors']),terrain=len(v['surface_rows']))for k,v in data.items()})
if __name__=='__main__':main()
