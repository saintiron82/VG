#!/usr/bin/env python3
"""Produce source-revision DATA ONLY. No master or cache writes, no compilation."""
import copy, gzip, hashlib, json, math, resource, time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(64*1024*1024,64*1024*1024))
resource.setrlimit(resource.RLIMIT_CPU,(45,45))
t0=time.process_time()
OUT=Path(__file__).with_suffix('.json');F=OUT.parent.parent
MEASURE=OUT.parent/'cathedral_contact_gap_measurement.json'
m=json.loads(MEASURE.read_text());src=Path(m['source_master_path']);raw=src.read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def ch(x):return sha(canon(x))
assert sha(raw)==m['source_master_sha256']
d=json.loads(raw);ops={o['id']:o for c in d['components'] for o in c['operations']}
window_catalog=json.loads((F/'generated/catalog.json').read_text())
wc=next(a for a in window_catalog['assets'] if a['asset_key']==d['id'])
wp=Path(wc['emitted_master_path']);wb=wp.read_bytes();assert sha(wb)==wc['emitted_master_sha256']
w=json.loads(gzip.decompress(wb));assert wc['source_sha256']==sha(raw)
active=json.loads((OUT.parent/'active_boundary_r02.catalog.json').read_text())['assets'][0]
assert active['source_sha256']==sha(raw)
COMP='cathedral_eave_support_r01';WIDTH=.15;IDENTITY=[[1,0,0],[0,1,0],[0,0,1]]
def transform(o,p):
 t=o.get('transform',{});b=t.get('basis',IDENTITY);tr=t.get('translation',[0,0,0])
 return [sum(b[i][j]*p[j] for j in range(3))+tr[i] for i in range(3)]
def points(o):
 s=o['shape']
 if s['kind']=='box':return [transform(o,[x,y,z]) for x in [s['min'][0],s['max'][0]] for y in [s['min'][1],s['max'][1]] for z in [s['min'][2],s['max'][2]]]
 return [transform(o,[x,y,z]) for x,y in s['polygon'] for z in [s['z_min'],s['z_max']]]
def bounds(o):
 ps=points(o);return {'min':[min(p[i] for p in ps) for i in range(3)],'max':[max(p[i] for p in ps) for i in range(3)]}
def polyarea(p):
 return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))))/2 if len(p)>2 else 0

def clip(subject,window):
 if not subject or not window:return []
 signed=sum(window[i][0]*window[(i+1)%len(window)][1]-window[(i+1)%len(window)][0]*window[i][1] for i in range(len(window)));sg=1 if signed>0 else -1
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

rows=[];newops=[]
for sid in ['nave_west','nave_east','transept_rear','transept_front']:
 r=next(r for r in m['eave_strips'] if r['eave_strip_id']==sid);roof=ops[r['source_roof_operation']]
 lo,hi=r['wall_cross_interval_m'];outer_min=sid in ['nave_west','transept_rear']
 a,b=(lo,lo+WIDTH) if outer_min else (hi-WIDTH,hi)
 def roofy(u):return r['roof_underside_y_at_cross_minmax_m'][0]+r['roof_slope_dy_du']*(u-lo)
 top=r['wall_top_y_m'];poly=[[a,top],[b,top],[b,roofy(b)],[a,roofy(a)]]
 intervals=r['continuous_gap_intervals_m'] if sid.startswith('nave') else [r['continuous_gap_intervals_m'][0],r['continuous_gap_intervals_m'][2]]
 for k,(v0,v1) in enumerate(intervals):
  name='eave_support_'+sid+('' if sid.startswith('nave') else ('_west_arm' if v1<0 else '_east_arm'))+'_outer015'
  shape={'kind':'extrusion','polygon':poly,'z_min':v0,'z_max':v1}
  op={'id':name,'part':'solid','action':'paint','shape':shape,'material':'stone'}
  if roof.get('transform'):
   op['transform']=copy.deepcopy(roof['transform']);shape['z_min']=-v1;shape['z_max']=-v0
  newops.append(op);section=polyarea(poly);length=v1-v0
  rows.append({'operation_id':name,'base_operation_hash':None,'new_operation_sha256':ch(op),'change_type':'insert_new_physical_masonry_source_occupancy','source_wall_operations':r['wall_operations'],'source_wall_operation_hashes':{x:ch(ops[x]) for x in r['wall_operations']},'source_roof_operation':r['source_roof_operation'],'source_roof_operation_sha256':ch(roof),'cross_axis':r['cross_axis'],'longitudinal_axis':r['longitudinal_axis'],'cross_interval_m':[a,b],'longitudinal_interval_m':[v0,v1],'width_m':b-a,'length_m':length,'bottom_y_m':top,'top_y_at_cross_minmax_m':[roofy(a),roofy(b)],'height_range_m':[min(roofy(a),roofy(b))-top,max(roofy(a),roofy(b))-top],'cross_section_m2':section,'gross_volume_m3':section*length,'gross_horizontal_area_m2':WIDTH*length,'gross_upper_contact_area_m2':WIDTH*length*math.sqrt(1+r['roof_slope_dy_du']**2),'change_aabb_m':bounds(op),'original_source_gap_subset_verified':True,'source_gap_measurement_strip':sid})
