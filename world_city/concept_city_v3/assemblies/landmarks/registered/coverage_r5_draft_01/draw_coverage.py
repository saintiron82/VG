"""Readable plan accounting, not a concept-image segmentation or game render."""
from account_coverage import *
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/riverstone_coverage_mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Patch
from matplotlib.colors import ListedColormap

def main():
 report=load(HERE/'coverage_accounting.json');plan=load(CITY/'registered_source/plan.json');size=load(HERE/'ordinary_size_audit.json');r=np.load(HERE/'plan_raster.npz');fig=plt.figure(figsize=(18,12),constrained_layout=True);gs=fig.add_gridspec(2,2,width_ratios=[1.2,1]);ax=fig.add_subplot(gs[:,0]);cl=fig.add_subplot(gs[0,1]);mo=fig.add_subplot(gs[1,1]);extent=[BOUNDS[0],BOUNDS[2],BOUNDS[1],BOUNDS[3]]
 for b in plan['blocks']:ax.add_patch(Polygon(b['polygon_xz_m'],facecolor='#eeeae0',edgecolor='#6f716c',lw=.7))
 for s in plan['spaces']:ax.add_patch(Polygon(s['polygon_xz_m'],facecolor='#d9dde1',edgecolor='#9aa4b1',lw=.5))
 for p in plan['plots']:
  if p.get('land_use')=='enclosed_noble_compound':ax.add_patch(Polygon(p['polygon_xz_m'],facecolor='#d6dfc7',edgecolor='#8b9c75',lw=.6))
 ax.imshow(np.ma.masked_where(~r['roof'],r['roof']),extent=extent,origin='lower',cmap=ListedColormap(['#925841']),interpolation='nearest',zorder=3)
 for row,b in zip(report['ordinary_blocks'],plan['blocks']):
  pts=b['polygon_xz_m'];x=sum(q[0]for q in pts)/len(pts);z=sum(q[1]for q in pts)/len(pts);v=row['ordinary_review_domain']['native_roof_projection']['coverage_center'];label=b['id'].replace('BLOCK_','B')+'\n'+(f'{v:.0%}'if v is not None else'reserved');ax.text(x,z,label,fontsize=7.5,ha='center',va='center',zorder=5,bbox=dict(facecolor='white',edgecolor='none',alpha=.8,pad=1.2))
 buildings={b['id']:b for b in plan['buildings']}
 for row in size['prioritized_replacement_review']:
  x,z=buildings[row['instance_id']]['position_xz_m'];ax.scatter([x],[z],s=34,marker='*',color='#b21d25',zorder=8)
 ax.set_xlim(-465,465);ax.set_ylim(430,-405);ax.set_aspect('equal');ax.set_title('R5 draft: native roof plan\nLabels: roof share after protected precincts, estates and lanes are removed',fontsize=12);ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');ax.legend(handles=[Patch(color='#925841',label='Actual cached roof/canopy projection'),Patch(color='#d9dde1',label='Protected institutional/public space'),Patch(color='#d6dfc7',label='Reserved noble property'),Patch(color='#eeeae0',label='Ordinary block ground'),plt.Line2D([],[],marker='*',linestyle='None',color='#b21d25',label='Eight undersized retained master instances')],loc='lower left',fontsize=8)
 colors=['#ffffff','#925841','#d3b78d','#86a579','#678749','#c9bda0','#e2d8c2','#ddb957','#466949','#e6e7e7'];labels=['Outside precinct','Native roof','Public lane reservation','Existing garden/cemetery/orchard','New productive enclosure','New native service court','Old floor / procession','Exterior access candidate','Low native boundary belt','Unresolved implementation']
 for axis,sid in [(cl,'SITE_CLERGY'),(mo,'SITE_MONASTERY')]:
  site=next(s for s in plan['spaces']if s['id']==sid);row=next(s for s in report['precincts']if s['site_id']==sid);axis.imshow(r['precinct_classes'],extent=extent,origin='lower',cmap=ListedColormap(colors),vmin=0,vmax=9,interpolation='nearest');axis.add_patch(Polygon(site['polygon_xz_m'],facecolor='none',edgecolor='#303b35',lw=1));q=site['polygon_xz_m'];axis.set_xlim(min(p[0]for p in q)-5,max(p[0]for p in q)+5);axis.set_ylim(max(p[1]for p in q)+5,min(p[1]for p in q)-5);axis.set_aspect('equal');u=row['unresolved_native_land'];axis.set_title(f"{sid.replace('SITE_','').title()} | unresolved {u['center_sample_area_m2']:,.0f} m² ({row['unresolved_fraction_center']:.1%})\nBound: {u['area_lower_bound_m2']:,.0f}–{u['area_upper_bound_m2']:,.0f} m²",fontsize=11);axis.set_xlabel('World X (m)');axis.set_ylabel('World Z (m)')
 fig.legend(handles=[Patch(color=colors[i],label=labels[i])for i in range(1,10)],loc='outside lower center',ncol=3,fontsize=8.5);fig.suptitle('Where the registered city is still empty\n0.5 m source-bound plan raster; protected uses stay reserved. No concept-image roof segmentation or final-city approval.',fontsize=15);fig.savefig(HERE/'coverage_plan.png',dpi=130);plt.close(fig)
 print(ref(HERE/'coverage_plan.png'))
if __name__=='__main__':main()
