#!/usr/bin/env python3
"""Read-only exact original-source eave gap measurement; no voxel compilation."""
import json, math, hashlib, time, resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS, (64*1024*1024,64*1024*1024))
resource.setrlimit(resource.RLIMIT_CPU, (45,45))
START=time.process_time()
OUT=Path(__file__).with_suffix('.json')
CAT=OUT.parent/'active_boundary_r02.catalog.json'
cat=json.loads(CAT.read_text())['assets'][0]
SRC=Path(cat['source_master_path'])
raw=SRC.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
assert sha==cat['source_sha256']
render_catalog=json.loads((OUT.parent.parent/'compiled_active_r02/registered_cathedral_nave_aisles_transept.subset_opening_008.catalog.json').read_text())['assets'][0]
render_path=Path(render_catalog['source_render_path']);render_hash=hashlib.sha256()
with render_path.open('rb') as f:
 for chunk in iter(lambda:f.read(262144),b''):render_hash.update(chunk)
render_sha=render_hash.hexdigest()
assert render_sha==render_catalog['source_render_sha256']
assert render_catalog['source_sha256']==sha
doc=json.loads(raw)
assert not doc['assembly_cuts']
assert all(set(i)<= {'id','component'} for i in doc['instances'])
assert all(not c.get('transform') for c in doc['components'])
OPS={o['id']:(c['id'],o) for c in doc['components'] for o in c['operations']}
I=[[1,0,0],[0,1,0],[0,0,1]]
def tf(o,p):
 t=o.get('transform',{}); b=t.get('basis',I); off=t.get('translation',[0,0,0])
 return [sum(b[i][j]*p[j] for j in range(3))+off[i] for i in range(3)]
def rep(c,o):
 s=o['shape']; pts=[]; p=None; axis=None
 if s['kind']=='box':
  pts=[tf(o,[x,y,z]) for x in [s['min'][0],s['max'][0]] for y in [s['min'][1],s['max'][1]] for z in [s['min'][2],s['max'][2]]]
 else:
  assert s['kind']=='extrusion'
  pts=[tf(o,[x,y,z]) for x,y in s['polygon'] for z in [s['z_min'],s['z_max']]]
  basis=o.get('transform',{}).get('basis',I)
  assert basis[1]==[0,1,0]
  axis=next(i for i in [0,2] if abs(basis[i][2])==1)
  pa=2 if axis==0 else 0
  p=[(q[pa],q[1]) for q in [tf(o,[x,y,s['z_min']]) for x,y in s['polygon']]]
 return {'id':o['id'],'component':c,'action':o['action'],'bbox':[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]],'axis':axis,'poly':p}
SHAPES=[rep(c,o) for c,o in OPS.values()]
def area(p):
 return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))))/2 if len(p)>2 else 0

