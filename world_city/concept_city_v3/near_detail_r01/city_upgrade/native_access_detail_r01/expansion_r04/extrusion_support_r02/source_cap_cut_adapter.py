"""Data-selected convex horizontal source-cap paths with exact component-cut exclusion.
Proof/transport only. Uses unchanged common source transforms, polygon union,
patch generator, author/crop compiler and runtime mesh helpers. No source mesher.
"""
from pathlib import Path
from fractions import Fraction as F
import copy,sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent/'extrusion_support_r01'));import author_extrusion as e
b=e.b;a=e.a

def projected_extrusion(op,tr,pitch):
 shape=op.get('shape',{})
 if shape.get('kind')!='extrusion':raise ValueError('unsupported_nonextrusion_source')
 if b.core.prepare_shape(shape,pitch)!=shape:raise ValueError('pitch_dependent_source_expansion')
 if any(v not in [-1,0,1]for row in tr['basis']for v in row):raise ValueError('unsupported_nonaxis_component_transform')
 normal=[tr['basis'][i][2]for i in range(3)]
 if normal not in ([0,1,0],[0,-1,0]):raise ValueError('unsupported_nonhorizontal_extrusion_cap')
 rings=[[b.core.apply(tr,[*p,z])for p in shape['polygon']]for z in [shape['z_min'],shape['z_max']]]
 if any(len({p[1]for p in ring})!=1 for ring in rings):raise ValueError('nonhorizontal_cap')
 poly=[[p[0],-p[2]]for p in rings[0]]
 if not e.convex(e.fp(poly)) or not a.polygons.is_convex_polygon(poly):raise ValueError('nonconvex_or_malformed_source_polygon')
 return poly,min(r[0][1]for r in rings),max(r[0][1]for r in rings)

def source_contract(master,rule,pitch):
 if master.get('assembly_cuts'):raise ValueError('unsupported_assembly_cut_selector')
 ids=set(rule['operation_ids']);components=set(rule['source_components']);owners=[];cuts=[];seen=set();component_records={c['id']:c for c in master['components']}
 for inst,op,tr in a.previous.source_parts(master):
  if inst['component'] not in components:continue
  part=next(p for p in component_records[inst['component']]['parts'] if p['id']==op['part'])
  if part.get('dynamic') or part.get('metadata',{}).get('dynamic'):raise ValueError('dynamic_source_part_excluded')
  if op['action']=='cut':
   poly,low,high=projected_extrusion(op,tr,pitch);cuts.append({'instance':inst['id'],'component':inst['component'],'part':op['part'],'operation':op['id'],'operation_sha256':e.digest(op),'selector':op.get('selector',{}),'cut_scope':'instance local; never filtered by cut part label','polygon_uv_m':poly,'polygon_sha256':e.digest(poly),'y_interval_m':[low,high],'transform':tr});continue
  if op['id'] not in ids:continue
  if op['action']!='paint' or op.get('material')!=rule['material'] or op['part']!=rule['part']:raise ValueError('semantic_paint_ownership_mismatch')
  poly,low,high=projected_extrusion(op,tr,pitch)
  owners.append({'instance':inst['id'],'component':inst['component'],'part':op['part'],'material':op['material'],'operation':op['id'],'operation_sha256':e.digest(op),'semantic_key':[inst['id'],inst['component'],op['material'],op['part']],'top_y_m':high,'polygon_uv_m':poly,'polygon_sha256':e.digest(poly),'bounds_uv_m':[min(p[i]for p in poly)for i in [0,1]]+[max(p[i]for p in poly)for i in [0,1]],'transform':tr});seen.add(op['id'])
 if seen!=ids:raise ValueError('missing_declared_semantic_path')
 # Common compiler cuts are instance-local and selector-based, NOT scoped
 # by the cut operation's own part label. Conservatively consider all such cuts.
 instances={o['instance']for o in owners};cuts=[c for c in cuts if c['instance']in instances]
 if len(owners)>64 or len(cuts)>16:raise ValueError('bounded_source_owner_budget')
 return owners,cuts

def intersection_area(subject,cover):
 inside=subject;direction=1 if e.signed(cover)>0 else -1
 for x,y in zip(cover,cover[1:]+cover[:1]):inside=e.clip(inside,x,y,direction,True)
 return e.area(inside)

def patch_proof(rect,plane,owners,cuts):
 own=e.semantic_proof(rect,plane,owners);subject=e.fp(a.polygon(rect));cutproof=[]
 for cut in cuts:
  low,high=map(F,cut['y_interval_m']);p=F(plane);top=p+F(.0375);relevant=not(high<p or low>top)
  value=intersection_area(subject,e.fp(cut['polygon_uv_m'])) if relevant else F(0)
  cutproof.append({'operation':cut['operation'],'operation_sha256':cut['operation_sha256'],'source_y_interval_m':cut['y_interval_m'],'intersects_additional_visual_y_envelope':relevant,'exact_overlap_area_ratio':[value.numerator,value.denominator],'polygon_sha256':cut['polygon_sha256']})
 return {'supported':own['supported'] and all(c['exact_overlap_area_ratio'][0]==0 for c in cutproof),'source_cap_union':own,'cut_exclusion':cutproof,'positive_area_cut_overlap_allowed':False,'shared_boundary_contact':'zero-area boundary contact only; no positive-area fill','additional_visual_offset_m':.0375,'geometric_tolerance_m':0}