assert len(newops)==6
component={'id':COMP,'parts':[{'id':'solid','pivot':[0,0,0],'metadata':{'source_category':'masonry','dynamic':False}}],'operations':newops}
instance={'id':COMP,'component':COMP}
# Extend existing exact window cavity geometry to only the new support instance.
# Original selector-bearing cuts remain unchanged; one geometry per window is used.
cutdefs=[];cutbindings=[]
for old in w['assembly_cuts']:
 if not old['id'].endswith('_cavity_masonry'):continue
 new={'id':old['id'].replace('_cavity_masonry','_cavity_eave_support'),'selector':{'instance':COMP},'shape':copy.deepcopy(old['shape'])}
 if old.get('transform'):new['transform']=copy.deepcopy(old['transform'])
 cutdefs.append(new);cutbindings.append({'new_cut_id':new['id'],'new_cut_sha256':ch(new),'original_cut_id':old['id'],'original_cut_sha256':ch(old),'geometry_fields_unchanged':True})
assert len(cutdefs)==33
entry=ops['nave_door_opening']
entrycut={'id':'eave_support_protect_nave_door_opening','selector':{'instance':COMP},'shape':copy.deepcopy(entry['shape'])}
if entry.get('transform'):entrycut['transform']=copy.deepcopy(entry['transform'])
cutdefs.append(entrycut);cutbindings.append({'new_cut_id':entrycut['id'],'new_cut_sha256':ch(entrycut),'original_operation_id':'nave_door_opening','original_operation_sha256':ch(entry),'geometry_fields_unchanged':True})

# Exact convex intersections: all overlapping cavities extrude along a support's longitudinal axis.
cut_hits=[]
for row,op in zip(rows,newops):
 bb=row['change_aabb_m'];uaxis=0 if row['cross_axis']=='x' else 2;vaxis=2 if uaxis==0 else 0
 sp=[(p[uaxis],p[1]) for p in [transform(op,[x,y,op['shape']['z_min']]) for x,y in op['shape']['polygon']]]
 hits=[]
 for cut in cutdefs:
  cb=bounds(cut)
  if any(min(bb['max'][i],cb['max'][i])-max(bb['min'][i],cb['min'][i])<=1e-9 for i in range(3)):continue
  cs=cut['shape'];basis=cut.get('transform',{}).get('basis',IDENTITY)
  assert cs['kind']=='extrusion' and abs(basis[vaxis][2])==1,('requires nonconstant intersection',row['operation_id'],cut['id'])
  cp=[(p[uaxis],p[1]) for p in [transform(cut,[x,y,cs['z_min']]) for x,y in cs['polygon']]]
  a=polyarea(clip(sp,cp));v0=max(bb['min'][vaxis],cb['min'][vaxis]);v1=min(bb['max'][vaxis],cb['max'][vaxis])
  if a>1e-9:
   assert abs(a-row['cross_section_m2'])<1e-8,('Partial-width cut requires more detailed integration',cut['id'])
   hits.append({'operation_id':row['operation_id'],'cut_id':cut['id'],'removed_longitudinal_interval_m':[v0,v1],'cross_section_m2':a,'removed_volume_m3':a*(v1-v0)})
 # Present source geometry yields disjoint full-cross-section cavity trims.
 for i,h in enumerate(hits):
  for g in hits[:i]:assert min(h['removed_longitudinal_interval_m'][1],g['removed_longitudinal_interval_m'][1])<=max(h['removed_longitudinal_interval_m'][0],g['removed_longitudinal_interval_m'][0])+1e-9
 removed=sum(h['removed_volume_m3'] for h in hits);removedlen=sum(h['removed_longitudinal_interval_m'][1]-h['removed_longitudinal_interval_m'][0] for h in hits)
 row['cavity_trim_intersections']=hits;row['removed_by_protected_cavities_m3']=removed;row['net_added_analytic_volume_m3']=row['gross_volume_m3']-removed;row['net_horizontal_area_m2']=row['gross_horizontal_area_m2']-WIDTH*removedlen;row['net_solid_length_m']=row['length_m']-removedlen
 cut_hits.extend(hits)
