"""Independent exact native-cell/finite-plane check of the southern cover."""
import sys,pathlib,json,hashlib,math,collections
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'assemblies/waterworks/registered_bridge';A=BASE/'south_approach_r02'
from world_city.runtime_city.checks import placement as g
read=lambda p:json.loads(pathlib.Path(p).read_bytes())
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def write(p,d):
 with p.open('x') as f:json.dump(d,f,separators=(',',':'),allow_nan=False);f.write('\n')
def plane(tri):
 a,b,c=tri;dx1,dz1=b[0]-a[0],b[2]-a[2];dx2,dz2=c[0]-a[0],c[2]-a[2];dy1,dy2=b[1]-a[1],c[1]-a[1];den=dx1*dz2-dx2*dz1
 return [(dy1*dz2-dy2*dz1)/den,(dx1*dy2-dx2*dy1)/den]
def pheight(r,x,z):
 gx,gz,c=r['plane_local_y'];return gx*x+gz*z+c
def bounds(p):return [min(q[0] for q in p),min(q[1] for q in p),max(q[0] for q in p),max(q[1] for q in p)]
def overlap(a,b):return a[0]<=b[2]+1e-10 and a[2]>=b[0]-1e-10 and a[1]<=b[3]+1e-10 and a[3]>=b[1]-1e-10
def cells(d):return {tuple(c[:3]) for c in d['cells']}
def columns(d):
 c=collections.defaultdict(list)
 for x,y,z,*_ in d['cells']:c[x,z].append(y)
 return {k:(min(v)*d['pitch'],(max(v)+1)*d['pitch']) for k,v in c.items()}
