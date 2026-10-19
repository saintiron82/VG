"""Independent render-only artifact checks, with explicit occupancy evidence limits.

No compiler import or cell payload is needed. Directed unit faces are independently
rasterized from the retained render. Occupancy certificates are validated for
internal consistency; a retained-cell comparison is a separate stronger gate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import layered_qa as qa

SCHEMA='riverstone.house_detail.render_only_qa.v1'
MODE='render_only_transient_cells'
REQUIRED_CODE={'core','engine','adapter','connected_constraints','polygon_crop_guard','retention','render_data','mesh','rules','catalog'}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def merged_fingerprints(values):
    count=xor=total=0
    for value in values:
        value=qa._fingerprint(value)
        count+=value['count'];xor^=int(value['xor256'],16);total=(total+int(value['sum256'],16))%(1<<256)
    return {'count':count,'xor256':f'{xor:064x}','sum256':f'{total:064x}'}


def verify(stats_path,source_catalog,retained_stats=None):
    stats_path=Path(stats_path)
    with qa._text_file(stats_path) as stream:stats=json.load(stream)
    header=stats['compiled_header'];chunks=stats['chunks'];replay=stats['replay_contract']
    render_record=stats['files']['.render.json'];render_path=qa.ROOT/render_record['path']
    surface=qa.analyze_render(render_path,header['grid_origin']);meta=surface['metadata'];provenance=meta.get('provenance',{})
    info=qa._file_info(render_path)
    checks={
        'stats_schema':stats.get('schema')=='riverstone.house_detail.layered_stats.v1',
        'render_only_mode':stats.get('storage_mode')==header.get('storage_mode')==provenance.get('storage_mode')==MODE,
        'no_retained_cells_declared':stats.get('retained_cell_payload') is False and set(stats['files'])=={'.render.json'},
        'native_original_shapes':stats.get('spatial_sampling_contract')==header.get('sampling_contract')=='original_shapes_integer_cell_bounds_v1',
        'render_size_hash':all(render_record.get(k)==info[k] for k in ('bytes','sha256')),
        'render_surface_valid':surface['pass'],
        'face_fingerprint':qa._fingerprint(stats['fine_face_fingerprint'])==surface['face_fingerprint']==qa._fingerprint(provenance['fine_face_fingerprint']),
        'global_constraints_pass':all(c.get('pass') is True for c in stats['constraints']),
        'chunk_count':len(chunks)==header.get('chunks'),
        'chunks_nonempty':bool(chunks),
        'sampling_checks_pass':all(c.get('seam_and_overlap_check') is True for c in chunks),
        'chunk_occupancy_certificates':all(qa._fingerprint(c['full_fine_fingerprint'])==qa._fingerprint(c['expanded_fingerprint']) for c in chunks),
        'chunk_occupancy_counts':all(c['reference_owned_fine_cells']==c['full_fine_fingerprint']['count']==c['stored_fine_cells']+8*c['stored_core_cells'] for c in chunks),
        'fine_occupancy_certificate_sum':merged_fingerprints(c['full_fine_fingerprint'] for c in chunks)==qa._fingerprint(stats['full_fine_fingerprint']),
        'fine_expansion_certificate_sum':merged_fingerprints(c['expanded_fingerprint'] for c in chunks)==qa._fingerprint(stats['full_fine_fingerprint']),
        'no_geometry_fallback':stats.get('geometry_fallback') is False,
        'no_full_cell_union':stats.get('full_building_cell_merge_created') is False,
        'no_visible_core_faces':stats.get('core_visible_faces')==provenance.get('core_visible_faces')==0,
    }
    for key in ('source_id','source_revision','master_hash','grid_origin','materials'):
        checks['render_'+key]=header.get(key)==meta.get(key)
    for hk,pk in (('compiler_source_sha256','compiler_source_hash'),('layer_engine_sha256','layer_engine_sha256'),('layer_rules_sha256','layer_rules_sha256')):
        checks['provenance_'+hk]=qa._sha256(header.get(hk)) and header[hk]==provenance.get(pk)
    certificate=canonical_hash({'master_hash':header['master_hash'],'grid_origin':header['grid_origin'],'fine_occupancy_fingerprint':stats['full_fine_fingerprint']})
    checks['payload_certificate']=certificate==stats.get('occupancy_certificate_sha256')==meta.get('payload_hash')
    checks['payload_kind']=provenance.get('payload_hash_kind')=='fine_occupancy_fingerprint_certificate'
    edge=header['chunk_edge_fine_cells'];boxes=[]
    for c in chunks:
        if len(c['chunk'])!=3 or any(type(v)is not int for v in c['chunk']):raise qa.QAError('Invalid chunk coordinates')
        lo=[v*edge for v in c['chunk']];boxes.append([lo,[v+edge for v in lo]])
    checks['chunk_ownership_nonoverlapping']=not any(qa.boxes_overlap(boxes[i],boxes[j]) for i in range(len(boxes)) for j in range(i))
    for key,expected in (
        ('reference_full_fine_cells',stats['full_fine_fingerprint']['count']),
        ('stored_fine_cells',sum(c['stored_fine_cells'] for c in chunks)),
        ('stored_core_cells',sum(c['stored_core_cells'] for c in chunks)),
        ('stored_total_cells',sum(c['stored_fine_cells']+c['stored_core_cells'] for c in chunks)),
        ('lossless_fine_expanded_cell_count',sum(c['reference_owned_fine_cells'] for c in chunks)),
        ('quads',surface['quad_count']),('visible_unit_faces',surface['face_fingerprint']['count'])):
        checks[key]=stats.get(key)==expected
    checks['render_cell_count']=meta.get('cell_count')==stats['full_fine_fingerprint']['count']
    checks['chunk_face_count']=sum(c['visible_unit_faces'] for c in chunks)==surface['face_fingerprint']['count']
    checks['chunk_quad_count']=sum(c['quads'] for c in chunks)==surface['quad_count']
    checks['gzip_mtime_zero']=render_path.suffix=='.gz' and render_path.read_bytes()[4:8]==b'\0'*4
    source=qa._source_checks(header,stats,source_catalog);checks['source_artifacts']=source['pass']
    snapshots=replay.get('code_snapshots',{})
    checks['replay_code_complete']=REQUIRED_CODE.issubset(snapshots)
    checks['replay_snapshot_hashes']=all(qa._file_info(qa.ROOT/r['snapshot_path'])['sha256']==r['sha256'] for r in snapshots.values())
    checks['replay_input_hashes']=all(qa._file_info(qa.ROOT/r['path'])['sha256']==r['sha256'] for r in replay.get('inputs',{}).values())
    checks['replay_input_complete']=set(replay.get('inputs',{}))=={'authored_master','source_master','catalog','layer_rules'}
    for role,hk in (('core','compiler_source_sha256'),('engine','layer_engine_sha256'),('rules','layer_rules_sha256'),('catalog','input_catalog_sha256'),('connected_constraints','connectivity_source_sha256'),('polygon_crop_guard','polygon_guard_source_sha256')):
        checks['replay_'+role]=snapshots.get(role,{}).get('sha256')==header.get(hk)
    if 'chunk_enumeration_sha256' in header:
        checks['replay_chunk_enumeration']=snapshots.get('chunk_enumeration',{}).get('sha256')==header['chunk_enumeration_sha256']
    checks['replay_exporter']=snapshots.get('render_data',{}).get('sha256')==provenance.get('exporter_sha256')
    retained=None
    if retained_stats is not None:
        with qa._text_file(retained_stats) as stream:rs=json.load(stream)
        rc=qa.ROOT/rs['files']['.cells.jsonl.gz']['path'];rr=qa.ROOT/rs['files']['.render.json']['path']
        retained=qa.verify(layered_cells=rc,layered_render=rr,layered_stats=retained_stats,source_catalog=source_catalog)
        checks['retained_qa_pass']=retained['pass']
        checks['retained_occupancy_match']=retained['layered_cells']['expanded_fingerprint']==stats['full_fine_fingerprint']
        checks['retained_faces_match']=retained['layered_render']['face_fingerprint']==surface['face_fingerprint']
        checks['retained_source_identity']=all(rs.get(k)==stats.get(k) for k in ('asset_key','source_master_sha256','authored_master_sha256'))
        checks['retained_quads_match']=retained['layered_render']['quad_count']==surface['quad_count']
    passed=all(checks.values())
    return {'schema':SCHEMA,'pass':passed,'status':('PASS_RETAINED_CELL_PARITY' if retained else 'PASS_RENDER_ONLY_CERTIFICATE_STRUCTURAL') if passed else 'FAIL',
            'checks':checks,'surface':surface,'source_artifacts':source,'stats_file':qa._file_info(stats_path),'render_file':info,
            'retained_comparison':({'stats_file':qa._file_info(retained_stats),'pass':retained['pass']} if retained else None),
            'limitations':[] if retained else ['No retained voxel payload was supplied for independent occupancy recomputation. Occupancy evidence is the sampled per-chunk certificate; rerun the preserved common compiler with identical inputs to reproduce cells.'],
            'visual_status':'PENDING','full_building_cell_merge_created':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stats',required=True,type=Path);p.add_argument('--source-catalog',required=True,type=Path);p.add_argument('--retained-stats',type=Path);p.add_argument('--output',required=True,type=Path)
    x=p.parse_args()
    try:report=verify(x.stats,x.source_catalog,x.retained_stats)
    except (qa.QAError,OSError,ValueError,TypeError,KeyError) as error:report={'schema':SCHEMA,'pass':False,'error':str(error),'error_type':type(error).__name__}
    x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'pass':report['pass'],'status':report.get('status','FAIL'),'output':str(x.output)}))
    return 0 if report['pass'] else 1

if __name__=='__main__':raise SystemExit(main())
