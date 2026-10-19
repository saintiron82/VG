import json,math,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mpl-market');os.environ.setdefault('XDG_CACHE_HOME','/tmp/market-cache')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
H=Path(__file__).resolve().parent;M=H.parents[1]/'r9/market_clusters';O=H/'candidate_r01'
def load(p):return json.loads(p.read_bytes())
def main():
 c=load(M/'source_context.json');market=load(M/'pack.json');layout=load(M/'layout.json');owner=load(O/'geometry_ownership.json');z=owner['geometry'];routes=load(O/'routes.json')['routes'];fig,axes=plt.subplots(1,2,figsize=(15,7),gridspec_kw={'width_ratios':[1,1.35]})
 for ax in axes:
  ax.set_facecolor('#eee6d1')
  for road in c['roads']:
   if road['id'].startswith('MARKET'):
    a=road['polyline_xz_m'];ax.plot(*zip(*a),color='#d2c6a2',lw=road['width_m']*2,zorder=1,solid_capstyle='round');ax.plot(*zip(*a),color='#b69b69',lw=.8,zorder=2)
  for s in c['solids']:
   if s['y_max']>4.1:ax.add_patch(Polygon(s['polygon'],fc='#928779',ec='#6b6256',lw=.5))
  for p in market['add_instances']:ax.add_patch(Polygon(p['footprint_xz_m'],fc={'grain':'#bd9c62','produce':'#71926b','textile':'#b36456'}[p['trade_family']],ec='#4d5645',lw=.6))
  for r in layout['routes']:
   a=r['path_xz_m'];ax.plot(*zip(*a),color='#6c9ca1'if r['route_type']=='customer'else'#a188b4',lw=.7,alpha=.6,zorder=2)
  fountain=c['fountain']['position_m'];ax.add_patch(plt.Circle((fountain[0],fountain[2]),10,fc='#dbc28c',alpha=.5,zorder=1))
  ax.add_patch(Polygon(z['pad'],fc='#bdc1bc',ec='#4c6055',lw=1.8,zorder=4));ax.add_patch(Polygon(z['lane'],fc='#dadecf',ec='none',zorder=5))
  pts=routes[0]['points'];ax.plot([p[0]for p in pts],[p[2]for p in pts],color='#18606c',lw=2,zorder=6)
  hp=routes[2]['points'];ax.plot([p[0]for p in hp],[p[2]for p in hp],color='#5b7a36',lw=2,ls='--',zorder=6)
  ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)')
 axes[0].set_xlim(60,145);axes[0].set_ylim(45,-16);axes[0].set_title('Existing market access preserved')
 axes[0].text(101,24,'Fountain\n10 m reserve',ha='center',fontsize=8);axes[0].plot(99.289901,34.853597,'s',color='#2e84a0',ms=5);axes[0].text(101.5,35.5,'Low-head water\nunchanged',fontsize=8)
 ax=axes[1];ax.set_xlim(91,126);ax.set_ylim(13,-12);ax.set_title('One-cart hardstand and forward return circuit')
 a=z['A'];b=z['B'];t=[7/math.sqrt(58),3/math.sqrt(58)];n=[t[1],-t[0]];mid=z['mid'];fixture=[[mid[k]+f*t[k]+l*n[k]for k in(0,1)]for l,f in [(-.9,-1.6),(.9,-1.6),(.9,1.6),(-.9,1.6)]];ax.add_patch(Polygon(fixture,fc='#936d43',ec='#53432b',zorder=7))
 ax.annotate('7.62 m × 4 m lane\n+ 1.5 m unloading apron',xy=(106.3,3.8),xytext=(98,9.9),fontsize=9,arrowprops={'arrowstyle':'-','color':'#364d39'})
 ax.annotate('Entry: Y4.000',xy=z['P'],xytext=(92,7.5),fontsize=8,arrowprops={'arrowstyle':'->','color':'#174b58'})
 ax.annotate('Exit: Y3.973\nto existing east road',xy=z['E'],xytext=(117.2,-7.5),fontsize=8,arrowprops={'arrowstyle':'->','color':'#174b58'})
 ax.text(116.3,1.8,'R3.882 m\noff-road turn',fontsize=8,color='#174b58')
 ax.text(97.5,-9.8,'Return uses the existing junction',fontsize=8,color='#174b58')
 ax.annotate('Hand-carry link\nto retained rear service path',xy=(112,6.9),xytext=(114,10.5),fontsize=8,arrowprops={'arrowstyle':'->','color':'#5b7a36'})
 for idx in [21,56,104,159,218]:
  p,q=pts[idx],pts[idx+3];ax.annotate('',xy=(q[0],q[2]),xytext=(p[0],p[2]),arrowprops=dict(arrowstyle='->',color='#174b58',lw=2),zorder=9)
 fig.suptitle('Market delivery bay · source-bound static plan, runtime/render review pending',fontsize=14)
 fig.text(.5,.02,'Brown rectangle: 1.8 × 3.2 m test envelope, not a spawned cart. One cart unloads or briefly waits; no second-cart queue. All ground heights and 66 stalls are retained.',ha='center',fontsize=9)
 fig.tight_layout(rect=[0,.10,1,.94]);fig.savefig(H/'plan_r01.png',dpi=150);plt.close(fig)
if __name__=='__main__':main()
