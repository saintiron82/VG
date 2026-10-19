"""Generic fail-closed eligibility contract for continuous source roof LOD.

No asset-name dispatch. No geometry or external files are changed by inspection.
"""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent;P=H.parent;U=P.parent;R=P.parents[4];C=U.parents[1]
sys.path[:0]=[str(R),str(P),str(U),str(U/'facility_roofs')]
from voxel_character.common import core
from build_near_catalog import source_parts
import author_facility_roofs as roofs
import source_surface_adapter as surface

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(Path(p).relative_to(R)),'sha256':sha(p)}
def load(p):return json.loads(Path(p).read_bytes())
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n')
def reject(key,codes,details=None):return {'schema':'riverstone.source_roof_lod_input.v1','asset_key':key,'status':'UNSUPPORTED','reason_codes':sorted(set(codes)),'details':details or []}

def inspect(key,mapping,source,master):
 try:
  source_path=R/source['master_path']
  if sha(source_path)!=source['master_sha256'] or mapping['master_sha256']!=source['master_sha256']:return reject(key,['SOURCE_IDENTITY_MISMATCH'])
  transforms=roofs.instance_transforms(master)
  d=roofs.describe(key,mapping,master)
 except core.InvalidMaster as exc:return reject(key,['UNSUPPORTED_TRANSFORM_OR_INVALID_SOURCE'],[str(exc)])
 except (KeyError,ValueError,AssertionError)as exc:return reject(key,['INVALID_OR_UNSUPPORTED_SOURCE'],[str(exc)])
 has_roof=d['planes']or d['retained_ridge_boxes']or d['pending']
 if not has_roof:return {'schema':'riverstone.source_roof_lod_input.v1','asset_key':key,'status':'NOT_APPLICABLE','reason_codes':['NO_CLASSIFIED_ROOF_SOURCE']}
 reasons=[]
 if any(p['reason']=='trimmed_or_cut_roof_pending'for p in d['pending']):reasons.append('ROOF_INTERSECTING_OR_SELECTOR_RELEVANT_CUT')
 if any(p['reason']!='trimmed_or_cut_roof_pending'for p in d['pending']):reasons.append('UNSUPPORTED_ROOF_SHAPE_OR_THICKNESS')
 if d['suppression']['unsafe_material_groups']:reasons.append('WHOLE_MATERIAL_GROUP_OWNERSHIP_UNPROVEN')
 if reasons:return reject(key,reasons,d['pending']+d['suppression']['unsafe_material_groups'])
 mats=d['suppression']['safe_material_groups_when_full_matching_near_resource_ready'];raw=[];priority={};operations=[];components={c['id']:c for c in master['components']};transformed_non_axis=0
 try:
  for index,(ins,op,tr)in enumerate(source_parts(master)):
   if op.get('material')not in mats:continue
   if op['action']!='paint':return reject(key,['ROOF_OPERATION_NOT_PAINT'])
   part=next(p for p in components[ins['component']]['parts']if p['id']==op['part'])
   if part.get('metadata',{}).get('dynamic')or part.get('dynamic'):return reject(key,['DYNAMIC_ROOF_PART_UNSUPPORTED'])
   if core.prepare_shape(op['shape'],mapping['pitch_m'])!=op['shape']:return reject(key,['PITCH_DEPENDENT_MINIMUM_SHAPE_UNSUPPORTED'])
   record={'id':ins['id']+'/'+op['id'],'material':op['material'],'shape':op['shape'],'transform':tr,'priority':index}
   surface.solid(record)
   raw.append(record);priority[(ins['id'],op['id'])]=index
   operations.append({'instance':ins['id'],'component':ins['component'],'operation':op['id'],'material':op['material'],'operation_sha256':core.digest(op),'transform_sha256':core.digest(tr)})
   if any(min(abs(v),abs(abs(v)-1))>1e-9 for row in tr['basis']for v in row):transformed_non_axis+=1
  canonical=[]
  for p in d['planes']:
   aa,bb=p['x_min'],p['x_max'];ya,yb=p['y_at_x_min'],p['y_at_x_max'];th=p['vertical_skin_thickness_m']
   shape={'kind':'extrusion','polygon':[[aa,ya-th],[bb,yb-th],[bb,yb],[aa,ya]],'z_min':p['z_min'],'z_max':p['z_max']}
   for ins in p['component_instances']:
    canonical.append({'id':ins['id']+'/'+p['id'],'material':p['material'],'shape':shape,'transform':core.compose(ins['transform'],p['operation_transform']),'priority':max(priority[(ins['id'],op)]for op in p['source_operations']),'source_operations':p['source_operations']})
  for p in d['retained_ridge_boxes']:
   op=p['operation']
   for ins in p['component_instances']:
    canonical.append({'id':ins['id']+'/'+op['id'],'material':op['material'],'shape':op['shape'],'transform':core.compose(ins['transform'],core.transform(op.get('transform'))),'priority':priority[(ins['id'],op['id'])],'source_operations':[op['id']]})
  canonical.sort(key=lambda r:r['priority'])
  for r in canonical:surface.solid(r)
 except (KeyError,ValueError,AssertionError,StopIteration)as exc:return reject(key,['UNSUPPORTED_CONVEX_SOURCE_SOLID'],[str(exc)])
 if len(canonical)>64 or len(raw)>128:return reject(key,['BOUNDED_SOLID_BUDGET_EXCEEDED'],[{'raw_solids':len(raw),'canonical_solids':len(canonical)}])
 return {'schema':'riverstone.source_roof_lod_input.v1','asset_key':key,'status':'SUPPORTED_INPUT_UNBUILT','reason_codes':[],'source_master':ref(source_path),'baseline_far_render':{'path':source['render_path'],'sha256':source['render_sha256']},'materials':mats,'raw_solids':raw,'canonical_solids':canonical,'source_operations':operations,'source_assembly_cuts':len(master.get('assembly_cuts',[])),'cut_exclusion_proofs':d['cut_exclusion_proofs'],'non_axis_aligned_rigid_roof_operations':transformed_non_axis,'canonical_group_suppression_proof':d['suppression'],'limits':{'raw_solids':128,'canonical_solids':64,'relevant_roof_cuts':False,'arbitrary_rigid_rotation':True,'scale_shear_reflection':False,'curved_triangular_or_nonconvex_solids':False,'material_overlap_precedence':'later source paint; boundary replay mandatory','surface_topology':'may reject nonmanifold contacts; build verification mandatory','runtime_promotion':False}}
