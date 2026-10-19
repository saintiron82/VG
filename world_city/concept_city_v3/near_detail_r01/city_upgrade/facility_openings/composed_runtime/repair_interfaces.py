"""JSON-driven bounded canonical-source repair of finite mixed-resolution joins."""
from collections import defaultdict
import argparse,copy,gc,math,resource,time
from pathlib import Path
import compose as c
a=c.a
import estimate_run as b
import compile_set as runner
import seam_adapter as seam
HERE=c.HERE

def in_region(p,r):return all(r['min'][j]<=p[j]<r['max'][j] for j in range(3))

class ActiveOutside:
    def __init__(self,fine,coarse,regions,windows,roof_materials):
        self.fine={tuple(r[:3]):r for r in fine['cells']};self.coarse={tuple(r[:3]):r for r in coarse['cells']};self.regions=regions+windows;self.roof_materials=roof_materials
    def sample(self,point):
        f=self.fine.get(tuple(math.floor(v/.05+1e-8) for v in point));o=self.coarse.get(tuple(math.floor(v/.5+1e-8) for v in point))
        if any(in_region(point,r) for r in self.regions):return bool(f),f[5] if f else None,None
        if f and f[5] in self.roof_materials:return True,f[5],None
        if o and o[5] not in self.roof_materials:return True,o[5],None
        return False,None,None

