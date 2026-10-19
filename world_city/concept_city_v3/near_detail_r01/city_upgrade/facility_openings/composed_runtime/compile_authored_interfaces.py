"""Evaluate an explicit authored contact revision in serial finite common ROIs.

Source shapes are never cropped. The JSON specification owns support operations,
finite render replacement regions, source hashes and resource budgets.
"""
import argparse,copy,gc,math,resource,time
from pathlib import Path
import compose as c
a=c.a
import estimate_run as b
import compile_set as runner
import seam_adapter as seam
import active_composition

def prepare(spec,path):
    source_path=a.ROOT/spec['canonical_master_path'];assert a.sha(source_path)==spec['canonical_master_sha256']
    source=a.load(source_path);master=copy.deepcopy(source)
    revision_path=a.ROOT/spec['revision_path'];assert a.sha(revision_path)==spec['revision_sha256'];revision=a.load(revision_path)
    delta=revision['common_source_delta'];operations=[op for c in delta['prepend_components'] for op in c['operations']]
    master['components']=copy.deepcopy(delta['prepend_components'])+master['components'];master['instances']=copy.deepcopy(delta['prepend_instances'])+master['instances']
    contract=a.load(a.ROOT/spec['window_contract_path']);cuts=copy.deepcopy(delta['append_assembly_cuts'])
    assert len(operations)==6 and len(cuts)==34
    master.setdefault('assembly_cuts',[]).extend(cuts)
    master['id']=spec['asset_key']+'__authored_eave_contact_revision'
    master['provenance']={**master.get('provenance',{}),'authored_contact_revision':{'canonical_source_sha256':spec['canonical_master_sha256'],'revision_operations_sha256':a.core.digest(operations),'revision_file_sha256':spec['revision_sha256'],'original_occupancy_unchanged':False,'original_shapes_and_order_unchanged':True,'new_operations_precede_original_paints':True,'protected_new_component_cut_count':len(cuts)}}
    a.core.validate_master(master,.05);a.write(path,master)
    return source,master,contract

