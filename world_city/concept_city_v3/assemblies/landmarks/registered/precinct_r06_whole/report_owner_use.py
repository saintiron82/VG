"""Explicit owner ledger and human-readable source plan (not a game view)."""
from build_ledger import *

def main():
 pack=load(HERE/'resolved_placements.json');ledger=load(HERE/'actual_owner_use_ledger.json');projection=load(HERE/'actual_native_projection.json');m=np.load(HERE/'owner_masks.npz');new=b.mask([u['polygon_xz_m']for u in pack['holdings']]);rows=[];propertypath=CITY/'assemblies/property/registered/r1/resolved_placements.json';property=load(propertypath);trainingpath=CITY/'assemblies/landscape/registered/training/resolved_placements.json';training=load(trainingpath)
 for oi,o in enumerate(ledger['owners'],1):
  units=[u for u in pack['holdings']if u['owner_id']==o['owner_id']];nr=next((r for r in property['ownership_masks']if r.get('property_id')==o['owner_id']),None);existingfunctions=[]
  if nr:
   for p in property['placements']:
    if p.get('property_id')==o['owner_id'] and p['id']in {v['id']for v in projection['instances']}:existingfunctions.append({'instance_id':p['id'],'role':p.get('role'),'source':ref(propertypath)})
  if o['owner_id']=='SITE_TRAIN':existingfunctions=[{'instance_id':p['id'],'role':p.get('semantic_function',p.get('role')),'source':ref(trainingpath)}for p in training['placements']if p['id']in {v['id']for v in projection['instances']}]
  remaining=b.mask(o['remaining_parts_xz_m'])&~new;labels,n=ndimage.label(remaining);components=[]
  for label in range(1,n+1):
   part=labels==label
   if part.sum()>=25:components.append({'id':o['owner_id']+':remaining:'+str(label),'grid_area_m2':b.area(part),'polygon_parts_xz_m':b.parts(part),'status':'EXPLICIT_UNASSIGNED_OR_UNVERIFIED_FUNCTION_GAP'})
  rows.append({'owner_id':o['owner_id'],'exclusive_whole_owner_grid_m2':o['exclusive_whole_owner_grid_m2'],'baseline_partition':o['categories_disjoint_grid_m2'],'new_resolved_ground_units':[u['id']for u in units],'new_resolved_ground_exact_area_m2':sum(u['area_m2']for u in units),'new_actual_scene_applied_area_m2':0,'new_facilities':dict(sum((collections.Counter(u['facility_counts'])for u in units),collections.Counter())),'remaining_after_native_candidate_grid_m2':b.area(remaining),'remaining_components_over25m2':components,'actual_existing_functional_components':existingfunctions,'existing_internal_routes':[r['id']for r in property.get('internal_routes',[])if r.get('property_id')==o['owner_id']],'named_existing_open_ground':training['central_exercise_reservation']if o['owner_id']=='SITE_TRAIN'else None,'whole_owner_complete':False,'reason':'Current native floor/roof projection and named facilities are recorded separately; no entire source polygon is automatically accepted. New pack is resolved but not yet in actual scene; all unassigned and external-access gaps stay explicit.'})
 summary={'owners':len(rows),'new_resolved_holdings':len(pack['holdings']),'new_resolved_domain_area_m2':sum(x['new_resolved_ground_exact_area_m2']for x in rows),'new_native_placements':len(pack['placements']),'automatically_completed_owner_count':0,'source_only_large_remaining_components':sum(len(r['remaining_components_over25m2'])for r in rows)}
 write('owner_completion_ledger.json',{'schema':'riverstone.precinct.r06.explicit_owner_completion.v1','sources':{'baseline':ref(HERE/'actual_owner_use_ledger.json'),'native_pack':ref(HERE/'resolved_placements.json')},'owners':rows,'summary':summary,'scope':'Native ground completion batch and explicit entire protected-owner ledger. This does not claim whole-city completion.'})
 import os;os.environ.setdefault('MPLCONFIGDIR','/tmp/r06-mpl');import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.patches import Polygon
 fig,axes=plt.subplots(1,3,figsize=(19,11),layout='constrained');views=[('Castle / training / common',(-440,-420,-120,-20)),('Abbey productive grounds',(-440,-60,-100,310)),('Clergy precinct', (80,-390,390,-60))];colors={'kitchen_beds':'#b59b50','medicinal_nursery':'#859b53','fuel_workyard':'#aa7655','orchard':'#5d8c53','stable_service':'#bd9e78','common_maintenance':'#87a2a1'}
 for ax,(title,win)in zip(axes,views):
  for o in ledger['owners']:
   p=o['source_polygon_xz_m'];ax.add_patch(Polygon(p,fill=False,edgecolor='#5d6573',lw=.8));cx=sum(v[0]for v in p)/len(p);cz=sum(v[1]for v in p)/len(p)
   if win[0]<cx<win[2]and win[1]<cz<win[3]:ax.text(cx,cz,o['owner_id'].replace('SITE_',''),fontsize=8,color='#6e7480',ha='center')
  for inst in projection['instances']:
   for p in inst['native_parts_xz_m']:
    if min(v[0]for v in p)>win[2]or max(v[0]for v in p)<win[0]or min(v[1]for v in p)>win[3]or max(v[1]for v in p)<win[1]:continue
    ax.add_patch(Polygon(p,facecolor='#d1d0c9',edgecolor='none',zorder=1))
  for u in pack['holdings']:
   p=u['polygon_xz_m'];x,y,z=u['position_m']
   if not(win[0]<x<win[2]and win[1]<z<win[3]):continue
   ax.add_patch(Polygon(p,facecolor=colors[u['function']],edgecolor='#463e31',lw=1.3,zorder=3));ax.text(x,z,u['id'].split('_')[-1],fontsize=8,ha='center',va='center',zorder=4)
  ax.set_xlim(win[0],win[2]);ax.set_ylim(win[3],win[1]);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('World X, metres');ax.set_ylabel('World Z, metres');ax.set_facecolor('#f8f6ef');ax.grid(lw=.3,alpha=.4)
 fig.suptitle('Protected precinct grounds: 28 resolved native holdings / 9,076 m²\nGray = actual R7 native projection. Colors = new functional sources. Public continuation and actual scene review remain gated.',fontsize=15);fig.savefig(HERE/'precinct_ground_plan.png',dpi=130);print(summary)
if __name__=='__main__':main()