assert {h['cut_id'] for h in cut_hits}=={'opening_008_cavity_eave_support','opening_010_cavity_eave_support'}

# Separate UNAPPROVED design options: only the shared 0.6 m base band, never the triangle.
gables=[]
for j in m['gable_panel_joints_separate_from_eaves']:
 if j['depth_separation_m']<1e-9:continue
 wo=ops[j['wall_operation']];go=ops[j['gable_operation']];ws=wo['shape'];a,b=ws['min'][0],ws['max'][0]
 wd=j['lower_wall_depth_interval_m'];gd=j['gable_panel_depth_interval_m'];z0,z1=(wd[1],gd[0]) if wd[1]<gd[0] else (gd[1],wd[0])
 y0,y1=j['gable_base_y_m'],j['lower_wall_top_y_m']
 op={'id':'proposed_unapproved_'+j['gable_operation']+'_base_joint','part':'solid','action':'paint','material':'stone','shape':{'kind':'box','min':[a,y0,z0],'max':[b,y1,z1]}}
 volume=(b-a)*(y1-y0)*(z1-z0)
 gables.append({'status':'proposed_not_approved_do_not_apply','joint':j,'operation':op,'new_operation_sha256':ch(op),'change_aabb_m':bounds(op),'analytic_added_volume_m3':volume,'scope':'Only the shallow 0.1 m depth joint in the 0.6 m shared base band. No triangular gable-center or attic filling.','original_wall_operation_sha256':ch(wo),'original_gable_operation_sha256':ch(go)})
assert len(gables)==5

