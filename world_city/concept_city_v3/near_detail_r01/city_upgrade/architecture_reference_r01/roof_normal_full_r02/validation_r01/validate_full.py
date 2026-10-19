#!/usr/bin/env python3
"""Independent, bounded validation of the actual emitted full-roof sidecar.

Only the frozen SourceTile classifier and streaming JSON reader are reused.
Neither author_full.py nor count_extent.py is imported. No sampler, mesher,
compiler, GUI, or input writes. Sidecar records are streamed, never expanded.
"""
import os, sys
os.environ['OPENBLAS_NUM_THREADS']='1'; os.environ['OMP_NUM_THREADS']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'; sys.dont_write_bytecode=True
from pathlib import Path
V=Path(__file__).resolve().parent; FULL=V.parent; A=FULL.parent
R2=A/'roof_repair_r02'; R3=A/'roof_repair_r03'; R4=A/'roof_repair_r04'; R5=A/'roof_repair_r05'
sys.path.insert(0,str(R3/'normal_diagnostic_r01'))
from derive_normal_diagnostic import SourceTile, JsonStream, stream_quads, read, sha, np, resource
import collections, copy, gc, gzip, hashlib, json, math, time, zipfile
ROOT=next(p for p in V.parents if (p/'voxel_character/common/core.py').exists())
P=.03125; PIN=json.loads((FULL/'render_pin.json').read_text())['render_sha256']
OLDPIN='c5354c21ca7a12589f6a8ee0bd73ca9046c120a43914b0502b1fc88d96c120ca'
OLD_SIDE_PIN='bec8bbef6319d193c01cd1d2e4acd689c377ca5796b8d86b0964ca20fe68f95e'
SCHEMA='riverstone.roof.normal_split_sidecar.v1'
SELECTED={f'right_{col:02d}_r{row:02d}' for col in (3,4,5) for row in (8,9,10,11)}

def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def spec(q,strict=False):
 if strict:
  assert isinstance(q,list) and len(q)==4,'four_corners'
  assert all(isinstance(c,list) and len(c)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in c) for c in q),'finite_corners'
  assert all(abs(x/P-round(x/P))<1e-9 for c in q for x in c),'off_grid'
 g=[tuple(round(x/P) for x in c) for c in q]
 lo=tuple(min(c[k] for c in g) for k in range(3)); hi=tuple(max(c[k] for c in g) for k in range(3)); fixed=[k for k in range(3) if lo[k]==hi[k]]
 assert len(fixed)==1,'noncardinal_or_degenerate'; axis=fixed[0]; u,v=[k for k in range(3) if k!=axis]
 n=cross(sub(g[1],g[0]),sub(g[2],g[0])); assert n[axis]!=0,'degenerate'; sign=1 if n[axis]>0 else -1
 if strict:
  assert len(set(g))==4 and all(c[u] in (lo[u],hi[u]) and c[v] in (lo[v],hi[v]) for c in g),'not_rectangle'
  assert all(sum(a[k]!=b[k] for k in range(3))==1 for a,b in zip(g,g[1:]+g[:1])),'not_perimeter'
  for ids in ((0,2,1),(0,3,2)):
   tn=cross(sub(g[ids[1]],g[ids[0]]),sub(g[ids[2]],g[ids[0]])); assert tn[axis]*sign<0,'godot_clockwise_winding'
 return lo,hi,axis,sign,u,v

def unit_faces(s):
 lo,hi,axis,sign,u,v=s
 for a in range(lo[u],hi[u]):
  for b in range(lo[v],hi[v]):
   c=[0,0,0]; c[axis]=lo[axis]-int(sign>0); c[u]=a; c[v]=b
   yield a,b,tuple(c)

def rectangle(q,s,a,b,aa,bb):
 lo,hi,axis,sign,u,v=s; out=[]
 for c in q:
  p=list(c); p[u]=(a if round(c[u]/P)==lo[u] else aa)*P; p[v]=(b if round(c[v]/P)==lo[v] else bb)*P; out.append(p)
 return out

def target(row):
 assert isinstance(row,dict),'record_object'
 gi,qi=row.get('group_index'),row.get('quad_index')
 assert type(gi) is int and type(qi) is int and gi>=0 and qi>=0,'index_range'
 return gi,qi

