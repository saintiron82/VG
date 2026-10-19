"""Independent bounded geometry/ownership audit; reads sealed source/native meshes only."""
import sys,json,pathlib,hashlib,math,collections,time
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
from world_city.concept_city_v3.registered_topography.revisions.r10_density_reservoir import author as r10
from world_city.concept_city_v3.registered_topography.revisions.r11_ground_materials import author as r11
C=ROOT/'world_city/concept_city_v3';issues=[];inputs={}
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def bind(p,want=None):
 p=pathlib.Path(p);h=sha(p);assert want is None or h==want,(str(p),h,want);inputs[str(p.relative_to(ROOT))]=h;return json.loads(p.read_text()) if p.suffix=='.json' else None
def area(p):
 if len(p)<3:return 0.
 a=p[0];return abs(sum((p[i][0]-a[0])*(p[i+1][1]-a[1])-(p[i][1]-a[1])*(p[i+1][0]-a[0]) for i in range(1,len(p)-1)))/2

def tidy(p):
 out=[]
 for q in p:
  if not out or math.dist(q,out[-1])>1e-12:out.append(q)
 if len(out)>1 and math.dist(out[0],out[-1])<=1e-12:out.pop()
 return out
def intersection(p,q):return geo.convex_intersection(tidy(p),tidy(q))
def overlap(p,q):return area(intersection(p,q))
def centre(p):return [sum(v[k] for v in p)/len(p) for k in (0,1)]
def difference(p,qs):
 parts=[tidy(p)]
 for q in qs:
  parts=[tidy(t) for pp in parts for t in geo.convex_difference(tidy(pp),tidy(q)) if area(t)>1e-11]
 return parts

def uncovered(ps,qs):
 ix=geo._SpatialIndex(16)
 for i,q in enumerate(qs):ix.add(i,q)
 return sum(area(t) for p in ps for t in difference(p,[qs[i] for i in ix.candidates(p)]))
def index(records,key='polygon_xz_m',cell=16):
 ix=geo._SpatialIndex(cell)
 for i,r in enumerate(records):ix.add(i,r[key])
 return ix

def hits(p,records,ix,tolerance=1e-7):
 return [(i,overlap(p,records[i]['polygon_xz_m'])) for i in ix.candidates(p) if overlap(p,records[i]['polygon_xz_m'])>tolerance]

def partition(records,bounds):
 ix=index(records);double=sum(overlap(r['polygon_xz_m'],records[j]['polygon_xz_m']) for i,r in enumerate(records) for j in ix.candidates(r['polygon_xz_m']) if j>i)
 total=sum(area(r['polygon_xz_m']) for r in records);expected=(bounds[2]-bounds[0])*(bounds[3]-bounds[1]);return dict(bounds=bounds,records=len(records),sum_area_m2=total,expected_area_m2=expected,area_error_m2=abs(total-expected),pairwise_overlap_m2=double)
def samples(p,step=.5):
 out=p+[centre(p)]
 for a,b in zip(p,p[1:]+p[:1]):
  n=max(1,math.ceil(math.dist(a,b)/step));out.extend([[(1-i/n)*a[k]+i/n*b[k] for k in (0,1)] for i in range(1,n)])
 return out

def tiles(polys,size=16):
 out=set()
 for p in polys:
  for i in range(math.floor(min(q[0] for q in p)/size),math.floor(max(q[0] for q in p)/size)+1):
   for j in range(math.floor(min(q[1] for q in p)/size),math.floor(max(q[1] for q in p)/size)+1):
    b=[i*size,j*size,(i+1)*size,(j+1)*size];q=[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]]
    if overlap(p,q)>1e-9:out.add(tuple(b))
 return sorted(out)

def grade(t):
 a,b,c=t;u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)];det=u[0]*v[2]-u[2]*v[0];return math.hypot((u[1]*v[2]-u[2]*v[1])/det,(u[0]*v[1]-u[1]*v[0])/det)
for d in [r10.HERE,r11.HERE]:
 seal=bind(d/'freeze_manifest.json')
 for f,h in seal['files'].items():bind(d/f,h)
