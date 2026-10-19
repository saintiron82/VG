#!/usr/bin/env python3
"""Draw constraint and placed-source geometry review, not an engine screenshot."""
import os,json
from pathlib import Path
from author import ROOT,HERE,FILES,box,g
os.environ['MPLCONFIGDIR']=str(HERE/'.mplcache');os.environ['XDG_CACHE_HOME']=str(HERE/'.cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PolyCollection

def main():
 d=json.loads((HERE/'candidate_overlay.json').read_text());records=json.loads((HERE/'source_constraints.json').read_text());block=d['first_infill_block']
 for kind,bounds in [('oldtown',[-440,75,-215,220]),('market',[-75,-65,85,55])]:
  fig,ax=plt.subplots(figsize=(15,10));ax.set_facecolor('#faf7ed')
  for r in sorted(records,key=lambda r:r['category'] not in ('original_plot_grounds','remaining_reserved_courtyards','explicit_property_grounds')):
   p=r['polygon'];bb=box(p)
   if bb[2]<bounds[0] or bb[0]>bounds[2] or bb[3]<bounds[1] or bb[1]>bounds[3]:continue
   color={'building_envelopes':'#9c8875','public_road_ribbons':'#d5ac77','compiled_road_surfaces':'#d5ac77','original_plot_grounds':'#e7deca','remaining_reserved_courtyards':'#ddd4ba','fabric_envelopes':'#8f9c70','market_square':'#ede5d0','access_reservations':'#c6aab8'}.get(r['category'],'#dddfcf')
   ax.add_patch(Polygon(p,facecolor=color,edgecolor='none',alpha=.65))
  if kind=='oldtown':
   for zone in block['zones']:ax.add_patch(Polygon(zone['polygon_xz_m'],facecolor='#a7c493' if zone['material']=='grass' else '#cebca4',edgecolor='#46594b',lw=1))
   for path in block['paths']:
    for p in path['ribbon_polygons_xz_m']:ax.add_patch(Polygon(p,facecolor='#77b5c6',edgecolor='none',alpha=.9))
   for b in block['building_instances']:
    color={'clay_red':'#b76649','wood_brown':'#76553c','slate_gray':'#65757b'}[b['roof_material_family']]
    ax.add_patch(Polygon(b['source_footprint_xz_m'],facecolor=color,edgecolor='#332b28',lw=.8))
    x,y,z=b['position_m'];spec=json.loads((ROOT/FILES['scene']).read_text())['asset_specs'][b['asset_key']]
    ax.text(x,z,str(spec['floors'])+'F',ha='center',va='center',fontsize=7,color='white')
    for e in b['all_entrances_world_m']:ax.plot(e[0],e[2],'o',ms=2.5,color='#fff8ad')
   facilities=block['facility_placements']
   title='Old-town block: 23 actual cached house placements, 32 doors, 2 public gateways'
   subtitle='Blue: reserved 1.8–2.4 m paths | roofs: actual unchanged footprints | original plots retained'
  else:
   colors=['#e5cf9c','#b7c98f','#dcb193','#c5a789','#dfd3ad']
   for zone,col in zip(d['market_program']['zones'],colors):
    for p in zone['polygons_xz_m']:ax.add_patch(Polygon(p,facecolor=col,edgecolor='none',alpha=.55))
   facilities=d['market_program']['facility_placements']
   for a in d['market_program']['trade_aisles']:
    for p,q in zip(a['polyline_xz_m'],a['polyline_xz_m'][1:]):ax.add_patch(Polygon(g.road_ribbon(p,q,a['width_m']),facecolor='#77b5c6',edgecolor='none',alpha=.8))
   title='Market: 28 additional cached stalls in organized grain/produce clusters'
   subtitle='Five functional zones; exact source roads, existing stalls, fountain and civic circulation kept clear'
  for f in facilities:ax.add_patch(Polygon(f['footprint_xz_m'],facecolor='#536b3a' if f['category']=='garden_bed' else '#5a4638',edgecolor='white',lw=.4))
  ax.set_xlim(bounds[0],bounds[2]);ax.set_ylim(bounds[3],bounds[1]);ax.set_aspect('equal');ax.grid(alpha=.15)
  ax.set_title(title+'\n'+subtitle,fontsize=12);ax.set_xlabel('X metres');ax.set_ylabel('Z metres, north up')
  fig.savefig(HERE/(kind+'_candidate_plan.png'),dpi=140,bbox_inches='tight');plt.close(fig)
 fig,ax=plt.subplots(figsize=(14,11));palette={'D01':'#8e7770','D02':'#a7a1bf','D03':'#d9b564','D04':'#c5a074','D05':'#b9b3a1','D06':'#b8917b','D07':'#c8947f','D08':'#a4bb7d','D09':'#b8b581','D10':'#a2bbaa'}
 for patch in d['patches']:ax.add_collection(PolyCollection(patch['polygons_xz_m'],facecolors=palette[patch['district_id']],edgecolors='none',alpha=.9))
 for r in records:
  if r['category'] in ('building_envelopes','public_road_ribbons','wall_envelopes'):ax.add_patch(Polygon(r['polygon'],facecolor={'building_envelopes':'#5e5248','public_road_ribbons':'#e0d3ba','wall_envelopes':'#74736c'}[r['category']],edgecolor='none',alpha=.9))
 for region in d['residual_region_access']['regions']:
  if region['path']:
   points=region['path']['polyline_xz_m'];ax.plot([p[0] for p in points],[p[1] for p in points],color='#2c89a0',lw=.5)
 for b in block['building_instances']:ax.add_patch(Polygon(b['source_footprint_xz_m'],facecolor='#bd492e',edgecolor='none'))
 ax.set_xlim(-660,660);ax.set_ylim(465,-560);ax.set_aspect('equal');ax.set_title('Exact residual land-use assignment and connected service paths\n504,678 m² allocated in 221 named patches; allocation is not rendered completion',fontsize=12)
 ax.set_xlabel('X metres');ax.set_ylabel('Z metres, north up');fig.savefig(HERE/'wholecity_candidate_plan.png',dpi=140,bbox_inches='tight');plt.close(fig)
 print('Wrote three source-layout review drawings; no engine render claimed.')
if __name__=='__main__':main()