def ordered_target(last,row):
 at=target(row); assert last is None or last<at,'duplicate_or_unsorted_target'; return at

def cursor_check(key,pk,sk):
 assert pk is None or pk>=key,'index_range'
 assert sk is None or sk>=key,'index_range'
 assert pk!=sk or pk is None,'duplicate_target'

def records(path,section,meta):
 """Two independent bounded readers merge patches/splits against render order."""
 with gzip.open(path,'rt') as f:
  p=JsonStream(f); p.eat('{'); seen=set(); last=None
  while p.peek()!='}':
   key=p.value(); assert key not in seen,'duplicate_header'; seen.add(key); p.eat(':')
   if key in ('patches','splits'):
    p.eat('[')
    while p.peek()!=']':
     row=p.value()
     if key==section:
      last=ordered_target(last,row); yield row
     if p.peek()!=',':break
     p.eat(',')
    p.eat(']')
   else:meta[key]=p.value()
   if p.peek()!=',':break
   p.eat(',')
  p.eat('}'); assert p.peek()=='','trailing_json'; assert {'patches','splits'}<=seen,'missing_sections'

def header(m,palette):
 assert m.get('schema')==SCHEMA,'schema'; assert m.get('render_sha256')==PIN,'render_sha256'; assert m.get('grid_pitch')==P,'grid_pitch'
 assert m.get('unchanged_materials_sha256')==palette,'materials_hash'
 assert m.get('diagnostic_only') is True and m.get('production_gate_open') is False,'diagnostic_gate'
 assert m.get('geometry_invariant')=='exact coplanar area-preserving lattice partition; vertex/index representation changes; no displacement','geometry_contract'
 assert set(m)=={'schema','render_sha256','grid_pitch','unchanged_materials_sha256','diagnostic_only','production_gate_open','geometry_invariant'},'unexpected_header'

def normal_check(normals,s,expected):
 assert isinstance(normals,list) and len(normals)==4,'four_normals'
 for n in normals:
  assert isinstance(n,list) and len(n)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in n),'finite_normal'
  assert abs(sum(x*x for x in n)-1)<1e-9,'nonunit_normal'
  assert n[s[2]]*s[3]>0,'inward_normal'
  assert max(abs(x-y) for x,y in zip(n,expected))<1e-10,'wrong_normal'

def label_check(row,s,label):
 fid,cl,n,why=label
 assert row.get('source_tile_id')==fid,'wrong_source_owner'
 assert row.get('classification')==cl,'unsafe_classification'
 normal_check(row.get('normals'),s,n)

def validate_patch(row,q,label):
 assert set(row)=={'group_index','quad_index','normals','source_tile_id','classification'},'patch_fields'
 assert label[1]=='analytic_top_staircase','unsafe_complete_quad'
 label_check(row,spec(q,True),label)

def validate_split(row,material,q,labels):
 assert set(row)=={'group_index','quad_index','material','quads'},'split_fields'
 assert row['material']==material,'wrong_material'
 s=spec(q,True); lo,hi,axis,sign,u,v=s; covered=set(); safe=0
 assert isinstance(row['quads'],list) and row['quads'],'empty_split'
 for piece in row['quads']:
  assert set(piece)=={'corners','normals','source_tile_id','classification'},'piece_fields'
  c=piece['corners']; assert all(len(p)==3 and abs(p[axis]/P-lo[axis])<1e-9 for p in c),'wrong_plane'
  ns=spec(c,True); nl,nh,na,sg,nu,nv=ns
  assert na==axis and sg==sign,'winding'
  assert all(lo[k]<=nl[k]<=nh[k]<=hi[k] for k in range(3)),'outside_original'
  assert c==rectangle(q,s,nl[u],nl[v],nh[u],nh[v]),'changed_corner_order'
  for a,b,cell in unit_faces(ns):
   assert (a,b) not in covered,'overlap'; covered.add((a,b))
   label_check(piece,ns,labels[a,b]); safe+=labels[a,b][1]=='analytic_top_staircase'
 assert covered==set(labels),'gap'; assert safe>0,'unnecessary_split'
 return safe

