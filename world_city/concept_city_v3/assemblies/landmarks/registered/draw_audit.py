"""Read-only projection diagram. Uses saved common vertices and proxy boxes."""
import itertools
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from build_audit import HERE,CONTROLS,IMAGE,camera_functions,pose,hull


def main():
    audit=json.loads((HERE/'concept_shape_audit.json').read_text());proxy=json.loads((HERE/'proxy_masses.json').read_text())
    project,_,_,_=camera_functions(json.loads(CONTROLS.read_text()))
    fig=plt.figure(figsize=(15.36,10.24),dpi=100);ax=fig.add_axes([0,0,1,1]);ax.imshow(plt.imread(IMAGE))
    for c in audit['frozen_cache_projection']:
        pts=c['projected_cache']['anchor_translation_only']['convex_envelope_px'];ax.add_patch(Polygon(pts,fill=False,color='#ff40a0',lw=1.1,ls='--'))
    for g in proxy['groups']:
        for m in g['masses']:
            half=[v/2 for v in m['size_xyz_m']];pts=[]
            for v in itertools.product(*[[-h,h] for h in half]):
                p=pose(v,m['position_local_xyz_m'],m['yaw_degrees']);p=[p[j]+g['world_anchor_xyz_m'][j] for j in range(3)];pts.append(project(p))
            ax.add_patch(Polygon(hull(pts),fill=False,color='#23efbe',lw=.6,alpha=.7))
    for m in audit['vertical_measurements']:
        a,b=m['tip_px'],m['base_px'];ax.plot([a[0],b[0]],[a[1],b[1]],color='#ffef54',lw=1);ax.plot(*a,'o',color='#ffef54',ms=2.5)
    ax.text(10,1002,'Magenta: old cache outer envelope after anchor-only translation. Mint: new component/roof proxy. Yellow: observed vertical span.',color='white',fontsize=10,bbox={'facecolor':'#111','alpha':.85,'pad':5})
    ax.set_xlim(0,1536);ax.set_ylim(1024,0);ax.axis('off');fig.savefig(HERE/'projected_silhouette_comparison.png',dpi=100);plt.close(fig)


if __name__=='__main__':main()
