from author_plan import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle

def main():
 plan=load(HERE/'design_plan.json');pack=load(HERE/'resolved_placements.json');fig,axs=plt.subplots(1,2,figsize=(14,11),layout='constrained')
 for ax,h in zip(axs,plan['holdings']):
  w=box([v for p in h['polygon_parts_xz_m']for v in p]);ax.set_xlim(w[0]-8,w[2]+8);ax.set_ylim(w[3]+8,w[1]-8);ax.set_aspect('equal')
  for r in plan['native_reservations']:
   b=box(r['polygon_xz_m'])
   if b[2]<w[0]-5 or b[0]>w[2]+5 or b[3]<w[1]-5 or b[1]>w[3]+5:continue
   ax.add_patch(Polygon(r['polygon_xz_m'],facecolor='#bdb5ab',edgecolor='none'))
  for p in h['polygon_parts_xz_m']:ax.add_patch(Polygon(p,facecolor='#a9bc7e',edgecolor='none'))
  routes=next(r for r in plan['internal_routes']if r['holding_id']==h['id'])
  for p in routes['ribbon_polygons_xz_m']:ax.add_patch(Polygon(p,facecolor='#d4bc91',edgecolor='none'))
  for r in h['native_boundary_source_regions']:ax.add_patch(Polygon(r['polygon_xz_m'],facecolor='#5e655e',edgecolor='none'))
  for p in h['plantings']:
   x,y,z=p['position_m']
   if p['kind']=='tree':ax.add_patch(Circle((x,z),2.6,facecolor='#437443',edgecolor='#315431',lw=.4))
   else:ax.add_patch(Polygon([[x-3,z-1.5],[x+3,z-1.5],[x+3,z+1.5],[x-3,z+1.5]],facecolor='#71884d',edgecolor='#4d5734',lw=.4))
  if h['id'].startswith('B03'):
   c=plan['selected_stair_fit']['candidate'];ax.add_patch(Polygon(c['polygon_xz_m'],facecolor='#d8d3c3',edgecolor='#292a29',lw=.8));collar=load(HERE/'collar_design.json');ax.add_patch(Polygon(collar['polygon_xz_m'],facecolor='#c7b88f',edgecolor='#866033',lw=.7));ax.annotate('26 risers\n+8.1 → +12.0',xy=c['upper_landing_xz_m'],xytext=(-58,-174),arrowprops={'arrowstyle':'->'},fontsize=8)
  ax.set_title(h['id']+'\n'+str(h['area_m2'])+' m² source holding');ax.grid(alpha=.12);ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)')
 fig.suptitle('Phase 02: supported estate orchard links and abbey medicinal garden\nNative retaining boundaries, preserved existing owners (gray), service routes (tan); no city activation')
 fig.savefig(HERE/'phase02_plan.png',dpi=140)
if __name__=='__main__':main()
