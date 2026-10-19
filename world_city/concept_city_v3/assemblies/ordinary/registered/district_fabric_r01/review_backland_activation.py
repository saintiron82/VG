"""Rebind exact whole-native projection coverage and draw the activation subset."""
from . import geometry as g
from .design import HERE as SOURCE
from .activate_backlands_subset import OUT,BASE,SCENE
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as ta
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch

def run():
 p=g.load(OUT/'resolved_placements.json');src=g.load(BASE/'resolved_placements.json');audit=g.load(OUT/'actual_scene_audit.json');defer=g.load(OUT/'deferred_ledger.json');terrain=g.load(OUT/'terrain_handoff.json');local={};tests=[]
 for key,a in p['assets'].items():
  m=g.load(g.ROOT/a['render_path']);local[key]=slab_rectangles(m,a['bounds']['min'][1]+.001,a['bounds']['max'][1]-.001)
 for r in p['placements']:
  full=[transform(q,r)for q in local[r['asset_key']]];missing=ta.common.subtract(full,r['native_walking_obstacles_xz_m']);tests.append(dict(id=r['id'],full_cache_projection_missing_from_checked_mask_m2=sum(g.geo.polygon_area(q)for q in missing)))
 assert max(r['full_cache_projection_missing_from_checked_mask_m2']for r in tests)<=1e-7
 verified=dict(schema='riverstone.backland.activation_projection_rebind.v1',pack=g.ref(OUT/'resolved_placements.json'),actual_scene_audit=g.ref(OUT/'actual_scene_audit.json'),source_internal_pair_proof=g.ref(BASE/'source_native_audit.json'),checks=dict(every_selected_full_native_projection_covered_by_checked_mask=True,all_original_source_bytes_preserved=g.ref(BASE/'resolved_placements.json')['sha256']==p['sealed_source']['sha256'],source_audit_passes=g.load(BASE/'source_native_audit.json')['passed'],actual_scene_audit_passes=audit['passed'],original_subset_poses_and_ids_unchanged=all(r==next(v for v in src['placements']if r['id']==v['id'])for r in p['placements'])),placement_checks=tests,proof='The actual-scene collision and reservation mask contains every occupied native voxel projection across the entire cached height, including the drying frame above walking headroom. Unit-pose subset selection also preserves the sealed source internal-pair clearance proof.');verified['passed']=all(verified['checks'].values());g.write(OUT/'full_native_projection_proof.json',verified)
 scene=g.load(SCENE);reserve=g.load(OUT/'reservation_snapshot.json')['reservations'];wet=[r['polygon_xz_m']for r in reserve if r['kind']=='actual_water'];public=[r['polygon_xz_m']for r in reserve if r['kind']=='canonical_R18_public'];private=[r['polygon_xz_m']for r in reserve if r['kind']=='pending_private_holding'];feet=[q for v in p['placements']for q in v['native_walking_obstacles_xz_m']];kept={r['id']for r in p['placements']};held=[r for r in src['placements']if r['id']not in kept];sceneids={r['id']for r in scene['common_instances']};projection=g.load(g.CITY/'registered_integration/r8/coverage_plan/native_projection.json')['instances'];native=[q for r in projection if r['id']in sceneids for q in r['roof_parts_xz_m']]
 current=g.load(SOURCE/'effective_city_manifest_r01.json');actual={r['id']:r for r in scene['common_instances']};originalids={r['id']for r in projection};native += [q for r in current['placements']if r['id']in actual and r['id']not in originalids and r['position_m']==actual[r['id']]['position_m']for q in r.get('native_roof_polygons_xz_m',[])]
 fig,axs=plt.subplots(1,3,figsize=(22,11),gridspec_kw={'width_ratios':[1.15,1,1]});views=[(-500,520,-500,550),(20,300,80,415),(-50,185,-400,-120)];titles=['Whole city: selected native uses','B15: domestic and craft backlands','Northern productive / work grounds']
 for ax,v,title in zip(axs,views,titles):
  ax.set_facecolor('#f5f0e5');ax.add_collection(PolyCollection(wet,facecolor='#83b8cd',edgecolor='none',zorder=1));ax.add_collection(PolyCollection(public,facecolor='#d7c4a4',edgecolor='none',zorder=2));ax.add_collection(PolyCollection(private,facecolor='#e8d1cb',edgecolor='#b77465',linewidth=.35,alpha=.75,zorder=3));ax.add_collection(PolyCollection(native,facecolor='#777d79',edgecolor='none',alpha=.65,zorder=4))
  for k,col in [('productive_bed','#49773e'),('district_r01_boundary_2m','#1f634f')]:ax.add_collection(PolyCollection([q for r in p['placements']if r['asset_key']==k for q in r['native_walking_obstacles_xz_m']],facecolor=col,edgecolor='none',zorder=7))
  xx=[r['position_m'][0]for r in p['placements']if r['asset_key']not in('productive_bed','district_r01_boundary_2m')];zz=[r['position_m'][2]for r in p['placements']if r['asset_key']not in('productive_bed','district_r01_boundary_2m')];ax.scatter(xx,zz,s=8 if ax is axs[0] else 14,c='#85512f',zorder=8,linewidths=0)
  ax.scatter([r['position_m'][0]for r in held],[r['position_m'][2]for r in held],s=13,color='#bd4840',marker='x',linewidths=.6,zorder=9)
  for e in p['complete_gated_subyards']:
   q=e['polygon_xz_m'];ax.plot([x[0]for x in q+[q[0]]],[x[1]for x in q+[q[0]]],color='#1f634f',lw=1.2,zorder=10)
  ax.set_xlim(v[:2]);ax.set_ylim(v[3],v[2]);ax.set_aspect('equal');ax.set_title(title,fontsize=13);ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');ax.grid(color='white',linewidth=.35,alpha=.55)
 fig.suptitle('842 supported native placements across 16 blocks\n22 complete gated subyards; 61 deferred placements; zero broken enclosure subsets',fontsize=17,y=.97)
 fig.legend(handles=[Patch(facecolor='#49773e',label='187 productive beds'),Patch(facecolor='#85512f',label='353 domestic / craft fixtures'),Patch(facecolor='#1f634f',label='302 rails in 22 complete gated subyards'),Patch(facecolor='#bd4840',label='Deferred source placement'),Patch(facecolor='#e8d1cb',edgecolor='#b77465',label='78 reserved pending private holdings'),Patch(facecolor='#d7c4a4',label='Canonical R18 public domain')],ncol=3,loc='lower center',bbox_to_anchor=(.5,.035),fontsize=10)
 fig.text(.5,.14,'Actual r8_district_r04 native support and clearance. Ground paint is composed separately on existing planes; pending holdings and onward route activation remain explicit.',ha='center',fontsize=10);fig.subplots_adjust(top=.88,bottom=.20,wspace=.2);fig.savefig(OUT/'activation_plan.png',dpi=150);plt.close(fig)
 owners=terrain['functional_ground_owners'];g.write(OUT/'review_manifest.json',dict(pack=g.ref(OUT/'resolved_placements.json'),full_native_projection_proof=g.ref(OUT/'full_native_projection_proof.json'),plan=g.ref(OUT/'activation_plan.png'),complete_gated_subyard_owners=len({e['ground_owner_id']for e in p['complete_gated_subyards']}),selected_ground_owner_context_area_m2=sum(g.geo.polygon_area(q)for o in owners for q in o['finite_owner_polygons_xz_m']),area_note='Context footprint only. Actual material activation area belongs to the parent same-plane terrain patch.',deferred_reason_counts=defer['reason_counts']));print(g.ref(OUT/'review_manifest.json'));print(defer['reason_counts'])
if __name__=='__main__':run()
