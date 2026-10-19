"""Stream frozen whole house, replace bounded owner surface using common mesh."""
from repair_common import *
import time,traceback
def run():
 start=time.monotonic();assert sha(BASE)==BASE_SHA;build=read(O/'build_report.json');patch=read(O/'owned_surface.json.gz');local=read(O/'local_union.compiled.json.gz');local_cells={tuple(r[:3]):r[5] for r in local['cells']};surface={g['material']:g['quads'] for g in patch['groups']};materials=local['materials'];del local
 target=O/'gallery_repaired.render.json.gz';assert not target.exists();temporary=target.with_name(target.name+'.pending');assert not temporary.exists()
 meta={};roof_base={};roof_after={};group_counts=[];current=None;written=0;kept=0;removed=0;partial=0;outside_fragments=0;old_owned=set();new_owned=set();duplicates=0;outside_exact_checks=0;names=[]
 with temporary.open('xb') as raw:
  with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as out:
   def emit(v):out.write(json.dumps(v,separators=(',',':'),allow_nan=False).encode())
   def write_q(q):
    nonlocal written,group_count,first_q
    if not first_q:out.write(b',')
    first_q=False;emit(q);written+=1;group_count+=1
   def close_group(mat):
    nonlocal duplicates
    for q in surface.pop(mat,[]):
     write_q(q)
     for f in faces(q,mat):duplicates+=int(f in new_owned);new_owned.add(f)
    out.write(b']}');group_counts.append(group_count)
   out.write(b'{"groups":[')
   for gi,mat,qi,q in stream_render(BASE,meta):
    if gi!=current:
     if current is not None:close_group(names[-1]);out.write(b',')
     current=gi;names.append(mat);out.write(b'{"material":');emit(mat);out.write(b',"quads":[');first_q=True;group_count=0
     if gi in range(18,24):roof_base[gi]=hash_group_init(mat);roof_after[gi]=hash_group_init(mat)
    if gi in roof_base:hash_quad(roof_base[gi],q)
    outside,inside=partition_quad(q)
    if inside is None:kept+=1;write_q(q)
    else:
     removed+=1;partial+=int(bool(outside));outside_fragments+=len(outside)
     original=set(faces(q,mat));removed_faces=set(faces(inside,mat));fragments=set()
     for fq in outside:
      fs=set(faces(fq,mat));assert not fragments&fs;fragments|=fs;write_q(fq)
     assert original==fragments|removed_faces and not fragments&removed_faces;outside_exact_checks+=1
     assert not old_owned&removed_faces;old_owned|=removed_faces
    if gi in roof_after:
     assert inside is None and not surface.get(mat),'Frozen roof group would change';hash_quad(roof_after[gi],q)
   close_group(names[-1])
   original_names=list(names)
   for mat in sorted(surface):
    assert mat not in names;out.write(b',');out.write(b'{"material":');emit(mat);out.write(b',"quads":[');first_q=True;group_count=0
    for q in surface[mat]:
     write_q(q)
     for f in faces(q,mat):duplicates+=int(f in new_owned);new_owned.add(f)
    out.write(b']}');names.append(mat);group_counts.append(group_count)
   out.write(b']')
   assert original_names==meta.pop('group_names') and len(original_names)>23
   old_materials=dict(meta['materials']);assert all(materials.get(m,color)==color for m,color in old_materials.items())
   for m,color in materials.items():
    if m in old_materials:assert old_materials[m]==color
    else:meta['materials'][m]=color
   base_count=meta['cell_count'];a=baseline();roof=np.load(A/'roof_repair_r05/upper_union_arrays.npz');native_base=int((a[:76]>=0).sum())*64+int(roof['occupancy'].sum());count=native_base-build['removed_native_cells']+build['added_native_cells']
   meta.update(source_id='architecture_A_roof_r05_gallery_panel_r01',source_revision=1,master_hash=core.digest({'base':BASE_SHA,'local_master':build['master']['sha256']}),payload_hash=core.digest({'base':BASE_SHA,'owner_delta':build['delta']['sha256']}),cell_count=count,quad_count=written,geometry='Frozen whole-house common surface outside exact bounded owner box plus unchanged-common-mesher local union exterior. Mixed source resolutions represented on native lattice without whole-house resampling.',provenance={'base_render':ref(BASE),'local_master':build['master'],'local_compiled':build['compiled'],'owned_surface':build['owned_surface'],'delta':build['delta'],'composition_driver':ref(Path(__file__)),'diagnostic_only':True,'production_gate_open':False,'roof_geometry_frozen':True,'normal_sidecar':'Not embedded; original SHA-bound sidecar requires separately verified binding.','base_reported_mixed_resolution_cell_count':base_count,'candidate_count_policy':'Virtual native .03125m cell count, expanding preserved lower .125m cells by64 only arithmetically.'})
   for k,v in meta.items():out.write(b',');emit(k);out.write(b':');emit(v)
   out.write(b'}')
 expected=expected_faces(local_cells);assert duplicates==0 and new_owned==expected
 old_names=list(read(A/'foundation_repair_r01/foundation_revised.master.json.gz')['materials']);old_cells={p:old_names[m] for p,m in inherited_cells(baseline()).items()};assert old_owned==expected_faces(old_cells)
 assert all(roof_base[k].digest()==roof_after[k].digest() for k in roof_base)
 temporary.rename(target);assert sha(BASE)==BASE_SHA
 report={'schema':'riverstone.gallery_panel_repair.composition.v1','status':'TECHNICAL_PASS_PENDING_ACTUAL_VIEWS','render':ref(target),'base':ref(BASE),'quad_count':written,'original_quad_count':kept+removed,'original_quads_retained_exact':kept,'original_quads_replaced_or_clipped':removed,'partially_clipped_original_quads':partial,'outside_fragments_retained':outside_fragments,'partial_face_exact_partition_tests':outside_exact_checks,'old_owner_native_faces':len(old_owned),'new_owner_native_faces':len(new_owned),'missing_extra_or_duplicate_local_faces':0,'group_names':names,'group_quad_counts':group_counts,'original_group_order_preserved':True,'new_groups_appended':names[len(original_names):],'roof_group_hash_format':'SHA256 compact JSON material object + newline, then each unchanged compact JSON quad + newline; order-sensitive.','frozen_roof_groups':{str(k):{'material':names[k],'before_group_material_quad_array_sha256':roof_base[k].hexdigest(),'after_group_material_quad_array_sha256':roof_after[k].hexdigest(),'unchanged':True} for k in roof_base},'all_original_palette_entries_unchanged':True,'new_palette_entries':{m:c for m,c in meta['materials'].items() if m not in old_materials},'common_mesher_calls_in_composition':0,'roof_cache_calls':0,'whole_house_resampled':False,'source_files_unchanged':True,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_six_view_and_oblique':'PENDING_PARENT','production_gate_open':False}
 save('composition.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException as e:
  save('failed_composition_case.json',{'error':repr(e),'traceback':traceback.format_exc()});raise
