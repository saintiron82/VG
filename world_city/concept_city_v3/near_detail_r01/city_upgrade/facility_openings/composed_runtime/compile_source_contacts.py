"""JSON-driven finite reevaluation of unchanged canonical source contact regions."""
import argparse,gc,math,resource,time
from pathlib import Path
import compose as c
a=c.a
import compile_set as runner
import estimate_run as b
import seam_adapter as seam

class ExactOutside:
    def __init__(self,fine,coarse,roof,regions,roof_materials):
        self.fine={tuple(r[:3]):r[5] for r in fine['cells']};self.coarse={tuple(r[:3]):r[5] for r in coarse['cells']};self.roof=roof;self.regions=regions;self.roof_materials=roof_materials
    def sample(self,point):
        p=tuple(math.floor(v*20+1e-8) for v in point)
        if any(all(r['min'][j]<=point[j]<r['max'][j] for j in range(3)) for r in self.regions):return p in self.fine,self.fine.get(p),None
        if p in self.roof:return True,self.roof[p],None
        mat=self.coarse.get(tuple(math.floor(v*2+1e-8) for v in point));return bool(mat and mat not in self.roof_materials),mat,None

def main(path):
    start=time.monotonic();spec=a.load(path);old=a.load(a.ROOT/spec['previous_interface_catalog']);out=a.ROOT/spec['output_directory'];out.mkdir(parents=True,exist_ok=True)
    mp=a.ROOT/old['canonical_master_path'];assert a.sha(mp)==old['canonical_master_sha256'];master=a.load(mp)
    original=a.load(a.ROOT/old['original_master_path']);window=a.load(a.ROOT/spec['window_contract_path']);render=a.load(a.ROOT/window['source_render_path']);roof_path=a.ROOT/spec['roof_master_path'];assert a.sha(roof_path)==spec['roof_master_sha256'];roof_master=a.load(roof_path)
    bounds=b.bounds_list(master,.05);roofbounds=b.bounds_list(roof_master,.05);plans=[]
    for region in spec['regions']:
        cb={k:[round(v*20) for v in region[k]] for k in ['min','max']};outer={'min':[v-1 for v in cb['min']],'max':[v+1 for v in cb['max']]};chunks=b.split(bounds,cb,outer,180000)
        for chunk in chunks:chunk['roof_only_candidate_visits']=b.cost(roofbounds,chunk['sample_cell_bounds_with_one_cell_halo']);assert chunk['roof_only_candidate_visits']<200000
        plans.append({'id':region['id'],'region':region,'fine_cell_bounds':cb,'chunks':chunks})
    plan={'spec_sha256':a.sha(path),'canonical_master_sha256':a.sha(mp),'roof_master_sha256':a.sha(roof_path),'regions':plans,'chunks':sum(len(p['chunks']) for p in plans),'fine_candidates':sum(c['candidate_visits'] for p in plans for c in p['chunks']),'outside_roof_candidates':sum(c['roof_only_candidate_visits'] for p in plans for c in p['chunks'])};a.write(out/'cost_plan.json',plan);print({'stage':'plan',**{k:v for k,v in plan.items() if k!='regions'}},flush=True)
    signature=a.core.digest({'plan':plan,'runner_sha256':a.sha(__file__),'common_sha256':a.sha(a.core.__file__),'seam_sha256':a.sha(seam.__file__)})
    allregions=old['regions']+spec['regions']+[p['replacement_volume_master_m'] for p in window['patches']];outputs=[]
    for rp in plans:
        groups=[];chunks=[];patch={'id':rp['id'],'fine_cell_bounds':rp['fine_cell_bounds'],'replacement_volume_master_m':rp['region']}
        for ci,cp in enumerate(rp['chunks']):
            runner.guard(start);target=out/f"{rp['id']}.{ci:03d}.json.gz"
            if target.exists():
                result=a.load(target);assert result['signature']==signature
            else:
                cb=cp['sample_cell_bounds_with_one_cell_halo'];coarsecb={'min':[math.floor(v/10)-1 for v in cb['min']],'max':[math.ceil(v/10)+1 for v in cb['max']]}
                coarse=a.core.compile_master(original,{'pitch':.5},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=coarsecb)
                roof=a.core.compile_master(roof_master,{'pitch':.05},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=cb);roofhash=roof['payload_hash'];roofcells={tuple(r[:3]):r[5] for r in roof['cells']};del roof;gc.collect()
                fine=a.core.compile_master(master,{'pitch':.05},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=cb);assert fine['candidate_cells']==cp['candidate_visits']
                outside=ExactOutside(fine,coarse,roofcells,allregions,spec['roof_materials']);preview=runner.owned_surface(fine,cp['owned_cell_bounds']);adapter=seam.build(render,fine,preview,patch,original.get('assembly_cuts',[])+window['protected_component_entry_cuts'],owned_bounds=cp['owned_cell_bounds'],validate_edges=False,occupancy=outside);assert adapter['protected_entry_interface_violations']==0
                result={'signature':signature,'region':rp['id'],'chunk':ci,'groups':runner.merge_groups(adapter['fine_exterior_groups']+adapter['transition_groups']),'common_payload_sha256':fine['payload_hash'],'roof_only_payload_sha256':roofhash,'coarse_payload_sha256':coarse['payload_hash'],'fine_sample_bounds':cb,'owned_bounds':cp['owned_cell_bounds'],'source_shape_change':False,'protected_entry_violations':0,'outside_rule':'Fine canonical inside any active region; independently evaluated exact roof-only occupancy OR retained original coarse nonroof outside.'};a.write(target,result);del coarse,fine,roofcells,outside,preview,adapter;gc.collect()
            groups+=result['groups'];chunks.append({'path':str(target.relative_to(a.ROOT)),'sha256':a.sha(target)});progress={'region':rp['id'],'chunk':ci+1,'total':len(rp['chunks']),'seconds':round(time.monotonic()-start,2),'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};a.write(out/'progress.json',progress);print(progress,flush=True)
        target=out/(rp['id']+'.render.json.gz');a.write(target,{'schema':'riverstone.source_contact.region_render.v1','groups':runner.merge_groups(groups),'chunks':chunks,'region':rp['region'],'canonical_master_sha256':a.sha(mp),'source_shape_change':False,'collision_reference_changed':False});outputs.append({'path':str(target.relative_to(a.ROOT)),'sha256':a.sha(target),'region':rp['region'],'quad_count':sum(len(g['quads']) for g in groups)})
    catalog={**old,'regions':old['regions']+spec['regions'],'outputs':old['outputs']+outputs,'source_contact_restoration':{'spec_path':str(path.relative_to(a.ROOT)),'spec_sha256':a.sha(path),'source_shape_change':False,'previous_catalog_path':spec['previous_interface_catalog'],'previous_catalog_sha256':a.sha(a.ROOT/spec['previous_interface_catalog']),'canonical_master_sha256_unchanged':a.sha(mp),'runner_sha256':a.sha(__file__),'cost_plan_path':str((out/'cost_plan.json').relative_to(a.ROOT)),'cost_plan_sha256':a.sha(out/'cost_plan.json'),'additional_common_calls':3*plan['chunks'],'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'final_boundary_qa_pending':True};a.write(out/'catalog.json',catalog);print({'complete':True,**catalog['source_contact_restoration']},flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('spec',type=Path);args=p.parse_args();main(args.spec.resolve())
