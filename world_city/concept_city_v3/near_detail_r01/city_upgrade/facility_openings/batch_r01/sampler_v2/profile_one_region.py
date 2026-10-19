"""Profile one completed new-v2 ROI chunk without modifying its output.

A representative diagnostic replay, not an engine change. cProfile overhead is
explicit and stage times must not be mistaken for clean throughput benchmarks.
"""
import argparse,cProfile,gc,io,json,math,pstats,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path[:0]=[str(B.parent),str(B.parent/'composed_runtime')]
import author as a
import compile_set as helpers
import seam_adapter as seam
from compile_source_contacts import ExactOutside
from voxel_character.common import exact_sampling_v2 as v2
import reserved_io_r02 as reserved_io

def run(catalog_path,index):
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));cat=a.load(catalog_path);assert cat['complete'];writer=reserved_io.writer_for_catalog(cat,a.ROOT,B,a.HERE.parent/'house_rules');assert v2.get_sampler_provenance()==cat['sampler_provenance'];plan=a.load(a.ROOT/cat['plan_path']);wc=a.load(a.ROOT/cat['window_contract_path']);source=a.load(a.ROOT/cat['source_master_path']);roof=a.load(a.ROOT/cat['roof_master_path']);master=a.load(a.ROOT/cat['canonical_master_path']);render=a.load(a.ROOT/cat['source_render_path']);refs=[]
    for out in cat['outputs']:
        payload=a.load(a.ROOT/out['path']);assert a.sha(a.ROOT/out['path'])==out['sha256'];refs+=payload['chunks']
    ref=refs[index];stored=a.load(a.ROOT/ref['path']);assert a.sha(a.ROOT/ref['path'])==ref['sha256'];p=next(p for p in plan['plans'] if p['region']['id']==stored['region']);cp=p['chunks'][stored['chunk']];cb=cp['sample_cell_bounds_with_one_cell_halo'];coarsecb={'min':[math.floor(x/10)-1 for x in cb['min']],'max':[math.ceil(x/10)+1 for x in cb['max']]};patch={'id':p['region']['id'],'fine_cell_bounds':p['fine_cell_bounds'],'replacement_volume_master_m':p['region']};entries=wc.get('protected_component_entry_cuts',[])+source.get('assembly_cuts',[]);stages={};proof={};prof=cProfile.Profile();cpu0=resource.getrusage(resource.RUSAGE_SELF);start=time.monotonic()
    def timed(name,fn):
        t=time.monotonic();value=fn();stages[name]=time.monotonic()-t;return value
    prof.enable()
    coarse=timed('sample_original_coarse',lambda:v2.compile_master_v2(source,{'pitch':.5},max_candidate_cells=140000,max_output_cells=140000,cell_bounds=coarsecb));roofcompiled=timed('sample_selected_roof_fine',lambda:v2.compile_master_v2(roof,{'pitch':.05},max_candidate_cells=140000,max_output_cells=140000,cell_bounds=cb));proof['roof_payload_exact']=roofcompiled['payload_hash']==stored['roof_only_payload_sha256'];roofcells=timed('roof_lookup_build',lambda:{tuple(r[:3]):r[5] for r in roofcompiled['cells']});del roofcompiled;gc.collect()
    fine=timed('sample_canonical_fine',lambda:v2.compile_master_v2(master,{'pitch':.05},max_candidate_cells=140000,max_output_cells=140000,cell_bounds=cb));proof.update(coarse_payload_exact=coarse['payload_hash']==stored['coarse_payload_sha256'],fine_payload_exact=fine['payload_hash']==stored['common_payload_sha256'])
    outside=timed('outside_occupancy_index',lambda:ExactOutside(fine,coarse,roofcells,plan['ordered_regions'],cat['roof_materials']));preview=timed('common_exterior_meshing_and_owned_filter',lambda:helpers.owned_surface(fine,cp['owned_cell_bounds']));adapter=timed('seam_and_retained_boundary_validation',lambda:seam.build(render,fine,preview,patch,entries,owned_bounds=cp['owned_cell_bounds'],validate_edges=False,occupancy=outside));groups=timed('material_group_merge',lambda:helpers.merge_groups(adapter['fine_exterior_groups']+adapter['transition_groups']));proof.update(groups_exact=groups==stored['groups'],interface_counts_exact=adapter['interface_pixel_counts']==stored['interface_pixel_counts'],entry_violations_zero=adapter['protected_entry_interface_violations']==0)
    serialized=timed('checkpoint_json_gzip_serialization',lambda:reserved_io.encoded(Path(ref['path']),stored));timed('atomic_budget_check',lambda:writer.check(len(serialized)));prof.disable();cpu=resource.getrusage(resource.RUSAGE_SELF);stream=io.StringIO();pstats.Stats(prof,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(45)
    report={'schema':'riverstone.facility.roi_representative_profile.v1','asset_key':cat['asset_key'],'selected_chunk':ref,'chunk_index':index,'all_geometry_checks_pass':all(proof.values()),'tests':proof,'stage_seconds_with_profiler_overhead':stages,'profiled_wall_seconds':time.monotonic()-start,'user_cpu_seconds':cpu.ru_utime-cpu0.ru_utime,'system_cpu_seconds':cpu.ru_stime-cpu0.ru_stime,'peak_rss_kib':cpu.ru_maxrss,'original_unprofiled_chunk_seconds':stored['seconds'],'sample_candidate_visits':cp['candidate_visits']+cp['roof_only_candidate_visits'],'stored_chunks_modified':False,'sampler_provenance':cat['sampler_provenance'],'implementation_path':str(Path(__file__).relative_to(a.ROOT)),'implementation_sha256':a.sha(__file__),'cprofile_top45_cumulative':stream.getvalue(),'scope':'One identical completed chunk replay with profiling enabled. Stage timings include profiler overhead; no whole-job10.57x inference. Exterior meshing and ownership clipping share the frozen helper, while detailed cumulative function timings separate their internals.'};assert all(proof.values()) and cpu.ru_maxrss<256*1024;writer.write(catalog_path.parent/'representative_profile.json',report);print(json.dumps({k:report[k] for k in ['asset_key','all_geometry_checks_pass','stage_seconds_with_profiler_overhead','profiled_wall_seconds','original_unprofiled_chunk_seconds','peak_rss_kib']}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('--index',type=int,default=0);q=p.parse_args();run(q.catalog.resolve(),q.index)
