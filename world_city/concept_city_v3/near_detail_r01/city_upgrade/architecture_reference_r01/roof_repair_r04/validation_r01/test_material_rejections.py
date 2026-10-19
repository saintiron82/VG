#!/usr/bin/env python3
"""Real r04 data mutations in memory; source and render files never change."""
from validate_material_delta import *
from test_surface_rejections import surface_tests

def main():
 t=time.monotonic();before=pins();ctx=prepare_context();tests={}
 def reject(name,call):
  try:call()
  except (ValueError,AssertionError) as e:tests[name]={'rejected':True,'reason':str(e)}
  else:raise AssertionError('Mutation accepted: '+name)
  gc.collect()
 def mutate_cell(name,p,value):
  a=ctx['new'];previous=int(a[p]);require(previous!=value,'Fixture must alter cell');a[p]=value
  try:reject(name,lambda:check_array(ctx))
  finally:a[p]=previous
 x,y,z=ctx['expected_records'][0]['cell_xyz'];point=(y-300,x+200,z+164);material=int(ctx['new'][point])
 mutate_cell('selected_cell_wrong_palette_material',point,15+(material-14)%6)
 mutate_cell('selected_cell_material_change_omitted',point,int(ctx['old'][point]))
 mutate_cell('selected_occupied_cell_deleted',point,-1)
 empty=(4,0,0);require(ctx['new'][empty]<0,'Fixture empty cell expected');mutate_cell('unowned_empty_cell_added',empty,15)
 hit=ctx['front'];iy,ix=np.argwhere(hit>=0)[0];frontpoint=(int(iy),int(ix),int(hit[iy,ix]));mutate_cell('FRONT_first_hit_material_change',frontpoint,15 if ctx['new'][frontpoint]!=15 else 16)
 hit=ctx['back'];iy,ix=np.argwhere(hit>=0)[-1];backpoint=(int(iy),int(ix),int(hit[iy,ix]));mutate_cell('BACK_first_hit_material_change',backpoint,15 if ctx['new'][backpoint]!=15 else 16)
 def records_bad(name,mut):
  records=copy.deepcopy(ctx['expected_records']);mut(records);reject(name,lambda:check_records(records,ctx['expected_records']))
 records_bad('source_pixel_support_box_shrunk',lambda r:r[0]['whole_TOP_pixel_support_box'].__setitem__(2,r[0]['whole_TOP_pixel_support_box'][2]-1))
 records_bad('source_TOP_color_invented',lambda r:r[0]['source_TOP_median_rgb'].__setitem__(0,r[0]['source_TOP_median_rgb'][0]+1))
 records_bad('source_coordinate_shift',lambda r:r[0]['conditional_TOP_footprint_uv'].__setitem__(0,r[0]['conditional_TOP_footprint_uv'][0]+.1))
 records_bad('unselected_deferred_cell_injected',lambda r:r.append(copy.deepcopy(r[0])))
 def master_bad(name,mut):
  m=copy.deepcopy(ctx['master']);mut(m);reject(name,lambda:check_master_compile(ctx,m))
 master_bad('per_face_color_override',lambda m:m['metadata'].__setitem__('per_face_color_override',True))
 master_bad('palette_color_changed',lambda m:m['materials'].__setitem__('top_tile_00','ffffff'))
 master_bad('common_source_box_expansion',lambda m:m['components'][0]['operations'][0]['shape']['max'].__setitem__(2,m['components'][0]['operations'][0]['shape']['max'][2]+PITCH))
 master_bad('source_transform_introduced',lambda m:m['components'][0]['operations'][0].__setitem__('transform',{'translation':[0,PITCH,0]}))
 compileinfo=read(R/'compile.json');compiled=read(ROOT/compileinfo['delta']['path']);compiled['cells'][0][5]='top_tile_00' if compiled['cells'][0][5]!='top_tile_00' else 'top_tile_01';compiled['payload_hash']=core.digest(compiled['cells']);reject('compiled_wrong_material_with_rehashed_payload',lambda:check_master_compile(ctx,compiled=compiled))
 cache=read(R/'cache_plan.json');changed=next(i for i,p in enumerate(cache['chunks']) if not p['reuse_exact_cache']);cache['chunks'][changed]['reuse_exact_cache']=True;reject('reuse_changed_material_halo_cache',lambda:check_cache_plan(ctx,cache))
 cache=read(R/'cache_plan.json');cache['chunks'][0]['r03_halo_material_sha256']='0'*64;reject('forged_old_material_halo_hash',lambda:check_cache_plan(ctx,cache))
 cache=read(R/'cache_plan.json');cache['chunks'][0]['original_cache']['sha256']='0'*64;reject('cache_file_pin_changed',lambda:check_cache_plan(ctx,cache))
 tests.update(surface_tests());require(all(sha(ROOT/p)==h for p,h in before.items()),'Input mutation persisted')
 report={'schema':'riverstone.roof_repair_r04.adversarial_material_validation.v1','status':'PASS','negative_tests_count':len(tests),'negative_tests':tests,'all_mutations_in_memory_only':True,'all_source_files_unchanged':True,'sampling_calls':0,'mesher_calls':0,'address_space_limit_mib':256,'cpu_limit_seconds':60,'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'validator':ref(Path(__file__))}
 save(HERE/'adversarial_validation.json',report);print(json.dumps(report,sort_keys=True))
if __name__=='__main__':main()
