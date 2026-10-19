"""Prepared sequential build. Run only after parent's checkpoint-ready signal."""
from pathlib import Path
import argparse,copy,json,time
from .resolver import sha
from .resolve_approved import HERE,APPROVED_NOBLES,file_sha,write,run as resolve_approved
from . import recipes


def run(checkpoint_reference,approved_source_plan_sha256):
    if not checkpoint_reference:raise ValueError('Checkpoint-ready reference is required')
    pack,resolver=resolve_approved()
    if pack['source_plan_sha256']!=approved_source_plan_sha256:raise ValueError('Approved source checkpoint changed')
    if pack['approved_plot_ids']!=sorted(APPROVED_NOBLES) or len(pack['resolved_properties'])!=7:raise ValueError('Build scope must remain the seven approved noble plots')
    # Importing here keeps preparation/resolution entirely compile-free.
    from voxel_character.common import coordinate_planes,render_data
    sampled={x['asset_key']:x for x in json.loads((HERE/'generated/sampling_report.json').read_text())}
    assets={};results=[];directory=HERE/'cache';directory.mkdir(exist_ok=True)
    for key,a in sorted(pack['asset_manifest'].items()):
        existing=a.get('verified_runtime_asset')
        if existing:assets[key]=existing;results.append({'asset_key':key,'status':'verified_existing_cache','new_compile':False});continue
        source=resolver.source_for(key);before=copy.deepcopy(source);resource=recipes.resource_for(a['cache_spec']);pitch=resource['pitch'];started=time.monotonic()
        try:
            compiled=coordinate_planes.compile_master(source,resource,max_candidate_cells=300000,max_output_cells=100000)
            if source!=before:raise AssertionError('Compiler mutated common source')
            if not compiled['valid']:raise ValueError('Common constraints failed: '+str(compiled['constraints']))
            render=render_data.make_render_data(compiled);declared,_=recipes.describe_asset(a['cache_spec'])
            for axis in (0,2):
                if render['bounds']['min'][axis]<declared['min'][axis]-1e-5 or render['bounds']['max'][axis]>declared['max'][axis]+1e-5:raise ValueError('Sampled XZ bounds exceed validated envelope')
            if sha(source)!=a['master_source_sha256']:raise ValueError('Compiled source differs from resolution asset identity')
            master_path=directory/(key+'.master.json');render_path=directory/(key+f'.pitch_{pitch:g}.render.json');write(master_path,source);write(render_path,render)
            row={'asset_key':key,'master_source_sha256':a['master_source_sha256'],'sampling_resource':resource,'compile_identity':a['compile_identity'],'compiled_asset_ref':str(render_path),'master_path':str(master_path),'master_file_sha256':file_sha(master_path),'render_sha256':file_sha(render_path),'bounds':render['bounds'],'pitch_m':pitch,'cell_count':render['cell_count'],'quad_count':render['quad_count'],'common_master_hash':compiled['master_hash'],'common_payload_hash':compiled['payload_hash']}
            assets[key]=row;results.append({'asset_key':key,'status':'compiled','new_compile':True,'candidate_cells':compiled['candidate_cells'],'output_cells':len(compiled['cells']),'bounds':render['bounds'],'elapsed_s':round(time.monotonic()-started,3),'prototype_sampling_evidence':sampled.get(key),'compile_caps':{'candidate_cells':300000,'output_cells':100000}})
            print(json.dumps({k:v for k,v in results[-1].items() if k!='prototype_sampling_evidence'}),flush=True)
        except Exception as error:
            results.append({'asset_key':key,'status':'failed','error':type(error).__name__+': '+str(error)});break
    success=len(assets)==len(pack['asset_manifest']);manifest={'schema':'riverstone.concept_city.property_compiled_cache.v1','status':'complete' if success else 'partial_failed','source_plan_sha256':pack['source_plan_sha256'],'checkpoint_reference':checkpoint_reference,'approved_plot_ids':APPROVED_NOBLES,'assets':assets,'compiler_files_sha256':{str(Path('voxel_character/common')/f):file_sha(Path('voxel_character/common')/f) for f in ('coordinate_planes.py','core.py','render_data.py')},'recipe_source_sha256':pack['recipe_source_sha256'],'build_script_sha256':file_sha(Path(__file__)),'sequential':True,'whole_city_compiled':False,'geometry_scaling':False}
    write(directory/'manifest.json',manifest);write(HERE/'generated/resolver/cache_build_report.json',{'status':manifest['status'],'checkpoint_reference':checkpoint_reference,'results':results,'new_compilation_count':sum(r.get('new_compile',False) for r in results),'expected_unique_assets':len(pack['asset_manifest']),'actual_persisted_assets':len(assets)})
    if not success:raise RuntimeError('Bounded cache build failed; partial evidence preserved')
    rebound,_=resolve_approved();return rebound
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--checkpoint-ready-reference',required=True);parser.add_argument('--approved-source-plan-sha256',required=True);args=parser.parse_args();run(args.checkpoint_ready_reference,args.approved_source_plan_sha256)
