"""Readable source ownership / boundary continuity review, without a GUI."""
from . import geometry as g
from .design import HERE as SOURCE
from .allocate_backlands import OUT
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection,LineCollection
from matplotlib.patches import Patch
from collections import defaultdict

def run():
 t=g.load(OUT/'terrain_handoff.json');pack=g.load(OUT/'resolved_placements.json');b=g.load(OUT/'boundary_continuity.json');access=g.load(OUT/'access_handoff_final.json');m=g.load(SOURCE/'effective_city_manifest_r01.json');retired=set(m['replaced_placement_ids']);pr=g.load(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json')['instances'];native=[q for r in pr if r['id']not in retired for q in r['roof_parts_xz_m']];new=[]
 for d in m['districts']:
  pp=g.load(g.ROOT/d['pack']['path']);l=g.load(g.ROOT/pp['layout']['path']);new += [q for p in l['placements']for q in p['native_roof_polygons_xz_m']]
 colors={'shared_domestic_yard':'#d9bc89','productive_kitchen_and_fuel_garden':'#9dbb73','household_productive_service_ground':'#b7b987','shared_domestic_yard_and_allotment':'#b6c68d','craft_material_and_drying_ground':'#ce9d76','merchant_loading_and_storage_court':'#ba9bba'}
 funcs=sorted({o['planned_function']for o in t['material_owners']});fallback=['#d9bc89','#9dbb73','#b7b987','#b6c68d','#ce9d76','#ba9bba'];colors.update({k:colors.get(k,fallback[i%len(fallback)])for i,k in enumerate(funcs)})
 scene=g.load(g.R7);vs=scene['surfaces']['water'];wet=[[[v[0],v[2]]for v in vs[i:i+3]]for i in range(0,len(vs),3)];road=[[[v[0],v[2]]for v in scene['surfaces'].get('road',[])[i:i+3]]for i in range(0,len(scene['surfaces'].get('road',[])),3)];fig,axes=plt.subplots(1,3,figsize=(22,11),gridspec_kw={'width_ratios':[1.25,1,1]});views=[(-540,540,-540,660),(15,300,80,415),(180,470,60,300)];titles=['City: named functional ground ownership','B15: working and domestic backlands','B13: retained dense roofs and shared grounds']
 for ax,view,title in zip(axes,views,titles):
  ax.set_facecolor('#f2eee4');ax.add_collection(PolyCollection(wet,facecolor='#81b4cc',edgecolor='none',zorder=1));ax.add_collection(PolyCollection(road,facecolor='#d1c9b9',edgecolor='none',zorder=2))
  for fun in funcs:
   ps=[q for o in t['material_owners']if o['planned_function']==fun for q in o['finite_owner_polygons_xz_m']];ax.add_collection(PolyCollection(ps,facecolor=colors[fun],edgecolor='none',alpha=.85,zorder=3))
  ax.add_collection(PolyCollection(native,facecolor='#696b69',edgecolor='none',zorder=5));ax.add_collection(PolyCollection(new,facecolor='#795244',edgecolor='none',zorder=6));ax.add_collection(LineCollection([r['polyline_xz_m']for r in t['full_width_routes']],color='#f7f4e7',linewidth=.7,zorder=7));ax.add_collection(PolyCollection([q for p in pack['placements']if p['asset_key']!='district_r01_boundary_2m'for q in p['native_walking_obstacles_xz_m']],facecolor='#365543',edgecolor='none',zorder=8))
  for e in b['complete_gated_subyards']:
   q=e['polygon_xz_m'];ax.plot([x[0]for x in q+[q[0]]],[x[1]for x in q+[q[0]]],color='#146944',lw=1.7,zorder=10);c=g.np.mean(q,axis=0);ax.scatter(c[0],c[1],s=20,color='#146944',zorder=11)
  ax.set_xlim(view[:2]);ax.set_ylim(view[3],view[2]);ax.set_aspect('equal');ax.set_title(title,fontsize=13);ax.grid(color='#ffffff',alpha=.35,lw=.4);ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)')
 labels=[Patch(facecolor=colors[k],label=k.replace('_',' '))for k in funcs]+[Patch(facecolor='#696b69',label='Retained roofs'),Patch(facecolor='#795244',label='Selected new roofs'),Patch(facecolor='#146944',label='Complete gated subyard'),Patch(facecolor='#f7f4e7',edgecolor='#aaa',label='Reserved connected access')];fig.legend(handles=labels,loc='lower center',ncol=4,fontsize=10,bbox_to_anchor=(.5,.02));s=t['summary'];fig.suptitle(f"Backland source: {s['named_functional_holdings']} named holdings / {s['actual_R7_source_top_area_m2']:,.0f} m² existing ground planes\n{s['complete_gated_subyards']} complete gated subyards; outer enclosures held as whole systems; 0 fragment-perimeter rails active",fontsize=17,y=.98);fig.text(.5,.13,'Ground ownership colours do not claim fenced completion. Native support is source-tested; terrain routes, retained sides and final material composition remain R17/R18 acceptance gates.',ha='center',fontsize=10);fig.subplots_adjust(top=.89,bottom=.19,wspace=.17);fig.savefig(OUT/'ground_ownership_boundary_review.png',dpi=150);plt.close(fig);print(g.ref(OUT/'ground_ownership_boundary_review.png'))
if __name__=='__main__':run()
