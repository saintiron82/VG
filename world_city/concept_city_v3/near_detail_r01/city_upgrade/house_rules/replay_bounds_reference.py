"""Replay actual old full-reference houses with native cell_bounds, retaining no cells."""
import argparse,fcntl,json,resource,time
from pathlib import Path
import layered_compile as l


def run(keys,output):
    lock=(l.HERE/'compile.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(1500000000,1500000000))
    catalog=l.a.load(l.HERE/'generated/active_catalog.json');entries={r['asset_key']:r for r in catalog['assets']};reports=[]
    rules=l.a.load(l.HERE/'layer_rules.v1.json');edge,halo=rules['chunk_edge_fine_cells'],rules['halo_fine_cells']
    for key in keys:
        record=entries[key];master=l.load_master(l.a.ROOT/record['emitted_master_path']);old=l.a.load(l.HERE/'compiled'/f'{key}.layered.stats.json')
        source=l.SpatialSource(master,.05,range_only=True);origin=master.get('grid_origin',[0,0,0]);cells_fp=l.Fingerprint();faces_fp=l.Fingerprint();start=time.monotonic();chunks=[]
        for part in old['chunks']:
            low=[i*edge for i in part['chunk']];high=[i+edge for i in low]
            b={'min':[i-halo for i in low],'max':[i+halo for i in high]}
            world_low=[origin[j]+b['min'][j]*.05 for j in range(3)];world_high=[origin[j]+b['max'][j]*.05 for j in range(3)]
            fine=l.a.core.compile_master(source.bounded_master(world_low,world_high),{'pitch':.05},cell_bounds=b,max_candidate_cells=5000000,max_output_cells=600000)
            own=[r for r in fine['cells'] if l.owned(r[:3],low,high)];fp=l.Fingerprint()
            for row in own:fp.add(row)
            cells_fp.merge(fp)
            if fine['cells']:_,faces=l.owned_quads(l.make_render_data(fine),low,high,rules)
            else:faces=set()
            expected=l.expected_faces(own,{tuple(r[:3]):r for r in fine['cells']})
            if faces!=expected:raise ValueError('Native scope mesh seam mismatch')
            for face in faces:faces_fp.add(list(face))
            chunks.append({'chunk':part['chunk'],'native_fine_cells':len(own),'old_fine_cells':part['reference_owned_fine_cells'],'count_match':len(own)==part['reference_owned_fine_cells'],'surface_faces':len(faces),'old_surface_faces':part['visible_unit_faces'],'surface_count_match':len(faces)==part['visible_unit_faces']})
        report={'asset_key':key,'old_stats_sha256':l.a.sha(l.HERE/'compiled'/f'{key}.layered.stats.json'),'authored_master_sha256':record['emitted_master_sha256'],
                'native_compiler_sha256':l.a.sha(l.a.core.__file__),'original_compiler_sha256':'c4cc126554425211c7c670fefd0f97c22534ee5e489886354e0e00dd913f19e6',
                'cell_fingerprint':cells_fp.value(),'old_cell_fingerprint':old['full_fine_fingerprint'],'face_fingerprint':faces_fp.value(),'old_face_fingerprint':old['fine_face_fingerprint'],
                'cells_equal':cells_fp.value()==old['full_fine_fingerprint'],'faces_equal':faces_fp.value()==old['fine_face_fingerprint'],'chunks':chunks,
                'elapsed_seconds':time.monotonic()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'whole_building_cell_union_created':False}
        report['pass']=report['cells_equal'] and report['faces_equal'] and all(r['count_match'] and r['surface_count_match'] for r in chunks)
        reports.append(report);print(json.dumps({k:v for k,v in report.items() if k!='chunks'}),flush=True)
    result={'schema':'riverstone.house_detail.native_bounds_reference_replay.v1','assets':reports,'pass':all(r['pass'] for r in reports)}
    l.a.write(output,result);return result['pass']


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('keys',nargs='+');p.add_argument('--output',type=Path,default=l.HERE/'generated/native_bounds_reference_replay.json');x=p.parse_args()
    raise SystemExit(0 if run(x.keys,x.output) else 1)