old_seq=[{'component_id':c['id'],'operations':c['operations']} for c in d['components']]
new_seq=[{'component_id':COMP,'operations':newops}]+old_seq
old_window_seq=[{'component_id':c['id'],'operations':c['operations']} for c in w['components']]
new_window_seq=[{'component_id':COMP,'operations':newops}]+old_window_seq
agg={k:sum(r[k] for r in rows) for k in ['length_m','gross_volume_m3','gross_horizontal_area_m2','gross_upper_contact_area_m2','removed_by_protected_cavities_m3','net_added_analytic_volume_m3','net_horizontal_area_m2','net_solid_length_m']}
agg['paint_operation_count']=6;agg['new_support_only_assembly_cut_count']=len(cutdefs);agg['max_support_height_m']=max(r['height_range_m'][1] for r in rows)
agg['minimum_support_height_m']=min(r['height_range_m'][0] for r in rows)
agg['measurement_kind']='Exact analytic native-source trapezoids minus disjoint exact protected cavity intersections, binary64 tolerance; not voxel counts.'
report={'schema':'riverstone.cathedral.eave_support_source_revision.data.v1','id':'cathedral_eave_support_revision_r01','status':'approved_exterior_support_design_data_only_not_applied','authored_source_change':True,'original_occupancy_unchanged':False,'master_mutated':False,'voxel_compile_run':False,'runtime_activated':False,'scope':{'approved':'Six outer 0.15 m wall-top strips: nave west/east full measured exterior intervals, and transept rear/front west/east outer arms only. Material stone.','excluded':['All four aisle interior wedges','Transept central crossing inside nave footprint','Five unapproved gable-joint options','Any interior triangular gable or attic fill'],'surfaces':'Bottom exactly at original source wall top; top exactly matches original source roof underside. No padding, growth, fake seam volume, roof deformation, or occupancy-preservation claim.'},'source_bindings':{'original_master_path':str(src),'original_master_sha256':sha(raw),'original_master_id':d['id'],'original_master_revision':d['revision'],'original_render_path':m['source_render_path'],'original_render_sha256':m['source_render_sha256'],'measurement_path':str(MEASURE),'measurement_sha256':sha(MEASURE.read_bytes()),'window_master_path':str(wp),'window_master_sha256':sha(wb),'composed_roof_opening_master_path':active['emitted_master_path'],'composed_roof_opening_master_sha256':active['emitted_master_sha256'],'frozen_finished_roof_master_sha256':active['roof_composition_sha256'],'frozen_finished_roof_loaded':False},'common_source_delta':{'prepend_components':[component],'prepend_instances':[instance],'append_assembly_cuts':cutdefs,'retain_original_components_operations_instances_and_cuts_unchanged':True,'apply_order':'Insert the support component and instance at index 0. Preserve every existing instance order, source operation and original selector. Append new cuts targeting only this support instance. Existing materials therefore retain priority in source overlaps.','intended_revision_policy':'Mint a new source revision and fresh source/render bindings. This is not an interface adapter, unchanged-source claim, or permission to overwrite the frozen baseline.'},'operation_hashes':{'canonical_encoding':'UTF-8 JSON, sorted keys, compact separators, ensure_ascii=false. Grouped operation sequences retain component and operation order.','original_source_operations_grouped_sha256':ch(old_seq),'original_plus_support_operations_grouped_sha256':ch(new_seq),'original_source_operation_count':sum(len(c['operations']) for c in d['components']),'original_plus_support_operation_count':sum(len(c['operations']) for c in d['components'])+6,'window_source_operations_grouped_sha256':ch(old_window_seq),'window_plus_support_operations_grouped_sha256':ch(new_window_seq),'window_original_assembly_cuts_sha256':ch(w['assembly_cuts']),'window_plus_support_assembly_cuts_sha256':ch(w['assembly_cuts']+cutdefs),'new_component_operations_sha256':ch(newops),'new_support_assembly_cuts_sha256':ch(cutdefs),'note':'These are operation/cut payload hashes, not a fabricated file hash for a master that has not been written.'},'support_strips':rows,'aggregate':agg,'change_aabbs_m':[{'operation_id':r['operation_id'],**r['change_aabb_m']} for r in rows],'protected_window_and_entry_policy':{'window_geometry_source':str(wp),'copied_cavity_geometries':33,'original_window_cavity_shape_and_transform_preserved':True,'new_cut_target_only':COMP,'original_cut_selectors_untouched':True,'bindings':cutbindings,'actual_positive_volume_intersections':cut_hits,'entry':'The exact original nave_door_opening shape is also copied as a support-only protective assembly cut. It has no positive-volume support overlap. Preserve all original doors, windows, glazing, frames, mullions, source openings and entry clearances.','important':'Do not rely on original feature-selective cuts to affect new support features. The explicit support-targeted cuts are required: rear transept supports otherwise enter the 0.025 m outward cavity extensions of opening_008 and opening_010.','expected_guard_effect':'Both rear-arm supports lose 0.025 m at the nave-end joint. This intentional aperture protection supersedes blanket support continuity at those two endpoints.'},'unapproved_gable_depth_joint_options':{'status':'not_approved_do_not_apply','included_in_source_delta':False,'included_in_approved_hashes_volumes_or_change_aabbs':False,'required_next_step':'Obtain explicit scope approval before adding any of these five joint bridges.','total_candidate_volume_m3':sum(g['analytic_added_volume_m3'] for g in gables),'options':gables},'verification_and_limits':{'exact_source_geometric_definition':True,'support_subset_of_measured_original_gaps':True,'cavity_intersection_math':'Exact convex polygon intersection in the physical eave section multiplied by common longitudinal depth. Each intersecting cavity removes a complete cross-section over a disjoint depth interval; assertions enforce this.','completed':['Original source and window master file hashes checked','Six positive support trapezoids match source wall top and roof underside','Only measured exterior arm intervals selected','All 33 exact window cavity geometries and original portal cut explicitly targeted at support instance','Two positive protected-cavity intersections integrated analytically','Gable alternatives excluded from approved source delta and totals'],'pending':['Common-master schema validation after parent composes the new revision','Bounded fine-roof contact verification against frozen detailed roof','Approved bounded ROI voxel/mesh checks and near/far interface changes','Runtime and collision review if parent later authorizes activation'],'resource_limits':{'address_space_MiB':64,'cpu_seconds_limit':45,'measured_cpu_seconds':time.process_time()-t0,'maxrss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}}}
OUT.write_text(json.dumps(report,indent=1,sort_keys=True)+'\n')
assert OUT.stat().st_size+Path(__file__).stat().st_size<100000
print(json.dumps({'aggregate':agg,'protected_cut_hits':cut_hits,'unapproved_gable_volume_m3':report['unapproved_gable_depth_joint_options']['total_candidate_volume_m3'],'json_bytes':OUT.stat().st_size,'script_bytes':Path(__file__).stat().st_size,'report_sha256':sha(OUT.read_bytes()),'resources':report['verification_and_limits']['resource_limits']},indent=2))
