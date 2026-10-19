"""Output-only recovery from a complete immutable chunk chain. Sampling calls: zero.

The old full compiler, failed output and checkpoint remain unchanged. A separate
materialization identity binds the old sampling recipe to this writer revision.
"""
import argparse
from collections import defaultdict
import copy
import fcntl
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import zlib
import adapter as a
import checkpoint_store
import layered_compile_v2_r02 as sampling
import render_only_qa
import render_only_retention
import output_reservations_v3 as reservations

HERE=Path(__file__).resolve().parent


def reconstruct(directory):
    directory=Path(directory);manifest=a.load(directory/'manifest.json');identity=manifest['identity'];header=identity['header']
    store=checkpoint_store.Store(directory,identity)
    if store.completed_count!=header['chunks'] or len(identity['owned_lows'])!=store.completed_count:
        raise ValueError('Materialization requires every planned source-domain chunk')
    for role,path in identity['source_paths'].items():
        key={'master':'authored_master_sha256','source':'source_master_sha256','catalog':'input_catalog_sha256','rules':'layer_rules_sha256'}[role]
        if a.sha(a.ROOT/path)!=header[key]:raise ValueError('Frozen sampling input changed: '+role)
    master=sampling.load_master(a.ROOT/identity['source_paths']['master'])
    if a.core.digest(master)!=header['master_hash']:raise ValueError('Checkpoint canonical source differs')
    state=store.load_state();groups=defaultdict(list);chunks=[]
    for n,record in enumerate(store.load_records()):
        c=record['chunk_stats'];edge=header['chunk_edge_fine_cells']
        if c['chunk']!=[v//edge for v in identity['owned_lows'][n]] or c['quads']!=len(record['quads']):raise ValueError('Chunk ownership/order/quad count differs')
        if not c['seam_and_overlap_check'] or c['full_fine_fingerprint']!=c['expanded_fingerprint']:raise ValueError('Incomplete exact chunk certificate')
        chunks.append(c)
        for material,quad in record['quads']:groups[material].append(quad)
    if render_only_qa.merged_fingerprints(c['full_fine_fingerprint'] for c in chunks)!=state['all_fingerprint']:raise ValueError('Whole occupancy certificate differs')
    for state_key,chunk_key in (('total_fine','stored_fine_cells'),('total_core','stored_core_cells')):
        if state[state_key]!=sum(c[chunk_key] for c in chunks):raise ValueError('Stored cell counts differ')
    if state['candidate_total']!=sum(c['near_candidate_cells']+c['core_candidate_cells'] for c in chunks):raise ValueError('Candidate count differs')
    if state['face_fingerprint']['count']!=sum(c['visible_unit_faces'] for c in chunks):raise ValueError('Visible face count differs')
    checks=[]
    for constraint in master.get('constraints',[]):
        if constraint['kind']=='connected':result=checkpoint_store.restore_connected(state['connected'][constraint['id']]).result()
        elif constraint['kind']=='nonempty':
            count=state['constraints'].get(constraint['id'],0);result={'pass':count>=constraint.get('minimum_cells',1),'occupied_fine_reference_cells':count}
        else:raise ValueError('Unsupported global aggregation kind')
        checks.append({'id':constraint['id'],'kind':constraint['kind'],**result})
    if not all(c['pass'] for c in checks):raise ValueError('Global source constraints failed')
    origin=header['grid_origin'];certificate=a.core.digest({'master_hash':header['master_hash'],'grid_origin':origin,'fine_occupancy_fingerprint':state['all_fingerprint']})
    provenance={'compiler_source_hash':header['compiler_source_sha256'],'layer_engine_sha256':header['layer_engine_sha256'],
        'layer_rules_sha256':header['layer_rules_sha256'],'exporter_sha256':header['replay_dependency_hashes']['render_data'],
        'fine_face_fingerprint':{k:state['face_fingerprint'][k] for k in ('count','xor256','sum256')},'mixed_occupancy_pitches_m':[.05,.1],'core_visible_faces':0,
        'storage_mode':header['storage_mode'],'payload_hash_kind':'fine_occupancy_fingerprint_certificate'}
    if 'sampling_backend' in header:
        backend=sampling.verified_sampler_provenance()
        if backend!=header['sampling_backend']:raise ValueError('Original sampler provenance changed')
        provenance={'sampling_backend':backend,**provenance}
    render={'schema':'riverstone.voxel.render.v1','unit':'m','source_id':master['id'],'source_revision':master['revision'],
        'master_hash':a.core.digest(master),'payload_hash':certificate,'pitch':.05,'grid_origin':origin,'materials':master['materials'],
        'cell_count':state['all_fingerprint']['count'],'bounds':{'min':[round(origin[j]+state['mins'][j]*.05,8) for j in range(3)],
            'max':[round(origin[j]+state['maxs'][j]*.05,8) for j in range(3)]},
        'groups':[{'material':m,'quads':groups[m]} for m in sorted(groups)],'quad_count':sum(len(v) for v in groups.values()),
        'geometry':'Exact full-.05 exposed surfaces, owned/clipped from unchanged common halo meshing. Hidden structural cells use conservative .1 aggregation; no core faces are visible.',
        'provenance':provenance}
    return identity,header,state,chunks,checks,render


def partial_prefix(path):
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS);digest=hashlib.sha256();length=0
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(65536),b''):
            decoded=decoder.decompress(data);length+=len(decoded);digest.update(decoded)
    return {'bytes':length,'sha256':digest.hexdigest(),'gzip_stream_complete':decoder.eof,'compressed_sha256':a.sha(path)}


