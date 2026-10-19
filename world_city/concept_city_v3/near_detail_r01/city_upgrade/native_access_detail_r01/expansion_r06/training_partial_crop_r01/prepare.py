"""Source-only bounded crop input. No occupancy compilation or new mesh.

The mask is conservative geometry authoring data: every admitted microcell's
whole horizontal footprint must be in the exact source walk union. The normal
common author/assembly cuts/compiler/mesher consumes it in the separate build.
"""
from pathlib import Path
from fractions import Fraction as F
import collections,copy,json,math,resource,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;N=H.parents[1];E=N/'expansion_r04/extrusion_support_r01'
sys.path.insert(0,str(E));import author_extrusion as e
a=e.a;b=e.b;R=e.R;P=e.P
SELECTED=[0,1,2,6,14,16,100,130,220,280,340,392]
read=e.read;sha=e.sha;digest=e.digest
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def save(p,v):a.common.write_exact(p,a.common.payload(v))
def ratio(v):return [v.numerator,v.denominator]
def intersects(r,s):return min(r[2],s[2])>max(r[0],s[0]) and min(r[3],s[3])>max(r[1],s[1])
def rectpoly(r):return [[r[0],r[1]],[r[2],r[1]],[r[2],r[3]],[r[0],r[3]]]
def intersection(poly,cover):
 d=1 if e.signed(cover)>0 else -1
 for x,y in zip(cover,cover[1:]+cover[:1]):poly=e.clip(poly,x,y,d,True)
 return poly
def hull(points):
 pts=sorted(set(tuple(p)for p in points));lower=[];upper=[]
 for dest,seq in [(lower,pts),(upper,list(reversed(pts)))]:
  for p in seq:
   while len(dest)>1 and e.cross(dest[-2],dest[-1],p)<=0:dest.pop()
   dest.append(p)
 return [list(p)for p in lower[:-1]+upper[:-1]]
def lines(poly):
 d=1 if e.signed(poly)>0 else -1;out=[]
 for x,y in zip(poly,poly[1:]+poly[:1]):
  A=d*(x[1]-y[1]);B=d*(y[0]-x[0]);C=d*(x[0]*y[1]-y[0]*x[1]);den=math.lcm(A.denominator,B.denominator,C.denominator);out.append(tuple(int(v*den)for v in [A,B,C]))
 return out
def rect_in(r,ls):
 return all(A*(r[0]if A>=0 else r[2])+B*(r[1]if B>=0 else r[3])+C>=0 for A,B,C in ls)
def point_in(p,poly):return all(A*p[0]+B*p[1]+C>=0 for A,B,C in lines(poly))
def cell_rect(item,x,y):
 # EXACT real composition of the actual binary64 exported vertices and the
 # declared translation. Not a rounded centroid or idealized source polygon.
 ox,oy=item['trim']['offset_m'];u,v=item['bounds_uv_m'][:2]
 return [F(-ox+x*P)+F(u),F(-oy+y*P)+F(v),F(-ox+(x+1)*P)+F(u),F(-oy+(y+1)*P)+F(v)]
def safe_cell(r,polys,prepared=None):
 prepared=prepared or [lines(p)for p in polys]
 if any(rect_in(r,ls)for ls in prepared):return True,'single_convex_owner'
 value=e.exact_union(rectpoly(r),polys)
 if value==0:
  common=a.polygons.uncovered_area_by_union([[float(v)for v in p]for p in rectpoly(r)],[[[float(v)for v in p]for p in q]for q in polys],0)
  return common==0,'exact_multi_owner_union' if common==0 else 'common_numeric_disagreement'
 return False,'positive_uncovered_area'
def cell_runs(cells):
 out=[]
 for y in sorted(set(y for x,y in cells)):
  runs=[]
  for x in sorted(x for x,yy in cells if yy==y):
   if runs and runs[-1][1]==x:runs[-1][1]=x+1
   else:runs.append([x,x+1])
  out.extend([[x,y,z,y+1]for x,z in runs])
 return out
