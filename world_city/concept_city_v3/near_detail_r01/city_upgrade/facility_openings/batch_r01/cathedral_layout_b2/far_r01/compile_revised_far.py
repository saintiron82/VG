"""Exact whole-source coarse replay and visual-only revised-source export.

No geometry generation other than the common compiler and common static mesher.
No collision cache or city index changes. Runtime binds this explicit sidecar.
"""
import argparse,gc,hashlib,json,resource,signal,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
F=HERE.parents[2];sys.path.insert(0,str(F))
import author as a
from voxel_character.common import render_data

def run(revision_path, original_render_path):
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    def timeout(*args):raise TimeoutError('60-second total coarse replay/export cap')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(60)
    start=time.monotonic();revision=a.load(revision_path);rev=revision['source_revision'];original_path=a.ROOT/rev['original_master_path'];revised_path=a.ROOT/rev['revised_master_path']
    assert a.sha(original_path)==rev['original_master_sha256'] and a.sha(revised_path)==rev['revised_master_sha256']
    original=a.load(original_path);revised=a.load(revised_path);old_render=a.load(original_render_path);key=old_render['source_id']
    assert original['grid_origin']==revised['grid_origin']==old_render['grid_origin']==[0,0,0]
    assert original['materials']==revised['materials']==old_render['materials'] and old_render['pitch']==.5
    proofs={};rows={};boxlist=[]
    allowed=set(rev['allowed_operation_ids'])
    for master in [original,revised]:
        for c,i,o,t,bb in a.source_inventory(master):
            if o['id'] in allowed:boxlist.append(bb)
    for name,master in [('original',original),('revised',revised)]:
        t=time.monotonic();compiled=a.core.compile_master(master,{'pitch':.5},max_candidate_cells=200000,max_output_cells=100000)
        assert compiled['valid'] and compiled['candidate_cells']<=200000
        surface=render_data.make_render_data(compiled)
        compact={tuple(r[:3]):tuple(r[3:]) for r in compiled['cells']}
        proofs[name]={'candidate_cells':compiled['candidate_cells'],'cell_count':len(compiled['cells']),'payload_hash':compiled['payload_hash'],'quad_count':surface['quad_count'],'bounds':surface['bounds'],'constraint_results':compiled['constraints'],'surface_digest':a.core.digest(surface['groups']),'seconds':round(time.monotonic()-t,6)}
        if name=='original':
            same={k:surface[k]==old_render[k] for k in ['source_id','source_revision','master_hash','payload_hash','pitch','grid_origin','materials','cell_count','bounds','groups','quad_count']}
            proofs['original_cache_replay']={'exact_fields':same,'provenance_byte_equality_claimed':False,'all_pass':all(same.values())}
            assert all(same.values()),same
            rows=compact
        else:
            changed=[p for p in rows.keys()|compact.keys() if rows.get(p)!=compact.get(p)]
            added=len(compact.keys()-rows.keys());removed=len(rows.keys()-compact.keys())
            outside=[p for p in changed if not any(all(bb[0][j]-1e-7 <= (p[j]+.5)*.5 <= bb[1][j]+1e-7 for j in range(3)) for bb in boxlist)]
            assert not outside,'Changed coarse sample outside approved old/new window operation envelopes'
            proofs['revised_difference']={'changed_cell_labels':len(changed),'occupancy_added_cells':added,'occupancy_removed_cells':removed,'outside_approved_old_new_window_envelopes':len(outside),'changed_sample_height_range_m':[min((p[1]+.5)*.5 for p in changed),max((p[1]+.5)*.5 for p in changed)] if changed else None,'changed_cell_keys_sha256':a.core.digest(sorted(changed)),'same_palette':True,'collision_reference_changed':False}
            target=HERE/(key+'.b2.far.render.json.gz');assert not target.exists();a.write(target,surface)
        print(json.dumps({'phase':name,**proofs[name],'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
        del compiled,surface,compact;gc.collect()
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<256*1024
    tests={'original_cache_exact_geometry_material_and_payload_replay':proofs['original_cache_replay']['all_pass'],'same_pitch_grid_palette':True,'only_approved_window_envelopes_changed':not proofs['revised_difference']['outside_approved_old_new_window_envelopes'],'source_global_constraints_pass':all(c['pass'] for k in ['original','revised'] for c in proofs[k]['constraint_results']),'render_only_collision_reference_unchanged':True,'output_within_original_coarse_bounds':proofs['revised']['bounds']==old_render['bounds']}
    assert all(tests.values()),tests
    inputs=[]
    for p,role in [(revision_path,'explicit source revision'),(original_path,'indexed original source'),(revised_path,'approved revised original source'),(original_render_path,'unchanged original coarse render and collision reference'),(Path(__file__),'bounded common orchestration'),(Path(a.core.__file__),'common compiler'),(Path(render_data.__file__),'common static exporter'),(Path(render_data.mesh.__file__),'common greedy surface mesher')]:inputs.append({'path':str(p.resolve().relative_to(a.ROOT)),'sha256':a.sha(p),'role':role})
    contract={'schema':'riverstone.revised_far_visual.v1','asset_key':key,'original_master_sha256':rev['original_master_sha256'],'original_render_sha256':a.sha(original_render_path),'revised_master_sha256':rev['revised_master_sha256'],'render_path':str(target.relative_to(a.ROOT)),'render_sha256':a.sha(target),'pitch':.5,'grid_origin':[0,0,0],'output_quad_count':proofs['revised']['quad_count'],'collision_reference_changed':False,'tests':tests,'all_pass':True,'source_revision_path':str(revision_path.relative_to(a.ROOT)),'source_revision_sha256':a.sha(revision_path),'source_inputs':inputs,'bounds':proofs['revised']['bounds'],'proofs':proofs,'seconds':round(time.monotonic()-start,6),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'scope':'Visual-only common .5m compile of explicit original-style revised source. Runtime keeps indexed original collider and switches only far MeshInstance mesh. Original versus revised occupancy differences are reported, not treated as collider modifications.'}
    path=HERE/(key+'.b2.far.contract.json');assert not path.exists();a.write(path,contract);signal.alarm(0)
    print(json.dumps({'contract_path':str(path.relative_to(a.ROOT)),'contract_sha256':a.sha(path),'render_path':contract['render_path'],'render_sha256':contract['render_sha256'],'quad_count':contract['output_quad_count'],'seconds':contract['seconds'],'max_rss_kib':contract['max_rss_kib'],'difference':proofs['revised_difference'],'all_pass':True}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('revision',type=Path);p.add_argument('original_render',type=Path);args=p.parse_args();run(args.revision.resolve(),args.original_render.resolve())
