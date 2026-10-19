"""Compare old/new common source ONLY in the six exact changed-source AABBs."""
import argparse,gc,math,resource,time
from pathlib import Path
import compose as c
a=c.a
import estimate_run as b

def run(spec_path,estimate_only=False):
    start=time.monotonic();spec=a.load(spec_path);rev=a.load(a.ROOT/spec['revision_path']);base=a.load(a.ROOT/spec['canonical_master_path']);newpath=a.ROOT/spec['output_directory']/'canonical.authored.master.json.gz';new=a.load(newpath)
    baseline_bounds=b.bounds_list(base,.05);new_bounds=b.bounds_list(new,.05);plans=[]
    for region in rev['change_aabbs_m']:
        cb={'min':[math.floor(v*20)-1 for v in region['min']],'max':[math.ceil(v*20)+1 for v in region['max']]}
        oldcost=b.cost(baseline_bounds,cb);newcost=b.cost(new_bounds,cb);assert max(oldcost,newcost)<200000
        plans.append({'id':region['operation_id'],'cell_bounds':cb,'old_candidates':oldcost,'new_candidates':newcost})
    result={'schema':'riverstone.authored_contact.delta_qa.v1','old_master_sha256':a.sha(a.ROOT/spec['canonical_master_path']),'new_master_sha256':a.sha(newpath),'source_revision_sha256':a.sha(a.ROOT/spec['revision_path']),'plan':plans,'common_calls':12,'candidate_visits':sum(p['old_candidates']+p['new_candidates'] for p in plans),'source_shapes_cropped':False}
    print({'stage':'estimate','candidates':result['candidate_visits'],'calls':12},flush=True)
    if estimate_only:
        a.write(a.HERE/'composed/cathedral_authored_delta_cost.json',result);return
    protected=rev['common_source_delta']['append_assembly_cuts'];prepared=[(a.core.prepare_shape(cut['shape'],.05),a.core.transform(cut.get('transform'))) for cut in protected];alladded=set();tests=[]
    for plan in plans:
        old=a.core.compile_master(base,{'pitch':.05},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=plan['cell_bounds']);fresh=a.core.compile_master(new,{'pitch':.05},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=plan['cell_bounds'])
        before={tuple(r[:3]):r[3:] for r in old['cells']};after={tuple(r[:3]):r[3:] for r in fresh['cells']};added=set(after)-set(before);removed=set(before)-set(after);changed={p for p in before.keys()&after.keys() if before[p]!=after[p]};protected_hits=0;outside=0
        for p in added:
            assert after[p][0]=='cathedral_eave_support_r01';world=[(x+.5)*.05 for x in p]
            protected_hits+=any(a.core.contains(sh,a.core.inverse(tr,world),epsilon=.05*a.core.EPS) for sh,tr in prepared)
            outside+=not any(all(r['min'][j]-1e-8<=world[j]<=r['max'][j]+1e-8 for j in range(3)) for r in rev['change_aabbs_m'])
        assert not removed and not changed and not protected_hits and not outside
        alladded.update(added);tests.append({'operation':plan['id'],'old_payload_hash':old['payload_hash'],'new_payload_hash':fresh['payload_hash'],'added_cells':len(added),'removed_cells':len(removed),'relabelled_existing_cells':len(changed),'protected_cavity_or_entry_added_cells':protected_hits,'added_cell_centres_outside_declared_change_aabbs':outside});del old,fresh,before,after,added;gc.collect();print({'checked':plan['id'],'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed':round(time.monotonic()-start,2)},flush=True)
    result.update(all_pass=True,regions=tests,unique_added_cells=len(alladded),sampled_added_voxel_volume_m3=len(alladded)*.05**3,analytic_added_volume_m3=rev['aggregate']['net_added_analytic_volume_m3'],proof_scope='All grid cells in the six exact changed-source AABBs plus one-cell halo. New operations are analytically bounded there; original operations and order are byte-identical. Not a whole-building fine occupancy or whole-render manifold proof.',outside_changed_domains_source_ops_identical=True,original_occupancy_unchanged=False,elapsed_seconds=round(time.monotonic()-start,3),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    assert result['max_rss_kib']<256*1024 and result['elapsed_seconds']<600;a.write(a.HERE/'composed/cathedral_authored_delta_qa.json',result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('spec',type=Path);p.add_argument('--estimate-only',action='store_true');args=p.parse_args();run(args.spec.resolve(),args.estimate_only)
