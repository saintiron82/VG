"""Source-data diagnostic, not a game screenshot or compiled-geometry claim."""
import json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from .author import HERE,PLAN,Axis,cambered_height_at
from world_city.concept_city_v3.registered_topography import author as terrain

def draw():
 p=json.loads((HERE/'candidate.json').read_text());plan=json.loads(PLAN.read_text());road=next(r for r in plan['roads'] if r['id']=='MAIN_BRIDGE');axis=Axis(road)
 fig,(ax,profile)=plt.subplots(1,2,figsize=(15,8),gridspec_kw={'width_ratios':[1,2]});fig.patch.set_facecolor('#f3f0e8')
 for w in terrain.finite_water_polygons():
  if w['surface_id']=='MAIN_RIVER':ax.add_patch(Polygon(w['polygon_xz_m'],facecolor='#b8d5df',edgecolor='#88b4c2',lw=.6))
 for poly in p['navigation_channel']['proposed_water_approach_polygons_xz_m']:ax.add_patch(Polygon(poly,facecolor='#2d8aa6',alpha=.3,edgecolor='#15546f',lw=1))
 for r in p['approach_regions']:ax.add_patch(Polygon(r['polygon_xz_m'],facecolor='#cab88f',edgecolor='none'))
 for b in p['bays']:
  ax.add_patch(Polygon(b['footprint_xz_m'],facecolor='#bdae8c',edgecolor='#6f6759',lw=.6))
  ax.add_patch(Polygon(b['cart_lane_polygon_xz_m'],facecolor='#e2d4b8',edgecolor='none'))
  for foot in b['footings']:ax.add_patch(Polygon(foot['polygon_xz_m'],facecolor='#726b5f',edgecolor='none'))
 for a in p['abutments']:ax.add_patch(Polygon(a['polygon_xz_m'],facecolor='#544a3c',edgecolor='black',lw=.8))
 xy=road['polyline_xz_m'];ax.plot([a[0] for a in xy],[a[1] for a in xy],'--',color='#b35c46',lw=1,label='original registered axis')
 gate=next(g for g in plan['gates'] if g['road_id']=='MAIN_BRIDGE');ax.scatter(*gate['position_xz_m'],s=35,color='#8c4b36',zorder=10);ax.annotate('existing gate\n7 m approach',gate['position_xz_m'],xytext=(147,401),arrowprops={'arrowstyle':'-','color':'#6d6356'},fontsize=9)
 ax.set_xlim(60,195);ax.set_ylim(585,380);ax.set_aspect('equal');ax.set_title('Finite deck and navigation ownership');ax.set_xlabel('world X (m)');ax.set_ylabel('world Z (m)');ax.grid(alpha=.2)
 ss=[axis.length*i/700 for i in range(701)];old=[];new=[];water=[]
 for s in ss:
  x,z=axis.at(s);old.append(terrain.road_height_at('MAIN_BRIDGE',x,z));new.append(cambered_height_at(x,z,axis,p['camber_overlay']));water.append(terrain.river_water_y(x))
 profile.fill_between(ss,[v-3 for v in water],[-7]*len(ss),color='#a79a80',alpha=.7);profile.fill_between(ss,water,[v-3 for v in water],color='#b8d5df',alpha=.7)
 profile.plot(ss,water,color='#24758e',lw=1,label='normal river head');profile.plot(ss,[v-3 for v in water],color='#655d50',lw=1,label='river bed')
 for b in p['bays']:
  lo,hi=b['source_station_range_m'];base=b['arch_top_y_m'];xx=[-7,-6,-4,-2,0,2,4,6,7];yy=[-3,-2.3,-1.3,-.8,-.65,-.8,-1.3,-2.3,-3]
  sx=[(lo+hi)/2+x for x in xx];profile.plot(sx,[base+y for y in yy],color='#776b56',lw=2)
  for foot in b['footings']:
   x=(lo+.5) if foot['end_sign']<0 else (hi-.5);profile.add_patch(Polygon([[x-.5,foot['foundation_y_m']],[x+.5,foot['foundation_y_m']],[x+.5,base],[x-.5,base]],facecolor='#8c806b',edgecolor='none'))
 profile.plot(ss,old,'--',color='#b2644d',lw=1.4,label='preserved low-field deck');profile.plot(ss,new,color='#2a473b',lw=2.3,label='explicit cambered deck')
 b=p['bays'][4];center=sum(b['source_station_range_m'])/2;profile.axvspan(center-3,center+3,color='#80a799',alpha=.25)
 profile.annotate('Central 6 m opening\n≥3.43 m normal-stage clearance',(center,1),xytext=(112,5.0),arrowprops={'arrowstyle':'->','color':'#2a473b'},fontsize=10,color='#2a473b')
 profile.set_xlim(0,axis.length);profile.set_ylim(-6,6.2);profile.set_xlabel('station along registered crossing (m)');profile.set_ylabel('world Y (m)');profile.set_title('Deck camber, open arches and explicit bed-reaching piers');profile.grid(alpha=.2);profile.legend(loc='lower right',fontsize=8)
 fig.suptitle('Registered bridge source candidate • 14 m exterior / 8 m cart / 2.4 m walks / 0.6 m parapets',fontsize=14)
 fig.text(.5,.025,'Source-data diagram only. No compile or collision certificate. Original bank/gate endpoints preserved; maximum image shift 4.08 px.',ha='center',fontsize=10,color='#615a4e')
 fig.tight_layout(rect=[0,.04,1,.95]);fig.savefig(HERE/'candidate_overview.png',dpi=150);plt.close(fig)
if __name__=='__main__':draw()