def main(spec_path,estimate_only=False):
    start=time.monotonic();spec=a.load(spec_path);out=(a.ROOT/spec['output_directory']);out.mkdir(parents=True,exist_ok=True);mp=out/'canonical.authored.master.json.gz';base,master,contract=prepare(spec,mp)
    bounds=b.bounds_list(master,.05);plans=[]
    for r in spec['regions']:
        cb={k:[round(v*20) for v in r[k]] for k in ['min','max']};outer={'min':[x-1 for x in cb['min']],'max':[x+1 for x in cb['max']]}
        plans.append({'id':r['id'],'region':r,'fine_cell_bounds':cb,'chunks':b.split(bounds,cb,outer,spec['candidate_cap'])})
    plan={'schema':'riverstone.authored_contact.cost_plan.v1','spec_sha256':a.sha(spec_path),'canonical_master_sha256':a.sha(mp),'candidate_visits':sum(p['candidate_visits'] for r in plans for p in r['chunks']),'chunk_count':sum(len(r['chunks']) for r in plans),'regions':plans}
    plan['estimated_seconds_range']=[round(plan['candidate_visits']*12e-6),round(plan['candidate_visits']*35e-6)];a.write(out/'cost_plan.json',plan);print({'stage':'estimate','candidates':plan['candidate_visits'],'chunks':plan['chunk_count'],'seconds':plan['estimated_seconds_range']},flush=True)
    if estimate_only:return
    signature=a.core.digest({'plan':plan,'runner_sha':a.sha(__file__),'common_sha':a.sha(a.core.__file__),'seam_sha':a.sha(seam.__file__),'active_composition_sha':a.sha(active_composition.__file__)})
    source=a.load(a.ROOT/spec['original_master_path']);render=a.load(a.ROOT/contract['source_render_path']);regions=spec['regions'];windows=[p['replacement_volume_master_m'] for p in contract['patches']];outputs=[];total_changed=added=removed=0
    for rp in plans:
        groups=[];chunks=[];patch={'id':rp['id'],'fine_cell_bounds':rp['fine_cell_bounds'],'replacement_volume_master_m':rp['region']}
        for ci,cp in enumerate(rp['chunks']):
            runner.guard(start);target=out/f"{rp['id']}.{ci:03d}.json.gz"
            if target.exists():
                result=a.load(target);assert result['signature']==signature
            else:
                cb=cp['sample_cell_bounds_with_one_cell_halo'];coarse_cb={'min':[math.floor(v/10)-1 for v in cb['min']],'max':[math.ceil(v/10)+1 for v in cb['max']]}
                coarse=a.core.compile_master(source,{'pitch':.5},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=coarse_cb)
                fine=a.core.compile_master(master,{'pitch':.05},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=cb);assert fine['candidate_cells']==cp['candidate_visits']
                occupancy=active_composition.OutsideOccupancy(fine,coarse,regions+windows,spec['roof_materials']);preview=runner.owned_surface(fine,cp['owned_cell_bounds'])
                adapter=seam.build(render,fine,preview,patch,source.get('assembly_cuts',[])+contract['protected_component_entry_cuts'],owned_bounds=cp['owned_cell_bounds'],validate_edges=False,occupancy=occupancy)
                assert adapter['protected_entry_interface_violations']==0
                result={'signature':signature,'region':rp['id'],'chunk_index':ci,'fine_payload_sha256':fine['payload_hash'],'original_coarse_payload_sha256':coarse['payload_hash'],'sample_bounds':cb,'owned_bounds':cp['owned_cell_bounds'],'fine_candidate_cells':fine['candidate_cells'],'fine_output_cells':len(fine['cells']),'groups':runner.merge_groups(adapter['fine_exterior_groups']+adapter['transition_groups']),'protected_entry_violations':0,'source_shapes_cropped':False,'new_source_revision':True}
                a.write(target,result);del fine,coarse,occupancy,preview,adapter;gc.collect()
            groups+=result['groups'];chunks.append({'path':str(target.relative_to(a.ROOT)),'sha256':a.sha(target)})
            progress={'stage':'chunk','region':rp['id'],'done':ci+1,'total':len(rp['chunks']),'elapsed':round(time.monotonic()-start,2),'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};a.write(out/'progress.json',progress);print(progress,flush=True)
        merged=runner.merge_groups(groups);wp=out/(rp['id']+'.render.json.gz');a.write(wp,{'schema':'riverstone.authored_contact.region_render.v1','groups':merged,'region':rp['region'],'chunks':chunks,'canonical_master_sha256':a.sha(mp),'original_occupancy_unchanged':False,'source_shapes_deformed':False,'collider_changed':False});outputs.append({'path':str(wp.relative_to(a.ROOT)),'sha256':a.sha(wp),'region':rp['region'],'quad_count':sum(len(g['quads']) for g in merged)})
    catalog={'schema':'riverstone.authored_contact.compiled_set.v1','asset_key':spec['asset_key'],'spec_path':str(spec_path.relative_to(a.ROOT)),'spec_sha256':a.sha(spec_path),'canonical_master_path':str(mp.relative_to(a.ROOT)),'canonical_master_sha256':a.sha(mp),'original_master_path':spec['original_master_path'],'original_master_sha256':spec['original_master_sha256'],'authoring_revision':master['provenance']['authored_contact_revision'],'regions':regions,'outputs':outputs,'final_boundary_qa_pending':True,'collision_reference_changed':False,'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'whole_source_fine_compile':False,'common_call_count':2*plan['chunk_count']}
    a.write(out/'catalog.json',catalog);print({'complete':True,'seconds':catalog['elapsed_seconds'],'rss':catalog['max_rss_kib'],'outputs':len(outputs)},flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('spec',type=Path);p.add_argument('--estimate-only',action='store_true');args=p.parse_args();main(args.spec.resolve(),args.estimate_only)
