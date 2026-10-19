"""Readable eight-holding physical-owner plan, without new visual assets."""
from . import geometry as g
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/riverstone-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
def run():
 p=g.HERE/'final_source_preparation_r01/native_owner_replacements.json';data=g.load(p);fig,axes=plt.subplots(2,4,figsize=(18,11));fig.suptitle('Final eight native/core refits\nFlat native/court support, separate graded entries, and retained source-plane margins',fontsize=15)
 for ax,r in zip(axes.flat,data['records']):
  h=r['replacement_holding'];floor=h['floor_y_m'];hp=h['holding_polygon_xz_m'];cand=next(x for x in g.load(g.ROOT/r['selected_candidate']['path'])['records']if x['holding_id']==r['holding_id'])
  for ps,col,alpha in [(h['surface_following_margin_polygons_xz_m'],'#d7d9cb',1),(h['flat_owner_polygons_xz_m'],'#b3c6cf',1),(h['profile_domain_polygons_xz_m'],'#d4a157',.9),([q for pp in r['replacement_native_placements']for q in pp['native_roof_polygons_xz_m']],'#656455',1)]:
   ax.add_collection(PolyCollection(ps,facecolors=col,edgecolors='none',alpha=alpha))
  ax.plot([q[0]for q in hp+[hp[0]]],[q[1]for q in hp+[hp[0]]],color='#5d665e',lw=.9)
  for d in r['replacement_actual_doors']:
   q=d['actual_door_xyz_m'];v=d['outward_xz'];ax.plot(q[0],q[2],'.',color='#a33c34',markersize=3);ax.arrow(q[0],q[2],v[0]*1.5,v[1]*1.5,color='#a33c34',head_width=.45,length_includes_head=True)
  xs=[q[0]for q in hp];zs=[q[1]for q in hp];ax.set_xlim(min(xs)-6,max(xs)+6);ax.set_ylim(max(zs)+6,min(zs)-6);ax.set_aspect('equal');ax.grid(alpha=.13);ax.tick_params(labelsize=7);ax.set_title(f"{r['holding_id']} | +{floor:.3f} m\n{h['native_roof_area_m2']:.1f} m² roof; {len(r['replacement_actual_doors'])} doors; outer enclosure held",fontsize=10)
 fig.legend(handles=[Patch(color='#656455',label='Existing native cache roofs'),Patch(color='#b3c6cf',label='Exact flat feet/court/door supports'),Patch(color='#d4a157',label='Graded pedestrian entry'),Patch(color='#d7d9cb',label='Source-plane margin'),Patch(color='#a33c34',label='Actual exterior door and outward direction')],loc='lower center',ncol=3,fontsize=10);fig.subplots_adjust(left=.055,right=.985,bottom=.12,top=.855,wspace=.22,hspace=.38);out=p.parent/'native_core_partition_plan_r02.png';fig.savefig(out,dpi=150);plt.close(fig);g.write(p.parent/'plan_evidence_r02.json',dict(source=g.ref(p),image=g.ref(out),author=g.ref(__file__),scope='Source geometry review only. The selected finite terrain profiles, datum changes and final scene remain separate release gates.'));print(g.ref(out))
if __name__=='__main__':run()
