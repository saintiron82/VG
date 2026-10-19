#!/usr/bin/env python3
"""Analysis only: source-exact classification of previously skipped quads."""
import sys,os
os.environ['PYTHONDONTWRITEBYTECODE']='1'
from derive_normal_diagnostic import *

def unit_quad(q,low,high,axis,u,v,a,b):
 # Preserve q corner order and its exact plane while reducing its u/v rectangle.
 out=[]
 for p in q:
  t=list(p);t[u]=(a if round(p[u]/P)==low[u] else a+1)*P;t[v]=(b if round(p[v]/P)==low[v] else b+1)*P;out.append(t)
 return out

def center_exit(tile,cell,axis,sign):
 c=[(n+.5)*P for n in cell];nc=c.copy();nc[axis]+=sign*P;lc=tile.local(c);ln=tile.local(nc)
 # Preserve all physical endpoint / side boundaries, even if another inequality
 # could also be crossed by the same discrete center pair.
 if not (tile.x0<c[0]<tile.x1):return 'owner_outside_crop',None
 if not (tile.x0<nc[0]<tile.x1):return 'physical_crop_endpoint',None
 if not (tile.top[0][0]<lc[0]<tile.top[-1][0]):return 'owner_outside_barrel',None
 if not (tile.top[0][0]<ln[0]<tile.top[-1][0]):return 'physical_barrel_side',None
 if not (tile.op['shape']['z_min']<ln[2]<tile.op['shape']['z_max']):return 'physical_extrusion_endpoint',None
 sc=tile.seg(lc[0]);sn=tile.seg(ln[0]);tc=lc[1]-tile.height(lc[0],sc);tn=ln[1]-tile.height(ln[0],sn)
 if not (-.0625-1e-8<=tc<=1e-8):return 'owner_not_inside_strip',None
 if tn<-.0625-1e-8:return 'physical_bottom_surface',None
 if tn<=1e-9:return 'neighbor_not_above_top',None
 # Solve the exact center-to-neighbor exit against each explicit top segment.
 hits=[]
 for i,(a,b) in enumerate(zip(tile.top,tile.top[1:])):
  m=(b[1]-a[1])/(b[0]-a[0]);den=(ln[1]-lc[1])-m*(ln[0]-lc[0]);f=lc[1]-a[1]-m*(lc[0]-a[0])
  if den<=1e-12:continue
  t=-f/den;x=lc[0]+t*(ln[0]-lc[0])
  if -1e-9<=t<=1+1e-9 and a[0]-1e-9<=x<=b[0]+1e-9:hits.append((i,t,x))
 if len(hits)!=1:return 'analytic_top_exit_at_crease_ambiguous',None
 seg=hits[0][0]
 if sign*tile.normal(seg)[axis]<=0:return 'top_exit_orientation_conflict',None
 return 'proven_internal_top_center_exit',seg

