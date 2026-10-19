"""Read-only roof surface source ownership, final-mesh coverage and section audit."""
import collections,json,math,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent.parent
sys.path[:0]=[str(B.parent),str(B.parent/'composed_runtime'),str(B/'sampler_v2'),str(B.parent.parent/'house_rules')]
import author as a
import stream_render as sr
import reserved_io_r04 as rio
from output_reservations_v3 import ReservationBook

def top_map(path):
 out={};materials=collections.Counter();faces=collections.Counter()
 for mat,q in sr.iter_quads(path):
  axis,t,p,s,r=a.quad_info(q);faces[mat]+=1
  if axis!=1 or s<0:continue
  for u in range(round(r[0]*20),round(r[2]*20)):
   for v in range(round(r[1]*20),round(r[3]*20)):
    c=[0,0,0];c[t[0]]=u;c[t[1]]=v;key=(c[0],c[2]);old=out.get(key)
    if old is None or p>old[0]:out[key]=(p,mat)
 return out,faces

def role(oid):
 return 'underlay' if 'underlay' in oid else 'tile' if '_tile_' in oid else 'ridge' if 'ridge' in oid else 'edge_finish'

def polygon_top(shape,x):
 ys=[];poly=shape['polygon']
 for a0,b in zip(poly,poly[1:]+poly[:1]):
  if min(a0[0],b[0])-1e-9<=x<=max(a0[0],b[0])+1e-9:
   if abs(a0[0]-b[0])<1e-10:ys.extend([a0[1],b[1]])
   else:ys.append(a0[1]+(x-a0[0])*(b[1]-a0[1])/(b[0]-a0[0]))
 return max(ys) if ys else None

def main():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));start=time.monotonic();key='registered_main_gate_header';mp=B/'composed'/key/(key+'.manifest.json');m=a.load(mp);hp=B/'composed'/key/'roof_handoff_snapshot.json';h=a.load(hp);rp=a.ROOT/h['emitted_master_path'];roof=a.load(rp);full=a.ROOT/h['files']['.render.json']['path'];final=a.ROOT/m['render_path'];original=a.ROOT/m['collision_reference_path'];refs=[mp,hp,rp,full,final,original,Path(__file__),a.ROOT/'world_city/concept_city_v3/near_detail_r01/city_upgrade/evidence/gates_actual_r03/gate_oblique_after.png'];identity={'asset_key':key,'references':[{'path':str(p.relative_to(a.ROOT)),'sha256':a.sha(p)} for p in refs]};cfg=a.load(B.parent.parent/'house_rules/shared_output_budget.v2.json');book=ReservationBook(a.ROOT/cfg['book_path'],a.ROOT,[a.ROOT/p for p in cfg['retained_roots']],cfg['limit_bytes'],min_free_disk_bytes=cfg['min_free_disk_bytes']);rk='facility_readability:main_header:r01';scopes=[{'directory':str(HERE.relative_to(a.ROOT)),'prefix':''}];book.reserve(rk,scopes,300000,identity);book.acquire_writer(rk);w=rio.ReservedWriter(book,rk,B,scopes,a.ROOT)
 roofmap,roofmats=top_map(full);finalmap,finalmats=top_map(final);ops=[];buckets=collections.defaultdict(list);opcounts=collections.Counter();underlays=[]
 for cid,iid,op,tr,bb in a.source_inventory(roof):
  assert op['action']=='paint';shape=a.core.prepare_shape(op['shape'],.05);entry=(op,tr,shape,bb);idx=len(ops);ops.append(entry);opcounts[role(op['id']),op['material']]+=1
  if role(op['id'])=='underlay':underlays.append(entry)
  for x in range(math.floor(bb[0][0]*20),math.ceil(bb[1][0]*20)):
   for z in range(math.floor(bb[0][2]*20),math.ceil(bb[1][2]*20)):buckets[x,z].append(idx)
 ownercount=collections.Counter();examples={};delta=[];higher=[];missing=[];topowners={};gaps=[]
 for (x,z),(height,mat) in roofmap.items():
  point=[(x+.5)*.05,height-.025,(z+.5)*.05];owner=None
  for idx in reversed(buckets[x,z]):
   op,tr,shape,bb=ops[idx]
   if a.core.contains(shape,a.core.inverse(tr,point)):owner=op;break
  assert owner,(x,z,height);r=role(owner['id']);ownercount[r]+=1;topowners[x,z]=r;examples.setdefault(r,{'world_cell_center':point,'top_face_y':height,'operation':owner['id'],'material':mat})
  if (x,z) not in finalmap:missing.append([x,z,height])
  elif finalmap[x,z][0]>height+1e-7:higher.append({'xz_cell':[x,z],'roof_y':height,'final_y':finalmap[x,z][0],'final_material':finalmap[x,z][1]})
  else:delta.append(round(finalmap[x,z][0]-height,7))
  if r=='tile':
   uh=[]
   for op,tr,shape,bb in underlays:
    assert tr['basis']==[[1,0,0],[0,1,0],[0,0,1]]
    local=a.core.inverse(tr,point)
    if shape['z_min']<=local[2]<=shape['z_max']:
     y=polygon_top(shape,local[0])
     if y is not None:uh.append(y+tr['translation'][1])
   if uh:gaps.append(height-max(uh))
 sections=[]
 for z in [-.425,-.225,.025,.225]:
  iz=math.floor(z*20);samples=[]
  for ix in range(-88,-1):
   if (ix,iz) in roofmap:samples.append({'x':(ix+.5)*.05,'y':roofmap[ix,iz][0],'owner':topowners[ix,iz],'composed_y':finalmap[ix,iz][0]})
  sections.append({'z_cell_center':(iz+.5)*.05,'samples':samples})
 report={'schema':'riverstone.roof.surface_readability_audit.v1','identity':identity,'asset_key':key,'full_roof_quads_by_material':dict(roofmats),'composed_quads_by_material':dict(finalmats),'source_operations_by_role_material':[{'role':r,'material':m,'count':n} for (r,m),n in opcounts.items()],'upward_roof_cell_count':len(roofmap),'upward_top_cell_owner_counts':dict(ownercount),'owner_examples':examples,'full_roof_top_missing_in_composed':len(missing),'full_roof_top_covered_by_higher_composed':len(higher),'higher_examples':higher[:20],'unchanged_roof_top_cells':sum(d==0 for d in delta),'lower_composed_top_cells':sum(d<0 for d in delta),'tile_surface_above_analytic_underlay_top_m':{'samples':len(gaps),'min':min(gaps),'max':max(gaps),'median':sorted(gaps)[len(gaps)//2]},'cross_sections':sections,'tile_shape_sample':next(op for op,tr,shape,bb in ops if role(op['id'])=='tile'),'source_geometry_modified':False,'new_voxel_compiles':0,'visual_assessment':'Actual supplied image has weak tile joint readability. Geometry/source equivalence is not an artistic acceptance.','scope':'Exhaustive upward surface sample raster at exact .05 cell centers; source label containment and composed top-height comparison. Side/back silhouette appearance depends on actual camera, lighting and materials.','wall_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};w.write(HERE/'surface_audit.json',report);book.release(rk,identity,'Read-only actual face-domain and analytic backing comparison complete.');w.close();print(json.dumps({k:report[k] for k in ['upward_top_cell_owner_counts','full_roof_top_missing_in_composed','full_roof_top_covered_by_higher_composed','unchanged_roof_top_cells','tile_surface_above_analytic_underlay_top_m','wall_seconds','peak_rss_kib']}),flush=True)
if __name__=='__main__':main()
