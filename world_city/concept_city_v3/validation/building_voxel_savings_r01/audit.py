#!/usr/bin/env python3
"""Read-only audit of sealed r7 building render assets; writes only beside this file.
Run from any directory with Python 3. No compilation, meshing, GUI, or asset mutation.
"""
from pathlib import Path
from collections import Counter
import hashlib, json, math

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
SCENE = 'world_city/concept_city_v3/evidence/visual_registered_common_r7/scene.json'
EXPECTED_SCENE = '07af0d0f1913fe6b6749475c877dbd6d1e6f4bd590a5576d1d0628b37084d363'

def load(path):
    b = (ROOT / path).read_bytes()
    return json.loads(b), hashlib.sha256(b).hexdigest(), len(b)

def delta(before, after):
    return {'before': before, 'after': after, 'saved': before-after,
            'reduction_percent': (before-after)*100/before if before else 0,
            'before_over_after': before/after if after else None}

scene, scene_sha, scene_bytes = load(SCENE)
assert scene_sha == EXPECTED_SCENE, 'Scene changed: this audit is deliberately bound to sealed r7.'
ordinary = [i for i in scene['common_instances'] if i.get('source_pack') == 'ordinary']
counts = Counter(i['asset_key'] for i in ordinary)
representatives = ['ordinary_r2_2b48237662aa54', 'registered_castle_west_residence']
rows = {}
for key in sorted(set(counts) | set(representatives)):
    a = scene['common_assets'][key]
    r, rh, rb = load(a['render_path'])
    m, mh, mb = load(a['master_path'])
    assert rh == a['render_sha256'], key
    assert mh == a['master_sha256'], key
    assert r['schema'] == 'riverstone.voxel.render.v1', key
    assert r['cell_count'] == a['cell_count'], key
    p = float(r['pitch'])
    quads = [q for g in r['groups'] for q in g['quads']]
    assert len(quads) == r['quad_count'] == a['quad_count'], key
    unit_faces = 0
    for q in quads:
        assert len(q) == 4
        e = [q[1][i]-q[0][i] for i in range(3)]
        f = [q[3][i]-q[0][i] for i in range(3)]
        assert sum(abs(v)>1e-9 for v in e) == 1
        assert sum(abs(v)>1e-9 for v in f) == 1
        assert abs(sum(e[i]*f[i] for i in range(3))) < 1e-9
        assert all(abs(q[2][i] - q[1][i] - q[3][i] + q[0][i]) < 1e-9 for i in range(3))
        for vertex in q:
            for i, value in enumerate(vertex):
                t = (value-r['grid_origin'][i])/p
                assert abs(t-round(t)) < 1e-6
        area_units = math.sqrt(sum(v*v for v in e))*math.sqrt(sum(v*v for v in f))/(p*p)
        assert abs(area_units-round(area_units)) < 1e-6
        unit_faces += round(area_units)
    c, q = r['cell_count'], len(quads)
    rows[key] = {
        'asset_key':key, 'pitch_m':p, 'occupied_cells':c,
        'naive_six_faces_per_cell':6*c, 'exposed_unit_faces':unit_faces,
        'greedy_render_quads':q, 'render_triangles':2*q,
        'internal_face_culling':delta(6*c,unit_faces),
        'greedy_merge_vs_exposed_unit_faces':delta(unit_faces,q),
        'combined_vs_six_faces_per_cell':delta(6*c,q),
        'master_path':a['master_path'], 'master_sha256':mh, 'master_file_bytes':mb,
        'render_path':a['render_path'], 'render_sha256':rh, 'render_file_bytes':rb,
        'compiled_payload_hash_recorded_in_render':r['payload_hash'],
        'occupied_count_evidence':'Hash-verified render export cell_count agrees with sealed scene asset ledger; no recompilation or independent raw cell reconstruction.',
        'ordinary_placements':counts[key],
        'all_scene_placements':sum(i['asset_key']==key for i in scene['common_instances']),
        'assembly_class':a.get('author_metadata',{}).get('assembly_class'),
        'example_instance_ids':[i['id'] for i in scene['common_instances'] if i['asset_key']==key][:3],
    }

def sums(field, unique=False):
    return sum(rows[k][field]*(1 if unique else n) for k,n in counts.items())

def files(field):
    key = field.replace('_file_bytes','_path')
    return sum((ROOT/p).stat().st_size for p in {rows[k][key] for k in counts})

