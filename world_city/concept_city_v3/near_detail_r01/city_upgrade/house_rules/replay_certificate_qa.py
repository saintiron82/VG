"""Independent, bounded original-master replay of render-only chunk certificates.

Loads the exact preserved common core, evaluates the complete unpruned authored
master in selected halo bounds, and independently compares owned occupancy and
exterior faces to the committed certificates/render. This is explicitly sampled
replay, not a claim that all chunks were independently recomputed.
"""
from __future__ import annotations
import argparse
import importlib.util
import itertools
import json
from pathlib import Path
import resource
import time
import layered_qa as qa


def quad_owner(rect,edge):
    axis,sign,plane,u0,u1,v0,v1=rect;u=(axis+1)%3;v=(axis+2)%3
    if u0//edge!=(u1-1)//edge or v0//edge!=(v1-1)//edge:raise qa.QAError('Quad crosses original ownership boundary')
    result=[0,0,0];result[axis]=(plane-(sign>0))//edge;result[u]=u0//edge;result[v]=v0//edge
    return tuple(result)


def choose_chunks(chunks,limit=4):
    nonempty=[i for i,c in enumerate(chunks) if c['reference_owned_fine_cells']]
    if not nonempty:return []
    candidates=[max(nonempty,key=lambda i:chunks[i]['reference_owned_fine_cells']),nonempty[0],nonempty[len(nonempty)//2],nonempty[-1]]
    chosen=[]
    for i in candidates:
        if i not in chosen:chosen.append(i)
    for i in nonempty:
        if len(chosen)>=limit:break
        if i not in chosen:chosen.append(i)
    return chosen[:limit]


def owned(row,low,high):return all(low[j]<=row[j]<high[j] for j in range(3))


def verify(stats_path,limit=4):
    start=time.perf_counter();stats_path=Path(stats_path)
    stats=json.loads(stats_path.read_text());header=stats['compiled_header'];contract=stats['replay_contract']
    snapshot=contract['code_snapshots']['core'];path=qa.ROOT/snapshot['snapshot_path']
    if qa._file_info(path)['sha256']!=snapshot['sha256'] or snapshot['sha256']!=header['compiler_source_sha256']:raise qa.QAError('Replay core snapshot hash mismatch')
    for record in contract['inputs'].values():
        if qa._file_info(qa.ROOT/record['path'])['sha256']!=record['sha256']:raise qa.QAError('Replay source hash mismatch')
    spec=importlib.util.spec_from_file_location('preserved_common_replay',path);core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    with qa._text_file(qa.ROOT/contract['inputs']['authored_master']['path']) as f:master=json.load(f)
    if core.digest(master)!=header['master_hash']:raise qa.QAError('Replay canonical master mismatch')
    render_path=qa.ROOT/stats['files']['.render.json']['path']
    if qa._file_info(render_path)['sha256']!=stats['files']['.render.json']['sha256']:raise qa.QAError('Replay render hash mismatch')
    with qa._text_file(render_path) as f:render=json.load(f)
    indices=choose_chunks(stats['chunks'],limit);selected={tuple(stats['chunks'][i]['chunk']):i for i in indices}
    edge=header['chunk_edge_fine_cells'];halo=header['halo_fine_cells'];origin=header['grid_origin'];surface={key:qa.Fingerprint() for key in selected};quads={key:0 for key in selected}
    for group in render['groups']:
        for quad in group['quads']:
            rect=qa._quad_rectangle(quad,origin,.05);key=quad_owner(rect,edge)
            if key not in surface:continue
            quads[key]+=1;axis,sign,plane,u0,u1,v0,v1=rect
            for u in range(u0,u1):
                for v in range(v0,v1):surface[key].add([axis,sign,plane,u,v,group['material']])
    del render
    reports=[]
    for key,index in selected.items():
        tick=time.perf_counter();summary=stats['chunks'][index];low=[v*edge for v in key];high=[v+edge for v in low]
        bounds={'min':[v-halo for v in low],'max':[v+halo for v in high]}
        result=core.compile_master(master,{'pitch':.05},cell_bounds=bounds,max_candidate_cells=5000000,max_output_cells=600000)
        cells={tuple(row[:3]):row for row in result['cells']};occupancy=qa.Fingerprint();exterior=qa.Fingerprint()
        for row in result['cells']:
            if not owned(row,low,high):continue
            occupancy.add(row)
            for axis in range(3):
                for sign in (-1,1):
                    neighbor=list(row[:3]);neighbor[axis]+=sign
                    if tuple(neighbor) in cells:continue
                    plane=row[axis]+(sign>0);u=(axis+1)%3;v=(axis+2)%3
                    exterior.add([axis,sign,plane,row[u],row[v],row[5]])
        checks={'owned_occupancy_and_semantics_match':occupancy.as_dict()==qa._fingerprint(summary['full_fine_fingerprint']),
            'directed_material_exterior_faces_match':exterior.as_dict()==surface[key].as_dict(),
            'exterior_face_count_match':exterior.count==summary['visible_unit_faces'],
            'quad_count_match':quads[key]==summary['quads'],
            'bounded_constraints_not_global_claim':result.get('global_constraints_evaluated') is False}
        reports.append({'chunk_index':index,'chunk':list(key),'checks':checks,'pass':all(checks.values()),
            'owned_occupancy_fingerprint':occupancy.as_dict(),'exterior_fingerprint':exterior.as_dict(),
            'candidate_cells':result['candidate_cells'],'seconds':time.perf_counter()-tick})
        del cells,result
    return {'schema':'riverstone.house_detail.independent_native_replay.v1','pass':bool(reports) and all(r['pass'] for r in reports),
        'scope':'Deterministic sampled owned chunks, replayed from complete unpruned authored master using the exact preserved common core.',
        'sample_selection':'Largest occupied chunk, first/middle/last nonempty chunk; fill unique samples in index order.',
        'sampled_chunks':len(reports),'total_compiled_chunks':len(stats['chunks']),'all_chunks_independently_replayed':len(reports)==len(stats['chunks']),
        'source_shapes_and_operations_pruned':False,'source_shapes_modified':False,'global_constraint_pass_inferred':False,
        'reports':reports,'stats_file':qa._file_info(stats_path),'core_snapshot':snapshot,
        'elapsed_seconds':time.perf_counter()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'limitations':['Unsampled chunk occupancy relies on production common sampling and its complete per-chunk certificates, not this sampled replay.']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stats',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--samples',type=int,default=4);x=p.parse_args()
    if not 1<=x.samples<=16:raise ValueError('Sample count must be 1..16')
    resource.setrlimit(resource.RLIMIT_AS,(1500000000,1500000000))
    try:report=verify(x.stats,x.samples)
    except (qa.QAError,OSError,ValueError,TypeError,KeyError) as error:report={'schema':'riverstone.house_detail.independent_native_replay.v1','pass':False,'error':str(error),'error_type':type(error).__name__}
    x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k) for k in ('pass','sampled_chunks','total_compiled_chunks','elapsed_seconds','max_rss_kib','error')}))
    return 0 if report['pass'] else 1

if __name__=='__main__':raise SystemExit(main())
