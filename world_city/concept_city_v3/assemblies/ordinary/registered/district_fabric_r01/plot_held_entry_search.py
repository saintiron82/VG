from . import geometry as g
from .design import HERE as SOURCE
from .refit_held_private_entries import IDS,R17,R18
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection,LineCollection

def run():
 l=g.load(R17/'contour_bulk_r01/effective_source_layout_r03.json');p=g.load(g.CITY/'registered_source/plan.json');pr=g.load(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json');mf=g.load(SOURCE/'effective_city_manifest_r01.json');ret=set(mf['replaced_placement_ids']);pub=g.load(R18/'finite_field_candidate_r04_common.json')['records'];back=g.load(SOURCE/'backland_completion_r01/activation_subset_r01/resolved_placements.json');fig,axs=plt.subplots(4,3,figsize=(18,22));out=SOURCE/'held_private_entry_refit_r01'
 for ax,hid in zip(axs.ravel(),IDS):
  h=next(h for h in l['holdings']if h['id']==hid);hp=h['holding_polygon_xz_m'];cen=g.np.mean(hp,axis=0);bounds=g.rect(cen[0]-55,cen[1]-55,cen[0]+55,cen[1]+55)
  def nearby(polys):return[q for q in polys if g.geo.intersection_area(q,bounds)>1e-8]
  ax.add_collection(PolyCollection(nearby([q for r in p['spaces']+ [x for x in p['plots']if x['land_use']=='enclosed_noble_compound']for q in g.triangulate(r['polygon_xz_m'])]),facecolor='#dac6e2',alpha=.6))
  rr=[r for r in pub if g.geo.intersection_area(r['polygon_xz_m'],bounds)>1e-8];ys=[sum(g.np.array(r['polygon_xz_m']).mean(0)*g.np.array(r['plane_y_xz_m'][:2]))+r['plane_y_xz_m'][2]for r in rr];pc=PolyCollection([r['polygon_xz_m']for r in rr],cmap='terrain',array=g.np.array(ys),clim=(0,18));ax.add_collection(pc)
  ax.add_collection(PolyCollection(nearby([q for v in pr['instances']if v['id']not in ret for q in v['native_owner_parts_xz_m']]),facecolor='#7b7670',alpha=.7))
  ax.add_collection(PolyCollection(nearby([v['holding_polygon_xz_m']for v in l['holdings']if v['id']!=hid]),facecolor='#ddd',edgecolor='#aaa',alpha=.65))
  ax.add_collection(PolyCollection(nearby([q for v in l['placements']for q in v['native_roof_polygons_xz_m']]),facecolor='#9f6748',alpha=.85))
  ax.add_collection(PolyCollection(nearby([q for v in back['placements']for q in v['native_walking_obstacles_xz_m']]),facecolor='#4a854c'))
  ax.add_collection(PolyCollection([hp],facecolor='none',edgecolor='navy',linewidth=1.5));ax.add_collection(PolyCollection(h['core_court_polygons_xz_m'],facecolor='#edddaa',alpha=.65))
  ar=g.np.array(h['external_route']);ax.plot(ar[:,0],ar[:,1],color='red',ls='--',lw=1,label='old route');ax.plot(*h['gate_position_xz_m'],'ro',ms=4)
  source=out/(hid.replace(':','_')+'.json')
  if source.exists():
   row=g.load(source)
   for i,c in enumerate(row['candidates']):
    ar=g.np.array(c['polyline_xz_m']);ax.plot(ar[:,0],ar[:,1],lw=1.3,label=f"{i}: {c['source_average_rise_screen']:.1%}");ax.plot(*ar[-1],'o',ms=3)
  ax.set_xlim(cen[0]-55,cen[0]+55);ax.set_ylim(cen[1]+55,cen[1]-55);ax.set_aspect('equal');ax.set_title(f"{hid} court +{h['floor_y_m']:.2f}m / {h['external_width_m']}m wide",fontsize=10);ax.legend(fontsize=7,loc='upper right');ax.grid(alpha=.15)
 fig.suptitle('Held entries: existing native roofs, fixed courts and private-only route candidates\nPublic colors indicate actual sealed R18 height; purple areas are protected precinct/estate owners',fontsize=15);fig.tight_layout(rect=[0,0,1,.97]);fig.savefig(out/'entry_candidates_plan.png',dpi=130)
if __name__=='__main__':run()
