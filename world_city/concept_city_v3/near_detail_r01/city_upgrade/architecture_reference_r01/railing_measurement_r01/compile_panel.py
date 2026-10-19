"""Compile only the tiny positive-evidence panel and actual raster-edit regression."""
import copy,gzip,hashlib,json,resource,sys,time
from pathlib import Path
import numpy as np
from PIL import Image
import measure_panel as m
from scipy.ndimage import label
ROOT,O=m.ROOT,m.O;core=m.core;from voxel_character.common import render_data
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.resolve().relative_to(ROOT)),'sha256':sha(p)}
def save(p,o):
 assert not p.exists();b=json.dumps(o,separators=(',',':'),allow_nan=False).encode();p.write_bytes(gzip.compress(b,mtime=0) if p.suffix=='.gz' else b)
start=time.monotonic();master=json.loads(gzip.decompress((O/'railing_positive.master.json.gz').read_bytes()));data=np.load(O/'pixel_masks.npz');labels=data['labels'];crop=data['source_rgb'];pal=data['palette'];t=time.monotonic();c=core.compile_master(master,{'pitch':m.PITCH},max_candidate_cells=10000,max_output_cells=10000);sample=time.monotonic()-t;t=time.monotonic();r=render_data.make_render_data(c);mesh=time.monotonic()-t
actual={tuple(v[:3]) for v in c['cells']};expected={(152+x-256,496-(250+y)-1,z) for y,x in np.argwhere(labels==1) for z in (158,159)};assert actual==expected;holes={(152+x-256,496-(250+y)-1,z) for y,x in np.argwhere(labels==2) for z in (158,159)};assert not actual&holes
# Independently mutate the original raster, rerun the same extraction function,
# then compile those resulting runs through the original common core.
image=np.asarray(Image.open(m.P/'generated_candidate_r03.png').convert('RGB'));changed=image.copy();contract=json.loads((O/'source_contract.json').read_text());x,y=contract['original_raster_mutation_test']['source_pixel_xy'];changed[y,x]=[255,0,255];mutcrop=changed[250:298,152:216];mutlabels,_=m.classify(mutcrop);mutmaster=m.make_source(mutcrop,mutlabels,pal);cm=core.compile_master(mutmaster,{'pitch':m.PITCH},max_candidate_cells=10000,max_output_cells=10000);mutactual={tuple(v[:3]) for v in cm['cells']};diff=actual^mutactual;assert len(diff)==2 and len(actual)-len(mutactual)==2;repeat=core.compile_master(master,{'pitch':m.PITCH},max_candidate_cells=10000,max_output_cells=10000);assert repeat['cells']==c['cells'] and repeat['payload_hash']==c['payload_hash']
# Verify material/winding domains of every tiny-render unit face.
face_actual=set();duplicates=0
for g in r['groups']:
 for q in g['quads']:
  grid=np.rint(np.array(q)/m.PITCH).astype(int);normal=np.cross(grid[1]-grid[0],grid[2]-grid[0]);axis=int(np.argmax(abs(normal)));sgn=1 if normal[axis]>0 else -1;other=[k for k in range(3) if k!=axis];lo=grid.min(0);hi=grid.max(0)
  for u in range(lo[other[0]],hi[other[0]]):
   for v in range(lo[other[1]],hi[other[1]]):
    pt=[0,0,0];pt[axis]=int(grid[0,axis])-(1 if sgn>0 else 0);pt[other[0]]=u;pt[other[1]]=v;face=(axis,sgn,*pt,g['material']);duplicates+=int(face in face_actual);face_actual.add(face)
face_expected=set()
for row in c['cells']:
 xyz=tuple(row[:3])
 for axis in range(3):
  for sgn in (-1,1):
   q=list(xyz);q[axis]+=sgn
   if tuple(q) not in actual:face_expected.add((axis,sgn,*xyz,row[5]))
assert duplicates==0 and face_actual==face_expected
r['provenance']={'diagnostic_only':True,'production_gate_open':False,'occupancy_scope':'positive wood lower bound only; omitted uncertainty is not certified aperture','source_contract':ref(O/'source_contract.json'),'master':ref(O/'railing_positive.master.json.gz'),'core':ref(Path(core.__file__)),'renderer':ref(Path(render_data.__file__)),'mesher':ref(Path(render_data.mesh.__file__)),'driver':ref(Path(__file__))};save(O/'railing_positive.compiled.json.gz',c);save(O/'railing_positive.render.json.gz',r)
cc,n=label(labels==1);counts=np.bincount(cc.ravel())[1:].tolist();report={'schema':'riverstone.image_railing.common_proof.v1','technical_tests_pass':True,'production_gate_open':False,'diagnostic_only':True,'render':ref(O/'railing_positive.render.json.gz'),'compiled':ref(O/'railing_positive.compiled.json.gz'),'source_contract':ref(O/'source_contract.json'),'core':ref(Path(core.__file__)),'driver':ref(Path(__file__)),'cell_count':len(actual),'quad_count':r['quad_count'],'bounds':r['bounds'],'pitch_m':m.PITCH,'axes':{'up':'+Y','front':'+Z','right':'+X'},'source_raster_mutation':{'source_xy':[x,y],'replacement_rgb':[255,0,255],'changed_common_cells':sorted([list(v) for v in diff]),'changed_common_cell_count':len(diff),'removed_common_cell_count':2,'original_image_unchanged':sha(m.P/'generated_candidate_r03.png')==contract['source_image']['sha256'],'in_memory_mutated_raster_sha256':hashlib.sha256(changed.tobytes()).hexdigest()},'tests':{'compiled_exact_positive_pixels_times2':True,'observed_aperture86cells_empty':len(holes)==86 and not bool(actual&holes),'same_input_exact_common_cells_payload':True,'actual_original_pixel_edit_changes_common_cells':True,'external_material_faces_exact':True,'duplicate_faces_zero':True,'world_position_from_source_affine_exact':True},'unit_faces':len(face_expected),'duplicate_faces':duplicates,'positive_2d_connected_component_count':n,'positive_2d_component_pixel_counts':counts,'structure_limit':'Lower-bound evidence only. Shadow/occlusion/uncertainty can disconnect measured wood. No complete support, traversability or finished panel claim. Existing house, structural posts, backing wall and deck have not been compiled or changed.','sample_seconds':sample,'mesh_seconds':mesh,'total_seconds_including3core_calls_and_face_checks':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'sampling_calls':3,'max_candidate_budget_per_call':10000};save(O/'verification.json',report);print(json.dumps(report))
