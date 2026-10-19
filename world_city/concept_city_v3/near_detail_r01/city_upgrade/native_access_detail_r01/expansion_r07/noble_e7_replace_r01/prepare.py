"""Exact source-region masks on one stable metre grid. No volume sampling.
Integer half-plane interval acceleration is proof-only; source polygons,
common compiler and mesher remain unchanged.
"""
from pathlib import Path
from fractions import Fraction as F
import bisect,collections,copy,json,math,resource,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;N=H.parents[1]
sys.path.insert(0,str(N/'expansion_r06/noble_e7_audit_r01'));import audit as audit6
p=audit6.p;ad=audit6.ad;e=p.e;a=p.a;b=p.b;R=p.R;P=p.P
KEY=audit6.KEY;PLAN=audit6.PLAN;MASK=(1<<80)-1
read=p.read;sha=p.sha;digest=p.digest;ref=p.ref;save=p.save
D=1<<60

def span(lo,hi):return ((1<<(hi-lo))-1)<<lo if hi>lo else 0
def ranges(bits):
 out=[]
 while bits:
  lo=(bits&-bits).bit_length()-1;shift=bits>>lo;length=(shift^(shift+1)).bit_length()-1;out.append((lo,lo+length));bits&=~span(lo,lo+length)
 return out
def runs(rows):return [[x,y,z,y+1]for y,bits in enumerate(rows)for x,z in ranges(bits)]
def coords(anchor):
 values=[F(anchor)+F(i*P)for i in range(81)];assert all((v*D).denominator==1 for v in values)
 return values,[int(v*D)for v in values]
def poly_rows(poly,xx,yy,inside):
 """Whole-cell containment or strict positive-area convex SAT intersection.
 Exact integer inequalities, no epsilon and no center-point decisions.
 """
 ls=p.lines(poly);out=[];bounds=[min(q[i]for q in poly)for i in [0,1]]+[max(q[i]for q in poly)for i in [0,1]]
 for y in range(80):
  lo=0;hi=80
  if not inside and (F(yy[y+1],D)<=bounds[1]or F(yy[y],D)>=bounds[3]):out.append(0);continue
  for A,B,C in ls:
   # Min signed distance proves full containment; max plus AABB axes gives
   # exact separating-axis positive overlap for convex polygons.
   yi=y if (B>=0)==inside else y+1;term=B*yy[yi]+C*D
   if A==0:
    if term<0 if inside else term<=0:hi=0;break
   elif A>0:
    threshold=(-term+A-1)//A if inside else (-term)//A+1
    index=bisect.bisect_left(xx,threshold);lo=max(lo,index if inside else index-1)
   else:
    threshold=term//(-A)if inside else (term-1)//(-A)
    index=bisect.bisect_right(xx,threshold)-1;hi=min(hi,index if inside else index+1)
  if not inside:
   # AABB separating axes are necessary in addition to polygon edge normals.
   while lo<hi and F(xx[lo+1],D)<=bounds[0]:lo+=1
   while hi>lo and F(xx[hi-1],D)>=bounds[2]:hi-=1
  out.append(span(max(0,lo),min(80,hi)))
 return out

def actual_rows(rects,xx,yy):
 out=[0]*80
 for rect in rects:
  rr=[F(v)*D for v in rect];assert all(v.denominator==1 for v in rr);x0,y0,x1,y1=map(int,rr);lo=bisect.bisect_left(xx,x0);hi=bisect.bisect_right(xx,x1)-1;bottom=bisect.bisect_left(yy,y0);top=bisect.bisect_right(yy,y1)-1
  for y in range(max(0,bottom),min(80,top)):out[y]|=span(max(0,lo),min(80,hi))
 return out

