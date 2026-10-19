"""Source-native roof and court plan, with retained owners and terrain caveats."""
from . import geometry as g
from .design import HERE as SOURCE
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/district-fabric-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch

def run():
 layouts=[g.load(p)for p in sorted((SOURCE/'coherent_regrade_r01').glob('BLOCK_*/selected_layout.json'))if p.parent.name!='BLOCK_018'];proj=g.load(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json')['instances'];blocks=g.load(g.CITY/'registered_integration/r8/coverage_plan/baseline_blocks.json')['blocks'];plan=g.load(g.CITY/'registered_source/plan.json');retired={i for l in layouts for i in l['retired_source_ids']};pal={'clay_red':'#a96548','wood_brown':'#8a724d','slate_gray':'#637985'}
 def layers(ax,after=True):
  ax.add_collection(PolyCollection([b['polygon_xz_m']for b in blocks],facecolors='#d9d7bd',edgecolors='#b4b6a5',linewidths=.3))
  for r in plan['roads']:ax.add_collection(PolyCollection([g.geo.road_ribbon(a,b,r['width_m'])for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])],facecolors='#a4a6a0',edgecolors='none'))
  old=[q for i in proj if not after or i['id']not in retired for q in i['roof_parts_xz_m']];ax.add_collection(PolyCollection(old,facecolors='#79766a',edgecolors='#555a54',linewidths=.12))
  if after:
   for l in layouts:
    ax.add_collection(PolyCollection([h['holding_polygon_xz_m']for h in l['holdings']],facecolors='#d6c49b',edgecolors='#8b8b73',linewidths=.25,alpha=.8))
    ax.add_collection(PolyCollection([q for h in l['holdings']for q in h['core_court_polygons_xz_m']],facecolors='#eddbac',edgecolors='none'))
    routes=[q for h in l['holdings']for q in h['external_route_polygons_xz_m']]+[q for r in l['shared_private_routes']for q in r['polygons_xz_m']];ax.add_collection(PolyCollection(routes,facecolors='#92acac',edgecolors='none'))
    for p in l['placements']:ax.add_collection(PolyCollection(p['native_roof_polygons_xz_m'],facecolors=pal[p['palette_id']],edgecolors='#514d3f',linewidths=.22))
  ax.set_aspect('equal');ax.set_xlim(-530,530);ax.set_ylim(635,-520);ax.set_xticks([]);ax.set_yticks([]);ax.set_facecolor('#f2efdf')
 fig,axes=plt.subplots(1,2,figsize=(17,11));layers(axes[0],False);layers(axes[1]);axes[0].set_title('R7 native roofscape',loc='left');axes[1].set_title('Coherent native district source | terrain acceptance pending',loc='left');fig.suptitle('Riverstone | whole-city ordinary frontage and court source',x=.125,ha='left',fontsize=18);fig.text(.125,.02,'All roofs are native cache projections at unit scale. B18 replacement held for roof regression. B07 higher terraces await grade budgets.',fontsize=9);fig.savefig(SOURCE/'coherent_regrade_r01/city_native_plan.png',dpi=170,bbox_inches='tight');plt.close(fig)
 fig,ax=plt.subplots(figsize=(13,11));layers(ax);ax.set_xlim(65,395);ax.set_ylim(400,100);ax.set_title('BLOCK 015 | 26 connected holdings, 32 native ranges',loc='left',fontsize=18);ax.set_xticks(range(75,400,50));ax.set_yticks(range(100,401,50));ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');ax.legend(handles=[Patch(fc='#79766a',label='Retained R7 native'),Patch(fc='#a96548',label='Red-clay roofs'),Patch(fc='#8a724d',label='Brown timber roofs'),Patch(fc='#637985',label='Gray slate roofs'),Patch(fc='#eddbac',label='Working / domestic courts'),Patch(fc='#92acac',label='Full-width private routes')],loc='upper left',fontsize=8);fig.text(.125,.02,'8,592 m² new roofs | +3,546.5 m² net ordinary roof gain | 117 native exterior entrances\nResulting ordinary roof: 33.1% effective ordinary domain, 23.7% legacy domain. Finite coherent grading remains proposed.',fontsize=10);fig.savefig(SOURCE/'coherent_regrade_r01/block_015_native_plan.png',dpi=180,bbox_inches='tight');plt.close(fig)
if __name__=='__main__':run()