def clip(subject,window):
 if not subject:return []
 signed=sum(window[i][0]*window[(i+1)%len(window)][1]-window[(i+1)%len(window)][0]*window[i][1] for i in range(len(window)))
 sg=1 if signed>0 else -1
 for i,a in enumerate(window):
  b=window[(i+1)%len(window)]
  def f(p):return sg*((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
  out=[]
  for j,p in enumerate(subject):
   q=subject[(j+1)%len(subject)];fp=f(p);fq=f(q)
   if fp>=-1e-10:out.append(p)
   if (fp>1e-10 and fq< -1e-10) or (fp< -1e-10 and fq>1e-10):
    t=fp/(fp-fq);out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
  subject=out
  if not subject:break
 return subject

def section(poly,u):
 ys=[]
 for i,p in enumerate(poly):
  q=poly[(i+1)%len(poly)]
  if min(p[0],q[0])-1e-9<=u<=max(p[0],q[0])+1e-9:
   if abs(q[0]-p[0])<1e-10:ys.extend([p[1],q[1]])
   else:ys.append(p[1]+(u-p[0])/(q[0]-p[0])*(q[1]-p[1]))
 return (min(ys),max(ys)) if ys else None

def cross(s,uaxis,vaxis,v):
 lo,hi=s['bbox']
 if not lo[vaxis]-1e-9<=v<=hi[vaxis]+1e-9:return []
 if s['axis'] is None:return [(lo[uaxis],lo[1]),(hi[uaxis],lo[1]),(hi[uaxis],hi[1]),(lo[uaxis],hi[1])]
 if s['axis']==vaxis:return s['poly']
 sy=section(s['poly'],v)
 if sy is None:return []
 return [(lo[uaxis],sy[0]),(hi[uaxis],sy[0]),(hi[uaxis],sy[1]),(lo[uaxis],sy[1])]

def union_intervals(values):
 out=[]
 for a,b in sorted(values):
  if out and a<=out[-1][1]+1e-9:out[-1][1]=max(out[-1][1],b)
  else:out.append([a,b])
 return out

def complement(a,b,blocked):
 out=[];cursor=a
 for x,y in blocked:
  if x>cursor+1e-9:out.append([cursor,x])
  cursor=max(cursor,y)
 if cursor<b-1e-9:out.append([cursor,b])
 return out

specs=[('nave_west','nave_left_0',0,'min'),('nave_east','nave_right_4',0,'max'),('aisle_-1_west','aisle_-1_left_0',0,'min'),('aisle_-1_east','aisle_-1_right_1',0,'max'),('aisle_1_west','aisle_1_left_0',0,'min'),('aisle_1_east','aisle_1_right_1',0,'max'),('transept_rear','transept_left_0',2,'min'),('transept_front','transept_right_2',2,'max')]
results=[]
for wall,roof,uaxis,outer in specs:
 vaxis=2 if uaxis==0 else 0
 w=OPS[wall][1]['shape'];u0,u1=w['min'][uaxis],w['max'][uaxis]
 v0,v1=w['min'][vaxis],w['max'][vaxis];top=w['max'][1]
 corners=[]
 if wall.startswith('transept'):
  # End-wall corner masonry continues the real eave footprint by 0.7 m each end.
  v0,v1=-17.,17.;corners=['transept_west','transept_east']
 r=next(s for s in SHAPES if s['id']==roof)
 rpoly=cross(r,uaxis,vaxis,(v0+v1)/2)
 r0=section(rpoly,u0)[0];r1=section(rpoly,u1)[0]
 slope=(r1-r0)/(u1-u0)
 a,b=u0,u1
 if r0<top and r1>top:a=u0+(top-r0)/slope
 if r1<top and r0>top:b=u0+(top-r0)/slope
 def roofy(u):return r0+slope*(u-u0)
 cand=[(a,top),(b,top),(b,max(top,roofy(b))),(a,max(top,roofy(a)))]
 ca=area(cand);cw=b-a;maxy=max(r0,r1)
 blockers=[];tested=[];partial=[]
 for s in SHAPES:
  lo,hi=s['bbox']
  if hi[1]<=top+1e-9 or lo[1]>=maxy-1e-9 or hi[uaxis]<=a+1e-9 or lo[uaxis]>=b-1e-9 or hi[vaxis]<=v0+1e-9 or lo[vaxis]>=v1-1e-9:continue
  va,vb=max(v0,lo[vaxis]),min(v1,hi[vaxis])
  pp=cross(s,uaxis,vaxis,(va+vb)/2)
  overlap=area(clip(cand,pp)) if pp else 0
  tested.append({'operation':s['id'],'intersection_cross_section_m2':overlap})
  if overlap>1e-8:
   assert s['action']=='paint',('Eave-overlapping cut needs interval CSG',s)
   assert s['axis'] in [None,vaxis],('Nonconstant longitudinal blocker',s)
   item={'operation':s['id'],'component':s['component'],'longitudinal_interval_m':[va,vb]}
   if abs(overlap-ca)<1e-7:blockers.append(item)
   else:
    item['intersection_cross_section_m2']=overlap
    partial.append(item)
 blocked=union_intervals([x['longitudinal_interval_m'] for x in blockers])
 for p in partial:
  aa,bb=p['longitudinal_interval_m']
  assert any(aa>=x-1e-9 and bb<=y+1e-9 for x,y in blocked),('Uncovered partial obstacle needs exact sweep',wall,p)
  p['effect']='Redundant: its entire longitudinal span is already fully occupied by source masonry.'
 gaps=complement(v0,v1,blocked);length=sum(b-a for a,b in gaps)
 ext=max(0,(r0 if outer=='min' else r1)-top)
 inward=max(0,(r1 if outer=='min' else r0)-top)
 results.append({'eave_strip_id':wall,'wall_operations':[wall]+corners,'source_roof_operation':roof,'cross_axis':'x' if uaxis==0 else 'z','longitudinal_axis':'z' if vaxis==2 else 'x','wall_cross_interval_m':[u0,u1],'wall_top_y_m':top,'full_wall_longitudinal_interval_m':[v0,v1],'roof_underside_y_at_cross_minmax_m':[r0,r1],'roof_slope_dy_du':slope,'raw_wall_to_roof_cross_section_polygon_m':cand,'raw_gap_cross_section_m2':ca,'positive_gap_cross_interval_m':[a,b],'gap_width_m':cw,'gap_height_range_over_positive_width_m':[max(0,min(r0,r1)-top),max(r0,r1)-top],'exterior_face_gap_height_m':ext,'interior_face_gap_height_m':inward,'original_source_blockers':blockers,'redundant_partial_intersections':partial,'blocked_longitudinal_union_m':blocked,'continuous_gap_intervals_m':gaps,'continuous_gap_segment_count':len(gaps),'total_gap_length_m':length,'horizontal_projected_gap_area_m2':cw*length,'roof_underside_contact_area_if_filled_m2':cw*length*math.sqrt(1+slope*slope),'exterior_vertical_gap_elevation_area_m2':ext*length,'interior_vertical_gap_elevation_area_m2':inward*length,'empty_gap_volume_m3':ca*length,'analytically_intersected_source_shapes':tested,'interpretation':('External source slit over entire wall thickness.' if ext>0 else 'Interior wall-top wedge only: original roof already overlaps the exterior wall-top band. Do not call this an exterior slit.')})

# Independently evaluate original source vertical intervals at representative positions.
def intervals_at(x,z):
 out=[]
 for s in SHAPES:
  lo,hi=s['bbox']
  if not(lo[0]-1e-10<=x<=hi[0]+1e-10 and lo[2]-1e-10<=z<=hi[2]+1e-10):continue
  if s['axis'] is None:iv=(lo[1],hi[1])
  else:iv=section(s['poly'],z if s['axis']==0 else x)
  if iv:out.append((s,iv))
 return out
probes=[]
for row in results:
 for va,vb in row['continuous_gap_intervals_m']:
  v=(va+vb)/2;a,b=row['positive_gap_cross_interval_m'];u=(a+b)/2
  x,z=(u,v) if row['cross_axis']=='x' else (v,u)
  top=row['wall_top_y_m'];roof= row['roof_underside_y_at_cross_minmax_m'][0]+row['roof_slope_dy_du']*(u-row['wall_cross_interval_m'][0]);y=(top+roof)/2
  hits=[s['id'] for s,iv in intervals_at(x,z) if iv[0]+1e-9<y<iv[1]-1e-9]
  assert not hits,(row['eave_strip_id'],x,y,z,hits)
  probes.append({'strip':row['eave_strip_id'],'point_m':[x,y,z],'source_hits':hits})
# Validate prior point evidence and record precise roof underside.
x,z=7.975,20.025
sample_iv=intervals_at(x,z)
prior={'xz_m':[x,z],'wall_top_y_m':OPS['nave_east'][1]['shape']['max'][1],'roof_underside_y_m':next(iv[0] for s,iv in sample_iv if s['id']=='nave_right_4')}
prior['true_source_gap_m']=prior['roof_underside_y_m']-prior['wall_top_y_m']
keys=['total_gap_length_m','horizontal_projected_gap_area_m2','roof_underside_contact_area_if_filled_m2','exterior_vertical_gap_elevation_area_m2','interior_vertical_gap_elevation_area_m2','empty_gap_volume_m3']
groups={}
for label,prefixes in [('nave',['nave_']),('aisles_outer',['aisle_-1_west','aisle_1_east']),('aisles_inner',['aisle_-1_east','aisle_1_west']),('transept',['transept_'])]:
 rr=[r for r in results if any(r['eave_strip_id'].startswith(p) for p in prefixes)]
 groups[label]={k:sum(r[k] for r in rr) for k in keys}
 groups[label]['strips']=len(rr)
 groups[label]['positive_height_range_m']=[min(r['gap_height_range_over_positive_width_m'][0] for r in rr),max(r['gap_height_range_over_positive_width_m'][1] for r in rr)]
summary={k:sum(r[k] for r in results) for k in keys}
summary['gap_segments_total']=sum(r['continuous_gap_segment_count'] for r in results)
summary['all_eave_strips_measured']=8
summary['external_slit_strips']=4
summary['interior_only_wedge_strips']=4
summary['maximum_wall_top_gap_envelope_height_m']=max(r['gap_height_range_over_positive_width_m'][1] for r in results)
summary['external_slit_strip_horizontal_area_m2']=sum(r['horizontal_projected_gap_area_m2'] for r in results if r['exterior_face_gap_height_m']>0)
summary['external_slit_strip_volume_m3']=sum(r['empty_gap_volume_m3'] for r in results if r['exterior_face_gap_height_m']>0)
tr_partition={}
for label,which in [('outer_arms_outside_nave_footprint',[0,2]),('central_crossing_inside_nave_footprint',[1])]:
 selected=[]
 for r in results:
  if r['eave_strip_id'].startswith('transept'):
   length=sum(r['continuous_gap_intervals_m'][i][1]-r['continuous_gap_intervals_m'][i][0] for i in which)
   selected.append((r,length))
 tr_partition[label]={'gap_length_m':sum(n for r,n in selected),'horizontal_area_m2':sum(r['gap_width_m']*n for r,n in selected),'empty_volume_m3':sum(r['raw_gap_cross_section_m2']*n for r,n in selected),'outer_wall_face_elevation_area_m2':sum(r['exterior_face_gap_height_m']*n for r,n in selected)}
tr_partition['interpretation']='The central transept gap remains genuine source emptiness but is inside the nave footprint and is not an exposed cathedral exterior slit. External-face terms elsewhere mean the local wall face, not a proven exterior visibility result. No rendering or visibility ray tracing was done.'

joints=[]
for family,side,wall,ga in [('nave','rear','nave_rear','nave_gable_rear'),('nave','front','nave_front','nave_gable_front'),('aisle_-1','rear','aisle_-1_rear','aisle_-1_gable_rear'),('aisle_-1','front','aisle_-1_front','aisle_-1_gable_front'),('aisle_1','rear','aisle_1_rear','aisle_1_gable_rear'),('aisle_1','front','aisle_1_front','aisle_1_gable_front'),('transept','east','transept_east','transept_gable_rear'),('transept','west','transept_west','transept_gable_front')]:
 ws=next(s for s in SHAPES if s['id']==wall); gs=next(s for s in SHAPES if s['id']==ga);axis=gs['axis'];wl,wh=ws['bbox'];gl,gh=gs['bbox']
 overlap=max(0,min(wh[axis],gh[axis])-max(wl[axis],gl[axis]));separation=max(0,max(wl[axis],gl[axis])-min(wh[axis],gh[axis]))
 joints.append({'family':family,'end':side,'wall_operation':wall,'gable_operation':ga,'depth_axis':'x' if axis==0 else 'z','lower_wall_depth_interval_m':[wl[axis],wh[axis]],'gable_panel_depth_interval_m':[gl[axis],gh[axis]],'depth_overlap_m':overlap,'depth_separation_m':separation,'gable_base_y_m':gl[1],'lower_wall_top_y_m':wh[1],'vertical_base_overlap_m':wh[1]-gl[1],'classification':'offset gable-panel joint; not an eave support volume' if separation>0 else 'overlapping gable-panel joint'})

report={'schema':'riverstone.cathedral.original_source_contact_gap_measurement.v1','status':'measurement_only_no_geometry_authoring_no_voxel_compile','source_master_path':str(SRC),'source_master_sha256':sha,'source_render_path':str(render_path),'source_render_sha256':render_sha,'source_identity_hashes_verified_against_files':True,'frozen_finished_roof_master_sha256':cat['roof_composition_sha256'],'frozen_finished_roof_loaded':False,'measurement_units':'metres, square metres, cubic metres in source master coordinates','method':{'type':'exact analytic convex polygon cross-sections and interval unions; representative original-source vertical containment checks','scope':'Actual physical wall-top footprints under the eight roof eaves, including transept end-wall eave corners. Every original operation is screened for intersection; source masonry/buttress/gable occupants are subtracted. Front/rear gable-center attic interiors are explicitly excluded.','assumptions_checked':['All source instances and components have identity transform. All primitive operation transforms preserve vertical Y and are axis-aligned horizontal rotations.','Effective obstacles cover the entire candidate eave cross-section over fixed longitudinal intervals. Every partial intersection is asserted to lie entirely inside the already fully blocked longitudinal union; no partial coverage is estimated.','No source cut intersects candidate gaps. Clerestory windows partially intersect raw transept eave cross-sections but lie entirely inside the nave-wall occupied intervals; windows remove no additional empty gap. No external library, full cell grid, or voxel compiler is used.'],'precision':'Exact source coordinates and closed-form polygon areas in binary64; boundaries/contact sets have zero volume. Numerical tolerance 1e-8 m2 for positive-area intersection.','area_definitions':{'horizontal_projected_gap_area_m2':'Plan projection of still-empty gap over physical wall-top footprint; excludes roof-wall overlap band and existing blockers.','exterior_vertical_gap_elevation_area_m2':'Gap height at outer wall face times unblocked longitudinal length; zero for aisle internal wedges.','interior_vertical_gap_elevation_area_m2':'Gap height at inner wall face times unblocked longitudinal length.','roof_underside_contact_area_if_filled_m2':'Sloping underside area covering the measured empty gap footprint.','empty_gap_volume_m3':'Whole physical wall-top gap envelope, not a mandatory architectural support volume. Narrower/periodic eave supports would occupy less and require a separate authorized source design.'}},'summary':summary,'groups':groups,'eave_strips':results,'transept_gap_visibility_scope_partition':tr_partition,'gable_panel_joints_separate_from_eaves':joints,'gable_joint_notes':['Nave front and all four aisle front/rear gable panels are separated in depth from their lower end walls by 0.1 m, despite 0.6 m vertical base overlap. Do not fill the entire projected triangle from wall top to roof.','Nave rear and both transept end gable panels overlap their lower walls in depth by 0.5 m and meet their matching roof undersides. They remove the corresponding eave-gap end segments.','Broad central end-wall vertical rays can traverse intended gable/attic interiors. These are excluded from all support-area and volume totals.','Transept side-wall boxes stop at x +/-16.3; end-wall corner masonry extends the genuine eave strip to +/-17.0. Gables fill the outermost 0.5 m, leaving 0.2 m genuine additional gap at each end before the main side-wall box.'],'source_vs_interface_distinction':{'prior_source_probe_exact':prior,'evidence_path':str(OUT.parent/'cathedral_existing_source_contact_probe.json'),'true_source_gap':'Above continuous source wall top and below continuous original roof underside, excluding source occupants. It already exists before any coarse/fine interface replacement.','interface_mismatch':'Original 0.5 m cache can also be empty at positions still inside continuous wall (e.g. x=7.975,y=28.025,z=20.025), and below sampled roof layers. This measurement does not treat that extra sampling loss as source-gap volume.','restriction':'Any added real eave support is a new authored source revision; it cannot be disguised as unchanged-source interface repair. Finished detailed-roof contact still needs separate bounded verification against its frozen source before source authoring/activation.'},'representative_original_source_empty_gap_probes':probes,'resource_limits':{'address_space_limit_MiB':64,'cpu_limit_seconds':45,'measured_cpu_seconds':time.process_time()-START,'maxrss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}}
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
assert OUT.stat().st_size+Path(__file__).stat().st_size<80000
print(json.dumps({'summary':summary,'groups':groups,'resource_limits':report['resource_limits'],'json_bytes':OUT.stat().st_size,'script_bytes':Path(__file__).stat().st_size},indent=2))
