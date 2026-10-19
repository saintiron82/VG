from .geometry import *
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/district-fabric-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Patch

def run():
 m=np.load(HERE/'planning_masks.npz');s=load(HERE/'selected_layout.json')if(HERE/'selected_layout.json').exists()else{'placements':[],'holdings':[]};fig,ax=plt.subplots(figsize=(12,11));a=np.full(SHAPE,0);a[m['domain']]=1;a[m['floor_1_0']]=2;a[m['floor_2_5']]=3;a[m['nonmatching_native']]=4
 from matplotlib.colors import ListedColormap
 ax.imshow(a,extent=[BOUNDS[0],BOUNDS[2],BOUNDS[3],BOUNDS[1]],interpolation='nearest',cmap=ListedColormap(['#eee9dd','#d8c4a7','#d5dfb7','#b9d8c6','#a9847b']),vmin=0,vmax=4)
 if(HERE/'backland_routes.json').exists():
  for r in load(HERE/'backland_routes.json')['routes']:
   for p in r['polygons_xz_m']:ax.add_patch(Polygon(p,fc='#6796a3',ec='none'))
 plan=load(CITY/'registered_source/plan.json')
 for r in plan['roads']:
  for p in ribbons(r['polyline_xz_m'],r['width_m']):ax.add_patch(Polygon(p,fc='#b0aea4',ec='none'))
 for h in s['holdings']:
  ax.add_patch(Polygon(h['holding_polygon_xz_m'],fc='none',ec='#334942',lw=.6))
  for p in h['core_court_polygons_xz_m']:ax.add_patch(Polygon(p,fc='#e8c47b',ec='none'))
 for p in s['placements']:
  for q in p['native_roof_polygons_xz_m']:ax.add_patch(Polygon(q,fc={'clay_red':'#aa6c52','wood_brown':'#7b6045','slate_gray':'#62747c'}[p['palette_id']],ec='#514f45',lw=.3))
  x,_,z=p['position_m'];ax.text(x,z,p['holding_id'].split(':')[-1].replace('R8_',''),fontsize=7,ha='center')
 for r in s.get('shared_private_routes',[]):
  for p in r['polygons_xz_m']:ax.add_patch(Polygon(p,fc='#729ca5',ec='none',alpha=.8))
 ax.set_xlim(60,400);ax.set_ylim(400,100);ax.set_aspect('equal');ax.set_title('BLOCK 015 | route-first attached parcel fabric',loc='left',fontsize=18);ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');ax.legend(handles=[Patch(fc='#b9d8c6',label='Actual +2.5m / proven restorable support'),Patch(fc='#d5dfb7',label='Actual +1m / proven restorable support'),Patch(fc='#a9847b',label='Retained nonmatching / held ordinary'),Patch(fc='#e8c47b',label='Actual open court'),Patch(fc='#6796a3',label='Shared private lane')],loc='upper right',fontsize=8);fig.savefig(HERE/'district_plan.png',dpi=170,bbox_inches='tight');plt.close(fig)
if __name__=='__main__':run()
