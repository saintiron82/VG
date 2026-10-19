"""Whole-owner residual uses and finite level-ground field candidates."""
from pathlib import Path
import sys,json,collections
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from build_ledger import *
OUT=Path(__file__).resolve().parent
USES={'SITE_CEMETERY':'cemetery visitor/processional apron, retain burial boundaries','SITE_CLOISTER':'cloister garden and contemplative court, retain quadrangle','SITE_BASIN':'retained hydraulic reserve and maintenance edge','SITE_COMMON':'common maintenance/drying meadow and shared work court','SITE_MARKET':'retained trading/processional court and market service apron','SITE_TRAIN':'clear drill/exercise ground and tack/service verge','SITE_CASTLE':'outer-bailey exercise/service court; steep bank portions retained as defensive slopes','SITE_PORT':'quayside loading/staging apron and water-edge service margin','SITE_CLERGY':'canons service courts, orchard/growing edges and processional ground','SITE_MONASTERY':'productive orchard/growing grounds, working courts and processional ground'}

def main():
 old=load(BASE/'owner_completion_ledger.json');m=np.load(BASE/'owner_masks.npz');r=np.load(BASE/'terrain_raster.npz');pack=load(BASE/'resolved_connected_placements.json');allpack=load(BASE/'resolved_placements.json');h,g=r['height'],r['grade'];new=b.mask([u['polygon_xz_m']for u in allpack['holdings']]);paths=b.mask([p for x in pack['external_routes']for p in x['ribbon_polygons_xz_m']]);blocked=b.buffer(m['native']|m['reserved']|m['water']|m['public']|new,1);rows=[];fields=[];labels=np.zeros(b.SHAPE,np.int32);nextid=1
 for j,o in enumerate(old['owners'],1):
  raw=(m['labels']==j)&~m['native']&~m['reserved']&~m['water']&~m['public']&~new;nativefloor=np.isfinite(h)&(g<1e-7);flat=raw&nativefloor&~blocked&~paths;steep=raw&np.isfinite(g)&(g>.12);gently=raw&np.isfinite(g)&(g>1e-7)&(g<=.12);missing=raw&~np.isfinite(h);parts=[]
  # Homogeneous actual level components only; graded residuals are separately
  # retained, never flattened or declared a connected field by the raster.
  floors=sorted(set(np.round(h[flat],3).tolist()))
  for floor in floors:
   zmask=flat&(abs(h-floor)<1e-5);ll,n=ndimage.label(zmask)
   for k in range(1,n+1):
    field=ll==k;area=b.area(field)
    if area<100:continue
    near=bool(np.any(b.buffer(field,3)&paths));z,x=np.nonzero(field);center=[float(b.BOUNDS[0]+x.mean()+.5),float(b.BOUNDS[1]+z.mean()+.5)];fid=f'FIELD_{o["owner_id"]}_{nextid:03d}';ps=b.parts(field)
    row={'id':fid,'owner_id':o['owner_id'],'screen_grid_area_m2':area,'screen_polygon_parts_xz_m':ps,'floor_y_m':float(floor),'centroid_xz_m':center,'adjacent_to_ready21_public_spur_screen':near,'status':'FINITE_EXACT_DOMAIN_AND_FACILITY_AUTHORING_REQUIRED'};fields.append(row);parts.append(fid);labels[field]=nextid;nextid+=1
  kind=USES.get(o['owner_id'],'retained noble residential garden, household service court and estate access')
  rows.append({'owner_id':o['owner_id'],'intended_use':kind,'prior_unassigned_grid_m2':o['remaining_after_native_candidate_grid_m2'],'residual_raw_grid_m2':b.area(raw),'existing_steep_surface_grid_m2':b.area(steep),'existing_gently_graded_surface_grid_m2':b.area(gently),'missing_actual_surface_grid_m2':b.area(missing),'screen_level_field_ids':parts,'existing_native_facilities':o['actual_existing_functional_components'],'completion_criteria':['Actual native facilities and exact owned open ground have a stated, visible land use.','Entry, service/inspection edge and public continuation have finite actual-surface and native-clearance evidence.','Boundaries follow retained precinct/cemetery/cloister/estate limits.','Steep defensive/service banks are classified from their actual geometry, not used to excuse missing level ground.'],'complete':False})
 np.savez_compressed(OUT/'field_screen.npz',labels=labels)
 out={'sources':{'owner_ledger':ref(BASE/'owner_completion_ledger.json'),'ready21':ref(BASE/'resolved_connected_placements.json'),'scene':ref(terrain.SCENE_PATH)},'owner_uses':rows,'fields':fields,'summary':{'owners':len(rows),'screen_level_fields':len(fields),'screen_level_area_m2':sum(f['screen_grid_area_m2']for f in fields),'adjacent_screen_fields':sum(f['adjacent_to_ready21_public_spur_screen']for f in fields),'adjacent_screen_area_m2':sum(f['screen_grid_area_m2']for f in fields if f['adjacent_to_ready21_public_spur_screen'])},'policy':'This is an explicit source-use and candidate screen, not implemented land coverage. Exact source pieces, facilities, routes and independent checks must precede promotion.'};(OUT/'whole_owner_use_plan.json').write_text(json.dumps(out,indent=2)+'\n');print(out['summary'])
 for x in rows:print(x['owner_id'],len(x['screen_level_field_ids']),x['existing_steep_surface_grid_m2'],x['missing_actual_surface_grid_m2'])
if __name__=='__main__':main()