matpath=C/'registered_integration/r4/material_candidate.json';mat=bind(matpath,'2684871a3e975fdbabe287e435b84f8952e57e7e43489b98b46259011924be53');original=bind(C/'registered_integration/r4/candidate.json',mat['provenance']['material_promotion']['parent_sha256'])
for f in mat['provenance']['input_packs']:bind(ROOT/f['path'],f['sha256'])
for k in ['common_instances','common_assets','floor_ownership_masks','remove_proxy_ids','replace_plot_ids','replace_landmark_groups','access_overlay']:assert mat[k]==original[k],k
assert len({p['id'] for p in mat['common_instances']})==len(mat['common_instances'])
D=bind(r10.DENSITY_PATH,r10.DENSITY_SHA);south=bind(r10.SOUTH_PATH,r10.SOUTH_SHA)
water=r10.finite_water_polygons();wi=index(water);roads=[r for r in r10.r07._owners() if r['kind']=='road'];ri=index(roads)
print('Bound frozen r4/r10/r11 inputs',flush=True)
# SOUTH: exact coverage of all six planar road triangles through the actual terrain consumer.
sp=[r['polygon_xz_m'] for r in south['triangles']];south_records=[];south_partitions=[]
for b in tiles(sp):
 rs=r11.surface_domains(b,False);south_partitions.append(partition(rs,b));south_records+=rs
roadpieces=[r['polygon_xz_m'] for r in south_records if r.get('road_id')==south['route_id']]
south_gaps=uncovered(sp,roadpieces);south_excess=uncovered(roadpieces,sp)
assert south_gaps<1e-7 and south_excess<1e-7,(south_gaps,south_excess)
profile_errors=[]
for r in south_records:
 if r.get('road_id')!=south['route_id']:continue
 for q in samples(r['polygon_xz_m']):
  expected=r10.R04.point_y(r['triangle_xyz_m'],*q);delta=r11.surface_height_at(r,*q)-expected
  if abs(delta)>1e-8:profile_errors.append([q,delta])
assert not profile_errors
# Actual cache terminal strip, transformed from compiled native mesh rather than declared floor.
bridge=bind(ROOT/south['native_bridge']['path'],south['native_bridge']['sha256']);render=bind(ROOT/south['native_bridge']['render_path'],south['native_bridge']['render_sha256'])
placement=bridge['placements'][0];basis=placement['transform']['basis'];position=placement['transform']['translation']
def world(v):return [position[k]+sum(basis[k][j]*v[j] for j in range(3)) for k in range(3)]
up=[]
for g in render['groups']:
 for q in g['quads']:
  u=[q[1][k]-q[0][k] for k in range(3)];v=[q[2][k]-q[0][k] for k in range(3)];ny=u[2]*v[0]-u[0]*v[2]
  if ny>0 and max(p[0] for p in q)>=71.75 and abs(q[0][1]-1.25)<1e-8:up.append([[p[0],p[2]] for p in q])
strip=[[71.75,-3.5],[72,-3.5],[72,3.5],[71.75,3.5]];native_strip_gap=uncovered([strip],up);assert native_strip_gap<1e-9
seam=[world([72,1.25,z]) for z in [-3.5,3.5]]
assert max(math.dist(a,b) for a,b in zip(seam,south['native_shared_edge_xyz_m']))<1e-8
seam_errors=[];seam_owners=[]
for i in range(141):
 q=world([72,1.25,-3.5+7*i/140]);nextq=[(1-i/140)*south['cross_sections_xyz_m'][1][0][k]+i/140*south['cross_sections_xyz_m'][1][1][k] for k in range(3)];testq=[q[k]+1e-5*(nextq[k]-q[k]) for k in range(3)];r=r11.owner_at(testq[0],testq[2]);seam_owners.append(r['kind']);seam_errors.append(abs(r11.source_surface_height_at(r,q[0],q[2])-1.25))
