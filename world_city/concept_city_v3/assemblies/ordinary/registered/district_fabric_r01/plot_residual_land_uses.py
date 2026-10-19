"""Readable plan of all substantive residual ground assignments."""
from . import geometry as g
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch

def run():
 out=g.HERE/'backland_completion_r01/residual_land_use_r01';data=g.load(out/'source_plan.json');plan=g.load(g.CITY/'registered_source/plan.json');fig,axes=plt.subplots(4,4,figsize=(16,18));colors={'same_plane_functional_ground':'#91aa77','nonwalking_slope_regions':'#dcad66','retained_reservation_regions':'#a6b0ba','retained_native_clearance_regions':'#6b6966','existing_missing_top_regions_xz_m':'#bb6471'}
 for ax,r in zip(axes.flat,data['regions']):
  ps=r['source_domain_polygons_xz_m'];x=[v[0]for p in ps for v in p];z=[v[1]for p in ps for v in p];ax.add_collection(PolyCollection(ps,facecolor='#f5f1e7',edgecolor='none'))
  for k,c in colors.items():
   vv=r[k] if k=='existing_missing_top_regions_xz_m' else [p['polygon_xz_m']for p in r[k]]
   ax.add_collection(PolyCollection(vv,facecolor=c,edgecolor='none'))
  for road in plan['roads']:
   pp=road['polyline_xz_m'];ax.plot([p[0]for p in pp],[p[1]for p in pp],color='#6d6860',linewidth=.7,linestyle=':')
  ax.set_xlim(min(x)-5,max(x)+5);ax.set_ylim(max(z)+5,min(z)-5);ax.set_aspect('equal');ax.tick_params(labelsize=6);ax.grid(alpha=.12);ax.set_title(r['block_id']+' / '+r['id'].split(':')[-1]+' · '+str(round(r['source_area_m2']))+' m²\n'+r['named_function_owner'],fontsize=8)
 fig.suptitle('Final sixteen ordinary-land source assignments\nExisting planes retained; source reservations and physical exclusions remain explicit',fontsize=13)
 fig.legend(handles=[Patch(color=c,label=l)for c,l in [('#91aa77','Named functional ground'),('#dcad66','Measured >12% nonwalking slope'),('#a6b0ba','Prior owner/access reservation'),('#6b6966','Native clearance'),('#bb6471','Existing source hole/gap')]],loc='lower center',ncol=3,fontsize=9);fig.tight_layout(rect=[0,.04,1,.955]);path=out/'land_use_assignment_plan.png';fig.savefig(path,dpi=145);plt.close(fig);g.write(out/'plan_evidence.json',dict(source=g.ref(out/'source_plan.json'),image=g.ref(path),author=g.ref(__file__),note='This map visualizes source land-use ownership only; it is not an activated scene or a traversal proof.'));print(g.ref(path))
if __name__=='__main__':run()
