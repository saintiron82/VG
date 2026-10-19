#!/usr/bin/env python3
"""Bounded count-only source-normal extent audit. Never emits a sidecar."""
import os,sys
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from pathlib import Path
OUT=Path(__file__).resolve().parent;A=OUT.parent;R4=A/'roof_repair_r04';R3=A/'roof_repair_r03';R2=A/'roof_repair_r02'
sys.path.insert(0,str(R3/'normal_split_diagnostic_r01'))
from build_split_diagnostic import SourceTile,read,sha,stream_quads,qspec,rect,faces,np,resource,time,json,collections,gc
resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
P=.03125;PIN='45e9b206d2b126df7dd2ce878f70ada312a122a49c9a958098d08ae1406cb4d5'
ROOT=next(p for p in OUT.parents if(p/'voxel_character/common/core.py').exists())
def main():
 start=time.monotonic();cpu=time.process_time();render=R4/'roof_repaired.render.json.gz';assert sha(render)==PIN
 plans=[read(R2/'plan.json'),read(R3/'plan.json')];masters=[read(R2/'roof_patch.master.json.gz'),read(R3/'roof_patch.master.json.gz')]
 boxes={r['id']:r['bbox_px']for r in read(A/'roof_repair_r01/tile_measurement_r01/tile_regions.json')['regions']}
 source={};kind={};features=['unknown_current_union_owner'];fid_index={features[0]:0}
 def idx(fid):
  if fid not in fid_index:fid_index[fid]=len(features);features.append(fid)
  return fid_index[fid]
 for k,(pl,ma)in enumerate(zip(plans,masters)):
  ops={op['id']:op for c in ma['components']for op in c['operations']}
  for link in pl['tile_source_links']:
   fid=link['operation'];tile=SourceTile(ops[fid],link);source[idx(fid)]=tile;kind[fid]='old_measured'if k==0 else'recovered_interval'
   if k==0:assert link['source_bbox_px']==boxes[fid]
   else:
    b=link['source']['bbox_px'];o=[868,795,908,849];assert b[2]<=o[0]or b[0]>=o[2]or b[3]<=o[1]or b[1]>=o[3]
 assert len(source)==354
 u=np.load(R4/'upper_union_arrays.npz');mat=u['materials'];origin=u['origin_cell_xyz'].tolist();names=u['material_names'].tolist();mids={n:i for i,n in enumerate(names)}
 delta=np.load(R3/'delta_ownership_arrays.npz')['delta_class'];owners=np.zeros(mat.shape,np.uint16)
 pins={str(p.relative_to(ROOT)):sha(p)for p in[render,R4/'upper_union_arrays.npz',R3/'delta_ownership_arrays.npz',R2/'plan.json',R3/'plan.json',R2/'roof_patch.master.json.gz',R3/'roof_patch.master.json.gz']}
 assigned=collections.Counter();all_compiled=0;r4_owner_ids=set();r4_changed_cells=0
 for rec in read(R2/'compile.json')['chunks']:
  p=ROOT/rec['compiled']['path'];assert sha(p)==rec['compiled']['sha256'];pins[str(p.relative_to(ROOT))]=sha(p);d=read(p)
  for x,y,z,inst,part,m,fid in d['cells']:
   iy,ix,iz=y-origin[1],x-origin[0],z-origin[2]
   if delta[iy,ix,iz]==0 and mat[iy,ix,iz]==mids[m]:owners[iy,ix,iz]=idx(fid);assigned[kind.get(fid,'other')]+=1
  all_compiled+=len(d['cells']);del d;gc.collect()
 for rev in(R3,R4):
  rec=read(rev/'compile.json')['delta'];p=ROOT/rec['path'];assert sha(p)==rec['sha256'];pins[str(p.relative_to(ROOT))]=sha(p);d=read(p)
  for x,y,z,inst,part,m,fid in d['cells']:
   iy,ix,iz=y-origin[1],x-origin[0],z-origin[2]
   if mat[iy,ix,iz]!=mids[m]:continue
   if rev==R3 and not((part=='observed_shadow_tile_extensions'and delta[iy,ix,iz]==3)or(part=='foreground_resampled_gable_edge'and delta[iy,ix,iz]==2)):continue
   owners[iy,ix,iz]=idx(fid);assigned[kind.get(fid,'other')]+=1
   if rev==R4:r4_owner_ids.add(idx(fid));r4_changed_cells+=1;assert idx(fid)not in source
  all_compiled+=len(d['cells']);del d;gc.collect()
 assert r4_changed_cells==2609
 del delta;gc.collect();ownership_seconds=time.monotonic()-start
 def ix(c):return(c[1]-origin[1],c[0]-origin[0],c[2]-origin[2])
 import zlib
 patchzip=zlib.compressobj(9,zlib.DEFLATED,31);splitzip=zlib.compressobj(9,zlib.DEFLATED,31);zipbytes=[0,0]
 def zipfeed(which,text):zipbytes[which]+=len((patchzip if which==0 else splitzip).compress(text.encode()))
 total=collections.Counter();per=collections.defaultdict(collections.Counter);skips=collections.Counter();meta={};groupcounts=collections.Counter();cardinal_reasons=collections.Counter();unsupported_owners=collections.Counter();classified=0;cutoff=False;piece_max_bytes=patch_max_bytes=0
 # The exact existing whole-quad then unit-face classifier is reused. Only one
 # quad's labels exist at a time. No sidecar object or file is constructed.
 for gi,qi,m,q in stream_quads(render,meta):
  total['all_render_quads']+=1
  if not m.startswith('top_tile_'):continue
  total['top_material_quads']+=1;sp=qspec(q);lo,hi,axis,sign,u,v=sp;fs=list(faces(sp));oset={int(owners[ix(c)])for a,b,c in fs};selected=oset.intersection(source)
  total['top_material_unit_faces']+=len(fs)
  total['R4_changed_owner_exterior_unit_faces']+=sum(int(owners[ix(c)])in r4_owner_ids for a,b,c in fs)
  if not selected:continue
  total['source_owned_candidate_quads']+=1;total['source_candidate_quad_unit_faces']+=len(fs)
  for a,b,c in fs:
   oid=int(owners[ix(c)]);fid=features[oid]
   if oid in source:per[fid]['candidate_unit_faces']+=1;groupcounts[kind[fid]+'_candidate_unit_faces']+=1
  if time.process_time()-cpu>25:
   cutoff=True;continue
  for a,b,c in fs:
   nc=list(c);nc[axis]+=sign;assert mat[ix(c)]==mids[m]and mat[ix(nc)]<0
  total['classified_candidate_quads']+=1;total['classified_candidate_quad_unit_faces']+=len(fs)
  if len(oset)==1:
   oid=next(iter(oset));res,why=source[oid].classify(q,[c for a,b,c in fs],axis,sign)
   if res:
    n,seg=res;assert abs(sum(x*x for x in n)-1)<1e-9 and n[axis]*sign>0;fid=features[oid];total['complete_quad_patches']+=1;total['complete_patch_unit_faces']+=len(fs);per[fid]['treated_unit_faces']+=len(fs);per[fid]['patches']+=1
    # Exact compact payload byte count only; discarded immediately.
    patch={'group_index':gi,'quad_index':qi,'normals':[[round(t,10)for t in n]for _ in range(4)],'source_tile_id':fid,'classification':'analytic_top_staircase'}
    encoded=json.dumps(patch,separators=(',',':'),allow_nan=False);zipfeed(0,encoded+',');size=len(encoded);total['patch_payload_bytes']+=size;patch_max_bytes=max(patch_max_bytes,size);continue
  else:why='mixed_or_unproven_tile_ownership'
  labels={};safe=0;cn=[0,0,0];cn[axis]=sign
  for a,b,c in fs:
   oid=int(owners[ix(c)]);res=None;fid=features[oid];reason='non_source_owner'
   if oid in source:res,reason=source[oid].classify(rect(q,sp,a,b,a+1,b+1),[c],axis,sign)
   if res is None:
    label=(fid,'preserved_cardinal',tuple(cn));cardinal_reasons[reason]+=1
    if oid not in source:unsupported_owners['R4_recolor_box'if oid in r4_owner_ids else('backing_support'if fid.startswith('support_')else'other_or_unknown')]+=1
   else:
    n,seg=res;label=(fid,'analytic_top_staircase',tuple(round(t,10)for t in n));safe+=1;per[fid]['treated_unit_faces']+=1
   labels[a,b]=label
  if not safe:
   total['untouched_source_candidate_quads']+=1;skips[why]+=1;continue
  used=set();pieces=0;safe_rects=0;piecebytes=0
  zipfeed(1,json.dumps({'group_index':gi,'quad_index':qi,'material':m,'quads':[]},separators=(',',':'))[:-2])
  for a,b,c in fs:
   if(a,b)in used:continue
   label=labels[a,b];b1=b+1
   while b1<hi[v]and(a,b1)not in used and labels[a,b1]==label:b1+=1
   a1=a+1
   while a1<hi[u]and all((a1,x)not in used and labels[a1,x]==label for x in range(b,b1)):a1+=1
   footprint={(x,y)for x in range(a,a1)for y in range(b,b1)};assert not used.intersection(footprint);used.update(footprint);fid,cl,n=label;assert abs(sum(x*x for x in n)-1)<1e-9 and n[axis]*sign>0;pieces+=1;safe_rects+=cl=='analytic_top_staircase'
   corners=rect(q,sp,a,b,a1,b1);ps=qspec(corners);assert ps[2:]==sp[2:]and ps[0][axis]==lo[axis]and ps[0][u]==a and ps[1][u]==a1 and ps[0][v]==b and ps[1][v]==b1
   piece={'corners':corners,'normals':[list(n)for _ in range(4)],'source_tile_id':fid,'classification':cl}
   encoded=json.dumps(piece,separators=(',',':'),allow_nan=False);zipfeed(1,encoded+',');sz=len(encoded);piecebytes+=sz;piece_max_bytes=max(piece_max_bytes,sz)
  assert len(used)==len(fs);zipfeed(1,']},')
  total['split_original_quads']+=1;total['new_subquads']+=pieces;total['new_analytic_subquads']+=safe_rects;total['new_preserved_cardinal_subquads']+=pieces-safe_rects;total['newly_treated_unit_faces']+=safe;total['preserved_unit_faces_inside_splits']+=len(fs)-safe
  shell={'group_index':gi,'quad_index':qi,'material':m,'quads':[]};total['split_payload_bytes']+=len(json.dumps(shell,separators=(',',':')))+piecebytes+max(0,pieces-1)
 total['total_treated_unit_faces']=total['complete_patch_unit_faces']+total['newly_treated_unit_faces'];total['quad_delta']=total['new_subquads']-total['split_original_quads'];total['unindexed_triangle_vertex_delta']=total['quad_delta']*6
 total['arraymesh_position_normal_float32_extra_bytes']=total['unindexed_triangle_vertex_delta']*24
 total['arraymesh_position_normal_color_float32_extra_bytes']=total['unindexed_triangle_vertex_delta']*40
 # Fixed envelope copied exactly from validated schema. No patches/splits retained.
 shell={'schema':'riverstone.roof.normal_split_sidecar.v1','render_sha256':PIN,'patches':[],'splits':[],'diagnostic_only':True,'production_gate_open':False,'geometry_invariant':'exact coplanar area-preserving lattice partition; vertex/index representation changes; no displacement','unchanged_materials_sha256':__import__('hashlib').sha256(json.dumps(meta['materials'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'grid_pitch':P}
 total['prospective_compact_sidecar_bytes']=len(json.dumps(shell,separators=(',',':'),allow_nan=False))+1+total['patch_payload_bytes']+max(0,total['complete_quad_patches']-1)+total['split_payload_bytes']+max(0,total['split_original_quads']-1)
 zipbytes[0]+=len(patchzip.flush());zipbytes[1]+=len(splitzip.flush());total['gzip_level9_separate_section_payload_estimate_bytes']=sum(zipbytes)
 report={'status':'PARTIAL_CPU_CAPPED_COUNT_ONLY'if cutoff else'EXACT_COUNT_ONLY_NO_SIDECAR_WRITTEN','render_sha256':PIN,'limits':{'AS_mib':256,'CPU_seconds':30,'classification_soft_cpu_seconds':25},'source_counts':dict(collections.Counter(kind.values())),'structurally_supported_features':len(source),'features_with_exterior_candidate_faces':len(per),'features_with_treated_faces':sum(p['treated_unit_faces']>0 for p in per.values()),'cached_compiled_rows_scanned':all_compiled,'ownership_assigned_counts':dict(assigned),'totals':dict(total),'group_candidate_counts':dict(groupcounts),'group_treated_counts':{k:sum(p['treated_unit_faces']for fid,p in per.items()if kind[fid]==k)for k in('old_measured','recovered_interval')},'untreated_source_ids':[features[i]for i in source if per[features[i]]['treated_unit_faces']==0],'per_source':dict(per),'skip_counts_quad_level':dict(skips),'preserved_candidate_unit_face_reasons':dict(cardinal_reasons),'preserved_non_source_unit_face_owners_inside_candidate_quads':dict(unsupported_owners),'R4_recolor_cells_proven_non_source':r4_changed_cells,'R4_recolor_cells_admitted_to_tile_source_set':0,'piece_max_payload_bytes':piece_max_bytes,'patch_max_payload_bytes':patch_max_bytes,'ownership_elapsed_seconds':ownership_seconds,'elapsed_seconds':time.monotonic()-start,'CPU_seconds':time.process_time()-cpu,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_pins':pins,'gzip_estimate_method':'Two count-only gzip streams for patch payload sequence and split payload sequence, plus separately excluded fixed envelope; no compressed artifact retained. This is a representative storage estimate, not the exact one-member whole-sidecar gzip byte count.', 'sidecars_written':0,'sampler_calls':0,'compiler_calls':0,'mesher_calls':0,'GUI_calls':0,'classification_support_caveat':'Conditional source-appearance intervals plus unchanged explicit barrel-profile/height prior; not observed 3D normals or globally registered geometry.'}
 assert sha(render)==PIN
 report['all_recorded_source_pins_unchanged']=all(sha(ROOT/path)==digest for path,digest in pins.items())
 assert report['all_recorded_source_pins_unchanged']
 report['actual_checks']={'current_source_owner_material_and_exact_exterior_all_candidate_unit_faces':True,'all_354_source_intervals_have_nonzero_eligible_faces':not cutoff and report['features_with_treated_faces']==354,'every_counted_split_is_same_plane_winding_and_exact_disjoint_integer_cover':True,'all_counted_patch_and_piece_normals_unit_outward':True,'complete_sidecar_constructed_or_roundtripped':False,'adapter_load_exercised':False,'new_negative_fixtures_run':False,'visual_or_production_acceptance':False}
 assert cutoff or sum(cardinal_reasons.values())==total['source_candidate_quad_unit_faces']-total['total_treated_unit_faces']
 (OUT/'counts.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in('source_pins','per_source')},indent=2))
if __name__=='__main__':main()