def main():
 started=time.monotonic();sidepath=H/'normal_sidecar.json';sealed=sha(sidepath);assert sealed=='dbd7994bc11353b841aed5423c03292c41858767800adfdfc5103d88b9fec0ae'
 assert sha(R2/'roof_repaired.render.json.gz')==PIN
 evidence=read(H/'face_evidence.json.gz');skipped={(q['group_index'],q['quad_index']):q for q in evidence['skipped']};meta={};quads={};needs=set();quad_spec={}
 for gi,qi,mat,q in stream_quads(R2/'roof_repaired.render.json.gz',meta):
  if (gi,qi) not in skipped:continue
  quads[(gi,qi)]=(mat,q);g=[[round(n/P) for n in p] for p in q];lo=[min(p[i] for p in g) for i in range(3)];hi=[max(p[i] for p in g) for i in range(3)];axis=next(i for i in range(3) if lo[i]==hi[i]);normal=cross(sub(g[1],g[0]),sub(g[2],g[0]));sign=1 if normal[axis]>0 else -1;u,v=[i for i in range(3) if i!=axis];faces=[]
  for a in range(lo[u],hi[u]):
   for b in range(lo[v],hi[v]):
    cell=[0,0,0];cell[axis]=lo[axis]-(sign>0);cell[u]=a;cell[v]=b;cell=tuple(cell);needs.add(cell);faces.append((cell,a,b))
  quad_spec[(gi,qi)]=(lo,hi,axis,sign,u,v,faces)
 assert len(quads)==1769
 plan=read(R2/'plan.json');links={v['operation']:v for v in plan['tile_source_links']};master=read(R2/'roof_patch.master.json.gz');ops={op['id']:op for c in master['components'] for op in c['operations']};tiles={s:SourceTile(ops[s],links[s]) for s in links}
 union=np.load(R2/'upper_union_arrays.npz');arr=union['materials'];origin=union['origin_cell_xyz'].tolist();names=union['material_names'].tolist();ids={n:i for i,n in enumerate(names)}
 def material(c):
  x,y,z=c;return int(arr[y-origin[1],x-origin[0],z-origin[2]])
 owners={};zmin=min(c[2] for c in needs);zmax=max(c[2] for c in needs);used=[];pins={str(sidepath.relative_to(ROOT)):sealed,str((R2/'roof_repaired.render.json.gz').relative_to(ROOT)):PIN}
 for rec in read(R2/'compile.json')['chunks']:
  low,high=rec['owned_z_cells']
  if high<=zmin or low>zmax:continue
  p=ROOT/rec['compiled']['path'];assert sha(p)==rec['compiled']['sha256'];pins[str(p.relative_to(ROOT))]=sha(p);c=read(p);used.append(rec['index'])
  for row in c['cells']:
   key=tuple(row[:3])
   if key in needs and material(key)==ids[row[5]]:owners[key]=row[6]
  del c;gc.collect()
 by_reason={r:collections.Counter() for r in set(s['reason'] for s in skipped.values())};center_counts=collections.Counter();candidate_counts=collections.Counter();mixed_features=collections.Counter();all_ids=collections.Counter();safe_examples=[];per_quad=[];fullsafe=0;partial=0;all_faces=0;selected_faces=0;safe_faces=0;center_top_faces=0;selected_top_rejected=collections.Counter();ambiguous_examples=[]
 for key,(mat,q) in quads.items():
  original=skipped[key]['reason'];bucket=by_reason[original];bucket['quads']+=1;lo,hi,axis,sign,u,v,faces=quad_spec[key];bucket['unit_faces_total']+=len(faces);all_faces+=len(faces);safe=0;sel=0;top=0;reason_counts=collections.Counter();fids=set()
  for cell,a,b in faces:
   fid=owners.get(cell);all_ids[str(fid)]+=1;fids.add(str(fid))
   if fid not in SELECTED:
    bucket['unit_faces_other_owner']+=1;reason_counts['other_owner_preserved']+=1;continue
   sel+=1;selected_faces+=1;bucket['unit_faces_selected_owner']+=1;tile=tiles[fid];nc=list(cell);nc[axis]+=sign;assert material(nc)<0 and material(cell)==ids[mat]
   result,seg=center_exit(tile,cell,axis,sign);center_counts[result]+=1;bucket['center_'+result]+=1;reason_counts[result]+=1
   if result=='neighbor_not_above_top' and len(ambiguous_examples)<6:
    wc=[(n+.5)*P for n in cell];wn=wc.copy();wn[axis]+=sign*P;lc=tile.local(wc);ln=tile.local(wn);sc=tile.seg(lc[0]);sn=tile.seg(ln[0]);ambiguous_examples.append({'group_index':key[0],'quad_index':key[1],'source_tile_id':fid,'owner_cell_xyz':list(cell),'axis':axis,'sign':sign,'original_reason':original,'owner_local':lc,'neighbor_local':ln,'owner_height_above_top':lc[1]-tile.height(lc[0],sc),'neighbor_height_above_top':ln[1]-tile.height(ln[0],sn),'source_crop_x':[tile.x0,tile.x1],'extrusion_range':[tile.op['shape']['z_min'],tile.op['shape']['z_max']]})
   if result=='proven_internal_top_center_exit':top+=1;center_top_faces+=1
   uq=unit_quad(q,lo,hi,axis,u,v,a,b);klass,why=tile.classify(uq,[cell],axis,sign)
   if klass is not None:
    safe+=1;safe_faces+=1;bucket['safe_unit_faces_after_coplanar_split']+=1
    assert result=='proven_internal_top_center_exit';n,source_segment=klass
    if len(safe_examples)<12:safe_examples.append({'group_index':key[0],'quad_index':key[1],'source_tile_id':fid,'owner_cell_xyz':list(cell),'original_reason':original,'source_profile_segment':source_segment,'subrectangle_world':uq})
   elif result=='proven_internal_top_center_exit':bucket['center_top_but_whole_unit_face_unproven']+=1;selected_top_rejected[why]+=1
  if original=='mixed_or_unproven_tile_ownership':mixed_features[' | '.join(sorted(fids))]+=1
  if safe:
   bucket['quads_with_safe_unit_subfaces']+=1
   if safe==len(faces):fullsafe+=1;bucket['quads_fully_resolved_by_lattice_split']+=1
   else:partial+=1;bucket['quads_partially_resolved_by_lattice_split']+=1
  if top:bucket['quads_with_proven_top_center_exits']+=1
  if len(per_quad)<16 and safe:per_quad.append({'group_index':key[0],'quad_index':key[1],'original_reason':original,'unit_faces_total':len(faces),'selected_owner_faces':sel,'safe_subfaces':safe,'top_center_faces':top,'all_owner_features':sorted(fids)})
 assert all(sha(ROOT/p)==h for p,h in pins.items())
 report={'schema':'riverstone.roof_normal_diagnostic.skipped_analysis.v1','analysis_only':True,'sealed_sidecar_sha256':sealed,'sealed_sidecar_unchanged':True,'frozen_render_sha256':PIN,'frozen_render_unchanged':True,'source_sidecar_patch_quads':1390,'source_sidecar_patch_unit_faces':2131,'skipped_quads':1769,'skipped_unit_faces_total':all_faces,'skipped_unit_faces_selected_12_owners':selected_faces,'skipped_unit_faces_other_owner':all_faces-selected_faces,'all_skipped_counts_by_original_reason':{k:dict(v) for k,v in sorted(by_reason.items())},'selected_owner_center_exit_classification':dict(center_counts),'provable_coplanar_lattice_split':{'safe_unit_subfaces':safe_faces,'safe_unit_subface_area_m2':safe_faces*P*P,'original_skipped_quads_with_any_safe_subfaces':fullsafe+partial,'original_skipped_quads_fully_resolved':fullsafe,'original_skipped_quads_partially_resolved':partial,'gate':'Each subquad passes unchanged original unique source-top facet classifier, exact compiled owner, actual empty neighbor and material checks. No new classification assumption.'},'additional_center_top_only_candidates':{'unit_faces':center_top_faces-safe_faces,'remaining_whole_unit_face_exclusions':dict(selected_top_rejected),'status':'NOT_APPROVED_FOR_NORMAL_REPLACEMENT','reason':'A unique source-top crossing on the cell-center ray does not prove every point of the unit face has that ownership or analytic facet. Exact clipping plus fragment-area validation is still required.'},'unresolved_non_top_neighbor_examples':ambiguous_examples,'mixed_quad_owner_sets':dict(mixed_features),'safe_subface_examples':safe_examples,'safe_original_quad_examples':per_quad,'split_method':{'minimal_proven':'Partition only affected existing axis-aligned render quads at integer .03125m grid lines, retaining the exact plane, winding, material and covered rectangle. For each subquad use original source-facet classifier; patch only accepted selected-owner subquads and retain cardinal normals on the rest. Can re-merge only coplanar adjacent pieces sharing material, source tile ID, analytic top segment and normal.','more_complete_not_yet_proven':'For remaining unitfaces, partition against exact source crop planes and five-point-profile facet boundaries; derive source-top intersections and keep separate vertices on each real crease. Prove per-fragment source ownership/top-only exit and area-exact cover; preserve endpoint/side/underside fragments. Never average across a crease or owner boundary.','geometry_invariant':'Same geometric surface as a set, same bounds, silhouette, occupied volume, material colors and rectangle area; no displacement or new occupied geometry.','important_contract_change':'Any quad split changes vertex/index array representation and topology; it cannot satisfy the sealed sidecar unchanged-position-array contract. A new isolated tessellation-equivalence diagnostic and authorization would be required.'},'geometry_created':False,'new_sidecar_created':False,'sealed_files_modified':False,'compiler_calls':0,'sampling_calls':0,'mesher_calls':0,'GUI_calls':0,'source_chunks_read':used,'address_space_limit_mib':256,'cpu_limit_seconds':45,'elapsed_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 save('skipped_analysis.json',report)
 total=sum(p.stat().st_size for p in H.iterdir() if p.is_file());assert total<500000,total
 print(json.dumps({'skipped_unit_faces':all_faces,'selected':selected_faces,'other_owner':all_faces-selected_faces,'center_counts':dict(center_counts),'safe_unit_subfaces':safe_faces,'quads_full':fullsafe,'quads_partial':partial,'center_top_only_not_yet_face_proven':center_top_faces-safe_faces,'mixed':dict(mixed_features),'bytes':total,'seconds':report['elapsed_seconds'],'rss_kib':report['peak_rss_kib']},sort_keys=True))
if __name__=='__main__':main()