def cell_rows(path):
 with gzip.open(path,'rt') as f:
  parser=JsonStream(f);parser.eat('{')
  while parser.peek()!='}':
   key=parser.value();parser.eat(':')
   if key=='cells':
    parser.eat('[')
    while parser.peek()!=']':
     yield parser.value()
     if parser.peek()!=',':break
     parser.eat(',')
    parser.eat(']')
   else:parser.value()
   if parser.peek()!=',':break
   parser.eat(',')
  parser.eat('}');assert parser.peek()==''

def build_source(pins):
 names=['unknown_current_union_owner']; ids={names[0]:0}; tiles={}; kinds={}
 def intern(fid):
  if fid not in ids:ids[fid]=len(names);names.append(fid)
  return ids[fid]
 boxes={r['id']:r['bbox_px'] for r in read(A/'roof_repair_r01/tile_measurement_r01/tile_regions.json')['regions']}
 for rev,kind in ((R2,'old_measured'),(R3,'recovered_interval')):
  mp=rev/'roof_patch.master.json.gz'; pp=rev/'plan.json'; pins[mp]=sha(mp); pins[pp]=sha(pp)
  ops={o['id']:o for c in read(mp)['components'] for o in c['operations']}
  for link in read(pp)['tile_source_links']:
   fid=link['operation']; oid=intern(fid); assert oid not in tiles,'duplicate_source'
   tiles[oid]=SourceTile(ops[fid],link); kinds[fid]=kind
   if rev==R2:assert link['source_bbox_px']==boxes[fid]
   else:
    b=link['source']['bbox_px']; assert b[2]<=868 or b[0]>=908 or b[3]<=795 or b[1]>=849,'occluded_source_interval'
 assert len(tiles)==354 and collections.Counter(kinds.values())=={'old_measured':339,'recovered_interval':15}
 up=R4/'upper_union_arrays.npz'; dp=R3/'delta_ownership_arrays.npz'; pins[up]=sha(up); pins[dp]=sha(dp)
 with np.load(up) as z:mat=z['materials']; origin=tuple(z['origin_cell_xyz']); mn=z['material_names'].tolist()
 mids={n:i for i,n in enumerate(mn)}
 with np.load(dp) as z:delta=z['delta_class']
 owners=np.zeros(mat.shape,np.uint16); rows=0; assigned=collections.Counter(); recolor=set(); rc=0; r4protected=set(); shadow={}
 def ix(c):return c[1]-origin[1],c[0]-origin[0],c[2]-origin[2]
 for rev in (R2,R3,R4):
  cp=rev/'compile.json'; pins[cp]=sha(cp); manifest=read(cp)
  recs=[r['compiled'] for r in manifest['chunks']] if rev==R2 else [manifest['delta']]
  for rec in recs:
   path=ROOT/rec['path']; pins[path]=sha(path); assert pins[path]==rec['sha256'],'compiled_hash'; d=read(path)
   for x,y,z,inst,part,m,fid in d['cells']:
    if rev==R3 and part=='observed_shadow_tile_extensions':shadow[x,y,z]=(m,fid)
    if rev==R4:r4protected.add((x,y,z))
    j=ix((x,y,z))
    if mat[j]!=mids[m]:continue
    if rev==R2 and delta[j]!=0:continue
    if rev==R3 and not ((part=='observed_shadow_tile_extensions' and delta[j]==3) or (part=='foreground_resampled_gable_edge' and delta[j]==2)):continue
    oid=intern(fid); owners[j]=oid; assigned[kinds.get(fid,'other')]+=1
    if rev==R4:recolor.add(oid);rc+=1;assert oid not in tiles,'recolor_source_owner'
   rows+=len(d['cells']);del d;gc.collect()
 assert rc==2609 and len(r4protected)==2609
 baseline=read(A/'roof_normal_full_r01/report.json')
 assert rows==baseline['cached_compiled_rows_scanned'] and dict(assigned)==baseline['ownership_assigned_counts'],'baseline_ownership_counts'
 # Independently verify exact source operation identity, including both crop cuts.
 rp=R5/'plan.json'; rm=R5/'roof_patch.master.json.gz'
 for path in [rp,rm,R5/'compile.json',R5/'delta_cells.json.gz',R5/'upper_union_arrays.npz',R5/'union_validation.json',A/'roof_normal_full_r01/report.json']:
  pins[path]=sha(path)
 plan=read(rp); cm={c['id']:c['operations'] for c in read(rm)['components']}
 assert len(cm)==354 and len(plan['source_tile_links'])==354
 for rev in (R2,R3):
  ops={o['id']:o for c in read(rev/'roof_patch.master.json.gz')['components'] for o in c['operations']}
  revnum=2 if rev==R2 else 3
  for link in plan['source_tile_links']:
   if link['source_revision']!=revnum:continue
   fid=link['source_feature']; assert fid in kinds
   expected=[ops[fid],ops[fid+'_crop_left'],ops[fid+'_crop_right']]
   assert cm[link['component']]==expected,'source_profile_identity'
 del cm,ops,plan;gc.collect()
 changes=read(R5/'delta_cells.json.gz')['cells']; change_by_xyz={tuple(r[:3]):r for r in changes}
 assert len(changes)==len(change_by_xyz)==18965,'duplicate_delta'
 # Isolated compiler rows are evidence only. Rebuild the accepted/deferred
 # decision independently before changing any material or source owner.
 accepted=set(); blocked=collections.Counter(); stable=0; isolated=0
 oldchunks=read(R2/'compile.json')['chunks']; newchunks=read(R5/'compile.json')['chunks']
 for oldrec,newrec in zip(oldchunks,newchunks):
  assert oldrec['owned_z_cells']==newrec['owned_z_cells']; z0,z1=newrec['owned_z_cells']
  oldtiles={};support={}
  for r in cell_rows(ROOT/oldrec['compiled']['path']):
   if r[4]=='measured_tile_regions':oldtiles[tuple(r[:3])]=tuple(r[5:])
   elif r[4]=='thin_roof_support':support[tuple(r[:3])]=r[5]
  oldtiles.update({xyz:r for xyz,r in shadow.items() if z0<=xyz[2]<z1})
  path=ROOT/newrec['compiled']['path'];pins[path]=sha(path);assert pins[path]==newrec['compiled']['sha256']
  newrows={}; rowcount=0
  for r in cell_rows(path):newrows[tuple(r[:3])]=r;rowcount+=1
  assert len(newrows)==rowcount;isolated+=rowcount
  for xyz,oldrow in oldtiles.items(): assert xyz in newrows and oldrow==tuple(newrows[xyz][5:]),'old_source_row_changed'
  for xyz,row in newrows.items():
   if xyz in oldtiles:stable+=1; assert xyz not in change_by_xyz,'existing_tile_delta';continue
   j=ix(xyz); prior=int(mat[j]); lab=int(delta[j]); reason=None
   if xyz in r4protected:reason='r04_TOP_material_owner'
   elif lab in (1,2):reason='r03_original_restoration_or_foreground'
   elif prior>=0 and not (xyz in support and mids[support[xyz]]==prior and lab==0):reason='other_preserved_source_owner'
   if reason:
    blocked[reason]+=1; assert xyz not in change_by_xyz,'protected_conflict_applied';continue
   assert xyz in change_by_xyz,'missing_eligible_delta'
   d=change_by_xyz[xyz]
   assert d[3]==prior and d[4]==mids[row[5]] and d[5]==row[6] and d[6]==('empty' if prior<0 else 'original_support'),'wrong_recorded_delta'
   assert xyz not in accepted;accepted.add(xyz)
  del newrows,oldtiles,support;gc.collect()
 assert isolated==189026 and stable==169726 and accepted==set(change_by_xyz)
 assert dict(blocked)=={'r03_original_restoration_or_foreground':172,'r04_TOP_material_owner':72,'other_preserved_source_owner':91}
 del delta,shadow;gc.collect()
 restored=collections.Counter()
 for x,y,z,old,new,fid,why in changes:
  j=ix((x,y,z));assert int(mat[j])==old and int(owners[j]) not in recolor and fid in kinds
  if why=='original_support':assert names[int(owners[j])].startswith('support_')
  else:assert why=='empty' and old<0 and int(owners[j])==0
  mat[j]=new;owners[j]=intern(fid);restored[kinds[fid]]+=1
 h=hashlib.sha256()
 with zipfile.ZipFile(R5/'upper_union_arrays.npz') as archive:
  with archive.open('materials.npy') as raw:
   version=np.lib.format.read_magic(raw); shape,fort,dtype=(np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0)(raw)
   assert shape==mat.shape and dtype==mat.dtype and not fort
   for block in iter(lambda:raw.read(65536),b''):h.update(block)
 assert h.hexdigest()==hashlib.sha256(memoryview(mat).cast('B')).hexdigest(),'delta_union_mismatch'
 info={'isolated_compiled_rows_checked':isolated,'existing_source_rows_preserved':stable,'applied_delta_cells':len(accepted),'deferred_protected_cells':sum(blocked.values()),'deferred_by_reason':dict(blocked),'restored_owner_counts':dict(restored),'source_operations_and_cuts_exact_original':True}
 del changes,change_by_xyz;gc.collect()
 return names,tiles,kinds,mat,mids,owners,ix,recolor,rows,assigned,accepted,info

