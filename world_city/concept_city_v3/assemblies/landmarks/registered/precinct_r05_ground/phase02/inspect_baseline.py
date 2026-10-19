"""Read-only finite R6 ownership and grade study for two stepped holdings."""
import sys,json,hashlib,math,collections
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[6];CITY=ROOT/'world_city/concept_city_v3';sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import frozen_r6 as f
from world_city.runtime_city.checks import placement as geo

def load(p):return json.loads(p.read_text())
def ref(p):return{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def box(p):return[min(v[0]for v in p),min(v[1]for v in p),max(v[0]for v in p),max(v[1]for v in p)]
def rect(x,z,X,Z):return[[x,z],[X,z],[X,Z],[x,Z]]
def main():
 p=load(HERE.parent/'phase01/phase02_step_inputs.json');scene=f.load_scene();windows=[box([v for q in h['polygon_parts_xz_m']for v in q])for h in p['holdings']];idx=f.SurfaceIndex(scene,windows,margin=5);rows=[];raster={}
 for hi,h in enumerate(p['holdings']):
  x0,z0,x1,z1=windows[hi];nx,nz=round((x1-x0)*2),round((z1-z0)*2);inside=np.zeros((nz,nx),bool)
  for poly in h['polygon_parts_xz_m']:
   a,b,c,d=box(poly);inside[round((b-z0)*2):round((d-z0)*2),round((a-x0)*2):round((c-x0)*2)]=True
  ys=np.full(inside.shape,np.nan);owners=collections.Counter();misses=[];samples=[]
  for iz,ix in np.argwhere(inside):
   x,z=x0+(ix+.5)*.5,z0+(iz+.5)*.5;rr=idx.at(x,z)
   if not rr:misses.append([x,z]);continue
   r=max(rr,key=lambda r:idx.height(r,x,z));y=idx.height(r,x,z);ys[iz,ix]=y;owners[r['material']]+=.25;samples.append([x,z,y])
  route=[];station=0
  for a,b in zip(h['source_access']['polyline_xz_m'],h['source_access']['polyline_xz_m'][1:]):
   L=math.dist(a,b);n=max(1,math.ceil(L/.25));u=[-(b[1]-a[1])/L,(b[0]-a[0])/L]
   for j in range(n):
    t=j/n;pts=[]
    for side in(-1,0,1):
     x,z=[a[k]+(b[k]-a[k])*t+u[k]*side for k in(0,1)];rr=idx.at(x,z);pts.append({'xz_m':[x,z],'y_m':max([idx.height(r,x,z)for r in rr],default=None),'owners':[r['material']for r in rr]})
    route.append({'station_m':station+L*t,'samples':pts})
   station+=L
  edges=[]
  for dz,dx in[(0,1),(1,0)]:
   for iz,ix in np.argwhere(inside):
    zz,xx=iz+dz,ix+dx
    if zz>=nz or xx>=nx or not inside[zz,xx]or not np.isfinite(ys[iz,ix]+ys[zz,xx]):continue
    diff=abs(float(ys[zz,xx]-ys[iz,ix]))
    if diff>.3:edges.append({'a_xyz_m':[x0+(ix+.5)*.5,float(ys[iz,ix]),z0+(iz+.5)*.5],'b_xyz_m':[x0+(xx+.5)*.5,float(ys[zz,xx]),z0+(zz+.5)*.5],'rise_m':diff})
  vals=ys[np.isfinite(ys)];row={'holding_id':h['id'],'source_area_m2':h['area_m2'],'bounds_xz_m':windows[hi],'centroid_xz_m':h['centroid_xz_m'],'ground_height_range_m':[float(vals.min()),float(vals.max())],'rounded_half_m_height_area_m2':{k:v*.25 for k,v in sorted(collections.Counter(round(float(y)*2)/2 for y in vals).items())},'material_sample_area_m2':dict(owners),'missing_ground_samples':misses,'source_access_profile':route,'steep_cell_edges':edges,'source_access':h['source_access'],'polygon_parts_xz_m':h['polygon_parts_xz_m']};rows.append(row);raster[f'h{hi}_height']=ys;raster[f'h{hi}_mask']=inside;raster[f'h{hi}_bounds']=np.array(windows[hi]);print(h['id'],row['ground_height_range_m'],'missing',len(misses),'steep edges',len(edges),row['material_sample_area_m2'],flush=True)
 write(HERE/'baseline_study.json',{'base_scene':ref(f.SCENE_PATH),'source_step_inputs':ref(HERE.parent/'phase01/phase02_step_inputs.json'),'method':'0.5m planning-cell centers and 0.25m full-width access samples against exact frozen upward R6 triangles; design screening, not final support acceptance.','sample_grid_m':.5,'surface_records_in_windows':len(idx.records),'holdings':rows,'R16_reserved':ref(CITY/'assemblies/ordinary/registered/working_ranges_r01/terrain_handoff.json'),'R16_unresolved_collar_bounds':[209.9,132,228,151],'new_common_compile':False});np.savez_compressed(HERE/'baseline_raster.npz',**raster)
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(1,2,figsize=(14,10),layout='constrained')
 for i,(ax,h)in enumerate(zip(axes,rows)):
  im=ax.imshow(raster[f'h{i}_height'],origin='lower',extent=[windows[i][0],windows[i][2],windows[i][1],windows[i][3]],cmap='terrain',vmin=5,vmax=16);ax.plot(*zip(*h['source_access']['polyline_xz_m']),c='red',lw=1);ax.set_aspect('equal');ax.invert_yaxis();ax.set_title(h['holding_id']+'\n'+str(h['source_area_m2'])+' m²');ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');fig.colorbar(im,ax=ax,label='Frozen R6 upward ground Y (m)')
 fig.suptitle('Phase 02: existing stepped ground, before terrace design\nBlank patches retain existing native owners; red lines are unresolved source access');fig.savefig(HERE/'baseline_ground.png',dpi=130)
if __name__=='__main__':main()
