from plan import *
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/riverstone_remaining_mpl');os.environ.setdefault('XDG_CACHE_HOME','/tmp/riverstone_cache')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Patch
from matplotlib.colors import ListedColormap
COLORS={'dense_court_housing':'#d89565','canal_workyard':'#d0aa68','working_compound':'#c4a273','estate_service_compound':'#c4a273','estate_productive_gardens':'#8fa875','institutional_edge_garden':'#a1b594','wall_service_garden':'#a5b49b','institutional_productive':'#8fbb79','cemetery_expansion':'#b9b7a3','institutional_workyard':'#d5bb84','ceremonial_open_ground':'#e4ddc4'}
def main():
 p=load(CITY/'registered_source/plan.json');d=load(HERE/'remaining_land_plan.json');a=load(HERE/'access_review.json');t=load(HERE/'terrain_screen.json');r=np.load(HERE/'review_masks.npz');pr=np.load(HERE/'program_raster.npz');fig=plt.figure(figsize=(23,12),constrained_layout=True);gs=fig.add_gridspec(2,3,width_ratios=[1.1,1,1]);main=fig.add_subplot(gs[:,0]);b15=fig.add_subplot(gs[:,1]);cl=fig.add_subplot(gs[0,2]);ab=fig.add_subplot(gs[1,2]);extent=[BOUNDS[0],BOUNDS[2],BOUNDS[1],BOUNDS[3]];axes=[main,b15,cl,ab]
 for ax in axes:
  for q in p['blocks']:ax.add_patch(Polygon(q['polygon_xz_m'],facecolor='#f2efe7',edgecolor='#bbb9ae',lw=.5))
  for q in p['spaces']:ax.add_patch(Polygon(q['polygon_xz_m'],facecolor='#e0e2df',edgecolor='#a0aaa0',lw=.7))
  for zone in d['zones']:
   for h in zone['contiguous_holdings']:
    for q in h['polygon_parts_xz_m']:ax.add_patch(Polygon(q,facecolor=COLORS[zone['function']],edgecolor='none',zorder=2))
  for k,col in [('merchant','#bc70ab'),('water','#64a8bb'),('roof','#895741')]:ax.imshow(np.ma.masked_where(~r[k],r[k]),extent=extent,origin='lower',interpolation='nearest',cmap=ListedColormap([col]),zorder=3)
  for b in d['range_parcels']:
   ax.add_patch(Polygon(b['building_envelope_xz_m'],facecolor='#b94f31',edgecolor='#703b2b',lw=.8,zorder=6))
  for q in a['connections']:
   if 'polyline_xz_m'in q:
    xs,zs=zip(*q['polyline_xz_m']);ax.plot(xs,zs,color='#355d65',lw=.7,alpha=.8,zorder=7)
  for zone in d['zones']:
   h=max(zone['contiguous_holdings'],key=lambda h:h['area_m2']);x,z=h['centroid_xz_m'];short=zone['id'].replace('B15_','15 ').replace('B03_','03 ').replace('B05_','05 ').replace('C_','C ').replace('A_','A ').replace('_','\n');ax.text(x,z,short,fontsize=6,ha='center',va='center',zorder=10,clip_on=True,in_layout=False,bbox=dict(facecolor='white',edgecolor='none',alpha=.7,pad=.7))
  ax.grid(alpha=.14);ax.set_aspect('equal');ax.set_xlabel('World X / m');ax.set_ylabel('World Z / m')
 main.set_xlim(-440,440);main.set_ylim(410,-410);main.set_title('Registered city: contiguous land programs\nOld precincts, plots and final 19 merchant holdings stay reserved',fontsize=11)
 b15.set_xlim(95,391);b15.set_ylim(370,108);b15.set_title('BLOCK_015: attached courts + canal work compounds\n14 native-dimension range parcels; rear lanes remain provisional',fontsize=11)
 cl.set_xlim(96,374);cl.set_ylim(-74,-375);cl.set_title('Cathedral: productive plots, school service and procession\nNo new building field across the church approach',fontsize=11)
 ab.set_xlim(-414,-120);ab.set_ylim(296,-49);ab.set_title('Abbey: continuous working/garden grounds\nExisting orchard, cloister and guarded access preserved',fontsize=11)
 handles=[Patch(color='#895741',label='Existing R5 native roof'),Patch(color='#b94f31',label='New source range parcel (uncompiled)'),Patch(color='#bc70ab',label='Pending final merchant 19 reservation'),Patch(color='#d89565',label='Dense ordinary housing courts'),Patch(color='#d0aa68',label='Working compound / canal yard'),Patch(color='#8fbb79',label='Productive precinct / estate gardens'),Patch(color='#b9b7a3',label='Burial expansion reservation'),Patch(color='#e4ddc4',label='Intentional procession / forecourt'),Patch(color='#a5b49b',label='Wall / institutional service terraces'),Patch(color='#f2efe7',label='Existing owners or unresolved land'),plt.Line2D([],[],color='#355d65',label='Provisional 2-D service/foot lane')]
 fig.legend(handles=handles,loc='outside lower center',ncol=4,fontsize=9);fig.suptitle('Remaining-land draft: meaningful holdings before more buildings\n34 functional zones / 60 contiguous holdings / 26 dimension-authored range parcels. Source-only; no new terrain, cache or scene placement.',fontsize=16);fig.savefig(HERE/'remaining_land_plan.png',dpi=130);plt.close(fig);print(ref(HERE/'remaining_land_plan.png'))
if __name__=='__main__':main()
