"""Read-only shadow source candidate; original component path stays compatible.

No catalog/native/collider writes. Operation-scoped fallback requires an exact
source-bound roof replacement contract and strict cut/later-paint separation.
"""
from pathlib import Path
import importlib.util,json,hashlib,sys,gzip
HERE=Path(__file__).resolve().parent;B=HERE.parents[1];U=B.parent.parent;ROOT=U.parents[3];C=U.parents[1]
sys.path[:0]=[str(ROOT),str(U),str(HERE)]
from facility_roofs.author_facility_roofs import instance_transforms,transformed_bounds,relevant_cuts
from voxel_character.common import core
from source_parts_snapshot import source_parts

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 p=Path(p);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def strictly_separated(a,b):return any(a['max'][j]<b['min'][j] or b['max'][j]<a['min'][j] for j in range(3))
def cut_proofs(master,component,op,transforms):
 affected,proofs=relevant_cuts(master,component,op,transforms)
 assert not affected,'Intersecting original cut; retain actual fine caster'
 for p in proofs:
  if p['exclusion']=='strictly_disjoint_transformed_aabb':assert strictly_separated(p['roof_operation_aabb'],p['cut_aabb']),'Touching or overlapping original cut; retain actual fine caster'
  else:assert p['exclusion']=='selector_excludes_roof_operation'
 return proofs

def make_data(key,master,source_sha,visible_sha,contract=None):
 transforms=instance_transforms(master);components={c['id']:c for c in master['components']};parts=list(source_parts(master));selected=[(i,o,t) for i,o,t in parts if i.get('component')=='roof' or str(i.get('component','')).endswith('_roof')];mode='legacy_whole_roof';selected_refs=[]
 if not selected:
  mode='explicit_source_operations';assert isinstance(contract,dict),'No legacy roof component and no source-bound operation contract';assert contract['source_sha256']==source_sha and contract['asset_key']==key
  scope=contract['roof_replacement_scope'];assert scope['exclusive_source_material_ownership_verified'] is True;declared=scope['source_roof_materials'];assert declared and len(set(declared))==len(declared)
  refs=scope['source_roof_operations'];assert refs
  lookup={(i['component'],i['id'],o['id']):(i,o,t) for i,o,t in parts};seen=set()
  for r in refs:
   token=(r['component'],r['instance'],r['operation']);assert token not in seen,'Duplicate source operation binding';seen.add(token);assert token in lookup,'Unknown source operation binding';i,o,t=lookup[token]
   assert o==r['original_operation'] and core.digest(o)==r['operation_sha256'],'Source operation hash/content mismatch';assert o['action']=='paint' and o.get('material') in declared,'Not a selected roof paint';assert t==r['world_transform'],'Source operation transform mismatch';assert not o.get('selector'),'Selected paint selector unsupported';selected.append((i,o,t));selected_refs.append(r)
  all_declared={(i['component'],i['id'],o['id']) for i,o,t in parts if o['action']=='paint' and o.get('material') in declared};assert all_declared==seen,'Covering material not exclusively bound to exact selected operations'
 roofs=[];ops=[];proof_rows=[];checked=set();later_proofs=[];selected_ids={(i['component'],i['id'],o['id']) for i,o,t in selected}
 for ins,op,tr in selected:
  cid=str(ins['component']);assert op['action']=='paint' and op.get('material','').startswith('slate'),'Only authenticated semantic slate covering paints';token=(cid,op['id'])
  if token not in checked:proof_rows.extend({'operation':op['id'],**p} for p in cut_proofs(master,components[cid],op,transforms));checked.add(token)
  if mode=='explicit_source_operations':
   bb=transformed_bounds(op['shape'],tr);co=components[cid]['operations'];pos=next(j for j,o in enumerate(co) if o['id']==op['id'])
   for after in co[pos+1:]:
    if after['action']!='paint' or (cid,ins['id'],after['id']) in selected_ids:continue
    at=core.compose(transforms[ins['id']],core.transform(after.get('transform')));ab=transformed_bounds(after['shape'],at);assert strictly_separated(bb,ab),'Later nonselected paint touches/overlaps roof source';later_proofs.append({'roof_operation':op['id'],'later_operation':after['id'],'later_operation_sha256':core.digest(after),'roof_aabb':bb,'later_paint_aabb':ab,'strictly_separated':True})
  shape=op['shape']
  if shape['kind']=='extrusion':assert len(shape['polygon'])==4;ex={k:shape[k] for k in ['polygon','z_min','z_max']}
  elif shape['kind']=='box':
   lo,hi=shape['min'],shape['max'];ex={'polygon':[[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]],'z_min':lo[2],'z_max':hi[2]}
  else:raise AssertionError('Unsupported source shape; retain actual fine caster')
  ex['transform']={'basis':tr['basis'],'translation':tr['translation']};roofs.append(ex);ops.append({'instance':ins['id'],'operation':op['id'],'operation_sha256':hashlib.sha256(json.dumps(op,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()})
 assert roofs
 data={'schema':'riverstone.source_roof_shadow_proxy.v1','asset':key,'source_master_sha256':source_sha,'extrusions':roofs,'source_operations':ops,'visible_geometry':False,'collision_changed':False,'visible_render_sha256':visible_sha,'scope':'Exact cut-free authored slate covering solids, including ridge boxes; fine visible geometry still receives building/sun shadows but does not self-cast cell striping','shadow_triangles':len(roofs)*12,'shadow_vertex_normal_estimated_bytes':len(roofs)*36*24}
 if proof_rows:data['cut_exclusion_proofs']=proof_rows;data['cut_proof_helper_sha256']=sha(U/'facility_roofs/author_facility_roofs.py')
 evidence={'selection_mode':mode,'source_component_heuristic_expanded':False,'selected_original_operation_count':len(selected),'later_paint_exclusion_proofs':later_proofs,'all_original_cut_guards_strict':True,'source_shape_modified':False,'runtime_or_catalog_modified':False}
 return data,evidence

def derive(key):
 near=load(C/'playable_detail_r01/near_catalog.json')['assets'][key];idx=load(C/'playable_r01/generated/tile_r01/index.json')['common_assets'][key];sp=ROOT/idx['master_path'];assert sha(sp)==idx['master_sha256']==near['source_master_sha256'];master=load(sp);contract=None;refs=[{'path':idx['master_path'],'sha256':idx['master_sha256']}]
 parts=list(source_parts(master))
 if not any(i.get('component')=='roof' or str(i.get('component','')).endswith('_roof') for i,o,t in parts):
  mp=ROOT/near['composed_manifest_path'];assert sha(mp)==near['composed_manifest_sha256'];m=load(mp);assert m['asset_key']==key and m['source_master_sha256']==idx['master_sha256'] and m['render_sha256']==near['sha256'];cp=ROOT/m['replacement_contract_path'];assert sha(cp)==m['replacement_contract_sha256'];contract=load(cp);refs.extend([{'path':str(mp.relative_to(ROOT)),'sha256':sha(mp)},{'path':str(cp.relative_to(ROOT)),'sha256':sha(cp)}])
 data,evidence=make_data(key,master,idx['master_sha256'],near['sha256'],contract);evidence['inputs']=refs;evidence['candidate_helper_sha256']=sha(__file__);evidence['frozen_helper_sha256']=sha(U/'build_source_roof_shadow_proxy.py');evidence['immutable_source_parts_snapshot_sha256']=sha(HERE/'source_parts_snapshot.py');return data,evidence
