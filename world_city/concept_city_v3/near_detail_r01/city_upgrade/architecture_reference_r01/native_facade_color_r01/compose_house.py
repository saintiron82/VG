"""Keep original geometry; replace only source-bound BACK surface materials."""
from native_common import *
import traceback
def run():
 started=time.monotonic();assert sha(BASE)==BASE_SHA;build=read(O/'build_report.json');patch=read(O/'owned_surface.json.gz');surface={g['material']:g['quads'] for g in patch['groups']};palette=patch['source_materials'];del patch
 target=O/'native_facade_exact_rgb.render.json.gz';tmp=target.with_name(target.name+'.pending');assert not target.exists() and not tmp.exists();meta={};names=[];counts=[];current=None;quad_count=0;kept=removed=partials=fragments=0;oldfaces=set();newfaces=set();duplicates=0;roof_before={};roof_after={}
 with tmp.open('xb') as raw:
  with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as out:
   def emit(v):out.write(json.dumps(v,separators=(',',':'),allow_nan=False).encode())
   def write_q(q):
    nonlocal quad_count,group_count,first
    if not first:out.write(b',')
    first=False;emit(q);quad_count+=1;group_count+=1
   def add_owned(mat,qs):
    nonlocal duplicates
    for q in qs:
     write_q(q)
     for f in faces(q,mat):duplicates+=int(f in newfaces);newfaces.add(f)
   def close_group(mat):add_owned(mat,surface.pop(mat,[]));out.write(b']}');counts.append(group_count)
   out.write(b'{"groups":[')
   for gi,mat,qi,q in stream_render(BASE,meta):
    if gi!=current:
     if current is not None:close_group(names[-1]);out.write(b',')
     current=gi;names.append(mat);out.write(b'{"material":');emit(mat);out.write(b',"quads":[');first=True;group_count=0
     if mat.startswith('top_tile_'):roof_before[gi]=hash_group_init(mat);roof_after[gi]=hash_group_init(mat)
    if gi in roof_before:hash_quad(roof_before[gi],q)
    outside,insideq=partition_quad(q,LOW,HIGH)
    if insideq is None:write_q(q);kept+=1
    else:
     removed+=1;partials+=bool(outside);fragments+=len(outside);original=set(faces(q,mat));old=set(faces(insideq,mat));retained=set()
     for fq in outside:
      ff=set(faces(fq,mat));assert not retained&ff;retained|=ff;write_q(fq)
     assert old|retained==original and not old&retained;assert not oldfaces&old;oldfaces|=old
    if gi in roof_after:assert insideq is None and not surface.get(mat);hash_quad(roof_after[gi],q)
   close_group(names[-1]);original_names=list(names);assert names==meta.pop('group_names')
   for mat in sorted(surface):
    assert mat not in names;out.write(b',{"material":');emit(mat);out.write(b',"quads":[');first=True;group_count=0;add_owned(mat,surface[mat]);out.write(b']}');names.append(mat);counts.append(group_count)
   out.write(b']');oldpalette=dict(meta['materials']);assert oldpalette==base_materials()
   for m,color in palette.items():
    if m in oldpalette:assert oldpalette[m]==color
    else:meta['materials'][m]=color
   base_cells=meta['cell_count'];meta.update(source_id='architecture_A_native_facade_exact_rgb_r01',source_revision=1,master_hash=core.digest({'base':BASE_SHA,'chunk_masters':[r['master']['sha256'] for r in build['chunks']]}),payload_hash=core.digest({'base':BASE_SHA,'assignments':build['accepted_source_assignments']['sha256']}),quad_count=quad_count,geometry='Identical solid occupancy and exterior geometry to frozen r05+gallery union. Only source-backed BACK outermost native material cells differ; geometry uses unchanged common mesher.',provenance={'base_render':ref(BASE),'source_raster':build['source_raster'],'chunk_build':ref(O/'build_report.json'),'owned_surface':build['owned_surface'],'source_assignments':build['accepted_source_assignments'],'composition_driver':ref(Path(__file__)),'exact_source_rgb_data':True,'all_original_geometry_preserved':True,'roof_and_gallery_retained':True,'native_surface_pitch_m':P,'preserved_body_volume_pitch_m':.125,'normal_sidecar':'Separate explicit binding required for unchanged roof groups; no sidecar edited.','runtime_batching':'Not implemented here. Source material count is not reduced for draw-call convenience.','diagnostic_only':True,'production_gate_open':False})
   assert meta['cell_count']==base_cells
   for k,v in meta.items():out.write(b',');emit(k);out.write(b':');emit(v)
   out.write(b'}')
 assert duplicates==0;assert {f[:-1] for f in oldfaces}=={f[:-1] for f in newfaces};assert len(oldfaces)==len(newfaces)==5184
 assert all(roof_before[k].digest()==roof_after[k].digest() for k in roof_before);tmp.rename(target);assert sha(BASE)==BASE_SHA
 report={'schema':'riverstone.native_facade.exact_rgb_composition.v1','status':'TECHNICAL_PASS_PENDING_INDEPENDENT_AUDIT','render':ref(target),'base_render':ref(BASE),'original_quads':kept+removed,'new_quads':quad_count,'original_quads_kept_exact':kept,'original_quads_clipped_or_replaced':removed,'partial_originals':partials,'retained_outside_fragments':fragments,'old_owner_faces':len(oldfaces),'new_owner_faces':len(newfaces),'owner_exterior_geometry_identical':True,'original_cell_count_preserved':base_cells,'original_material_entries_unchanged':True,'new_material_entries':len(meta['materials'])-len(oldpalette),'new_used_color_groups':len(names)-len(original_names),'group_names':names,'group_quad_counts':counts,'original_group_slots_retained':True,'frozen_roof_group_material_array_hashes':{str(k):{'material':names[k],'before':roof_before[k].hexdigest(),'after':roof_after[k].hexdigest(),'exact':True} for k in roof_before},'sampling_calls':0,'mesher_calls':0,'roof_cache_rebuilds':0,'elapsed_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_six_view_gate':'PENDING_PARENT','production_gate_open':False}
 save('composition.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('group_names','group_quad_counts')}),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException as e:save('failed_composition_case.json',{'error':repr(e),'traceback':traceback.format_exc()});raise
