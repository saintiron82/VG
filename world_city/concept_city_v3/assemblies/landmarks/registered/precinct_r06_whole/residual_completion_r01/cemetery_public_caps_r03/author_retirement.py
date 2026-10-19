"""Retire one obsolete cemetery connection; retain the cemetery source intact."""
from pathlib import Path
import sys,json,copy,time
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE));sys.path.insert(0,str(OUT.parent/'noble_entry_batch_r01'))
from resolve_pack import *
from author_native_entries import estimate_candidates
from build_ground_patch import faces,upper,lift
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg
OUT=Path(__file__).resolve().parent

def write(n,d):p=OUT/n;p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n');return ref(p)
def main():
 projection=load(BASE/'actual_native_projection.json');old=next(p for p in projection['instances']if p['id']=='REGISTERED_LANDSCAPE:SITE_CEMETERY');a=projection['assets'][old['asset_key']];source=load(ROOT/a['source']['path']);oldmesh=load(ROOT/a['cache']['path']);operation='CLERGY_CEMETERY:connection:1:0';deleted=[o for o in source['components'][0]['operations']if o['id']==operation];assert len(deleted)==1
 master=copy.deepcopy(source);master['id']='registered_precinct_cemetery_caps_r03';master['revision']=1;master['components'][0]['operations']=[o for o in source['components'][0]['operations']if o['id']!=operation];master['metadata']['obsolete_connection_retirement']=dict(source=a['source'],cache=a['cache'],operation=deleted[0],reason='Old rejected analytical branch intrudes into canonical public traffic. Accepted cemetery route uses a separate retained entrance.',accepted_route=ref(OUT.parent/'retained_garden_access_r02/cemetery_entry_route.json'));sr=write('masters/'+master['id']+'.json',master);estimate=estimate_candidates(master,.5);assert estimate['candidate_cells_exact_aabb_visits']<200000;pf=write('preflight.json',dict(source=sr,pitch_m=.5,estimate=estimate));compiled=coordinate_planes.compile_master(master,{'pitch':.5},max_candidate_cells=200000,max_output_cells=50000);assert compiled['valid'];mesh=render_data.make_render_data(compiled);cr=write('cache/'+master['id']+'.render.json',mesh);new=dict(id='R06_CEMETERY_CAP_R03:retained_site',owner_id='SITE_CEMETERY',asset_key=master['id'],source=sr,cache=cr,position_m=old['position_m'],yaw_rad=old['yaw_rad'],scale=[1,1,1],role='retained_cemetery_without_obsolete_connection')
 oldup=upper(faces(dict(old,cache=a['cache']))[0]);newup=upper(faces(new)[0]);ni=geo._SpatialIndex(4)
 for i,r in enumerate(newup):ni.add(i,r['polygon_xz_m'])
 removed=[]
 for r in oldup:
  if abs(r['plane_y_xz_m'][2]-14)>1e-8:continue
  for q in fg.subtract([r['polygon_xz_m']],[newup[i]['polygon_xz_m']for i in ni.candidates(r['polygon_xz_m'])]):
   if fg.area(q)>1e-8:removed.append(dict(id='CEMETERY_OLD_CONNECTION:'+str(len(removed)),polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m']))
 pubpath=CITY/'registered_topography/revisions/public_corridors_r18/finite_field_candidate_r07_native_bound.json';public=load(pubpath);publicrows=public['records'];pi=geo._SpatialIndex(8)
 for i,r in enumerate(publicrows):pi.add(i,r['polygon_xz_m'])
 restorations=[];public_retired=[]
 for r in removed:
  cuts=[]
  for i in pi.candidates(r['polygon_xz_m']):
   pu=publicrows[i];q=fg.clip(r['polygon_xz_m'],pu['polygon_xz_m'])
   if fg.area(q)>1e-8:cuts.append(q);public_retired.append(dict(polygon_xz_m=q,public_owner_id=pu['id'],plane_y_xz_m=pu['plane_y_xz_m'],old_native_floor_y_m=14))
  for q in fg.subtract([r['polygon_xz_m']],cuts):
   if fg.area(q)>1e-8:restorations.append(dict(r,polygon_xz_m=q,material='ground_earth'))
 sourcecheck=dict(all_other_operations_exact=master['components'][0]['operations']==[o for o in source['components'][0]['operations']if o['id']!=operation],removed_operation_count=len(deleted),removed_floor_area_m2=sum(fg.area(r['polygon_xz_m'])for r in removed),public_owned_retirement_area_m2=sum(fg.area(r['polygon_xz_m'])for r in public_retired),off_public_same_datum_restoration_area_m2=sum(fg.area(r['polygon_xz_m'])for r in restorations),new_source=sr,new_cache=cr)
 pack=dict(schema='riverstone.precinct.cemetery_cap_retirement.v1',status='CANDIDATE_GROUND_CLOSURE_PENDING',assets=[dict(id=master['id'],source=sr,cache=cr,pitch_m=.5,preflight=pf)],placements=[new],replacement_ledger=dict(existing_native_placements_removed=[old['id']]),source_original=a['source'],cache_original=a['cache'],retired_operation=operation,summary=sourcecheck,runtime_ready=False)
 write('resolved_native_candidate.json',pack);write('retirement_partition.json',dict(public_source=ref(pubpath),native_pack=ref(OUT/'resolved_native_candidate.json'),retired_native_floor=removed,off_public_restoration=restorations,public_traffic_replacement=public_retired,summary=sourcecheck));print(sourcecheck,flush=True)
if __name__=='__main__':main()
