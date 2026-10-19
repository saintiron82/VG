"""Bind exact common .5m visual revision without changing source colliders/index."""
from pathlib import Path
import hashlib,json,gzip,sys
H=Path(__file__).resolve().parent;R=H.parents[3];C=H.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def main(raw):
 p=Path(raw).resolve();c=load(p)
 assert c['schema'] in ('riverstone.revised_far_visual.v1','riverstone.revised_far_visual.v2') and c['all_pass'] is True and c['collision_reference_changed'] is False
 assert c['tests'] and all(v is True for v in c['tests'].values())
 cp=C/'playable_detail_r01/near_catalog.json';cat=load(cp);key=c['asset_key'];e=cat['assets'][key]
 source=load(C/'playable_r01/generated/tile_r01/index.json')['common_assets'][key]
 assert c['original_master_sha256']==source['master_sha256'] and c['original_render_sha256']==source['render_sha256']
 assert c['revised_master_sha256']==e['source_revision']['revised_master_sha256']
 r=R/c['render_path'];assert sha(r)==c['render_sha256'];d=load(r);old=load(R/source['render_path'])
 assert d['pitch']==c['pitch']==.5 and d['grid_origin']==c['grid_origin']==[0,0,0]
 assert d['materials']==old['materials']
 if c['schema']=='riverstone.revised_far_visual.v2':
  assert c['geometry_mode']=='source_roof_union_lod' and d['source_surface_lod']['source_solid_union'] is True
  assert c['source_bounds_contract']==e['bounds_contract']
  from bounds_contract import validate
  validate(c['source_bounds_contract'],d['bounds'],old['bounds'],source['master_sha256'])
  q=load(R/c['union_provenance_path']);assert sha(R/c['union_provenance_path'])==c['union_provenance_sha256']
  assert q['all_geometry_tests_pass'] and q['changed_collision'] is False and q['render']['sha256']==c['render_sha256']
  assert c['source_shadow_proxy_sha256']==e['shadow_proxy_sha256']
  e.update(far_union_provenance_sha256=c['union_provenance_sha256'],far_union_provenance_path=c['union_provenance_path'])
 else:assert d['bounds']==old['bounds']
 n=sum(len(g['quads'])for g in d['groups']);assert n==c['output_quad_count'] and 0<n<=50000
 e.update(far_visual_contract_path=str(p.relative_to(R)),far_visual_contract_sha256=sha(p),far_visual_render_path=c['render_path'],far_visual_render_sha256=c['render_sha256'])
 cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'asset':key,'far_quads':n,'render_sha256':c['render_sha256'],'index_changed':False,'collision_changed':False,'fine_render_changed':False}))
if __name__=='__main__':main(sys.argv[1])