assert set(seam_owners)=={'external_triangular_surface'} and max(seam_errors)<1e-8
walking=slab_rectangles(render,1.30,3.05);assert sum(overlap(strip,p) for p in walking)<1e-8
water_overlap=sum(overlap(p,w['polygon_xz_m']) for p in sp for w in water);assert water_overlap<1e-8
# Exterior sides/end are finite cut/fill edges, not silently certified as supported routes.
edge_ledger=[]
sections=south['cross_sections_xyz_m']
for side in [0,1]:
 for segment in range(len(sections)-1):
  a,b=sections[segment][side],sections[segment+1][side];centreseg=[(sum(p[0] for p in sections[segment])+sum(p[0] for p in sections[segment+1]))/4,(sum(p[2] for p in sections[segment])+sum(p[2] for p in sections[segment+1]))/4];middle=[(a[0]+b[0])/2,(a[2]+b[2])/2];normal=[middle[k]-centreseg[k] for k in (0,1)];L=math.hypot(*normal);normal=[v/L for v in normal];diff=[];owners=set()
  for i in range(101):
   q=[(1-i/100)*a[k]+i/100*b[k] for k in range(3)];outside=[q[0]+normal[0]*1e-4,q[2]+normal[1]*1e-4];o=r11.owner_at(*outside);owners.add(o['kind']);diff.append(q[1]-r11.source_surface_height_at(o,*outside))
  edge_ledger.append(dict(side=side,segment=segment,outside_owner_kinds=sorted(owners),height_delta_range_m=[min(diff),max(diff)]))
south_result=dict(source_triangles=len(sp),source_area_m2=sum(map(area,sp)),full_width_source_uncovered_m2=south_gaps,unexpected_road_area_m2=south_excess,maximum_full_triangle_grade=max(grade(t['vertices_xyz_m']) for t in south['triangles']),native_terminal_strip_gap_m2=native_strip_gap,native_full_width_seam_samples=len(seam_errors),maximum_native_seam_error_m=max(seam_errors),water_overlap_m2=water_overlap,partitions=south_partitions,exterior_edge_ledger=edge_ledger,endpoint_status='Explicit off-city boundary; countryside continuation and painted barbican absent.')
(HERE/'south_progress.json').write_text(json.dumps(south_result,indent=2)+'\n');print('South finite coverage/native seam pass',flush=True)
# B015: reconstruct all native foundation sections and walking-height obstruction projections.
renders={};foundation=[];walking=[]
for key,a in D['assets'].items():
 for kind in ['render','master','compiled']:
  if kind+'_path' in a:bind(ROOT/a[kind+'_path'],a[kind+'_sha256'])
 renders[key]=json.loads((ROOT/a['render_path']).read_text())
for inst in D['placements']:
 mesh=renders[inst['asset_key']];y=2.5-inst['position_m'][1]
 fs=[transform(p,inst) for p in slab_rectangles(mesh,y-.5,y)];mask=next(m for m in D['ownership_masks'] if m['owner_id']==inst['id'])['terrain_exclusion_regions_xz_m']
 assert uncovered(fs,mask)<1e-7 and uncovered(mask,fs)<1e-7,inst['id']
 foundation += [dict(owner_id=inst['id'],polygon_xz_m=p) for p in fs]
 walking += [dict(owner_id=inst['id'],polygon_xz_m=transform(p,inst)) for p in slab_rectangles(mesh,y+.05,y+1.85)]
assert len(foundation)==59
print('B015 native mesh sections reconstructed',flush=True)
fsi=index(foundation);wsi=index(walking)
for f in foundation:
 assert not hits(f['polygon_xz_m'],water,wi) and not hits(f['polygon_xz_m'],roads,ri)
# Native group identity: 10 actual instances, no duplicate 28 semantic bodies or retained old owners.
instances={p['id']:p for p in mat['common_instances']}
assert not(set(D['replaced_placement_ids'])&instances.keys()) and not(set(p['id'] for p in D['component_placements'])&instances.keys())
for p in D['placements']:
 i=instances[p['id']]
 for k in ['position_m','yaw_rad','asset_key']:assert i[k]==p[k]
 assert mat['common_assets'][p['asset_key']]['render_sha256']==p['render_sha256']