def expand(rectangles):return {(x,y)for x0,y0,x1,y1 in rectangles for x in range(x0,x1)for y in range(y0,y1)}
def prepare():
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(60,)*2)
 plan=read(E/'source_plan.json');row=plan['assets'][0];audit=read(E/'source_application_audit.json');master=read(R/row['source_master_path']);source=read(R/row['source_render_path']);assert sha(R/row['source_master_path'])==row['source_master_sha256'] and sha(R/row['source_render_path'])==row['source_render_sha256'];assert not master.get('assembly_cuts') and not any(op['action']=='cut'for c in master['components']for op in c['operations']);owners=e.source_caps(master,row['rule']);assert owners==row['source_polygon_owners'];old=[p['bounds_uv_m']for p in row['placements']];assert sum((r[2]-r[0])*(r[3]-r[1])for r in old)==347.25
 rows=[];allcells=set();full_area=safe_area=domain_area=F(0);kinds=collections.Counter()
 for rid in SELECTED:
  rejected=audit['rejected_patches'][rid];bounds=rejected['bounds_uv_m'];gi,qi=rejected['source_face_ref'];quad=source['groups'][gi]['quads'][qi];face=a.top_rectangle(quad);rect=[a.strict_grid(v)for v in bounds];assert a.union_proof(rect,[face])['uncovered_area_cells2']==0;assert not any(intersects(bounds,r)for r in old)
  ix,iy=math.floor(bounds[0]),math.floor(bounds[1]);trim={'width_m':bounds[2]-bounds[0],'height_m':bounds[3]-bounds[1],'offset_m':[bounds[0]-ix,bounds[1]-iy]};low=[round(v/P)for v in trim['offset_m']];high=[round((trim['offset_m'][i]+trim[['width_m','height_m'][i]])/P)for i in range(2)];subject=e.fp(rectpoly(bounds));local=[];parts=[]
  for owner in owners:
   if not intersects(bounds,owner['bounds_uv_m']):continue
   part=intersection(subject,e.fp(owner['polygon_uv_m']))
   if e.area(part)>0:local.append(owner);parts.append(part)
  polys=[e.fp(o['polygon_uv_m'])for o in local];ls=[lines(p)for p in polys];outside=e.exact_union(subject,polys);available=e.area(subject)-outside;assert outside==F(*rejected['proof']['exact_uncovered_area_ratio']);convex_hull=hull([p for part in parts for p in part]);hull_missing=e.exact_union(convex_hull,polys);angles=sorted(set(round(math.atan2(float(y[1]-x[1]),float(y[0]-x[0]))%math.pi,6)for part in parts for x,y in zip(part,part[1:]+part[:1])if x[0]!=y[0]and x[1]!=y[1]));positive_intersections=sum(e.area(intersection(p,q))>0 for i,p in enumerate(parts)for q in parts[i+1:]);item={'id':'training_boundary_%03d'%rid,'rejected_patch_index':rid,'bounds_uv_m':bounds,'grid_xy_m':[ix,iy],'trim':trim,'seed':[41873,41879,41887][(ix*17+iy*31)%3],'source_face_ref':[gi,qi],'source_face_sha256':digest(quad),'source_quad':quad,'source_owner_operation_ids':[o['operation']for o in local],'local_owner_count':len(local),'source_domain_area_ratio':ratio(available),'source_domain_area_m2':float(available),'forbidden_rectangle_area_m2':float(outside),'slanted_boundary_angles_rad':angles,'nonconvex_source_union_witness_area_m2':float(hull_missing),'positive_owner_intersections':positive_intersections,'source_plane_y_m':quad[0][1]}
  safe=set();reasons=collections.Counter();center_only_rejected=0
  for x in range(low[0],high[0]):
   for y in range(low[1],high[1]):
    r=cell_rect(item,x,y);okay,reason=safe_cell(r,polys,ls);reasons[reason]+=1
    if okay:
     assert e.exact_union(rectpoly(r),[e.fp([[p[0],-p[2]]for p in quad])])==0
     key=(ix*80+x,iy*80+y);assert key not in allcells;allcells.add(key);safe.add((x,y))
    elif any(point_in([(r[0]+r[2])/2,(r[1]+r[3])/2],p)for p in polys):center_only_rejected+=1
  assert safe;safe_runs=cell_runs(safe);safe_exact=sum((cell_rect(item,x,y)[2]-cell_rect(item,x,y)[0])*(cell_rect(item,x,y)[3]-cell_rect(item,x,y)[1])for x,y in safe)
  # Reuse the common exact-lattice rectangular hole partitioner to obtain
  # disjoint cuts. These are standard assembly cuts, not a custom mesher.
  partition={'pitch_m':P,'trim':{'width_m':1,'height_m':1},'holes':[{'rect':[v*P for v in r]}for r in safe_runs]};forbidden=a.common.allowed_rectangles(partition);cuts=[[round(v/P)for v in r]for r in forbidden];assert expand(cuts)=={(x,y)for x in range(80)for y in range(80)}-safe
  item.update({'allowed_cell_runs_xy':safe_runs,'common_cut_rectangles_xy':cuts,'allowed_horizontal_cells':len(safe),'candidate_cells_in_rectangle':(high[0]-low[0])*(high[1]-low[1]),'whole_footprint_recovered_area_m2':float(safe_exact),'whole_footprint_recovered_area_ratio':ratio(safe_exact),'ideal_lattice_area_m2':len(safe)/6400,'fine_grid_boundary_loss_m2':float(available-safe_exact),'fine_grid_boundary_loss_ratio':ratio(available-safe_exact),'centroid_would_accept_but_full_footprint_rejects':center_only_rejected,'cell_proof_methods':dict(reasons),'actual_quad_union_outside_area_m2':0,'walk_union_outside_area_m2':0,'existing_detail_overlap_area_m2':0,'duplicate_cells':0});assert available>=safe_exact;rows.append(item);full_area+=e.area(subject);domain_area+=available;safe_area+=safe_exact;kinds.update(reasons);print(json.dumps({k:item[k]for k in ['id','local_owner_count','allowed_horizontal_cells','whole_footprint_recovered_area_m2','fine_grid_boundary_loss_m2','centroid_would_accept_but_full_footprint_rejects','nonconvex_source_union_witness_area_m2']}),flush=True)
 deps=[E/'source_plan.json',E/'source_application_audit.json',R/row['source_master_path'],R/row['source_render_path'],Path(a.common.__file__),Path(a.edge.__file__),Path(b.core.__file__),R/'voxel_character/common/render_data.py',R/'voxel_character/tools/mesh.py',Path(a.polygons.__file__),Path(e.__file__)]
 result={'schema':'riverstone.native_access.partial_crop_input.v1','status':'SOURCE_PREPARED_NO_SAMPLING','asset_key':row['asset_key'],'source_plan':ref(E/'source_plan.json'),'source_master':ref(R/row['source_master_path']),'source_render':ref(R/row['source_render_path']),'source_dependencies':{str(p.relative_to(R)):sha(p)for p in deps},'author':ref(Path(__file__)),'selected_patches':rows,'summary':{'patches':len(rows),'source_candidate_rectangles_area_m2':float(full_area),'exact_source_domain_area_m2':float(domain_area),'source_forbidden_area_m2':float(full_area-domain_area),'whole_footprint_recovery_area_m2':float(safe_area),'fine_grid_boundary_loss_m2':float(domain_area-safe_area),'existing_supported_area_m2':347.25,'existing_detail_overlap_m2':0,'duplicate_cells':0,'safe_horizontal_cells':len(allcells),'centroid_only_unsafe_cells_rejected':sum(r['centroid_would_accept_but_full_footprint_rejects']for r in rows),'nonconvex_union_examples':sum(r['nonconvex_source_union_witness_area_m2']>0for r in rows),'overlapping_source_junction_examples':sum(r['positive_owner_intersections']>0for r in rows),'new_geometry_bytes':0,'compile_or_occupancy_sampling_performed':False,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'method':'Exact source footprint lattice proof; common polygon union plus rational oracle; unchanged common polygon surface author and standard assembly box cuts for unsafe full cells, then unchanged compiler and greedy mesher. No cell-center acceptance and no occupancy post-filter.','limits':{'address_space_bytes':256*1024*1024,'build_unit_wall_seconds':60,'new_geometry_bytes':8*1024*1024},'runtime_activation':False,'new_colliders':0}
 assert result['summary']['nonconvex_union_examples']>0 and result['summary']['overlapping_source_junction_examples']>0;save(H/'prepared_inputs.json',result);print(json.dumps(result['summary']),flush=True)
if __name__=='__main__':prepare()
