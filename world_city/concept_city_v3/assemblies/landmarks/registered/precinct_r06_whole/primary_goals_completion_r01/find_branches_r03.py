"""Read-only finite route search on retained named approach and native floor owners."""
from pathlib import Path
import sys,json,time,math,heapq,os
os.environ['MPLCONFIGDIR']='/tmp/primary-goals-mpl'
O=Path(__file__).resolve().parent;B=O.parent;sys.path.insert(0,str(B))
from resolve_pack import *
from matplotlib.path import Path as MP
from scipy.ndimage import distance_transform_edt
O=Path(__file__).resolve().parent
SC=CITY/'evidence/r8_final110_runtime_r01/scene.json';PK=CITY/'assemblies/landmarks/registered/assembly_r01/resolved_placements.json';CAT=CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_final_catalog_r01/route_catalog_481_r01.json'

def write(n,d):(O/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def raster(polys,bounds,step):
 x0,z0,x1,z1=bounds;xs=np.arange(x0,x1+step/2,step);zs=np.arange(z0,z1+step/2,step);a=np.zeros((len(zs),len(xs)),bool)
 for poly in polys:
  x=np.array(poly);ix0=max(0,int(math.floor((x[:,0].min()-x0)/step)));ix1=min(len(xs)-1,int(math.ceil((x[:,0].max()-x0)/step)));iz0=max(0,int(math.floor((x[:,1].min()-z0)/step)));iz1=min(len(zs)-1,int(math.ceil((x[:,1].max()-z0)/step)))
  if ix0>ix1 or iz0>iz1:continue
  xx,zz=np.meshgrid(xs[ix0:ix1+1],zs[iz0:iz1+1]);hit=MP(poly).contains_points(np.column_stack((xx.ravel(),zz.ravel())),radius=1e-8).reshape(xx.shape);a[iz0:iz1+1,ix0:ix1+1]|=hit
 return a,xs,zs

def main():
 scene=load(SC);cat={r['id']:r for r in load(CAT)['routes']};pk=load(PK);ents={e['id']:e for e in pk['entrances']};cache={};results=[]
 for group,eid,rid in [('castle','castle_registered:front_gate_wing:main_entry','ROAD:CASTLE_APPROACH'),('cathedral','cathedral_registered:nave_aisles_transept:main_entry','ROAD:CATHEDRAL_APPROACH'),('monastery','monastery_registered:monastic_church:main_entry','ROAD:WEST_MONASTERY_EDGE')]:
  started=time.monotonic();e=ents[eid];floor=e['threshold_world_xyz_m'][1];end=[e['threshold_world_xyz_m'][i]-.6*e['forward_into_asset_world'][i]for i in [0,2]];graph=load(B/f'entry_graph_{group}.json');sources=graph['rows'];verts=[p for r in sources for p in r['polygon_xz_m']]+[end];bounds=[math.floor(min(v[0]for v in verts))-2,math.floor(min(v[1]for v in verts))-2,math.ceil(max(v[0]for v in verts))+2,math.ceil(max(v[1]for v in verts))+2];win=b.rect(*bounds);native=[];body=[];floors=[]
  for p in scene['common_instances']:
   a=scene['common_assets'][p['asset_key']];bb=a.get('bounds');py=p['position_m'][1]
   if bb is None:
    mesh=cache.setdefault(a['render_path'],load(ROOT/a['render_path']));bb=mesh['bounds']
   if bb['min'][1]+py>floor+2.2 or bb['max'][1]+py<floor-1e-7:continue
   if geo.intersection_area(b.xform(b.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),p),win)<1e-8:continue
   mesh=cache.setdefault(a['render_path'],load(ROOT/a['render_path']));native.append(dict(id=p['id'],cache=dict(path=a['render_path'],sha256=a['render_sha256']),position_m=p['position_m'],yaw_rad=p['yaw_rad']))
   body.extend(b.xform(q,p)for q in slab_rectangles(mesh,floor-py+.01,floor-py+2.2));floors.extend(b.xform(q,p)for q in horizontal(mesh,floor-py,True))
  step=.25;roadpts=[[p[0],p[2]]for p in cat[rid]['points_xyz_m']];roadpolys=b.ribbon(roadpts,cat[rid].get('source_width_m',4));mask,xs,zs=raster([r['polygon_xz_m']for r in sources]+floors+roadpolys,bounds,step);obs,_,_=raster(body,bounds,step);clear=distance_transform_edt(mask&~obs)*step>=.25
  # Public road only becomes a destination if its exact point lies on the retained named landing.
  road=cat[rid]['points_xyz_m'];candidates=[]
  for i,(aa,cc) in enumerate(zip(road,road[1:])):
   a=[aa[0],aa[2]];c=[cc[0],cc[2]];length=math.dist(a,c)
   for t in np.linspace(0,1,max(2,math.ceil(length/.25)+1)):
    q=[a[j]+float(t)*(c[j]-a[j])for j in range(2)]
    if not(bounds[0]<q[0]<bounds[2]and bounds[1]<q[1]<bounds[3]):continue
    ix=round((q[0]-bounds[0])/step);iz=round((q[1]-bounds[1])/step)
    if 0<=iz<len(zs)and 0<=ix<len(xs)and clear[iz,ix]:candidates.append((iz,ix,i,float(t),q))
  iz=round((end[1]-bounds[1])/step);ix=round((end[0]-bounds[0])/step);print(group,'grid',clear.shape,'open',clear.sum(),'endclear',clear[iz,ix],'targets',len(candidates),flush=True)
  target={(z,x):(si,t,q)for z,x,si,t,q in candidates};parents={(iz,ix):None};cost={(iz,ix):0.};heap=[(0.,iz,ix)];found=None
  if clear[iz,ix]:
   while heap:
    ds,z,x=heapq.heappop(heap)
    if ds!=cost[z,x]:continue
    if (z,x)in target:found=(z,x);break
    for dz,dx in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
     zz,xx=z+dz,x+dx
     if not(0<=zz<len(zs)and 0<=xx<len(xs)and clear[zz,xx]):continue
     if dz and dx and (not clear[z,xx]or not clear[zz,x]):continue
     nd=ds+math.hypot(dz,dx)*step
     if nd<cost.get((zz,xx),float('inf')):cost[zz,xx]=nd;parents[zz,xx]=(z,x);heapq.heappush(heap,(nd,zz,xx))
  chain=[]
  if found:
   cur=found
   while cur is not None:chain.append([float(xs[cur[1]]),float(zs[cur[0]])]);cur=parents[cur]
   chain=[target[found][2]]+chain+[end]
  row=dict(group=group,entrance=e,selected_exterior_standing_xz_m=end,source_road_id=rid,source_landing=graph['road_seams'],status='CANDIDATE'if chain else'NO_SOURCE_OWNED_CLEAR_PATH',grid_step_m=step,screen_clearance_m=.25,road_cut=dict(segment_index=target[found][0],t=target[found][1],point_xz_m=target[found][2])if found else None,polyline_xz_m=chain,actual_native_sources=native,screen=dict(end_clear=bool(clear[iz,ix]),public_targets=len(target),reachable=len(parents)),seconds=time.monotonic()-started)
  write(group+'_branch_search_r03.json',row);np.savez_compressed(O/(group+'_branch_grid_r03.npz'),clear=clear,xs=xs,zs=zs);print(group,row['status'],'points',len(chain),'seconds',row['seconds'],flush=True)
  results.append({k:v for k,v in row.items()if k not in('actual_native_sources','source_landing','polyline_xz_m')})
 write('branch_search_summary_r03.json',dict(scene=ref(SC),source_pack=ref(PK),routes=results))
if __name__=='__main__':main()
