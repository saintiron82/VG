from ..design import *
import numpy as np
from world_city.runtime_city.checks import placement as geo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
DEST=HERE/'court_phase01'
cs=load(HERE/'court_plan.json')['courts'];a=load(HERE/'access_handoff.json');fig,axes=plt.subplots(1,2,figsize=(14,7))
for c,ax in zip(cs,axes):
 center=[sum(p[k]for p in c['polygon_xz_m'])/4 for k in(0,1)];yaw=math.radians(-48)
 def inv(p):return xform([p[0]-center[0],p[1]-center[1]],[0,0],-yaw)
 local=[inv(p)for p in c['polygon_xz_m']];ax.add_patch(Polygon(local,fc='#e6d6b4',ec='black'))
 routes=[r for r in a['internal_routes']+a['external_routes'] if r['holding_id']==c['holding_id']]+[c['access_link']]
 for r in routes:
  for poly in r['ribbon_and_join_polygons_xz_m']:
   if geo.intersection_area(poly,c['polygon_xz_m'])>1e-8:ax.add_patch(Polygon([inv(p)for p in poly],fc='#87babc',alpha=.5,ec='none'))
 ax.set_xlim(min(p[0]for p in local)-.5,max(p[0]for p in local)+.5);ax.set_ylim(min(p[1]for p in local)-.5,max(p[1]for p in local)+.5);ax.set_aspect('equal');ax.grid(alpha=.3);ax.set_title(c['id']);ax.set_xlabel('court local X / m');ax.set_ylabel('court local Z / m')
fig.savefig(DEST/'space_inspection.png',dpi=130,bbox_inches='tight')
