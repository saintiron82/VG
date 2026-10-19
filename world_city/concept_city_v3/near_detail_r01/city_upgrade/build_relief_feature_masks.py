"""Separate actual authored window envelopes from much wider compile ROI bounds.

Meshes/collision untouched. The surface adapter subtracts these envelopes from
original exterior wall rectangles and uses precompiled quarter-metre trims.
"""
from pathlib import Path
import hashlib,json,sys,copy
H=Path(__file__).resolve().parent;R=H.parents[3];C=H.parents[1]
sys.path.insert(0,str(H/'facility_openings'));import author
from build_near_catalog import source_parts
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def window_regions(source,contract):
 components={x['id']:x for x in source['components']};regions=[];bindings=[]
 effective={(i['id'],op['id']):(i,op,tr)for i,op,tr in source_parts(source)}
 for patch in contract['patches']:
  if 'source_surround' in patch:
   binding=patch['source_surround'];op=next(x for x in components[binding['component']]['operations']if x['id']==binding['operation'])
   assert author.core.digest(op)==binding['operation_sha256']
   low,high=author.bounds(op['shape'],patch['local_to_master']);bindings.append(binding)
  else:
   # Existing modular windows have several real framing operations, not a
   # fabricated surround. Resolve their complete source instance transforms.
   refs=patch['source_features']+[patch['source_glass'],patch['source_aperture']]
   boxes=[]
   for binding in refs:
    instance,op,tr=effective[(binding['instance'],binding['operation'])]
    assert instance['component']==binding['component'] and author.core.digest(op)==binding['operation_sha256']
    boxes.append(author.bounds(op['shape'],tr));bindings.append(binding)
   low=[min(b[0][n]for b in boxes)for n in range(3)];high=[max(b[1][n]for b in boxes)for n in range(3)]
  regions.append({'id':patch['id'],'min':[v-.05 for v in low],'max':[v+.05 for v in high],'semantic':'actual source surround plus one fine-cell safety margin'})
 return regions,bindings
def main(key='registered_port_long_loading_shed'):
 cp=C/'playable_detail_r01/near_catalog.json';cat=author.load(cp)
 manifest_path=R/cat['assets'][key]['composed_manifest_path']
 manifest=author.load(manifest_path)
 assert manifest['asset_key']==key and manifest['all_pass'] and manifest['render_sha256']==cat['assets'][key]['sha256']
 contract_path=R/manifest['replacement_contract_path'] if manifest.get('replacement_contract_path') else H/'facility_openings/generated'/f'{key}.replacement.json.gz'
 if manifest.get('replacement_contract_sha256'):assert sha(contract_path)==manifest['replacement_contract_sha256']
 contract=author.load(contract_path)
 source_path=contract.get('patch_source_master_path',contract.get('source_master_path'))
 source_sha=contract.get('patch_source_master_sha256',contract.get('source_sha256'))
 source=author.load(R/source_path);assert sha(R/source_path)==source_sha
 original_sha=contract.get('source_sha256',contract.get('source_master_sha256'))
 if source_sha!=original_sha:
  from window_revision_contract import validate as validate_revision
  revision=manifest['source_revision'];assert revision==contract['source_revision']
  assert revision['original_master_sha256']==original_sha and revision['revised_master_sha256']==source_sha
  validate_revision(revision,author.load(R/revision['original_master_path']),source)
 regions,bindings=window_regions(source,contract)
 window_ids={r['id']for r in manifest['window_regions']};assert window_ids=={p['id']for p in contract['patches']}
 regions.extend(copy.deepcopy(r) for r in manifest['surface_exclusion_regions']if r['id'] not in window_ids)
 assert len(regions)==len(contract['patches'])+sum(r['id'] not in window_ids for r in manifest['surface_exclusion_regions'])
 target=H/'surface_feature_masks';target.mkdir(exist_ok=True)
 out=target/(f'{key}.revised.r01.json' if manifest.get('source_revision') else f'{key}.r01.json')
 data={'schema':'riverstone.surface.feature_exclusions.v1','asset_key':key,'source_master_sha256':original_sha,'source_render_sha256':contract['source_render_sha256'],'composed_render_sha256':manifest['render_sha256'],'source_opening_contract':str(contract_path.relative_to(R)),'source_opening_contract_sha256':sha(contract_path),'source_operations':bindings,'regions':regions,'all_source_operation_hashes_match':True,'collision_changed':False,'mesh_changed':False,'policy':'Subtract outward quarter-grid rounded envelopes from source exterior wall faces. Tile each surviving rectangle using existing common precompiled trim modules. Never scale modules or cover openings. Compile ROI stays a separate geometry ownership contract.'}
 if manifest.get('source_revision'):data.update(source_operations_master_sha256=source_sha,source_revision=manifest['source_revision'],source_revision_sha256=manifest['source_revision_sha256'])
 encoded=json.dumps(data,indent=2)+'\n'
 if out.exists() and out.read_text()!=encoded:
  out=out.with_name(f'{key}.{hashlib.sha256(encoded.encode()).hexdigest()[:16]}.json')
 if out.exists():assert out.read_text()==encoded
 else:out.write_text(encoded)
 cat['assets'][key]['surface_feature_mask_path']=str(out.relative_to(R));cat['assets'][key]['surface_feature_mask_sha256']=sha(out)
 cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'path':str(out),'sha256':sha(out),'regions':len(regions),'geometry_changed':False}))
if __name__=='__main__':
 for key in sys.argv[1:] or ['registered_port_long_loading_shed']:main(key)
