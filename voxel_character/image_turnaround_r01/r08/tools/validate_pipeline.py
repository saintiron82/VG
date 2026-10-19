"""Independent reproducibility + real input-pixel perturbation regression."""
from pathlib import Path
import copy,json,numpy as np
from PIL import Image
from scipy import ndimage as ndi
from measured_cloth import ROOT,COMMON,sha,read,write,gzread,gzwrite,measure,build,geometry_from_measurement,compile_master,make_render_data,digest,budget

def run():
 contract=ROOT/'data/region_contract.json';c=read(contract);m=read(ROOT/'generated/measured/measurements.json');master=gzread(ROOT/'generated/region/master.json.gz');compiled=gzread(ROOT/'generated/region/compiled.cells.json.gz');render=gzread(ROOT/'generated/region/region.render.json.gz')
 # Mandatory input and missing-section gates, with no output fallback.
 missing_pass=False
 try:build(ROOT/'evidence/intentionally_missing_measurement.json',ROOT/'generated/invalid_missing')
 except ValueError as e:missing_pass='mandatory' in str(e)
 assert missing_pass
 rebuilt=compile_master(master,{'pitch':c['compiler']['pitch_m']},max_candidate_cells=c['compiler']['max_candidates'],max_output_cells=c['compiler']['max_cells'])
 assert rebuilt==compiled
 regenerated=make_render_data(rebuilt);regenerated['frame']=render['frame'];assert regenerated==render
 # Same input measurement is deterministic; write only small evidence, no duplicate image caches.
 repeat=measure(contract,m['source']['sheet_path'],ROOT/'generated/repeated_measurement')
 assert repeat['sections']==m['sections'] and repeat['views']==m['views']
 assert digest(geometry_from_measurement(repeat,c)[0])==digest(master['components'][0]['operations'])
 # Change actual source pixels at an observed left skirt edge. Do not change
 # annotation, generation constants, or any other view / body / hair pixels.
 source=Path(m['source']['sheet_path']);pixels=np.array(Image.open(source).convert('RGB'));original=pixels.copy();changed=[]
 for row in range(645,658):
  mask=np.load(m['mask_path'])['front'][row];xs=np.where(mask)[0];left=int(xs.min());right=left+32
  bg=np.median(np.concatenate([pixels[row,:8],pixels[row,652:660]],axis=0),axis=0).astype(np.uint8)
  pixels[row,left:right]=bg;changed.append({'row':row,'x_interval':[left,right]})
 mutant=ROOT/'evidence/violet_sheet_local_pixel_mutation.png';Image.fromarray(pixels).save(mutant)
 recipe={'parent_sha256':sha(source),'mutant_sha256':sha(mutant),'purpose':'regression fixture only, never a replacement reference','changed_region':'front skirt leftmost 32 pixels, rows 645..657 inclusive','changed_pixels':int(np.any(pixels!=original,2).sum()),'row_intervals':changed,'background_value':'source row edge median','annotation_changed':False}
 write(ROOT/'evidence/pixel_mutation_recipe.json',recipe)
 mm=measure(contract,mutant,ROOT/'generated/mutated_measurement',recipe);mut_manifest=build(ROOT/'generated/mutated_measurement/measurements.json',ROOT/'generated/mutated_region');mut_master=gzread(ROOT/'generated/mutated_region/master.json.gz');mut_compiled=gzread(ROOT/'generated/mutated_region/compiled.cells.json.gz')
 changed_sections=[i for i,(a,b) in enumerate(zip(m['sections'],mm['sections'])) if a!=b];assert changed_sections
 # Sections outside rows hit by the image change must be exactly equal.
 expected=[i for i,s in enumerate(m['sections']) if 645<=s['samples']['front']['row_y']<=657]
 assert changed_sections==expected
 for a,b in zip(m['sections'],mm['sections']):assert a['samples']['side']==b['samples']['side'] and a['samples']['back']==b['samples']['back']
 aops=master['components'][0]['operations'];bops=mut_master['components'][0]['operations'];changed_ops=[i for i,(a,b) in enumerate(zip(aops,bops)) if a!=b]
 expected_rows=set(changed_sections)|{i-1 for i in changed_sections if i>0};changed_geometry_rows=sorted({int(aops[i]['id'].split('_')[1]) for i in changed_ops});assert set(changed_geometry_rows)<=expected_rows
 allowed_y=[m['sections'][min(expected_rows)]['y_m']-.05,m['sections'][max(expected_rows)+1]['y_m']+.05]
 aset={tuple(r[:3]) for r in compiled['cells']};bset={tuple(r[:3]) for r in mut_compiled['cells']};delta=aset^bset;assert delta
 world_y=[(p[1]+.5)*c['compiler']['pitch_m'] for p in delta];assert min(world_y)>=allowed_y[0] and max(world_y)<=allowed_y[1]
 ps=np.array(list(aset));lo=ps.min(0)-1;grid=np.zeros(tuple(ps.max(0)-lo+2),bool);grid[tuple((ps-lo).T)]=True;labels,n=ndi.label(grid);sizes=sorted(np.bincount(labels.ravel())[1:].tolist(),reverse=True)
 # Every operation vertex is generated from measured row support, with no arbitrary curves.
 report={'missing_measurement_rejected':missing_pass,'independent_common_recompile_exact':rebuilt==compiled,'independent_common_mesh_exact':regenerated==render,'same_pixels_same_measurements':repeat['sections']==m['sections'],'same_measurements_same_geometry':True,'original_source_unchanged':sha(source)==c['sheet_sha256'],'original_illustration_unchanged':sha(ROOT/c['original'])==c['original_sha256'],'pixel_mutation':{'input_changed_pixels':recipe['changed_pixels'],'changed_sections':changed_sections,'expected_changed_sections':expected,'changed_geometry_rows':changed_geometry_rows,'other_row_operations_exactly_unchanged':True,'other_view_measurements_exactly_unchanged':True,'changed_operations':len(changed_ops),'occupancy_delta_cells':len(delta),'cell_delta_y_m':[min(world_y),max(world_y)],'allowed_local_y_m':allowed_y,'locality_pass':True,'mutant_payload_hash':mut_compiled['payload_hash']},'structure':{'six_connected_components':int(n),'sizes_cells':sizes,'enclosed_empty_cells':int((ndi.binary_fill_holes(grid)&~grid).sum()),'boundary_status':'open-sided garment region with deliberately cropped ends; not a closed complete costume'},'input_provenance':{'source_sha256':sha(source),'contract_sha256':sha(contract),'measurement_sha256':sha(ROOT/'generated/measured/measurements.json'),'master_sha256':sha(ROOT/'generated/region/master.json.gz'),'compiled_sha256':sha(ROOT/'generated/region/compiled.cells.json.gz'),'compiler_sha256':sha(COMMON/'core.py'),'validator_sha256':sha(__file__)},'art_approved':False,'GPU_reviewed':False,'limitations':c['limits']}
 write(ROOT/'evidence/pipeline_regression.json',report);print(json.dumps(report));budget()
if __name__=='__main__':run()
