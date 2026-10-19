"""Bounded district-window reuse of the frozen B15 source producer.
No compilation or scale change. Existing finite flat bands and proven retired
holes are eligible; all unmatched owners remain hard exclusions.
"""
from . import geometry as g
from .design import HERE as SOURCE
import sys,types,fcntl

def run(block_id):
 if (SOURCE/'flat_mode_stop.json').exists():print('Flat-only diagnostic superseded by authorized coherent regrading');return
 out=SOURCE/'district_jobs'/block_id;out.mkdir(parents=True,exist_ok=True);lock=(out/'producer.lock').open('w');fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
 plan=g.CITY/'registered_integration/r8/coverage_plan';terr=g.CITY/'registered_topography/revisions/r17_district_batches';blocks=g.load(plan/'baseline_blocks.json')['blocks'];bi=next(i for i,b in enumerate(blocks)if b['block_id']==block_id);block=blocks[bi];p=block['polygon_xz_m'];bounds=[g.math.floor(min(q[0]for q in p)/10)*10-10,g.math.floor(min(q[1]for q in p)/10)*10-10,g.math.ceil(max(q[0]for q in p)/10)*10+10,g.math.ceil(max(q[1]for q in p)/10)*10+10]
 g.HERE=out;g.BOUNDS=bounds;g.NX=round((bounds[2]-bounds[0])/g.GRID);g.NZ=round((bounds[3]-bounds[1])/g.GRID);g.SHAPE=(g.NZ,g.NX);g.XS=bounds[0]+(g.np.arange(g.NX)+.5)*g.GRID;g.ZS=bounds[1]+(g.np.arange(g.NZ)+.5)*g.GRID
 bands=g.load(terr/'terrain_bands.json');info=next(b for b in bands['blocks']if b['block_id']==block_id);floors=[b['floor_y_m']for b in info['flat_ground_bands']if b['area_m2']>=200]
 baseline=g.np.load(plan/'baseline_masks.npz');x=((g.XS-float(baseline['bounds'][0]))/float(baseline['pitch'])).astype(int);z=((g.ZS-float(baseline['bounds'][1]))/float(baseline['pitch'])).astype(int);ms={k:baseline[k][g.np.ix_(z,x)]for k in baseline.files if baseline[k].ndim==2};domain=ms['block_labels']==bi+1;protected=g.np.logical_or.reduce([ms[k]for k in['spaces','estates','water','road','wall','retained_native','retained_access']]);rows=[r for r in g.load(terr/'all_blocks_r01/retirement_candidates.json')['rows']if r['block_id']==block_id];safe={r['source_id']for r in g.load(terr/'all_blocks_r01/body_boundary_audit.json')['rows']if r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'}
 # Reuse the precise parser/search source with only explicit district parameters.
 text=(SOURCE/'dense.py').read_text();text=text.replace("from .geometry import *","from .geometry import *\nFLOORS="+repr(floors)).replace("for floor in(2.5,1.):","for floor in FLOORS:").replace("center=[200.25,250.25]","center=point((NZ//2,NX//2))").replace("B15",'B'+str(int(block_id[-3:]))).replace('BLOCK_015',block_id).replace("nearroad=ndimage.distance_transform_edt(~public)*GRID<3","nearroad=ndimage.distance_transform_edt(~public)*GRID<1.5")
 text=text.replace("TERR/'retired_body_boundary_audit.json'","TERR/'all_blocks_r01/body_boundary_audit.json'").replace("TERR/'retirement_candidates.json'","TERR/'all_blocks_r01/retirement_candidates.json'")
 text=text.replace("public=world_scene_floor(scene,floor,{'road','alley'});band=","public=world_scene_floor(scene,floor,{'road','alley'})&old['road'][np.ix_(z,x)];band=")
 # Freeze the parameterized source alongside its output for reproducibility.
 (out/'producer_source.py').write_text(text);engine=types.ModuleType(__package__+'.district_job_engine');engine.__package__=__package__;exec(compile(text,str(out/'producer_source.py'),'exec'),engine.__dict__)
 scene=g.load(g.R7);projection=g.load(plan/'native_projection.json')['instances'];rowids={r['source_id']for r in rows};ordinary=[i for i in projection if i['source_pack']=='ordinary'and i['id']in rowids]
 outputs=dict(domain=domain,protected=protected,nonmatching_native=g.raster([q for i in ordinary if i['id']not in safe for q in i['native_owner_parts_xz_m']],True))
 for floor in floors:
  actual=engine.world_scene_floor(scene,floor);matching=[r for r in rows if r['matching_level_band_y_m']==floor and r['source_id']in safe];holes=g.raster([r['old_terrain_body_hole_polygon_xz_m']for r in matching]);tag=str(float(floor)).replace('.','_');outputs['floor_'+tag]=(actual|holes)&domain&~protected;outputs['restorable_'+tag]=holes;outputs['visible_'+tag]=actual
 g.np.savez_compressed(out/'planning_masks.npz',**outputs,grid=g.GRID,bounds=bounds)
 g.write(out/'input.json',dict(block=block,restorable_candidates=rows,floor_bands=floors,source= g.ref(SOURCE/'dense.py'),fixed_family_bulk_contract=g.ref(plan/'fixed_family_bulk_contract.json'),summary={k:g.area(v)for k,v in outputs.items()}))
 snapshot=g.load(SOURCE/'owner_route_source_snapshot.json');snapshot['district_job_block_id']=block_id;snapshot['fixed_family_bulk_contract']=g.ref(plan/'fixed_family_bulk_contract.json');g.write(out/'owner_route_source_snapshot.json',snapshot)
 for name in['native_local.json','compile_report.json']:(out/name).write_bytes((SOURCE/name).read_bytes())
 if not floors:
  g.write(out/'job_result.json',dict(block_id=block_id,status='BOUNDED_GRADE_DESIGN_REQUIRED',reason='No actual existing flat band above 200 m². Source capacity does not authorize flattening.',new_native_holdings=0));return
 result=engine.run()
 # Correct native before/after coverage includes all actual ordinary owners,
 # including those outside the limited existing restoration candidate ledger.
 before=sum(i['roof_area_m2']for i in ordinary);removed=sum(i['roof_area_m2']for i in ordinary if i['id']in result['retired_source_ids']);result['summary'].update(before_ordinary_roof_m2=before,retired_ordinary_roof_m2=removed,after_ordinary_roof_m2=before-removed+result['summary']['native_roof_m2'],net_ordinary_roof_gain_m2=result['summary']['native_roof_m2']-removed);g.write(out/'selected_layout.json',result)
 # Door and court producers read the same final native masks and finite owners.
 for name in['access','furnish']:
  src=(SOURCE/(name+'.py')).read_text();module=types.ModuleType(__package__+'.job_'+name);module.__package__=__package__;exec(compile(src,str(SOURCE/(name+'.py')),'exec'),module.__dict__);module.run()
 freeze_source=(SOURCE/'freeze.py').read_text().split(' # A finite residual ledger')[0].replace('BLOCK_015',block_id).replace('B15',block_id)+'\n return pack\n';fm=types.ModuleType(__package__+'.job_freeze');fm.__package__=__package__;exec(compile(freeze_source,str(SOURCE/'freeze.py'),'exec'),fm.__dict__);pack=fm.run()
 status='NATIVE_SOURCE_PENDING_R17_AND_PUBLIC_SEAM_PROOF'if result['summary']['net_ordinary_roof_gain_m2']>=0 else'HELD_NATIVE_ROOF_REGRESSION'
 g.write(out/'job_result.json',dict(block_id=block_id,status=status,summary=result['summary'],layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'),producer=g.ref(out/'producer_source.py')))
 print('JOB',block_id,result['summary'],flush=True)
if __name__=='__main__':run(sys.argv[1])
