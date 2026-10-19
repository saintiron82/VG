#!/usr/bin/env python3
"""Actual original image pixels changed in memory, using the validator predicate.
No files are edited and no geometry is sampled, compiled or meshed.
"""
from validate_material_delta import *
def main():
 t=time.monotonic();before=pins();ctx=prepare_context();image=np.asarray(Image.open(SOURCE).convert('RGB')).copy();original=image.copy();palette=np.array([[int(ctx['palette'][f'top_tile_{i:02d}'][j:j+2],16) for j in (0,2,4)] for i in range(6)]);records=ctx['expected_records'];selected=records[0];u,v,U,V=selected['whole_TOP_pixel_support_box'];before_pixel=image[v,u].tolist();before_evidence=source_pixel_evidence(image,[u,v,U,V],palette);require(before_evidence is not None,'Positive eligible source fixture missing')
 image[v,u]=[255,255,255];after_evidence=source_pixel_evidence(image,[u,v,U,V],palette);require(after_evidence is None,'Non-terracotta overlapped source pixel did not remove cell eligibility');dropped=[];unchanged=0
 for r in records:
  e=source_pixel_evidence(image,r['whole_TOP_pixel_support_box'],palette)
  if e is None:dropped.append(r['cell_xyz'])
  else:
   median,nearest=e;require(median.tolist()==r['source_TOP_median_rgb'] and f'top_tile_{nearest:02d}'==r['proposed_material'],'Untouched source cell evidence changed');unchanged+=1
 require(selected['cell_xyz'] in dropped and len(dropped)>0 and unchanged+len(dropped)==2609,'Causal eligibility accounting failure')
 nonred={'selected_cell_xyz':selected['cell_xyz'],'whole_TOP_pixel_support_box':[u,v,U,V],'actual_pixel_uv':[u,v],'original_RGB':before_pixel,'mutated_RGB':[255,255,255],'selected_before_eligible':True,'selected_after_eligible':False,'selected_cells_removed_by_one_actual_pixel':dropped,'remaining_selected_cells_exact':unchanged,'predicate_used_by_positive_validator':True}
 # A one-pixel source footprint makes its actual RGB the entire median sample.
 image[:]=original;color=None
 for r in records:
  u,v,U,V=r['whole_TOP_pixel_support_box']
  if U-u!=1 or V-v!=1:continue
  old=source_pixel_evidence(image,[u,v,U,V],palette);require(old is not None,'Missing one-pixel positive fixture')
  for pid,px in enumerate(palette):
   if pid==old[1]:continue
   image[v,u]=px;new=source_pixel_evidence(image,[u,v,U,V],palette)
   if new is not None and new[1]!=old[1] and not np.array_equal(new[0],old[0]):
    color={'selected_cell_xyz':r['cell_xyz'],'whole_TOP_pixel_support_box':[u,v,U,V],'actual_pixel_uv':[u,v],'original_RGB':original[v,u].tolist(),'mutated_RGB':px.tolist(),'old_source_median_RGB':old[0].tolist(),'new_source_median_RGB':new[0].tolist(),'old_material':f'top_tile_{old[1]:02d}','new_material':f'top_tile_{new[1]:02d}','entire_footprint_is_this_one_actual_pixel':True,'strict_terracotta_still_passes':True,'nearest_changed_to_exact_existing_palette_entry':new[1]==pid};break
   image[v,u]=original[v,u]
  if color is not None:break
 require(color is not None,'No complete one-pixel color causal fixture found');require(color['nearest_changed_to_exact_existing_palette_entry'],'Exact palette transfer failed')
 require(all(sha(ROOT/p)==h for p,h in before.items()),'Original source changed')
 report={'schema':'riverstone.roof_repair_r04.actual_pixel_causality.v1','status':'PASS','source_image':ref(SOURCE),'actual_pixel_nonterracotta_fixture':nonred,'actual_single_pixel_complete_footprint_color_fixture':color,'original_image_file_unchanged':True,'image_mutation_in_memory_only':True,'source_records_unmodified':True,'sampling_calls':0,'mesher_calls':0,'compiler_calls':0,'address_space_limit_mib':256,'cpu_limit_seconds':60,'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'validator':ref(Path(__file__)),'positive_source_predicate':ref(HERE/'validate_material_delta.py')}
 save(HERE/'actual_pixel_causality.json',report);print(json.dumps(report,sort_keys=True))
if __name__=='__main__':main()
