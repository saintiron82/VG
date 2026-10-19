"""Prepare finite district masks from the actual scene and matching old holes."""
from .geometry import *
PLAN=CITY/'registered_integration/r8/coverage_plan';TERR=CITY/'registered_topography/revisions/r17_district_batches'

def run():
 base=load(PLAN/'baseline_blocks.json');block=next(b for b in base['blocks']if b['block_id']=='BLOCK_015');old=np.load(PLAN/'baseline_masks.npz');x=((XS-float(old['bounds'][0]))/float(old['pitch'])).astype(int);z=((ZS-float(old['bounds'][1]))/float(old['pitch'])).astype(int);ms={k:old[k][np.ix_(z,x)]for k in old.files if old[k].ndim==2};domain=ms['block_labels']==15
 protected=np.logical_or.reduce([ms[k]for k in['spaces','estates','water','road','wall','retained_native','retained_access']]);bands=load(TERR/'terrain_bands.json');retire=load(TERR/'retirement_candidates.json');rows=[r for r in retire['rows']if r['block_id']=='BLOCK_015'];projection=load(PLAN/'native_projection.json');native={i['id']:i for i in projection['instances']}
 boundary=load(TERR/'retired_body_boundary_audit.json');safe_ids={r['source_id']for r in boundary['rows']if r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'}
 outputs=dict(domain=domain,protected=protected)
 for floor in(1.,2.5):
  actual=raster([r['polygon_xz_m']for r in bands['priority_exact_band_regions']if r['block_id']=='BLOCK_015'and r['floor_y_m']==floor]);matching=[r for r in rows if r['matching_level_band_y_m']==floor and r['source_id']in safe_ids];holes=raster([r['old_terrain_body_hole_polygon_xz_m']for r in matching]);outputs['floor_'+str(floor).replace('.','_')]=(actual|holes)&domain&~protected
  outputs['visible_'+str(floor).replace('.','_')]=actual;outputs['restorable_'+str(floor).replace('.','_')]=holes
 # Buildings on other datums remain obstacles. Candidate rows retire only if a
 # selected new holding/route actually overlaps; old files and scene stay intact.
 outputs['nonmatching_native']=raster([p for r in rows if r['source_id']not in safe_ids for p in native[r['source_id']]['native_owner_parts_xz_m']],touch=True)
 np.savez_compressed(HERE/'planning_masks.npz',**outputs,grid=GRID,bounds=BOUNDS)
 d=dict(schema='riverstone.district_fabric.input.v1',base_scene=ref(R7),block=block,references=[ref(PLAN/'baseline_masks.npz'),ref(PLAN/'native_projection.json'),ref(TERR/'terrain_bands.json'),ref(TERR/'retirement_candidates.json')],restorable_candidates=rows,summary={k:area(v)for k,v in outputs.items()},status='Source masks only. Raster search is conservative layout aid; exact vectors and actual R7 triangles decide terrain promotion.');write(HERE/'input.json',d);print(json.dumps(d['summary'],indent=2))
if __name__=='__main__':run()