def main():
 p=read(A/'profile.json');pack=read(A/'resolved_placements.json');assets=pack['assets'];coarse=read(ROOT/assets['recessed_fixed']['compiled']['path']);fine=read(ROOT/assets['visible_cover']['compiled']['path']);old=read(BASE/'drawbridge_candidate/cache/stone_approaches.pitch_0.25.compiled.json');cc,fc,oc=columns(coarse),columns(fine),cells(old);removed=oc-cells(coarse);added=cells(coarse)-oc;issues=[]
 if added:issues.append('Derived coarse assembly unexpectedly adds native cells.')
 bad=[q for q in removed if not(64<=q[0]*.25<72 and -3.55-.125<=(q[2]+.5)*.25<=3.55+.125 and 1<=q[1]*.25<2.5)]
 if bad:issues.append('Coarse changes escape declared source-cut extent.')
 tris=p['triangles'];polys=[r['polygon_local_xz_m'] for r in tris];pbs=list(map(bounds,polys));source_area=sum(g.polygon_area(q) for q in polys)
 pair_overlap=sum(g.intersection_area(a,b) for i,a in enumerate(polys) for b in polys[i+1:])
 if pair_overlap>1e-8:issues.append('Positive-area overlap between continuous top triangles.')
 render=read(ROOT/assets['visible_cover']['render']['path']);up=[]
 for gi,group in enumerate(render['groups']):
  for qi,q in enumerate(group['quads']):
   # Common greedy upward quads have outward quad normal (cross Y > 0); RenderData reverses triangle winding for Godot.
   a,b,c=q[:3];ny=(b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2])
   if abs(max(v[1] for v in q)-min(v[1] for v in q))<1e-10 and ny>0:
    up.append({'group_index':gi,'quad_index':qi,'y':q[0][1],'polygon_xz_m':[[v[0],v[2]] for v in q]})
 # Exact positive-area coplanar upward-face comparison against derived native base.
 coarse_render=read(ROOT/assets['recessed_fixed']['render']['path']);coplanar=[]
 for group in coarse_render['groups']:
  for q in group['quads']:
   a,b,c=q[:3];ny=(b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2])
   if ny<=0 or max(v[1] for v in q)-min(v[1] for v in q)>1e-10:continue
   poly=[[v[0],v[2]] for v in q]
   for face in up:
    if abs(face['y']-q[0][1])>1e-9:continue
    hit=g.convex_intersection(poly,face['polygon_xz_m']);ar=g.polygon_area(hit)
    if ar>1e-9:coplanar.append({'area_m2':ar,'y':q[0][1],'polygon_xz_m':hit})
 if coplanar:issues.append('Native cover/base have positive-area coplanar top faces.')
 covered=[0.]*len(tris);max_error=0.;min_error=1e9;max_signed=-1e9;checked=0
 for face in up:
  q=face['polygon_xz_m'];qb=bounds(q)
  for i,r in enumerate(tris):
   if not overlap(qb,pbs[i]):continue
   hit=g.convex_intersection(q,polys[i]);ar=g.polygon_area(hit)
   if ar<1e-12:continue
   covered[i]+=ar
   for x,z in hit:
    e=face['y']-pheight(r,x,z);max_error=max(max_error,abs(e));min_error=min(min_error,e);max_signed=max(max_signed,e);checked+=1
 uncovered=[max(0,g.polygon_area(poly)-c) for poly,c in zip(polys,covered)]
 if max(uncovered)>1e-7:issues.append('Actual fine top leaves finite collision profile uncovered.')
 if max_error>.03:issues.append('Visual/physical error exceeds declared 3 cm acceptance bound.')
 # Top ownership from disjoint native column rectangles, so sum is exact unique area.
 native_area=len(fc)*fine['pitch']**2;spill=native_area-sum(covered)
 b=p['frame']['basis'];t=p['frame']['translation'];world=lambda v:[t[i]+sum(b[i][j]*v[j] for j in range(3)) for i in range(3)]
 # Index exact completed-scene floor triangles. No analytic floor invented for support.
 scene=read(CITY/'traversal_r5/geometry/SOUTH_NATIVE_TERMINAL_TO_COUNTRY.json');index=collections.defaultdict(list);ground=[]
 for tri in scene['triangles']:
  poly=[[v[0],v[2]] for v in tri]
  if g.polygon_area(poly)<1e-10:continue
  gx,gz=plane(tri);a=tri[0];rec=(poly,gx,gz,a[1]-gx*a[0]-gz*a[2]);idx=len(ground);ground.append(rec);bb=bounds(poly)
  for ix in range(math.floor(bb[0]),math.floor(bb[2])+1):
   for iz in range(math.floor(bb[1]),math.floor(bb[3])+1):index[ix,iz].append(idx)
 def support(x,z):
  opts=[];ix,iz=math.floor(x/.25+1e-9),math.floor(z/.25+1e-9)
  for jx in [ix-1,ix]:
   for jz in [iz-1,iz]:
    if jx*.25-1e-9<=x<=(jx+1)*.25+1e-9 and jz*.25-1e-9<=z<=(jz+1)*.25+1e-9 and (jx,jz) in cc:opts.append(cc[jx,jz][1])
  v=world([x,0,z])
  for j in index[math.floor(v[0]),math.floor(v[2])]:
   poly,gx,gz,c=ground[j]
   if g.point_in_convex_polygon([v[0],v[2]],poly,1e-9):opts.append(gx*v[0]+gz*v[2]+c)
  return max(opts) if opts else None
 unsupported=[];min_embed=1e9;sample_count=0;pitch=fine['pitch']
 for (ix,iz),(bottom,top) in fc.items():
  for dx,dz in [(0,0),(.5,.5),(0,1),(1,0),(1,1)]:
   x,z=(ix+dx)*pitch,(iz+dz)*pitch;h=support(x,z);sample_count+=1
   if h is None or h<bottom-1e-8:
    if len(unsupported)<100:unsupported.append({'x':x,'z':z,'bottom':bottom,'support':h})
   elif h<top+.1:min_embed=min(min_embed,h-bottom)
 if unsupported:issues.append('Some native cover column/corner bearings are unsupported by actual coarse/scene surfaces.')
 # Exact seam heights: first section against unchanged native top, last section against source road.
 first=p['sections_local_xyz_m'][0];last=p['sections_local_xyz_m'][-1];seams=[]
 for name,sec,expected in [('native_start',first,2.),('country_end',last,1.25)]:
  for f in [i/32 for i in range(33)]:
   v=[sec[0][i]*(1-f)+sec[1][i]*f for i in range(3)];actual=support(v[0]-(1e-5 if name=='native_start' else 0),v[2]);seams.append({'seam':name,'fraction':f,'profile_y':v[1],'underlying_y':actual,'target_y':expected})
 if any(abs(r['profile_y']-r['target_y'])>1e-9 for r in seams):issues.append('Source endpoint height mismatch.')
 changed_bounds={'min':[min(q[i]*.25 for q in removed) for i in range(3)],'max':[max((q[i]+1)*.25 for q in removed) for i in range(3)]}
 report={'status':'pass_bounded_native_geometry' if not issues else 'fail','issues':issues,'inputs':{'profile':ref(A/'profile.json'),'pack':ref(A/'resolved_placements.json'),'baseline_failure':ref(CITY/'traversal_r5/freeze_initial.json'),'scene_collision':ref(CITY/'traversal_r5/geometry/SOUTH_NATIVE_TERMINAL_TO_COUNTRY.json'),'checker':ref(pathlib.Path(__file__))},'source':{'triangles':len(tris),'area_m2':source_area,'maximum_grade':max(math.hypot(*plane(r['triangle_local_xyz_m'])) for r in tris),'positive_area_overlap_m2':pair_overlap,'first_section_world':p['sections_world_xyz_m'][0],'last_section_world':p['sections_world_xyz_m'][-1]},'coarse_delta':{'removed_cells':len(removed),'added_cells':len(added),'removed_cell_bounds_local':changed_bounds,'outside_source_extent_removed':len(bad),'original_cells':len(oc),'derived_cells':len(cells(coarse))},'visible_cover':{'pitch_m':pitch,'native_columns':len(fc),'native_unique_top_area_m2':native_area,'upward_quads':len(up),'native_base_coplanar_top_area_m2':sum(r['area_m2'] for r in coplanar),'coplanar_faces':coplanar,'profile_covered_area_m2':sum(covered),'uncovered_area_m2':sum(uncovered),'per_triangle_uncovered_m2':uncovered,'visual_spill_apron_m2':spill,'visual_to_collision_max_abs_m':max_error,'visual_minus_collision_range_m':[min_error,max_signed],'exact_clipped_vertex_samples':checked},'support':{'column_centers_and_corners':sample_count,'minimum_measured_embed_m':min_embed,'unsupported_samples':unsupported,'seams':seams},'limits':['Finite source/native support and alignment only. Actual generic-capsule outcomes are separate.','Continuous collision is only the declared seven-metre lane; visible sampling apron is not an approved crossing route.','Central moving span, gameplay traffic, carts and navigation are not covered.']}
 write(H/'evidence/native_audit.json',report);write(H/'geometry/visible_upward_faces.json',{'source':ref(ROOT/assets['visible_cover']['render']['path']),'local_upward_faces':up,'frame':p['frame']});print(json.dumps({k:v for k,v in report.items() if k in ['status','issues','source','coarse_delta','visible_cover']}));print('SUPPORT',sample_count,min_embed,len(unsupported));return bool(issues)
if __name__=='__main__':sys.exit(main())
