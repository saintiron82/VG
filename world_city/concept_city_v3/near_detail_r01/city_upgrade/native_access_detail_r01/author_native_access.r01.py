"""Source-hash-bound native top surfaces -> existing common material-module demand.
No renderer/collision/source changes; all placement rectangles remain within one
actual retained source face. Source box metadata is only the semantic ownership
check, never the geometric support substitute.
"""
from pathlib import Path
import copy,hashlib,json,math,sys
HERE=Path(__file__).resolve().parent;U=HERE.parent;R=U.parents[3];C=U.parents[1]
sys.path.insert(0,str(U));from build_near_catalog import source_parts
P=.0125;EPS=1e-7

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def quant(v):
 q=round(v/P)
 if not math.isfinite(v)or abs(v-q*P)>EPS:raise ValueError('non-native-microgrid boundary')
 return q

def top_rectangle(q):
 if len(q)!=4 or any(len(p)!=3 for p in q):raise ValueError('quad required')
 e=[q[1][i]-q[0][i]for i in range(3)];f=[q[2][i]-q[0][i]for i in range(3)];n=cross(e,f)
 if n[1]<=0 or abs(n[0])+abs(n[2])>EPS:raise ValueError('only upward horizontal faces in this bounded revision')
 if max(p[1]for p in q)-min(p[1]for p in q)>EPS:raise ValueError('nonplanar top')
 points={(quant(p[0]),quant(-p[2]))for p in q};lo=[min(p[i]for p in points)for i in (0,1)];hi=[max(p[i]for p in points)for i in (0,1)]
 if points!={(x,z)for x in (lo[0],hi[0])for z in (lo[1],hi[1])}:raise ValueError('not exact rectangle')
 if min(hi[i]-lo[i]for i in (0,1))<=0:raise ValueError('empty rectangle')
 return lo+hi

def patches(rect):
 x0,y0,x1,y1=rect;out=[]
 for ix in range(x0//80,(x1-1)//80+1):
  for iy in range(y0//80,(y1-1)//80+1):
   a,b=max(x0,80*ix),max(y0,80*iy);c,d=min(x1,80*(ix+1)),min(y1,80*(iy+1))
   # Tiny <5cm strips do not receive decorative geometry; they remain original.
   if min(c-a,d-b)<4:continue
   trim={'width_m':(c-a)*P,'height_m':(d-b)*P,'offset_m':[(a-80*ix)*P,(b-80*iy)*P]}
   out.append({'trim':trim,'grid_xy':[ix,iy],'low_uv':[a*P,b*P],'high_uv':[c*P,d*P],'seed':[41873,41879,41887][(ix*17+iy*31)%3]})
 return out

def run():
 policy=read(HERE/'source_policy.json');ip=C/'playable_r01/generated/tile_r01/index.json';index=read(ip);assert sha(ip)==policy['source_city_index_sha256']
 plans=[];demand={};rows=[]
 for key,rule in policy['assets'].items():
  src=index['common_assets'][key];mp=R/src['master_path'];rp=R/src['render_path'];assert sha(mp)==src['master_sha256']and sha(rp)==src['render_sha256']
  m=read(mp);render=read(rp);assert not m.get('assembly_cuts',[]),'Cut-aware ownership not supported by this bounded source adapter'
  boxes=[]
  for inst,op,tr in source_parts(m):
   if inst['component']not in rule['source_components']:continue
   assert op['action']=='paint' and op['material']==rule['material']and op['shape']['kind']=='box'
   assert tr['basis']==[[1,0,0],[0,1,0],[0,0,1]],'Component orientation needs separately verified source-box adapter'
   s=op['shape'];boxes.append({'instance':inst['id'],'operation':op['id'],'min':[s['min'][i]+tr['translation'][i]for i in range(3)],'max':[s['max'][i]+tr['translation'][i]for i in range(3)],'operation_sha256':digest(op)})
  assert boxes
  selected=[];excluded={};placements=[]
  for gi,g in enumerate(render['groups']):
   if g['material']!=rule['material']:continue
   for qi,q in enumerate(g['quads']):
    try:rect=top_rectangle(q)
    except ValueError as e:excluded[str(e)]=excluded.get(str(e),0)+1;continue
    eps=src.get('pitch_m',render['pitch'])/2+EPS
    low=[min(p[i]for p in q)for i in range(3)];high=[max(p[i]for p in q)for i in range(3)]
    owners=[b for b in boxes if abs(q[0][1]-b['max'][1])<=eps and all(low[i]>=b['min'][i]-eps and high[i]<=b['max'][i]+eps for i in (0,2))]
    if not owners:excluded['no_declared_bearing_top_owner']=excluded.get('no_declared_bearing_top_owner',0)+1;continue
    face={'group_index':gi,'quad_index':qi,'quad_sha256':digest(q),'quad':q,'rect_uv_integer_cells':rect,'plane_y_m':q[0][1],'operation_owners':owners};selected.append(face)
    for p in patches(rect):
     trim=p['trim'];kind=rule['kind'];seed=p['seed'];token=kind+'_'+str(seed)+'_'+digest(trim)[:12]
     demand[token]={'id':token,'kind':kind,'seed':seed,'trim':trim}
     # XY source module is rigidly placed on local X/-Z, normal +Y.
     transform={'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[p['low_uv'][0],q[0][1]+policy['maximum_visual_offset_m'],-p['low_uv'][1]]}
     placements.append({'module_key':token,'transform':transform,'source_face_ref':[gi,qi],'source_face_sha256':face['quad_sha256'],'bounds_uv_m':p['low_uv']+p['high_uv'],'source_plane_y_m':q[0][1],'collision_changed':False})
  assert selected and placements
  # All emitted rectangles are inside exact original render rectangles. No AABB
  # or source metadata union is used to cover a missing native support face.
  lookup={(f['group_index'],f['quad_index']):f for f in selected}
  for p in placements:
   f=lookup[tuple(p['source_face_ref'])];r=[n*P for n in f['rect_uv_integer_cells']];b=p['bounds_uv_m'];assert r[0]-EPS<=b[0]<b[2]<=r[2]+EPS and r[1]-EPS<=b[1]<b[3]<=r[3]+EPS
  result={'asset_key':key,'source_master_path':src['master_path'],'source_master_sha256':src['master_sha256'],'source_render_path':src['render_path'],'source_render_sha256':src['render_sha256'],'rule':rule,'faces':selected,'placements':placements,'excluded':excluded,'existing_collision_unchanged':True};plans.append(result)
  rows.append({'asset_key':key,'selected_top_faces':len(selected),'planned_modules':len(placements),'excluded':excluded})
 save(HERE/'generated/source_plan.json',{'schema':'riverstone.native_access_detail.plan.v1','source_city_index_sha256':sha(ip),'policy_sha256':sha(HERE/'source_policy.json'),'assets':plans,'module_demand':list(demand.values()),'maximum_visual_collision_difference_m':policy['maximum_visual_offset_m'],'runtime_activation':False,'whole_city_upgrade_complete':False})
 print(json.dumps({'assets':rows,'module_demand_count':len(demand),'runtime_activation':False}))
if __name__=='__main__':run()
