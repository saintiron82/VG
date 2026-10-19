"""Four bounded native-color layers sampled/meshed by unchanged common tools."""
from native_common import *
import traceback
def run():
 start=time.monotonic();assert sha(BASE)==BASE_SHA;crop=source();labels=classify(crop);a=baseline();palette=full_palette(crop);assignment=source_assignment(crop,labels);assert len(assignment)==4156 and int((labels==0).sum())==1028
 raster_ref=save('source_raster.json.gz',{'source':ref(SOURCE),'roi_half_open':ROI,'source_rgb':crop.tolist(),'labels':labels.tolist(),'all_source_rgb_materials':{m:c for m,c in palette.items() if m.startswith('native_rgb_')},'rgb_unique_all':len(set(rgbid(rgb) for rgb in crop.reshape(-1,3))),'rgb_unique_accepted':len(set(assignment.values())),'all_source_pixels_preserved_as_data':True,'unresolved_not_applied':True})
 records=[];surface={};ownedcells={};allfaces=set();duplicates=0;sample_calls=0;mesh_calls=0
 for chunk in CHUNKS:
  t=time.monotonic();master=make_master(chunk,a,crop,labels);mr=save(f"masters/{chunk['id']}.json.gz",master);c=compile_master(master);sample_calls+=1;actual=cellmap(c);lo=master['metadata']['halo_bounds_native']['min'];hi=master['metadata']['halo_bounds_native']['max'];expect=expected(a,crop,labels,lo,hi);assert actual==expect
  oldnames=list(read(A/'foundation_repair_r01/foundation_revised.master.json.gz')['materials']);before=inherited(a,lo,hi,oldnames);assert set(before)==set(actual),'Occupancy changed'
  changed={p for p in actual if actual[p]!=before[p]};assert changed<=set(assignment)
  repeated=compile_master(master);sample_calls+=1;assert repeated['cells']==c['cells'] and repeated['payload_hash']==c['payload_hash'];del repeated
  mesh=render_data.make_render_data(c);mesh_calls+=1;owned={};chunkfaces=set()
  for g in mesh['groups']:
   for q in g['quads']:
    _,insideq=partition_quad(q,chunk['owned_min'],chunk['owned_max'])
    if insideq is None:continue
    owned.setdefault(g['material'],[]).append(insideq);surface.setdefault(g['material'],[]).append(insideq)
    for f in faces(insideq,g['material']):duplicates+=int(f in allfaces);assert f not in chunkfaces;chunkfaces.add(f);allfaces.add(f)
  assert chunkfaces==expected_faces(actual,chunk['owned_min'],chunk['owned_max'])
  for p,m in actual.items():
   if inside(p,chunk['owned_min'],chunk['owned_max']):assert p not in ownedcells;ownedcells[p]=m
  cr=save(f"compiled/{chunk['id']}.json.gz",c);rr=save(f"mesh_cache/{chunk['id']}.json.gz",{'groups':[{'material':m,'quads':qs} for m,qs in sorted(owned.items())],'quad_count':sum(len(qs) for qs in owned.values()),'owned_bounds_native':master['metadata']['owned_bounds_native'],'halo_bounds_native':master['metadata']['halo_bounds_native'],'halo_material_payload_hash':c['payload_hash'],'source_master':mr,'common_mesher':ref(Path(render_data.mesh.__file__))})
  rec={'id':chunk['id'],'master':mr,'compiled':cr,'cache':rr,'owned_bounds_native':master['metadata']['owned_bounds_native'],'halo_bounds_native':master['metadata']['halo_bounds_native'],'common_cells_with_halo':len(actual),'changed_material_cells_with_halo':len(changed),'owned_surface_cells':sum(inside(p,chunk['owned_min'],chunk['owned_max']) for p in actual),'owned_quads':sum(len(qs) for qs in owned.values()),'unit_faces':len(chunkfaces),'sample_repeat_exact':True,'geometry_occupancy_identical':True,'seconds':time.monotonic()-t};records.append(rec);print(json.dumps(rec),flush=True)
  del c,master,mesh,actual,before,expect
 assert len(ownedcells)==5184 and duplicates==0
 halo_lo=[v-1 for v in LOW];halo_hi=[v+1 for v in HIGH];global_expected=expected(a,crop,labels,halo_lo,halo_hi);assert allfaces==expected_faces(global_expected,LOW,HIGH)
 assert len(allfaces)==5184,'Expected exactly one existing outward BACK face per source pixel'
 # Actual raster mutation, keeping semantic classification fixed: one color changes,
 # one common native cell changes material, occupancy is exactly identical.
 sx,sy=1200,255;changed_crop=crop.copy();oldrgb=crop[sy-216,sx-1168].tolist();changed_crop[sy-216,sx-1168]=[13,29,36];ml=classify(changed_crop);assert np.array_equal(ml,labels)
 point=(1279-sx,495-sy,-148);chunk=next(ch for ch in CHUNKS if inside(point,ch['owned_min'],ch['owned_max']));mutmaster=make_master(chunk,a,changed_crop,ml);mutcompiled=compile_master(mutmaster);sample_calls+=1;mutmap=cellmap(mutcompiled);original=cellmap(read(O/f"compiled/{chunk['id']}.json.gz"));assert set(mutmap)==set(original);delta={p for p in original if original[p]!=mutmap[p]};assert delta=={point}
 mutation=save('source_color_mutation.json',{'source_xy':[sx,sy],'before_rgb':oldrgb,'after_rgb':[13,29,36],'actual_original_raster_mutated_in_memory':True,'semantic_masks_identical':True,'changed_common_material_cell':point,'changed_cells':len(delta),'geometry_occupancy_identical':True,'before_material':original[point],'after_material':mutmap[point],'original_source_unchanged':sha(SOURCE)==SOURCE_SHA,'before_payload_hash':read(O/f"compiled/{chunk['id']}.json.gz")['payload_hash'],'after_payload_hash':mutcompiled['payload_hash']})
 surface_ref=save('owned_surface.json.gz',{'groups':[{'material':m,'quads':qs} for m,qs in sorted(surface.items())],'quad_count':sum(len(qs) for qs in surface.values()),'owned_bounds_native':{'min':LOW,'max':HIGH},'source_materials':palette})
 assignments_ref=save('source_assignments.json.gz',{'accepted_cells':[{'xyz':p,'material':m,'rgb':palette[m],'source_xy':[1279-p[0],495-p[1]],'source_label':int(labels[495-p[1]-216,1279-p[0]-1168])} for p,m in sorted(assignment.items())],'count':4156,'all_rgb_exact':True})
 report={'schema':'riverstone.native_facade.common_exact_rgb_proof.v1','status':'TECHNICAL_PASS_PENDING_INTEGRATED_AUDIT','base_render':ref(BASE),'source_raster':raster_ref,'accepted_source_assignments':assignments_ref,'owned_surface':surface_ref,'chunks':records,'accepted_source_pixels':4156,'unresolved_preserved_pixels':1028,'native_source_unique_rgb_all':4233,'native_source_unique_rgb_accepted':3345,'exact_rgb_material_data':True,'surface_pitch_m':P,'body_volume_pitch_m':.125,'occupancy_changed_cells':0,'owned_face_geometry_changed':False,'source_color_mutation':mutation,'unit_faces':len(allfaces),'duplicate_faces':duplicates,'sampling_calls':sample_calls,'common_mesher_calls':mesh_calls,'new_roof_compilation_calls':0,'whole_volume_upsampled':False,'common_core':ref(Path(core.__file__)),'common_mesher':ref(Path(render_data.mesh.__file__)),'common_exporter':ref(Path(render_data.__file__)),'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'production_gate_open':False,'actual_six_view_gate':'PENDING_PARENT'}
 save('build_report.json',report);print(json.dumps({k:v for k,v in report.items() if k!='chunks'}),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException as e:save('failed_build_case.json',{'error':repr(e),'traceback':traceback.format_exc()});raise