paths=[dict(id=d['id'],polys=d['reserved_connection_polygons_xz_m']+d.get('reserved_round_join_polygons_xz_m',[]),line=d['complete_proposed_connection_xz_m'],width=d['width_m']) for d in D['access_proposals']]+[dict(id=d['id'],polys=d['reserved_polygons_xz_m']+d.get('reserved_round_join_polygons_xz_m',[]),line=d['polyline_xz_m'],width=d['width_m']) for d in D['court_paths']+D['ground_service_paths']]
rounded_join_count=0
for path in paths:
 for q in path['line'][1:-1]:
  radius=path['width']/2/math.cos(math.pi/32);disc=[[q[0]+radius*math.cos(j*math.pi/16),q[1]+radius*math.sin(j*math.pi/16)] for j in range(32)]
  path['polys'].append(disc);rounded_join_count+=1
path_errors=[];allpathpolys=[]
for path in paths:
 allpathpolys+=path['polys']
 for p in path['polys']:
  for category,records,ix in [('water',water,wi),('native_walking_slab',walking,wsi)]:
   for i,a in hits(p,records,ix):path_errors.append(dict(id=path['id'],kind=category,area_m2=a,obstacle=records[i].get('owner_id',records[i].get('surface_id'))))
  for q in samples(p):
   o=r11.owner_at(*q);delta=r11.source_surface_height_at(o,*q)-2.5
   if abs(delta)>1e-7 or (not o.get('render_land',True) and o['kind']!='b015_native_hole'):path_errors.append(dict(id=path['id'],kind='support',point=q,owner=o['owner_id'],delta_m=delta))
assert not path_errors,path_errors[:5]
print('B015 all route widths/slab/water/profile checks pass',flush=True)
for d in D['access_proposals']:
 p=d['actual_door_xyz_m'];assert abs(r11.height_at(p[0],p[2])-p[1])<1e-8
b15_bounds_tiles=tiles([f['polygon_xz_m'] for f in foundation]+allpathpolys+[d['polygon_xz_m'] for d in D['courts']]);b15_partitions=[];foundation_holes=[];path_visible=[]
for b in b15_bounds_tiles:
 rs=r11.surface_domains(b,False);b15_partitions.append(partition(rs,b));assert not any(r10.R04.prior.is_excluded(r,r10.EXCLUDED) for r in rs)
 foundation_holes.extend(r['polygon_xz_m'] for r in rs if r['kind']=='b015_native_hole');path_visible.extend(r['polygon_xz_m'] for r in rs if r.get('render_land',True))