def fixture_checks():
 xx=coords(-1)[1];yy=coords(-1)[1]
 polys=[e.fp([[-1,-1],[0,-1],[-1,0]]),e.fp([[-.9,-.9],[-.1,-.8],[-.2,-.1],[-.8,-.2]]),e.fp([[-1,-1],[-.5,-1],[-.5,0],[-1,0]])]
 cases=0
 for poly in polys:
  contained=poly_rows(poly,xx,yy,True);positive=poly_rows(poly,xx,yy,False)
  for x,y in [(0,0),(79,79),(39,40),(40,39),(20,30),(5,8),(70,17),(12,64),(49,29),(35,35)]:
   rect=[F(xx[x],D),F(yy[y],D),F(xx[x+1],D),F(yy[y+1],D)];exact_inside=e.exact_union(p.rectpoly(rect),[poly])==0;exact_overlap=ad.intersection_area(p.rectpoly(rect),poly)>0;assert bool(contained[y]>>x&1)==exact_inside and bool(positive[y]>>x&1)==exact_overlap;cases+=1
 return {'all_pass':True,'exact_halfplane_oracle_cases':cases,'negative_coordinates':True,'touching_boundaries_zero_positive_area':True}

def prepare():
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(90,)*2);fixtures=fixture_checks();old=read(PLAN);asset=next(v for v in old['assets']if v['asset_key']==KEY);source=read(R/asset['source_render_path']);master=read(R/asset['source_master_path']);owners,cuts=ad.source_contract(master,asset['rule'],asset['source_pitch_m']);assert owners==asset['source_polygon_owners']and cuts==asset['source_component_cuts'];assert len({tuple(o['semantic_key'])for o in owners})==1 and all(o['top_y_m']==0 for o in owners);assert sha(R/asset['source_master_path'])==asset['source_master_sha256']and sha(R/asset['source_render_path'])==asset['source_render_sha256']
 faces=[];grids=collections.defaultdict(list)
 for gi,g in enumerate(source['groups']):
  if g['material']!=asset['rule']['material']:continue
  for qi,q in enumerate(g['quads']):
   try:rect=a.top_rectangle(q)
   except ValueError:continue
   assert q[0][1]==0;rm=[v*P for v in rect];f={'source_face_ref':[gi,qi],'source_quad_sha256':digest(q),'rect_uv_m':rm};faces.append(f)
   for patch in a.previous.patches(rect):
    grid=tuple(patch['grid_xy'])
    if f not in grids[grid]:grids[grid].append(f)
 rows=[];empty=[];totals=collections.Counter();maskmap={}
 for (ix,iy),fs in sorted(grids.items()):
  bounds=[ix,iy,ix+1,iy+1];local=[o for o in owners if p.intersects(bounds,o['bounds_uv_m'])];walk=[e.fp(o['polygon_uv_m'])for o in local]
  if not walk:empty.append([ix,iy]);continue
  region,before=audit6.owned_domain(e.fp(p.rectpoly(bounds)),walk,[e.fp(c['polygon_uv_m'])for c in cuts]);domain=[]
  for f in fs:
   for poly in region:
    part=p.intersection(poly,e.fp(p.rectpoly(f['rect_uv_m'])))
    if e.area(part)>0:domain.append(part)
  exact_area=sum(e.area(poly)for poly in domain)
  if exact_area==0:empty.append([ix,iy]);continue
  xv,xx=coords(ix);yv,yy=coords(iy);actual=actual_rows([f['rect_uv_m']for f in fs],xx,yy);single=[0]*80;possible=[0]*80;cutmask=[0]*80
  for poly in walk:
   for y,v in enumerate(poly_rows(poly,xx,yy,True)):single[y]|=v
   for y,v in enumerate(poly_rows(poly,xx,yy,False)):possible[y]|=v
  for cut in cuts:
   if cut['y_interval_m'][1]<0 or cut['y_interval_m'][0]>.0375:continue
   for y,v in enumerate(poly_rows(e.fp(cut['polygon_uv_m']),xx,yy,False)):cutmask[y]|=v
  safe=[single[y]&actual[y]&~cutmask[y]&MASK for y in range(80)];fallback=unions=0
  for y in range(80):
   fringe=possible[y]&actual[y]&~single[y]&~cutmask[y]&MASK
   for x0,x1 in ranges(fringe):
    for x in range(x0,x1):
     rect=[xv[x],yv[y],xv[x+1],yv[y+1]];fallback+=1
     if e.exact_union(p.rectpoly(rect),walk)==0:
      assert a.polygons.uncovered_area_by_union([[float(v)for v in q]for q in p.rectpoly(rect)],[[[float(v)for v in q]for q in poly]for poly in walk],0)==0
      safe[y]|=1<<x;unions+=1
  n=sum(v.bit_count()for v in safe)
  if n==0:empty.append([ix,iy]);totals['lost_empty_source_domain_microm2']+=round(float(exact_area)*1e6);continue
  allowed=runs(safe);forbidden=runs([MASK^v for v in safe]);safe_area=sum((xv[z]-xv[x])*(yv[w]-yv[y])for x,y,z,w in allowed);assert safe_area<=exact_area;maskmap[(ix,iy)]=safe
  xs=[x for x,y,z,w in allowed];xe=[z for x,y,z,w in allowed];ys=[y for x,y,z,w in allowed];ye=[w for x,y,z,w in allowed];bbox=[min(xs),min(ys),max(xe),max(ye)];rectangular=n==(bbox[2]-bbox[0])*(bbox[3]-bbox[1]);seed=[41873,41879,41887][(ix*17+iy*31)%3]
  rows.append({'grid_xy_m':[ix,iy],'source_plane_y_m':0,'source_face_refs':[f['source_face_ref']for f in fs],'source_owner_ids':[o['operation']for o in local],'allowed_cell_runs_xy':allowed,'forbidden_cell_runs_xy':forbidden,'mask_sha256':digest(allowed),'safe_cell_count':n,'safe_area_m2':float(safe_area),'exact_source_domain_area_m2':float(exact_area),'fine_grid_loss_m2':float(exact_area-safe_area),'bbox_cells_xy':bbox,'rectangular':rectangular,'seed':seed,'union_fallback_cells':fallback,'multi_owner_union_cells':unions});totals['safe_cells']+=n;totals['fallback_cells']+=fallback;totals['multi_owner_union_cells']+=unions;totals['full_modules']+=n==6400;totals['rectangular_modules']+=rectangular;totals['partial_mask_modules']+=not rectangular
  if len(rows)%50==0:print(json.dumps({'grids':len(rows),'elapsed':time.monotonic()-start,'counts':dict(totals)}),flush=True)
 preserved=0
 for oldp in asset['placements']:
  x0,y0,x1,y1=[a.strict_grid(v)for v in oldp['bounds_uv_m']]
  for x in range(x0,x1):
   for y in range(y0,y1):
    ix,xx=divmod(x,80);iy,yy=divmod(y,80);assert maskmap[(ix,iy)][yy]>>xx&1;preserved+=1
 assert preserved==112.25*6400
 deps={str(q.relative_to(R)):sha(q)for q in [PLAN,Path(__file__),Path(ad.__file__),Path(e.__file__),Path(p.__file__),Path(audit6.__file__),Path(a.common.__file__),Path(a.edge.__file__),Path(b.core.__file__),R/'voxel_character/common/render_data.py',R/'voxel_character/tools/mesh.py',a.HERE/'author_r03.py',R/asset['source_master_path'],R/asset['source_render_path']]}
 result={'schema':'riverstone.native_access.whole_asset_mask_input.v1','asset_key':KEY,'source_plan':ref(PLAN),'source_dependencies':deps,'actual_faces':faces,'grids':rows,'rejected_empty_grids':empty,'fixture_checks':fixtures,'summary':{**dict(totals),'grid_modules':len(rows),'existing_area_m2':112.25,'preserved_original_cells':preserved,'lost_original_cells':0,'source_domain_area_m2':sum(r['exact_source_domain_area_m2']for r in rows),'safe_area_m2':sum(r['safe_area_m2']for r in rows),'fine_grid_boundary_loss_m2':sum(r['fine_grid_loss_m2']for r in rows),'added_safe_area_m2':sum(r['safe_area_m2']for r in rows)-112.25,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'new_geometry_bytes':0},'pipeline':'Exact integer half-plane full-footprint masks with exact rational union fallback; original actual quad union and original component cut exclusion. Common compiler not run.','same_metremetre_grid_and_seed_phase':True,'production_binding_changed':False};save(H/'prepared_masks.json',result);print(json.dumps(result['summary']),flush=True)
if __name__=='__main__':prepare()
