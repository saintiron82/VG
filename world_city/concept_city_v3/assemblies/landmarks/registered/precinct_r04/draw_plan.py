from plan_coverage import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

def main():
 p=load(HERE/'coverage_plan.json');fit=load(HERE/'native_building_fit.json');prod=load(HERE/'productive_frames.json');garden=load(GARDEN);land=load(LAND);fig,axes=plt.subplots(1,2,figsize=(16,10));colors=['#bd9f72','#8caba3','#c4958a','#b5ac8b','#9aaebf','#ae97b7']
 for ax,site in zip(axes,p['sites']):
  ax.add_patch(Polygon(site['polygon_xz_m'],facecolor='#e5e1cb',edgecolor='#45443c',lw=2)); sid=site['id']
  for q in garden['sites']:
   if q['space']==sid:ax.add_patch(Polygon(q['polygon_xz_m'],facecolor='#557d50',edgecolor='#365734',alpha=.7))
  for f in land['owned_floors']:
   if any(geo.positive_area_overlap(f['polygon_xz_m'],t,0)for t in triangulate(site['polygon_xz_m'])):ax.add_patch(Polygon(f['polygon_xz_m'],facecolor='#74766d',edgecolor='white',lw=.3))
  for i,c in enumerate(p['compounds']):
   if c['site_id']!=sid:continue
   for q in c['available_regions_xz_m']:ax.add_patch(Polygon(q,facecolor=colors[i],edgecolor='none',alpha=.85))
   ax.text(*c['center_xz_m'],c['id'].replace('CLERGY_','').replace('ABBEY_','').replace('_',' '),fontsize=8,ha='center',weight='bold')
  for b in fit['placements']:
   if b['site_id']==sid:ax.add_patch(Polygon(b['outer_footprint_xz_m'],facecolor='#925544'if b['role']!='school'else'#536b74',edgecolor='#3e322b',lw=.6))
  for f in prod['frames']:
   if f['site_id']==sid:ax.add_patch(Polygon(f['polygon_xz_m'],facecolor='#b8c89b',edgecolor='#496c39',lw=1.5));ax.text(*f['center_xz_m'],f['function'].replace('_',' '),fontsize=7,ha='center')
  for r in p['reserved_records']:
   if r['kind']=='recovered_landmark_access' and any(geo.positive_area_overlap(r['polygon_xz_m'],t,0)for t in triangulate(site['polygon_xz_m'])):ax.add_patch(Polygon(r['polygon_xz_m'],facecolor='#e9c868',edgecolor='none',alpha=.2))
  ax.set_aspect('equal');ax.autoscale();ax.invert_yaxis();ax.set_title(sid+' | native service compounds + productive grounds');ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');ax.grid(alpha=.15)
 fig.suptitle('Recovered precinct r04 plan: 33 unscaled buildings, 5 productive frames\nGray: existing landmarks; green: sealed gardens; gold: recovered access reservation',fontsize=12);fig.tight_layout();fig.savefig(HERE/'compound_overlay.png',dpi=120);plt.close(fig)
if __name__=='__main__':main()
