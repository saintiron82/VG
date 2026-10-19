"""Exact authored slate-roof solids as shadow-only underlay, no visible/collision edits."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent;R=H.parents[3];C=H.parents[1]
from build_near_catalog import source_parts
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(key):
 cp=C/'playable_detail_r01/near_catalog.json';cat=json.loads(cp.read_text());entry=cat['assets'][key]
 index=json.loads((C/'playable_r01/generated/tile_r01/index.json').read_text());source=index['common_assets'][key]
 master_path=R/source['master_path'];master=json.loads(master_path.read_text())
 assert sha(master_path)==source['master_sha256']==entry['source_master_sha256']
 assert not master.get('assembly_cuts'), 'Any global cuts require explicit cut-aware proxy, no silent fill'
 roofs=[];ops=[]
 for instance,op,tr in source_parts(master):
  if instance.get('component')!='roof':continue
  assert op['action']=='paint' and op.get('material','').startswith('slate'), 'Only cut-free authored slate roofs'
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
 out.write_text(json.dumps(data,indent=2)+'\n');entry.update(shadow_proxy_path=str(out.relative_to(R)),shadow_proxy_sha256=sha(out))
 entry.pop('native_scene_path',None);entry.pop('native_scene_sha256',None)
 cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'asset':key,'source_solids':len(roofs),'visible_render_unchanged':entry['sha256'],'proxy_sha256':sha(out),'shadow_bytes':data['shadow_vertex_normal_estimated_bytes']}))
if __name__=='__main__':main(sys.argv[1])

