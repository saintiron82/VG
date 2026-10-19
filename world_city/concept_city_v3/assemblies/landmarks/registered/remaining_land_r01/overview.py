from prepare import *
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/riverstone_remaining_mpl')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.colors import ListedColormap
r=np.load(HERE/'review_masks.npz');p=load(CITY/'registered_source/plan.json');fig,axs=plt.subplots(1,2,figsize=(16,10),constrained_layout=True);extent=[BOUNDS[0],BOUNDS[2],BOUNDS[1],BOUNDS[3]]
for ax in axs:
 for b in p['blocks']:ax.add_patch(Polygon(b['polygon_xz_m'],facecolor='#f1eee8',edgecolor='#aaa',lw=.5))
 for b in p['spaces']:ax.add_patch(Polygon(b['polygon_xz_m'],facecolor='#cdd5d7',edgecolor='#777',lw=.5))
 for name,col in [('BLOCK_003','#65a0e6'),('BLOCK_005','#c597d0'),('BLOCK_015','#e7ba59'),('SITE_CLERGY','#b4ce85'),('SITE_MONASTERY','#93c7b7'),('merchant','#b850a0'),('water','#52a5c4'),('roof','#8e5542')]:ax.imshow(np.ma.masked_where(~r[name],r[name]),origin='lower',extent=extent,cmap=ListedColormap([col]),interpolation='nearest',zorder=3)
 for b in p['plots']:
  if b.get('land_use')=='enclosed_noble_compound':ax.add_patch(Polygon(b['polygon_xz_m'],facecolor='none',edgecolor='#587342',lw=1))
 ax.grid(alpha=.25);ax.set_aspect('equal');ax.set_xticks(np.arange(-450,451,50));ax.set_yticks(np.arange(-400,451,50));ax.set_xlabel('X / m');ax.set_ylabel('Z / m')
axs[0].set_xlim(-440,440);axs[0].set_ylim(415,-420);axs[1].set_xlim(-260,430);axs[1].set_ylim(405,-160)
fig.suptitle('Whole-cell candidate ground after existing plots, roofs, access, water, wall and pending merchant reservations\nSource planning only; 0.5 m grid, no new placements',fontsize=13);fig.savefig(HERE/'available_ground.png',dpi=130)
