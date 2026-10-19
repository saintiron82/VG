from build_plan import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Polygon,Patch
COLORS=['#faf7ec','#b7bab0','#4d98a8','#899181','#efe7d2','#78695c','#cdb59f','#e6d395','#ad5c3f','#d8b994','#9a8b79','#a9bd80','#becaa3','#ddd3af','#dc81a0']
NAMES=['Outside','Protected precinct / estate','Water + dry bank service','Wall inspection corridor','Preserved public road','Retained special native owner','Reviewed special source reservation','Walking / gate routes first','Proposed attached roof envelope','Private domestic / working court','Retained detached roof, review due','Private garden / work-ground plan','Precinct-margin productive/service plan','Retained household ground retrofit','UNASSIGNED: decision required']

def main():
 plan=load(HERE/'whole_city_coverage_plan.json');parc=load(HERE/'parcel_candidates.json');p=load(CITY/'registered_source/plan.json');base=np.load(HERE/'baseline_masks.npz');m=np.load(HERE/'allocation_masks.npz');land=m['land_use']; cmap=ListedColormap(COLORS);proj=load(HERE/'native_projection.json')
 for detail in (False,True):
  fig=plt.figure(figsize=(18,13),facecolor='#faf7ec');ax=fig.add_axes([.035,.06,.72,.87]);side=fig.add_axes([.775,.07,.21,.84]);side.axis('off')
  ax.imshow(land,cmap=cmap,vmin=0,vmax=14,extent=[BOUNDS[0],BOUNDS[2],BOUNDS[3],BOUNDS[1]],interpolation='nearest',alpha=.95)
  for b in p['blocks']:
   if detail and b['id']!='BLOCK_015':continue
   q=np.array(b['polygon_xz_m']+[b['polygon_xz_m'][0]]);ax.plot(q[:,0],q[:,1],color='#464740',linewidth=1.0 if detail else .6)
   bm=base['block_labels']==next(i+1 for i,v in enumerate(p['blocks'])if v['id']==b['id']);dt=ndimage.distance_transform_edt(bm);iz,ix=np.unravel_index(np.argmax(dt),dt.shape);cx=BOUNDS[0]+(ix+.5)*PITCH;cz=BOUNDS[1]+(iz+.5)*PITCH
   if not detail:ax.text(cx,cz,b['id'].replace('BLOCK_','B'),fontsize=9,weight='bold',ha='center',bbox=dict(boxstyle='round,pad=.16',fc='white',ec='none',alpha=.85))
  for h in parc['holdings']:
   if detail and h['block_id']!='BLOCK_015':continue
   ax.add_patch(Polygon(h['holding_polygon_xz_m'],closed=True,fill=False,ec='#6c483a',lw=.9 if detail else .35))
   for poly in h['building_envelope_parts_xz_m']:ax.add_patch(Polygon(poly,closed=True,fc='#ad5c3f',ec='#633c2d',lw=.7 if detail else .2))
   q=np.array(h['street_connection_polyline_xz_m']);ax.plot(q[:,0],q[:,1],color='#bd9d43',lw=2 if detail else .7)
   if detail:ax.text(*h['origin_xz_m'],h['id'].split(':')[-1].replace('R8_',''),fontsize=9,ha='center',weight='bold',bbox=dict(fc='white',ec='none',alpha=.8,pad=1))
  if detail:
   ax.set_xlim(55,410);ax.set_ylim(405,95);title='BLOCK 015 | canal district route-first parcel plan'
   from collections import Counter
   native_bound=bool(plan.get('native_B15_binding'));hs=[h for h in parc['holdings']if h['block_id']=='BLOCK_015'];bb=next(b for b in plan['blocks']if b['block_id']=='BLOCK_015')
   side.text(0,.99,'FABRIC-OWNED NATIVE CANDIDATE' if native_bound else 'SOURCE DIAGNOSTIC ONLY',fontsize=10.5,weight='bold',va='top')
   side.text(0,.945,f"{len(hs)} holdings / {sum(h['source_building_envelope_area_m2'] for h in hs):,.0f} m² proposed roof\n{bb['unassigned_m2']:,.0f} m² still explicitly unassigned\nActual block completion: OPEN",fontsize=10,va='top',linespacing=1.5)
   families=Counter(h['grammar_id'] for h in hs);y=.84
   for name,count in sorted(families.items()):
    short=name.replace('district_r01_','').replace('working_r01_','').replace('ATTACHED_DOUBLE_RANGE_30_10','paired ranges').replace('_',' ')
    side.text(0,y,f'{count:2d}  {short}',fontsize=9,va='top');y-=.029
   binding='Native cache footprints and owner IDs\nare imported unchanged. Integration\nand actual scene review remain pending.' if native_bound else 'Street-facing source capacity proposals.\nExact native allocation belongs to the\ndistrict fabric batch.'
   side.text(0,.60,binding+'\n\nBoth canal banks: 4 m dry no-build band.\nTarget 3.5 m clear tow/service route.\nExisting verified bridges only.\n\nColored yards need actual boundaries,\ngates, working/domestic facilities.\nNo scene geometry is placed by this plan.',fontsize=9,va='top',linespacing=1.4)
   ly=.34
  else:
   ax.set_xlim(-470,460);ax.set_ylim(425,-435);title='R8 | all-block ordinary-city completion plan'
   side.text(0,.99,'ALL 18 REGISTERED BLOCK FACES',fontsize=11,weight='bold',va='top');y=.955
   for b in plan['blocks']:
    side.text(0,y,f"{b['block_id'].replace('BLOCK_','B')}   {len(b['candidate_holding_ids']):2d} new parcels   gap {b['unassigned_m2']:,.0f} m²",fontsize=8.8,va='top');y-=.025
   side.text(0,.475,f"{len(parc['holdings'])} source parcels / {len(parc['retirement_ledger'])} old native IDs\nproposed for atomic replacement.\n\nMarket B012 stays civic/market.\nProtected estate and institutional\nareas are not ordinary housing land.\n\nColored source ground is planned use,\nnot evidence of implemented facilities.",fontsize=9,va='top',linespacing=1.35);ly=.27
  leg=[Patch(facecolor=COLORS[i],edgecolor='none',label=NAMES[i])for i in range(1,15)];side.legend(handles=leg,loc='upper left',bbox_to_anchor=(-.05,ly),frameon=False,fontsize=8,handlelength=1.25,labelspacing=.55)
  ax.set_aspect('equal');ax.set_xlabel('Registered world X (m)');ax.set_ylabel('Registered world Z (m)');ax.grid(alpha=.12);fig.suptitle(title,x=.04,ha='left',fontsize=18,weight='bold',y=.99)
  fig.text(.04,.95,'Actual R7 bound to SHA 1429ae51… | 1 m plan accounting | native footprints preserved | source proposals are not runtime completion',fontsize=10,color='#55574c')
  name='block_015_plan'if detail else'whole_city_plan';fig.savefig(HERE/(name+'.png'),dpi=160,facecolor=fig.get_facecolor());fig.savefig(HERE/(name+'.svg'),facecolor=fig.get_facecolor());plt.close(fig)
if __name__=='__main__':main()
