"""Exact authored slate-roof solids as shadow-only underlay, no visible/collision edits."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent;R=H.parents[3];C=H.parents[1]
from build_near_catalog import source_parts
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prove_unaffected_roof_operation(master,component,op,transforms):
 from facility_roofs.author_facility_roofs import relevant_cuts
 affected,proofs=relevant_cuts(master,component,op,transforms)
 assert not affected,'Intersecting source cut requires cut-aware proxy; keep actual geometry caster'
 for proof in proofs:
  if proof['exclusion']=='strictly_disjoint_transformed_aabb':
   a,b=proof['roof_operation_aabb'],proof['cut_aabb']
   assert any(a['max'][i]<=b['min'][i] or b['max'][i]<=a['min'][i] for i in range(3)), 'No epsilon overlap tolerance for proxy exclusion'
  else:assert proof['exclusion']=='selector_excludes_roof_operation'
 return proofs
def main(key):
 cp=C/'playable_detail_r01/near_catalog.json';cat=json.loads(cp.read_text());entry=cat['assets'][key]
 index=json.loads((C/'playable_r01/generated/tile_r01/index.json').read_text());source=index['common_assets'][key]
 master_path=R/source['master_path'];master=json.loads(master_path.read_text())
 assert sha(master_path)==source['master_sha256']==entry['source_master_sha256']
 from facility_roofs.author_facility_roofs import instance_transforms,relevant_cuts
 transforms=instance_transforms(master);components={c['id']:c for c in master['components']}
 roofs=[];ops=[];cut_proofs=[];checked=set()
 for instance,op,tr in source_parts(master):
  component=str(instance.get('component',''))
  if not (component=='roof' or component.endswith('_roof')):continue
  assert op['action']=='paint' and op.get('material','').startswith('slate'), 'Only authored slate roof paints; component cuts require separate handling'
  token=(component,op['id'])
  if token not in checked:
   proofs=prove_unaffected_roof_operation(master,components[component],op,transforms)
   cut_proofs.extend({'operation':op['id'],**p} for p in proofs);checked.add(token)
  shape=op['shape']
  if shape['kind']=='extrusion':
   assert len(shape['polygon'])==4
   ex={k:shape[k]for k in ['polygon','z_min','z_max']}
  elif shape['kind']=='box':
   lo,hi=shape['min'],shape['max']
   ex={'polygon':[[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]],'z_min':lo[2],'z_max':hi[2]}
  else:raise AssertionError('Unsupported roof source shape; keep actual geometry caster')
  ex['transform']={'basis':tr['basis'],'translation':tr['translation']};roofs.append(ex)
  ops.append({'instance':instance['id'],'operation':op['id'],'operation_sha256':hashlib.sha256(json.dumps(op,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()})
 assert roofs
 out=H/'shadow_proxies'/f'{key}.source_solid.r01.json'
 data={'schema':'riverstone.source_roof_shadow_proxy.v1','asset':key,'source_master_sha256':source['master_sha256'],'extrusions':roofs,'source_operations':ops,'visible_geometry':False,'collision_changed':False,'visible_render_sha256':entry['sha256'],'scope':'Exact cut-free authored slate covering solids, including ridge boxes; fine visible geometry still receives building/sun shadows but does not self-cast cell striping','shadow_triangles':len(roofs)*12,'shadow_vertex_normal_estimated_bytes':len(roofs)*36*24}
 if cut_proofs:data['cut_exclusion_proofs']=cut_proofs;data['cut_proof_helper_sha256']=sha(H/'facility_roofs/author_facility_roofs.py')
 encoded=json.dumps(data,indent=2)+'\n'
 if out.exists() and out.read_text()!=encoded:
  out=out.with_name(f'{key}.source_solid.{hashlib.sha256(encoded.encode()).hexdigest()[:16]}.json')
 if out.exists():assert out.read_text()==encoded
 else:out.write_text(encoded)
 entry.update(shadow_proxy_path=str(out.relative_to(R)),shadow_proxy_sha256=sha(out))
 entry.pop('native_scene_path',None);entry.pop('native_scene_sha256',None)
 cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'asset':key,'source_solids':len(roofs),'visible_render_unchanged':entry['sha256'],'proxy_sha256':sha(out),'shadow_bytes':data['shadow_vertex_normal_estimated_bytes']}))
if __name__=='__main__':main(sys.argv[1])