print('B015 partitions collected',len(b15_partitions),flush=True)
foundation_uncovered=uncovered([f['polygon_xz_m'] for f in foundation],foundation_holes);foundation_excess=uncovered(foundation_holes,[f['polygon_xz_m'] for f in foundation]);assert foundation_uncovered<1e-7 and foundation_excess<1e-7
path_hidden=uncovered(allpathpolys,path_visible);assert path_hidden<1e-7,path_hidden
fixed=next(p for p in paths if p['id']=='DENS_B15E_HOUSE_020:ACTUAL_DOOR:1')
b15_result=dict(native_groups=len(D['placements']),actual_doors=len(D['access_proposals']),foundation_regions=len(foundation),walking_slabs=len(walking),full_width_routes=len(paths),round_joins_checked=rounded_join_count,route_polygons=len(allpathpolys),route_errors=path_errors,foundation_owner_uncovered_m2=foundation_uncovered,foundation_owner_excess_m2=foundation_excess,hidden_route_area_m2=path_hidden,repaired_dry_route=dict(id=fixed['id'],polygons=fixed['polys'],water_overlap_m2=0),partitions=b15_partitions,door_semantics='Closed exterior native doors; thresholds checked, no pass-through interior route certified.')
(HERE/'b015_progress.json').write_text(json.dumps(b15_result,indent=2)+'\n');print('B015 actual foundation masks and full-width dry ribbons pass',flush=True)
# MATERIALS: all 700 semantic regions, every touched tile; group by exact underlying owner.
for n in ['source_surface_height_at','surface_height_at','height_at','land_height_at','road_height_at','path_height_at']:assert getattr(r11,n) is getattr(r10,n)
material_tiles=tiles([r['polygon_xz_m'] for r in r11.REGIONS]);material_results=[];changed_records=0;max_height_delta=0;max_owner_area_delta=0
for ti,b in enumerate(material_tiles):
 old=r10.surface_domains(b,False);new=r11.surface_domains(b,False);op=collections.defaultdict(list);np=collections.defaultdict(list)
 def identity(r):return (r['owner_id'],r['kind'],r.get('render_land',True),r.get('road_id'),r.get('profile_domain_id'))
 for r in old:op[identity(r)].append(r['polygon_xz_m'])
 for r in new:np[identity(r)].append(r['polygon_xz_m'])
 assert op.keys()==np.keys(),b
 for k in op:
  delta=uncovered(op[k],np[k])+uncovered(np[k],op[k]);max_owner_area_delta=max(delta,max_owner_area_delta)
  if delta>1e-7:issues.append(dict(kind='material_owner_changed',bounds=b,owner=k,area_m2=delta))
 for r in new:
  if r.get('material_change_only'):changed_records+=1;assert r10.OWNERS is r11.prior.OWNERS and r11.eligible(r)
  q=centre(r['polygon_xz_m']);o=next(s for s in old if identity(s)==identity(r) and geo.point_in_convex_polygon(q,s['polygon_xz_m'],1e-7));delta=abs(r11.source_surface_height_at(r,*q)-r10.source_surface_height_at(o,*q));max_height_delta=max(max_height_delta,delta)
 result=partition(new,b);material_results.append(result)
 if ti%25==0:print('Material tiles',ti+1,'/',len(material_tiles),flush=True)
assert max_height_delta<1e-9 and not issues
allparts=south_partitions+b15_partitions+material_results
assert max(p['area_error_m2'] for p in allparts)<1e-6 and max(p['pairwise_overlap_m2'] for p in allparts)<1e-6
for p,h in inputs.items():assert sha(ROOT/p)==h,'input changed during audit: '+p
report=dict(schema='riverstone.independent_r10_r11_geometry_review.v1',status='pass_bounded_geometry_and_material_ownership',inputs=inputs,checker_sha256=sha(__file__),south=south_result,b015=b15_result,material=dict(semantic_regions=len(r11.REGIONS),tiles=len(material_tiles),changed_records=changed_records,maximum_same_owner_symmetric_difference_m2=max_owner_area_delta,maximum_height_delta_m=max_height_delta,height_api_aliases_verified=True,native_instances_unchanged=len(mat['common_instances']),native_assets_unchanged=len(mat['common_assets']),partitions=material_results),partition_maximum_area_error_m2=max(p['area_error_m2'] for p in allparts),partition_maximum_pair_overlap_m2=max(p['pairwise_overlap_m2'] for p in allparts),issues=issues,limits=['Finite source/native geometry and consumer ownership only; no capsule/cart/navigation release.','Southern road is six continuous preview/source triangles, not completed common voxel terrain; side cut/fill and off-city endpoint remain explicit.','Material subdivision preserves height function and finite owners; independently triangulated exported surfaces may differ, so no exported triangle parity inferred.','Inherited r09 ledger has40 raw/39 unique public clips; independently checked consumer avoids double floors. Real0.125m treads and0.070887m public edge remain.','Recovered landmark public mask retains known1.46416e-6m² preview-filter residual; original route/support metadata absent.','B015 slab checks cover its actual native groups; whole-city dynamic actors and every cross-pack obstacle are outside this scope.'])
out=HERE/('report_'+sha(matpath)[:12]+'_'+sha(__file__)[:12]+'.json');out.write_text(json.dumps(report,indent=2)+'\n');print('REPORT',out,flush=True)