def old_triples():
 old=R3/'normal_split_diagnostic_r01/normal_split_sidecar.json'; render=R3/'roof_repaired.render.json.gz'
 assert sha(old)==OLD_SIDE_PIN and sha(render)==OLDPIN
 d=read(old); patches={target(p):p for p in d['patches']}; splits={target(p):p for p in d['splits']}; out=set(); hit=set()
 for gi,qi,m,q in stream_quads(render,{}):
  k=gi,qi
  if k in patches:pieces=[dict(patches[k],corners=q)];hit.add(k)
  elif k in splits:pieces=splits[k]['quads'];hit.add(k)
  else:continue
  for piece in pieces:
   if piece['classification']!='analytic_top_staircase':continue
   fid=piece['source_tile_id'];assert fid in SELECTED;s=spec(piece['corners']);n=tuple(piece['normals'][0])
   for _,_,c in unit_faces(s):
    key=(s[2],s[3],c,fid,n);assert key not in out;out.add(key)
 assert hit==set(patches)|set(splits) and len(out)==3960
 return out

def main():
 start=time.monotonic(); cpu=time.process_time(); side=FULL/'normal_split_sidecar.json.gz'; render=R5/'roof_repaired.render.json.gz'
 assert sha(render)==PIN; sidehash=sha(side); pins={render:PIN,side:sidehash, R3/'normal_diagnostic_r01/derive_normal_diagnostic.py':sha(R3/'normal_diagnostic_r01/derive_normal_diagnostic.py')}
 for path in [R3/'normal_split_diagnostic_r01/normal_split_sidecar.json',R3/'roof_repaired.render.json.gz',A/'roof_repair_r01/tile_measurement_r01/tile_regions.json']:
  pins[path]=sha(path)
 names,tiles,kinds,mat,mids,owners,ix,recolor,rows,assigned,restored_cells,r5info=build_source(pins)
 ownership_seconds=time.monotonic()-start
 pmeta={};smeta={};pg=records(side,'patches',pmeta);sg=records(side,'splits',smeta);p=next(pg,None);s=next(sg,None)
 totals=collections.Counter(); reasons=collections.Counter(); per=collections.Counter(); current_old=set();fixtures={}; rmeta={}
 for gi,qi,m,q in stream_quads(render,rmeta):
  key=gi,qi; totals['all_render_quads']+=1; pk=target(p) if p else None;sk=target(s) if s else None
  cursor_check(key,pk,sk)
  actual=p if pk==key else (s if sk==key else None); mode='patch' if pk==key else ('split' if sk==key else None)
  if not m.startswith('top_tile_'):assert actual is None,'nonroof_target';continue
  totals['top_material_quads']+=1;sp=spec(q);fs=list(unit_faces(sp));oids={int(owners[ix(c)]) for _,_,c in fs}
  totals['top_material_unit_faces']+=len(fs);totals['R5_restored_owner_exterior_unit_faces']+=sum(c in restored_cells for _,_,c in fs);totals['R4_changed_owner_exterior_unit_faces']+=sum(int(owners[ix(c)]) in recolor for _,_,c in fs)
  if not oids.intersection(tiles):
   assert actual is None,'non_source_target';continue
  totals['source_owned_candidate_quads']+=1;totals['source_candidate_quad_unit_faces']+=len(fs)
  for a,b,c in fs:
   nc=list(c);nc[sp[2]]+=sp[3];assert mat[ix(c)]==mids[m] and mat[ix(nc)]<0,'not_current_material_exterior'
  whole=None
  if len(oids)==1:
   oid=next(iter(oids));res,why=tiles[oid].classify(q,[c for a,b,c in fs],sp[2],sp[3])
   if res:whole=(names[oid],'analytic_top_staircase',tuple(round(x,10) for x in res[0]),'analytic_top_staircase')
  if whole:
   assert mode=='patch','missing_whole_patch';validate_patch(actual,q,whole);totals['complete_quad_patches']+=1;totals['complete_patch_unit_faces']+=len(fs);per[whole[0]]+=len(fs)
   totals['R5_restored_owner_treated_unit_faces']+=sum(c in restored_cells for _,_,c in fs)
   fixtures.setdefault('patch',(copy.deepcopy(actual),q,whole))
   if whole[0] in SELECTED:
    for a,b,c in fs:current_old.add((sp[2],sp[3],c,whole[0],whole[2]))
   p=next(pg,None);continue
  labels={};safe=0;cn=[0,0,0];cn[sp[2]]=sp[3]
  for a,b,c in fs:
   oid=int(owners[ix(c)]);fid=names[oid];res=None;why='non_source_owner'
   if oid in tiles:res,why=tiles[oid].classify(rectangle(q,sp,a,b,a+1,b+1),[c],sp[2],sp[3])
   if res:
    label=(fid,'analytic_top_staircase',tuple(round(x,10) for x in res[0]),why);safe+=1;per[fid]+=1;totals['R5_restored_owner_treated_unit_faces']+=int(c in restored_cells)
    if fid in SELECTED:current_old.add((sp[2],sp[3],c,fid,label[2]))
   else:
    label=(fid,'preserved_cardinal',tuple(cn),why);reasons[why]+=1
    if oid in recolor:totals['R4_recolor_preserved_candidate_unit_faces']+=1; fixturetype='recolor'
    elif fid.startswith('support_'):totals['backing_preserved_candidate_unit_faces']+=1;fixturetype='backing'
    else:fixturetype=why
    if fixturetype not in fixtures:fixtures[fixturetype]=({'group_index':gi,'quad_index':qi,'source_tile_id':fid,'classification':'preserved_cardinal','normals':[list(cn) for _ in range(4)]},rectangle(q,sp,a,b,a+1,b+1),label)
   labels[a,b]=label
  if not safe:
   assert actual is None,'unsafe_target';totals['untouched_source_candidate_quads']+=1;continue
  assert mode=='split','missing_split';assert validate_split(actual,m,q,labels)==safe
  if 'split' not in fixtures:fixtures['split']=(copy.deepcopy(actual),m,q,copy.deepcopy(labels))
  totals['original_split_unit_faces']+=len(fs);totals['max_original_split_unit_faces']=max(totals['max_original_split_unit_faces'],len(fs));assert len(fs)<=65536,'parent_partition_budget';assert totals['original_split_unit_faces']<=200000,'total_partition_budget'
  totals['split_original_quads']+=1;totals['new_subquads']+=len(actual['quads']);totals['newly_treated_unit_faces']+=safe;totals['preserved_unit_faces_inside_splits']+=len(fs)-safe
  totals['new_analytic_subquads']+=sum(v['classification']=='analytic_top_staircase' for v in actual['quads']);totals['new_preserved_cardinal_subquads']+=sum(v['classification']=='preserved_cardinal' for v in actual['quads'])
  s=next(sg,None)
 assert p is None and s is None,'index_range';assert pmeta==smeta,'inconsistent_header'
 palette=hashlib.sha256(json.dumps(rmeta['materials'],sort_keys=True,separators=(',',':')).encode()).hexdigest();header(pmeta,palette)
 assert totals['all_render_quads']==rmeta['quad_count'];assert len(per)==354
 totals['total_treated_unit_faces']=totals['complete_patch_unit_faces']+totals['newly_treated_unit_faces'];totals['quad_delta']=totals['new_subquads']-totals['split_original_quads'];totals['unindexed_triangle_vertex_delta']=totals['quad_delta']*6;totals['result_render_quads']=totals['all_render_quads']+totals['quad_delta']
 totals['partition_total_cells']=totals['original_split_unit_faces'];totals['final_mesh_quads']=totals['result_render_quads']
 expected_counts=read(FULL/'report.json')['totals']
 assert all(totals[k]==expected_counts[k] for k in totals if k in expected_counts),'count_audit_mismatch'
 baseline=old_triples();retained=set();buried=set();owner_changed=set()
 for triple in baseline:
  axis,sign,c,fid,n=triple;nc=list(c);nc[axis]+=sign
  if names[int(owners[ix(c)])]!=fid:owner_changed.add(triple)
  elif mat[ix(nc)]>=0:buried.add(triple)
  else:retained.add(triple)
 assert not owner_changed,'old_source_ownership_changed'
 assert retained<=current_old,'retained_12tile_triples_mismatch'
 added=current_old-baseline
 assert baseline==retained|buried and len(retained)+len(buried)==len(baseline)
 old_comparison={'retained_unitface_sourceid_normal_triples_equal':True,'baseline_triples':len(baseline),'retained_exterior_triples':len(retained),'buried_by_r05_triples':len(buried),'owner_changed_triples':len(owner_changed),'new_selected_source_analytic_triples':len(added),'current_selected_source_analytic_triples':len(current_old),'all_selected_sources':sorted(SELECTED),'old_sidecar_sha256':OLD_SIDE_PIN,'old_render_sha256':OLDPIN,'full_old_geometry_equivalence_claimed':False,'quad_indices_intentionally_not_compared':True}
 tests=[]
 def reject(name,fn,expected):
  try:fn()
  except AssertionError as e:
   assert str(e)==expected,(name,str(e),expected);tests.append({'name':name,'rejected':True,'reason':str(e)});return
  raise AssertionError(('negative_accepted',name))
 def hp(k,v):mm=dict(pmeta);mm[k]=v;header(mm,palette)
 reject('wrong_render_hash',lambda:hp('render_sha256','0'*64),'render_sha256');reject('wrong_material_palette_hash',lambda:hp('unchanged_materials_sha256','0'*64),'materials_hash')
 base,material,quad,labs=fixtures['split']
 def split_mutate(fn):o=copy.deepcopy(base);fn(o);validate_split(o,material,quad,labs)
 reject('split_gap',lambda:split_mutate(lambda o:o['quads'].pop()),'gap')
 reject('split_overlap',lambda:split_mutate(lambda o:o['quads'].append(copy.deepcopy(o['quads'][0]))),'overlap')
 axis=spec(quad)[2]
 reject('wrong_plane',lambda:split_mutate(lambda o:o['quads'][0]['corners'][0].__setitem__(axis,o['quads'][0]['corners'][0][axis]+P)),'wrong_plane')
 reject('wrong_material',lambda:split_mutate(lambda o:o.update(material='wrong')),'wrong_material')
 patch,pq,pl=fixtures['patch']
 def patch_mutate(fn):o=copy.deepcopy(patch);fn(o);validate_patch(o,pq,pl)
 reject('nonunit_normal',lambda:patch_mutate(lambda o:o.update(normals=[[2*x for x in n] for n in o['normals']])),'nonunit_normal')
 reject('inward_normal',lambda:patch_mutate(lambda o:o.update(normals=[[-x for x in n] for n in o['normals']])),'inward_normal')
 reject('wrong_source_owner',lambda:patch_mutate(lambda o:o.update(source_tile_id='wrong_source')),'wrong_source_owner')
 reject('out_of_range_index',lambda:target(dict(patch,group_index=-1)),'index_range')
 reject('duplicate_patch_split_target',lambda:cursor_check(target(patch),target(patch),target(copy.deepcopy(patch))),'duplicate_target')
 reject('duplicate_patch_array_target',lambda:ordered_target(target(patch),copy.deepcopy(patch)),'duplicate_or_unsorted_target')
 reject('reversed_split_winding',lambda:split_mutate(lambda o:o['quads'][0].update(corners=[o['quads'][0]['corners'][i] for i in [0,3,2,1]])),'winding')
 reject('nonfinite_normal',lambda:patch_mutate(lambda o:o['normals'][0].__setitem__(0,float('nan'))),'finite_normal')
 required=['crop_endpoint_boundary','barrel_side_boundary','profile_crease_crossing','profile_crease_neighbor_ambiguity','top_vs_real_boundary_ambiguity','bottom_or_true_boundary_orientation','outside_source_profile','backing','recolor']
 for reason in required:
  assert reason in fixtures,('missing_source_fixture',reason)
  row,fq,label=fixtures[reason]
  def unsafe(row=row,fq=fq,label=label):o=copy.deepcopy(row);o['classification']='analytic_top_staircase';label_check(o,spec(fq,True),label)
  reject('unsafe_smoothing_'+reason,unsafe,'unsafe_classification')
 rawh=hashlib.sha256();rawbytes=0
 with gzip.open(side,'rb') as f:
  for b in iter(lambda:f.read(65536),b''):rawh.update(b);rawbytes+=len(b)
 assert rawbytes<=32*1024**2 and side.stat().st_size<=8*1024**2,'sidecar_size_budget'
 assert all(sha(path)==h for path,h in pins.items()),'frozen_input_changed'
 report={'status':'PASS_EXHAUSTIVE_FULL_ROOF_SIDECAR_TECHNICAL_GATE','sidecar_sha256':sidehash,'sidecar_decompressed_sha256':rawh.hexdigest(),'sidecar_gzip_bytes':side.stat().st_size,'sidecar_decompressed_bytes':rawbytes,'render_sha256':PIN,'totals':dict(totals),'source_feature_count':len(per),'per_source_treated_unit_faces':dict(per),'source_kind_treated_unit_faces':dict(collections.Counter({kind:sum(v for fid,v in per.items() if kinds[fid]==kind) for kind in set(kinds.values())})),'preserved_candidate_reasons':dict(reasons),'cached_compiled_rows_scanned':rows,'ownership_assigned_counts':dict(assigned),'R4_recolor_cells':2609,'R4_recolor_source_features':0,'12tile_retained_surface_comparison':old_comparison,'R5_applied_ownership_validation':r5info,'negative_tests':tests,'checks':{'all_target_ranges_and_disjoint_patch_split_targets':True,'all_materials_unchanged':True,'all_normals_finite_unit_outward':True,'all_split_pieces_same_original_cardinal_plane':True,'all_split_rectangles_exact_disjoint_unit_face_cover':True,'holes':0,'overlaps':0,'vertex_displacement':0,'godot_clockwise_triangle_order_verified':[0,2,1,0,3,2],'source_owner_and_current_exterior_reconstructed':True,'complete_classification_replay_all_354_sources':True,'author_counts_independently_matched':True,'original_source_profile_classifier_unchanged':True,'all_r05_isolated_rows_independently_accepted_or_deferred':True,'protected_335_conflicts_excluded_from_owner_updates':True,'actual_gzip_roundtrip_streamed':True,'full_25MB_sidecar_JSON_loaded':False,'frozen_inputs_unchanged':True,'visual_acceptance':False},'source_pins':{str(p.relative_to(ROOT)):h for p,h in pins.items()},'limits':{'AS_mib':256,'CPU_hard_seconds':45,'requested_CPU_seconds':60,'raw_bytes_cap':32*1024**2,'gzip_bytes_cap':8*1024**2,'partition_total_cells_cap':200000},'ownership_seconds':ownership_seconds,'elapsed_seconds':time.monotonic()-start,'CPU_seconds':time.process_time()-cpu,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'sampler_calls':0,'compiler_calls':0,'mesher_calls':0,'GUI_calls':0,'scope_caveat':'The frozen explicit top-profile and height prior are retained. This proves safe shading classification and exact surface invariance, not recovered observed 3D normals or perceptual superiority.'}
 (V/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','per_source_treated_unit_faces')},indent=2))
if __name__=='__main__':
 try:main()
 except BaseException as exc:
  import traceback
  (V/'failure.json').write_text(json.dumps({'status':'FAILED_NO_LIMIT_ESCALATION','exception':repr(exc),'traceback':traceback.format_exc(),'CPU_seconds':time.process_time(),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2)+'\n')
  raise
