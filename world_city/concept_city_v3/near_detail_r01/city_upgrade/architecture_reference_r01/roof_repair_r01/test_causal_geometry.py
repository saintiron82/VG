"""Tiny actual common-compiler fixtures propagate measured raster mutations."""
from pathlib import Path
import copy,json,resource,time
from author_roof import H,R,P,read,write,core,ref,pins

def main():
 t=time.monotonic();before=pins();tiles=read(H/'tile_measurement_r01/tile_regions.json');v=read(H/'tile_measurement_r01/validation.json');master=read(H/'roof_patch.master.json.gz');full=read(H/'roof_patch.compiled.json.gz')
 rid=v['color_mutation']['region_id'];region=next(r for r in tiles['regions']if r['id']==rid);op=next(o for o in master['components'][0]['operations']if o['id']==rid)
 assert region['color']['palette_id']==v['color_mutation']['before_palette_id']
 tiny=copy.deepcopy(master);tiny['components'][0]['operations']=[copy.deepcopy(op)]
 a=core.compile_master(tiny,{'pitch':P},max_candidate_cells=2000,max_output_cells=2000)
 mutated=copy.deepcopy(tiny);mutated['components'][0]['operations'][0]['material']=f'top_tile_{v["color_mutation"]["after_palette_id"]:02d}'
 color=core.compile_master(mutated,{'pitch':P},max_candidate_cells=2000,max_output_cells=2000)
 original=set(v['boundary_mutation']['before_v_troughs_px']);changed=set(v['boundary_mutation']['after_v_troughs_px']);removed=original-changed;added=changed-original;assert len(removed)==len(added)==1
 oldend,newend=next(iter(removed)),next(iter(added));assert region['bbox_px'][3]==oldend
 boundary=copy.deepcopy(tiny);boundary['components'][0]['operations'][0]['shape']['z_max']+=(newend-oldend)*tiles['conditional_mapping']['coefficients']['sz']
 b=core.compile_master(boundary,{'pitch':P},max_candidate_cells=2000,max_output_cells=2000)
 coords=lambda c:{tuple(r[:3])for r in c['cells']}
 basecoords=coords(a);colorcoords=coords(color);boundarycoords=coords(b)
 features={}
 for row in full['cells']:features[row[6]]=features.get(row[6],0)+1
 tests={'source_pixel_color_mutation_changes_common_material':{r[5]for r in a['cells']}!={r[5]for r in color['cells']},'source_pixel_color_mutation_keeps_geometry_and_height':basecoords==colorcoords,'observed_two_pixel_seam_mutation_changes_common_cells':basecoords!=boundarycoords,'changed_seam_does_not_change_y_range':{r[1]for r in a['cells']}=={r[1]for r in b['cells']},'all_339_measured_regions_have_actual_compiled_cells':all(features.get(r['id'],0)>0 for r in tiles['regions']),'no_measured_region_extruded_through_10m':max((o['shape']['z_max']-o['shape']['z_min'])for o in master['components'][0]['operations']if o['part']=='measured_tile_regions')<1.2,'shared_compiler_request_and_grid_retained':all(c['pitch']==P and c['grid_origin']==[0,0,0]for c in [a,b,color])}
 rejected=False
 try:core.compile_master(tiny,{'pitch':P},max_candidate_cells=1,max_output_cells=2000)
 except core.BudgetExceeded:rejected=True
 tests['candidate_budget_overrun_rejected']=rejected
 assert all(tests.values()),tests;assert before==pins()
 report={'schema':'riverstone.image_roof_repair.causal_geometry.v1','status':'PASS','tests':tests,'source_raster_mutation_test':ref(H/'tile_measurement_r01/validation.json'),'region_id':rid,'baseline_cells':len(a['cells']),'color_mutation_changed_material_cells':len(a['cells']),'boundary_mutation_pixels':[oldend,newend],'boundary_mutation_cell_symmetric_difference':len(basecoords^boundarycoords),'actual_region_cell_count_range':[min(features[r['id']]for r in tiles['regions']),max(features[r['id']]for r in tiles['regions'])],'three_small_positive_compiler_calls_candidate_cells':sum(c['candidate_cells']for c in [a,b,color]),'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'original_image_modified':False,'candidate_render_modified':False,'whole_house_compiled':False,'driver':ref(Path(__file__))}
 write('causal_geometry_tests.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,)*2);main()
