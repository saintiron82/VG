"""Frozen-input verification for the explicitly selected pending-near batch."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"expansion_r01"))
from input_contract import *
H=Path(__file__).resolve().parent
import gzip

def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def verify_ref(r):p=R/r['path'];assert sha(p)==r['sha256'],str(p);return p
rows=[];gv=load(H/'validation/godot_validation.json');assert gv['all_pass']
assert sha(H/'validation/RenderData.gd')==sha(C/'playable_detail_r01/RenderData.gd')
for pp in sorted(H.glob('*/candidate.provenance.json')):
 p=load(pp);assert p['all_geometry_tests_pass']and all(p['tests'].values());out=read(verify_ref(p['render']));base=read(verify_ref(p['baseline_far_render']));inp=load(verify_ref(p['input_contract']));verify_ref(p['source_master'])
 for r in out['provenance'].values():
  if isinstance(r,dict)and 'path'in r:verify_ref(r)
 for row in p['unchanged_nonroof_groups']:
  a=next(g for g in out['groups']if g['material']==row['material']);b=next(g for g in base['groups']if g['material']==row['material']);assert a==b and core.digest(a)==row['before']['sha256']==row['after']['sha256']
 raw=[surface.solid(r)for r in inp['raw_solids']];can=[surface.solid(r)for r in inp['canonical_solids']];regions,_=surface.regions(can);raw_regions,_=surface.regions(raw);groups,faces=surface.quads(regions)
 for g in groups:assert next(x for x in out['groups']if x['material']==g['material'])==g
 assert surface.compare_boundaries(regions,raw_regions)<1e-6 and surface.compare_boundaries(raw_regions,regions)<1e-6
 audit=surface.audit_boundary(faces,raw);assert audit['interior_surface_area_m2']<1e-6 and audit['coincident_surface_overlap_m2']<1e-6 and all(audit[k]==0 for k in ['normal_probe_errors','open_or_nonmanifold_edge_segments','edge_winding_errors'])
 godot=next(x for x in gv['reports']if x['render_sha256']==p['render']['sha256']);assert godot['all_pass']
 rows.append({'asset_key':p['asset_key'],'all_pass':True,'render':p['render'],'input_contract':p['input_contract'],'provenance':ref(pp),'unchanged_nonroof_groups':len(p['unchanged_nonroof_groups']),'nonroof_quads':sum(x['quad_count']for x in p['unchanged_nonroof_groups']),'roof_quads':p['roof_quad_count'],'total_quads':p['output_quad_count'],'godot_float32_triangles':godot['triangles'],'bounds':p['bounds'],'actual_city_visual_reviewed':False})
scope=load(H/'batch_scope.json')
assert {r['asset_key']for r in rows}=={r['asset_key']for r in scope['selected']if r['input_status']=='SUPPORTED_INPUT_UNBUILT'}
for path,digest in scope['frozen_method'].items():assert sha(R/path)==digest
for field in ['catalog_at_selection','city_index_at_selection']:verify_ref(scope[field])
for row in scope['selected']:
 verify_ref(row['source_master']);verify_ref(row['baseline_far_render']);verify_ref(row['input_contract'])
report={'schema':'riverstone.source_roof_lod_expansion_validation.v1','all_pass':True,'candidate_count':len(rows),'candidates':rows,'godot_validation':ref(H/'validation/godot_validation.json'),'input_audit':ref(H/'batch_scope.json'),'runtime_or_source_changes':False,'source_surface_adapter_unchanged_sha256':sha(P/'source_surface_adapter.py'),'original_cathedral_candidate_unchanged_sha256':sha(P/'candidate.render.json.gz'),'output_bytes':sum(p.stat().st_size for p in H.rglob('*')if p.is_file())}
assert report['output_bytes']<30*1024*1024
write(H/'expansion_validation.json',report);print(json.dumps(report))