p_cells = sums('occupied_cells'); p_faces = sums('exposed_unit_faces'); p_quads = sums('greedy_render_quads')
mesh_keys = {(i['asset_key'], i['palette_id']) for i in ordinary}
batch_keys = {(i['asset_key'], i['palette_id'], math.floor(i['position_m'][0]/64), math.floor(i['position_m'][2]/64)) for i in ordinary}
renderer_path = 'world_city/concept_city_v3/preview_r4/City.gd'
renderer = (ROOT/renderer_path).read_text()
assert all(x in renderer for x in ['var render_cache:Dictionary={}', 'var palette_mesh_cache:Dictionary={}', 'var mm:=MultiMesh.new()', 'var node:=MultiMeshInstance3D.new()', 'floori(float(p.position_m[0])/64.0)'])
code_paths = [renderer_path, 'voxel_character/common/render_data.py', 'voxel_character/tools/mesh.py', 'world_city/concept_city_v3/registered_integration/r7/city_r7.sh']
source_evidence = [{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in code_paths]
result = {
 'schema':'riverstone.audit.building_voxel_savings.r01',
 'status':'verified_read_only_subtotal',
 'scene':{'path':SCENE,'sha256':scene_sha,'bytes':scene_bytes},
 'scope':{
   'selection':'Exact source_pack == ordinary; all 518 placements are authored house assemblies. This is a verified building-only subtotal, not the whole city.',
   'ordinary_placement_count':len(ordinary),'ordinary_unique_asset_count':len(counts),
   'ordinary_assembly_classes':dict(Counter(rows[i['asset_key']]['assembly_class'] for i in ordinary)),
   'excluded_instance_counts_by_source_pack':dict(sorted(Counter(i.get('source_pack') for i in scene['common_instances'] if i.get('source_pack') != 'ordinary').items())),
   'excluded_other_geometry':'All terrain/surfaces, 518 proxy support/foundation boxes, bridge moving nodes and all non-ordinary packs. Excluded packs include further real buildings as well as mixed courtyards, walls, trees and props.',
   'whole_city_building_count':'Not inferred from common_instances=3260 or source building_masses=703; those are not current building-only counts.',
 },
 'ordinary_subtotal':{
   'placed_occupied_cells':p_cells, 'unique_asset_occupied_cells':sums('occupied_cells',True),
   'placed_exposed_unit_faces':p_faces, 'unique_asset_exposed_unit_faces':sums('exposed_unit_faces',True),
   'placed_greedy_render_quads':p_quads, 'unique_asset_greedy_render_quads':sums('greedy_render_quads',True),
   'internal_face_culling':delta(6*p_cells,p_faces),
   'greedy_merge_vs_exposed_unit_faces':delta(p_faces,p_quads),
   'combined_vs_six_faces_per_cell':delta(6*p_cells,p_quads),
   'hypothetical_render_file_deduplication_bytes':delta(sums('render_file_bytes'),files('render_file_bytes')),
   'hypothetical_master_file_deduplication_bytes':delta(sums('master_file_bytes'),files('master_file_bytes')),
   'hypothetical_master_plus_render_file_deduplication_bytes':delta(sums('master_file_bytes')+sums('render_file_bytes'),files('master_file_bytes')+files('render_file_bytes')),
 },
 'runtime_implementation':{
   'renderer_path':renderer_path,'render_read_cache_key':'asset_key',
   'mesh_resource_cache_key':'asset_key/palette_id',
   'multimesh_batch_key':'asset_key/palette_id/floor(x/64)/floor(z/64)',
   'ordinary_palette_mesh_resources_derived_from_code':len(mesh_keys),
   'ordinary_multimesh_batches_derived_from_code':len(batch_keys),
   'ordinary_palette_mesh_quad_sum':sum(rows[k]['greedy_render_quads'] for k,p in mesh_keys),
   'evidence':'Source code implements Godot ArrayMesh sharing and MultiMesh instancing. These are code-derived counts, not a new runtime capture. No assertion of hardware GPU execution or frame-rate improvement.',
 },
 'method_and_limits':[
   'Meshing removes no occupied voxels. It omits solid-to-solid faces and merges adjacent coplanar same-material faces; authored geometry is not simplified or resampled by this audit.',
   'Exposed unit faces are the sum of axis-aligned grid-aligned rectangle areas divided by pitch squared. This includes any empty-neighbor cavity faces; it is not camera visibility or outside-air flood-fill culling.',
   'Placed totals are sums over placements, not a union of city-space occupancy, nor current visible or drawn counts after culling.',
   'File bytes use exact filesystem byte lengths of native master/render JSONs. Hypothetical baseline repeats the same file once per placement; shared case counts each referenced path once. This is not measured before/after repository disk use.',
   'Storage figures exclude placement metadata, scene manifests, caches/ledgers, source code, historical snapshots, runtime instance buffers, mesh/material structures and palette-variant mesh duplication.',
   'No compile time, CPU time, GPU memory, draw-call reduction, or FPS improvement is measured; cached seconds fields are not used as performance benchmarks.',
   'Castle west residence is one building wing, not the whole castle; it occurs once, so it has no placement-file deduplication saving by itself.',
 ],
 'representative_assets':{k:rows[k] for k in representatives},
 'ordinary_asset_rows':[rows[k] for k in sorted(counts)],
 'source_evidence':source_evidence,
 'checks':{'scene_sha256_match':True,'all_selected_master_render_sha256_match':True,'render_counts_match_scene_ledger':True,'all_quads_axis_aligned_grid_rectangles':True,'no_compilation_performed':True,'sealed_inputs_not_written':True},
}
assert hashlib.sha256((ROOT/SCENE).read_bytes()).hexdigest() == scene_sha
(OUT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
o=result['ordinary_subtotal']; rt=result['runtime_implementation']
lines=['# 건물 복셀·렌더·저장량 읽기 전용 측정', '',
'기준: r7 scene.json / SHA-256 '+scene_sha,
'', '## 확정된 일반 주택 소계',
f'- 일반 주택 팩 518개 배치, 고유 자산 28개. 다른 팩의 건물까지 포함한 도시 전체 합계는 아니다.',
f'- 점유 복셀 {p_cells:,}개는 그대로다. 중복 자산을 한 번씩 세면 {o["unique_asset_occupied_cells"]:,}개다.',
f'- 배치 기준 노출 단위면 {p_faces:,}개 → greedy 사각형 {p_quads:,}개: {o["greedy_merge_vs_exposed_unit_faces"]["reduction_percent"]:.4f}% 감소.',
f'- 복셀마다 6면을 그리는 기준 {6*p_cells:,}면 → {p_quads:,}사각형: 총 {o["combined_vs_six_faces_per_cell"]["reduction_percent"]:.4f}% 감소.',
'', '## 파일 재사용 가정 비교']
for name,key in [('렌더 JSON','hypothetical_render_file_deduplication_bytes'),('원본 master JSON','hypothetical_master_file_deduplication_bytes'),('원본+렌더 JSON','hypothetical_master_plus_render_file_deduplication_bytes')]:
 d=o[key];lines.append(f'- {name}: 매 배치별 파일 복제 {d["before"]:,} B → 고유 파일 공유 {d["after"]:,} B. {d["saved"]:,} B / {d["reduction_percent"]:.4f}% 절약.')
lines+=['','## 실제 대표 건물']
for name,k in [('B_REG_0000 일반 주택(8×14m, 3층)','ordinary_r2_2b48237662aa54'),('성 서쪽 주거동(성 전체가 아님)','registered_castle_west_residence')]:
 r=rows[k];lines += [f'- {name}: 0.5m 복셀 {r["occupied_cells"]:,}개 보존. 노출 단위면 {r["exposed_unit_faces"]:,}개 → {r["greedy_render_quads"]:,}사각형 ({r["greedy_merge_vs_exposed_unit_faces"]["reduction_percent"]:.4f}% 감소).']
lines += ['', '## 런타임과 해석 한계',
f'- 현재 렌더러 코드는 자산별 렌더 읽기 캐시, 자산+팔레트별 ArrayMesh 공유, 64m 청크별 MultiMesh를 구현한다. 일반 주택만 코드대로 계산하면 팔레트 메쉬 {rt["ordinary_palette_mesh_resources_derived_from_code"]}개, MultiMesh 배치 {rt["ordinary_multimesh_batches_derived_from_code"]}개다.',
'- 위 배치는 건물 수나 실측 드로우콜/FPS 수치가 아니다. 새 런타임 실행은 하지 않았다.',
'- 파일 절감은 동일 파일을 518번 복제하는 가정과의 비교다. 실제 옛 버전 대비 디스크 사용량 차이가 아니다.',
'- 배치 메타데이터, 런타임 인스턴스 버퍼, 팔레트별 메쉬 복제, 머티리얼, 과거 스냅샷 등은 파일 절감치에서 제외했다.',
'- 노출 단위면에는 빈 공간에 접한 내부 공간 면도 포함될 수 있다. 카메라에서 보이는 면만 센 값이 아니다.',
'- 나무·성벽·가구·지형·기초 프록시 및 분류가 섞인 다른 팩은 일반 주택 소계에서 제외했다. 제외 목록과 개별 자산 해시는 audit.json에 있다.',
'- 점유 셀 수는 해시 검증된 기존 렌더 메타데이터와 장면 원장 일치를 확인했다. 원시 셀 재생성은 하지 않았다.',
'', '## 재현', '저장소 루트에서 python world_city/concept_city_v3/validation/building_voxel_savings_r01/audit.py 실행.', 'audit.py는 기존 파일을 읽기만 하고 이 검증 디렉터리의 audit.json, REPORT_KO.md만 갱신한다.']
(OUT/'REPORT_KO.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'ordinary':o,'runtime':rt,'outputs':[str(OUT/'audit.json'),str(OUT/'REPORT_KO.md')]},ensure_ascii=False,indent=2))