def main(spec_path,estimate_only=False):
    start=time.monotonic();spec=a.load(spec_path);key=spec['asset_key'];base=a.load(HERE/spec['input_manifest']);regions=spec['regions'];out=HERE/(key+'.interface_repair');out.mkdir(exist_ok=True)
    source=a.load(a.ROOT/base['collision_reference_path']);input_by_role={x['role']:x for x in base['source_inputs']}
    original=a.load(a.ROOT/input_by_role['original master']['path']);window=a.load(a.ROOT/input_by_role['authored window source']['path']);roof=a.load(a.ROOT/input_by_role['finished roof source']['path']);master=copy.deepcopy(window);assert window['materials']==roof['materials'];allops=[]
    for inst in roof['instances']:
        assert a.core.transform(inst.get('transform'))==a.core.transform(None) and not inst.get('parent')
        comp=next(q for q in roof['components'] if q['id']==inst['component'])
        for op in comp['operations']:
            assert op['action']=='paint';op=copy.deepcopy(op);op['id']=comp['id']+'__'+op['id'];allops.append(op)
    next(q for q in master['components'] if q['id']=='roof')['operations']=allops
    master['id']=key+'__canonical_interface_repair';master.setdefault('provenance',{})['interface_source_composition']={'window_source_sha256':input_by_role['authored window source']['sha256'],'roof_source_sha256':input_by_role['finished roof source']['sha256'],'shape_fields_unchanged':True,'transform_unchanged':True}
    mp=out/'canonical.master.json.gz';a.write(mp,master);a.core.validate_master(master,.05);bs=b.bounds_list(master,.05);plans=[]
    for r in regions:
        cb={k:[round(v/.05) for v in r[k]] for k in ['min','max']};outer={'min':[x-1 for x in cb['min']],'max':[x+1 for x in cb['max']]};plans.append({'id':r['id'],'region':r,'fine_cell_bounds':cb,'chunks':b.split(bs,cb,outer,spec['candidate_cap'])})
    total=sum(p['candidate_visits'] for r in plans for p in r['chunks']);plan={'spec_sha256':a.sha(spec_path),'canonical_master_sha256':a.sha(mp),'candidate_visits':total,'chunk_count':sum(len(r['chunks']) for r in plans),'estimated_common_seconds_range':[round(total*7.31e-6),round(total*18e-6)],'regions':plans};a.write(out/'cost_plan.json',plan);print({'stage':'estimate','candidates':total,'chunks':plan['chunk_count'],'seconds':plan['estimated_common_seconds_range']},flush=True)
    if estimate_only:return
    signature=a.core.digest({'plan':plan,'engine_sha':a.sha(a.core.__file__),'runner_sha':a.sha(__file__),'seam_sha':a.sha(seam.__file__)})
    contract=a.load(a.ROOT/input_by_role['finite window replacement contract']['path']);roof_mats={m['material_id'] for m in a.load(a.ROOT/input_by_role['immutable complete roof handoff']['path'])['original_roof_material_mapping']};outputs=[];source_cache=seam.CacheOccupancy(source)
    for rp in plans:
        finegroups=[];seamgroups=[];chunks=[]
        patch={'id':rp['id'],'fine_cell_bounds':rp['fine_cell_bounds'],'replacement_volume_master_m':rp['region']}
        for ci,cp in enumerate(rp['chunks']):
            assert time.monotonic()-start<spec['seconds_cap'];assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<spec['memory_cap_kib']
            target=out/f"{rp['id']}.{ci:03d}.json.gz"
            if target.exists():
                result=a.load(target);assert result['signature']==signature
            else:
                cb=cp['sample_cell_bounds_with_one_cell_halo'];coarse_cb={'min':[math.floor(x/10)-1 for x in cb['min']],'max':[math.ceil(x/10)+1 for x in cb['max']]}
                coarse=a.core.compile_master(original,{'pitch':.5},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=coarse_cb)
                for row in coarse['cells']:assert source_cache.sample([(v+.5)*.5 for v in row[:3]])[0]
                fine=a.core.compile_master(master,{'pitch':.05},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=cb);assert fine['candidate_cells']==cp['candidate_visits']
                occupancy=ActiveOutside(fine,coarse,regions,base['window_regions'],roof_mats);preview=runner.owned_surface(fine,cp['owned_cell_bounds']);adapter=seam.build(source,fine,preview,patch,original.get('assembly_cuts',[]),owned_bounds=cp['owned_cell_bounds'],validate_edges=False,occupancy=occupancy)
                result={'signature':signature,'region':rp['id'],'chunk':ci,'fine_payload_sha256':fine['payload_hash'],'original_coarse_payload_sha256':coarse['payload_hash'],'sample_bounds':cb,'owned_bounds':cp['owned_cell_bounds'],'fine_candidate_cells':fine['candidate_cells'],'fine_output_cells':len(fine['cells']),'fine_groups':adapter['fine_exterior_groups'],'seam_groups':adapter['transition_groups'],'protected_entry_violations':adapter['protected_entry_interface_violations'],'source_shapes_cropped':False}
                a.write(target,result);del fine,coarse,occupancy,preview,adapter;gc.collect()
            finegroups+=result['fine_groups'];seamgroups+=result['seam_groups'];chunks.append({'path':str(target.relative_to(a.ROOT)),'sha256':a.sha(target)});assert result['protected_entry_violations']==0
            print({'stage':'chunk','region':rp['id'],'done':ci+1,'total':len(rp['chunks']),'elapsed':round(time.monotonic()-start,2),'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},flush=True)
        groups=runner.merge_groups(finegroups+seamgroups);wp=out/(rp['id']+'.render.json.gz');a.write(wp,{'groups':groups,'region':rp['region'],'chunks':chunks,'canonical_master_sha256':a.sha(mp),'source_shapes_deformed':False,'collider_changed':False});outputs.append({'path':str(wp.relative_to(a.ROOT)),'sha256':a.sha(wp),'region':rp['region'],'quad_count':sum(len(g['quads']) for g in groups)})
    # Free large authoring objects before loading the complete render-only input.
    del master,roof,window,allops,source_cache,bs;gc.collect()
    render=a.load(a.ROOT/base['render_path']);grouped=defaultdict(list);finite_changes=0;retained=0
    for g in render['groups']:
        for q in g['quads']:
            kept=c.clip(q,regions);finite_changes+=kept!=[q];retained+=kept==[q];grouped[g['material']]+=kept
    for o in outputs:
        rr=a.load(a.ROOT/o['path'])
        for g in rr['groups']:grouped[g['material']]+=g['quads']
    render['groups']=[{'material':m,'quads':qs} for m,qs in sorted(grouped.items())];render['quad_count']=sum(len(g['quads']) for g in render['groups']);render['provenance']['native_interface_repair']={'canonical_master_sha256':a.sha(mp),'region_spec_sha256':a.sha(spec_path),'pre_repair_render_sha256':base['render_sha256'],'outside_occupancy':'Original .5 nonroof + active exact .05 roof/windows/neighbour replacement regions. Boundary-only evaluation, unchanged common shapes.'}
    rp=HERE/f'{key}.r03.composed.render.json.gz';c.dump(rp,render)
    # Keep this diagnostic provisional until independent external-leak checks.
    manifest={**base,'render_path':str(rp.relative_to(a.ROOT)),'render_sha256':a.sha(rp),'all_pass':False,'roof_variant_asset_key':key,'tests':{**base['tests'],'canonical_source_interface_repair':True,'external_leak_checks':False},'interface_regions':regions,'surface_exclusion_regions':base['window_regions']+regions,'output_quad_count':render['quad_count'],'interface_repair_outputs':outputs,'interface_changed_input_quad_count':finite_changes,'interface_untouched_input_quad_count':retained,'source_inputs':base['source_inputs']+[{'path':str(mp.relative_to(a.ROOT)),'sha256':a.sha(mp),'role':'canonical full source for bounded interface evaluation'},{'path':str(spec_path.relative_to(a.ROOT)),'sha256':a.sha(spec_path),'role':'finite interface region contract'},{'path':base['render_path'],'sha256':base['render_sha256'],'role':'pre-interface composed render r02'}],'interface_max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'interface_seconds':time.monotonic()-start,'interface_bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file())+rp.stat().st_size}
    a.write(HERE/f'{key}.r03.manifest.json',manifest);print({'complete':True,'seconds':manifest['interface_seconds'],'rss':manifest['interface_max_rss_kib'],'new_bytes':manifest['interface_bytes'],'sha':manifest['render_sha256']},flush=True);assert manifest['interface_bytes']<spec['new_bytes_cap']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('spec',type=Path);p.add_argument('--estimate-only',action='store_true');args=p.parse_args();main(args.spec.resolve(),args.estimate_only)