def encoded_pieces(render):
    for text in json.JSONEncoder(separators=(',',':'),ensure_ascii=False).iterencode(render):yield text.encode('utf-8')
    yield b'\n'


def verify_partial_prefix(render,partial):
    evidence=partial_prefix(partial);remaining=evidence['bytes'];digest=hashlib.sha256()
    for piece in encoded_pieces(render):
        if remaining<=0:break
        part=piece[:remaining];digest.update(part);remaining-=len(part)
    if remaining or digest.hexdigest()!=evidence['sha256']:raise ValueError('Preserved partial render prefix differs from immutable chunk values')
    return {**evidence,'exact_uncompressed_prefix_match':True}


def run(directory,output):
    begin=time.perf_counter();directory=Path(directory).resolve();output=Path(output).resolve()
    def timeout(signum,frame):raise TimeoutError('Output-only materialization exceeded 600 seconds')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(600)
    limit=738197504;_,hard=resource.getrlimit(resource.RLIMIT_AS)
    if hard!=resource.RLIM_INFINITY:limit=min(limit,hard)
    resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
    config=a.load(HERE/'shared_output_budget.v2.json')
    if a.sha(reservations.__file__)!='4585bb869ec736e30e524ec6d408db9ed3adceda7d82b336225b8f0079bd9b55':raise ValueError('Unreviewed budget matcher')
    with (HERE/'queue.lock').open('a') as qlock,(HERE/'compile.lock').open('a') as clock:
        for lock in (qlock,clock):
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ValueError('Original production execution is still active')
        identity,header,state,chunks,checks,render=reconstruct(directory);key=header['asset_key']
        if key!='registered_castle_front_gate_wing':raise ValueError('This recovery approval currently covers the complete castle output only')
        if output!=HERE.parent/'facility_roofs/compiled_expansion_r01/materialized_r01':raise ValueError('Unexpected recovery revision')
        if header['layer_engine_sha256']!=a.sha(sampling.__file__):raise ValueError('Original sampling engine no longer matches')
        prior=directory.parent/(key+'.layered.checkpoint_sessions.json');sessions=a.load(prior)
        if len(sessions['sessions'])!=2:raise ValueError('Both fixed original executions must be accounted for')
        stop_path=HERE/'compile_logs/castle_v2_full.r01.log'
        stop_evidence=None
        if sessions['sessions'][-1]['status']=='RUNNING':
            # A supervising subprocess timeout can kill before the child's final ledger write.
            # Both production locks are already acquired above; require its immutable receipt too.
            stop_evidence=json.loads(stop_path.read_text().splitlines()[-1])
            if (stop_evidence.get('facility_pending')!=key or stop_evidence.get('execution')!=2 or
                stop_evidence.get('state') not in ('PENDING_TIME_LIMIT','PENDING_COMPILE_FAILURE')):
                raise ValueError('Original execution has no verified terminal controller receipt')
        partial=directory.parent/(key+'.layered.render.json.gz.partial')
        prefix=verify_partial_prefix(render,partial)
        output.mkdir(parents=True,exist_ok=True)
        if any(output.glob(key+'.layered*')):raise ValueError('Existing recovery output preserved')
        replay_paths={'core':a.core.__file__,'engine':sampling.__file__,'adapter':a.__file__,
            'exact_sampling_v2':sampling.exact_sampling_v2.__file__,'output_reservations_v2':sampling.output_reservations_v2.__file__,
            'connected_constraints':sampling.connected_constraints.__file__,'polygon_crop_guard':sampling.polygon_crop_guard.__file__,
            'retention':sampling.render_only_retention.__file__,'chunk_enumeration':sampling.chunk_enumeration.__file__,
            'render_data':sys.modules[sampling.make_render_data.__module__].__file__,'mesh':sys.modules['mesh'].__file__,
            'rules':a.ROOT/identity['source_paths']['rules'],'catalog':a.ROOT/identity['source_paths']['catalog'],
            'checkpoint_store':checkpoint_store.__file__,'checkpoint_policy':HERE/'facility_checkpoint_policy.v1.json'}
        if {role:a.sha(path) for role,path in replay_paths.items()}!=header['replay_dependency_hashes']:raise ValueError('Original sampling dependencies changed')
        replay_paths.update(materializer=__file__,materialization_budget_helper=reservations.__file__,
            materialization_shared_budget=HERE/'shared_output_budget.v2.json')
        materialization={'schema':'riverstone.output_materialization.v1','sampling_calls':0,'sampling_identity':identity,
            'sampling_checkpoint_sha256':a.sha(directory/'manifest.json'),'checkpoint_directory':str(directory.relative_to(a.ROOT)),
            'sampling_execution_ledger_sha256':a.sha(prior),'preserved_partial':prefix,
            'materialization_wall_limit_seconds':600,'materializer_sha256':a.sha(__file__),'budget_helper_sha256':a.sha(reservations.__file__),
            'budget_contract_sha256':a.sha(HERE/'shared_output_budget.v2.json'),'output_directory':str(output.relative_to(a.ROOT)),
            'original_checkpoint_modified':False,'original_partial_modified':False,
            'terminal_controller_receipt':({'path':str(stop_path.relative_to(a.ROOT)),'sha256':a.sha(stop_path),
                'result':stop_evidence} if stop_evidence is not None else None)}
        book=reservations.ReservationBook(a.ROOT/config['book_path'],a.ROOT,[a.ROOT/p for p in config['retained_roots']],config['limit_bytes'],min_free_disk_bytes=config['min_free_disk_bytes'])
        rkey='materialization:'+key+'@'+str(output.relative_to(a.ROOT));scopes=[{'directory':str(output.relative_to(a.ROOT)),'prefix':key+'.layered'}]
        for role,path in replay_paths.items():
            path=Path(path);snapshot=HERE/'replay_code'/(role+'_'+a.sha(path)[:16]+path.suffix)
            if not snapshot.exists():scopes.append({'directory':str(snapshot.parent.relative_to(a.ROOT)),'prefix':snapshot.name})
        book.reserve(rkey,scopes,8000000,materialization)
        with book.writer(rkey):
            def save(path,value):
                data=(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode();book.check(rkey,len(data)+65536)
                if path.exists():raise ValueError('Existing artifact preserved')
                tmp=path.with_name(path.name+'.tmp')
                with tmp.open('xb',buffering=0) as stream:stream.write(data);os.fsync(stream.fileno())
                os.replace(tmp,path)
            save(output/(key+'.layered.materialization.json'),materialization)
            class Writer:
                def __init__(self,raw):self.raw=raw
                def write(self,data):book.check(rkey,len(data)+65536);return self.raw.write(data)
                def flush(self):self.raw.flush()
            rp=output/(key+'.layered.render.json.gz');tmp=rp.with_name(rp.name+'.partial');uncompressed=hashlib.sha256()
            with tmp.open('xb',buffering=0) as raw:
                with gzip.GzipFile(filename='',mode='wb',fileobj=Writer(raw),mtime=0,compresslevel=5) as zipped:
                    for piece in encoded_pieces(render):uncompressed.update(piece);zipped.write(piece)
            decoded=hashlib.sha256()
            with gzip.open(tmp,'rb') as stream:
                for data in iter(lambda:stream.read(1048576),b''):decoded.update(data)
            if decoded.digest()!=uncompressed.digest():raise ValueError('Gzip decoding differs from the exact reconstructed render bytes')
            os.replace(tmp,rp)
            rules=a.load(a.ROOT/identity['source_paths']['rules']);catalog=a.load(a.ROOT/identity['source_paths']['catalog'])
            entry=next(r for r in catalog['assets'] if r['asset_key']==key)
            elapsed=time.perf_counter()-begin
            stats={'schema':'riverstone.house_detail.layered_stats.v1','status':'PASS_STRUCTURAL_PENDING_VISUAL','asset_key':key,
                'render_encoding':'gzip_json','render_gzip_mtime':0,'source_master_sha256':header['source_master_sha256'],
                'authored_master_sha256':header['authored_master_sha256'],'full_fine_fingerprint':state['all_fingerprint'],
                'fine_face_fingerprint':state['face_fingerprint'],'reference_full_fine_cells':state['all_fingerprint']['count'],
                'stored_fine_cells':state['total_fine'],'stored_core_cells':state['total_core'],
                'stored_total_cells':state['total_fine']+state['total_core'],'lossless_fine_expanded_cell_count':state['total_fine']+8*state['total_core'],
                'quads':render['quad_count'],'visible_unit_faces':state['face_fingerprint']['count'],'core_visible_faces':0,'chunks':chunks,
                'candidate_cells_including_halos':state['candidate_total'],'elapsed_seconds':state['elapsed_seconds'],
                'elapsed_scope':'Original fully committed sampling/checkpoint time; materialization and failed output time recorded separately.',
                'authoring_seed':header.get('authoring_seed'),'connectivity_source_sha256':header['connectivity_source_sha256'],
                'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'memory_limit_bytes':limit,'wall_time_limit_seconds':900,
                'chunk_enumeration':header['chunk_enumeration'],'constraints':checks,'source_unchanged':True,'compiler_changed':True,
                'compiler_extension':'opt_in_exact_sampling_v2_with_integer_cell_bounds_v1','sampling_backend':header['sampling_backend'],
                'compiler_default_geometry_unchanged':True,'full_building_cell_merge_created':False,'geometry_fallback':False,
                'mixed_occupancy_pitches_m':[.05,.1],'spatial_sampling_contract':'original_shapes_integer_cell_bounds_v1',
                'op_pruning_mode':'bbox_disjoint_ops_only','all_chunks_exact_exterior_face_match':True,'all_chunks_overlap_free':True,
                'fine_grid_vertex_rounding_decimals':rules['vertex_decimal_places'],'storage_mode':header['storage_mode'],
                'retained_cell_payload':False,'compiled_header':header,'occupancy_certificate_sha256':render['payload_hash'],
                'files':{'.render.json':{'path':str(rp.relative_to(a.ROOT)),'bytes':rp.stat().st_size,'sha256':a.sha(rp),'encoding':'gzip_json'}},
                'materialization':{'identity_path':str((output/(key+'.layered.materialization.json')).relative_to(a.ROOT)),
                    'identity_sha256':a.sha(output/(key+'.layered.materialization.json')),'seconds':elapsed,'sampling_calls':0,
                    'decoded_render_sha256':decoded.hexdigest(),'exact_render_bytes_roundtrip':True,'original_execution_records':sessions},
                'checkpoint':{'directory':str(directory.relative_to(a.ROOT)),'committed_chunks':len(chunks),'sessions_started':2,
                    'max_sessions':2,'completed_checkpoints_preserved':True,'execution_ledger_path':str(prior.relative_to(a.ROOT))}}
            growth=sum(Path(p).stat().st_size for p in replay_paths.values());book.check(rkey,growth+65536)
            stats['replay_contract']=render_only_retention.preserve_replay_sources(a,HERE,key,a.ROOT/identity['source_paths']['master'],
                a.ROOT/identity['source_paths']['source'],a.ROOT/identity['source_paths']['catalog'],a.ROOT/identity['source_paths']['rules'],replay_paths)
            stats['replay_contract']['command'][1]=str(Path(sampling.__file__).relative_to(a.ROOT))
            stats['replay_contract']['sampling_backend']=header['sampling_backend']
            stats['output_reservation']={'key':rkey,'book_path':config['book_path'],'cap_bytes':8000000,'shared_limit_bytes':config['limit_bytes'],'release_requires_final_qa':True}
            save(output/(key+'.layered.stats.json'),stats)
        print(json.dumps({'materialized':key,'sampling_calls':0,'quads':stats['quads'],'seconds':time.perf_counter()-begin,
            'max_rss_kib':stats['max_rss_kib'],'files':stats['files'],'reservation_active_until_qa':rkey}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True,type=Path);p.add_argument('--output-dir',required=True,type=Path)
    x=p.parse_args();run(x.checkpoint,x.output_dir)
