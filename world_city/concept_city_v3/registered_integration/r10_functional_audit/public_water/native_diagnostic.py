"""Native RenderData diagnostic, not an integrated runtime screenshot."""
import os;os.environ['MPLCONFIGDIR']='/tmp/r10-water-mpl'
import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
H=Path(__file__).resolve().parent;d=json.load(open(H/'frozen_r01/cache/aboveground_drawhouse.render.json'));fig=plt.figure(figsize=(12,5.8),facecolor='#e8e8e3')
for i,az in enumerate([65,120]):
 ax=fig.add_subplot(1,2,i+1,projection='3d');ax.set_facecolor('#e8e8e3')
 for group in d['groups']:
  quads=[[[p[0],p[2],p[1]]for p in q]for q in group['quads']];color=d['materials'][group['material']];color='#'+color.lstrip('#');ax.add_collection3d(Poly3DCollection(quads,facecolors=color,edgecolors='#00000015',linewidths=.15))
 ax.add_collection3d(Poly3DCollection([[[-2,-2,0],[2,-2,0],[2,2,0],[-2,2,0]]],facecolors='#b0ad98',alpha=.5))
 ax.set_xlim(-2.3,2.3);ax.set_ylim(-2.3,2.3);ax.set_zlim(0,4.5);ax.set_box_aspect([1,1,1]);ax.view_init(elev=12,azim=az);ax.set_axis_off()
 ax.set_title('Common native exterior, front '+('left'if i==0 else'right'),fontsize=12)
fig.suptitle('R10 above-ground public drawhouse | 9,739 cells / 520 quads\nNative-data diagnostic only; integrated lighting and runtime review pending',fontsize=13)
fig.tight_layout();fig.savefig(H/'native_geometry_diagnostic.png',dpi=150)
