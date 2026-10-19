"""Resumable serial window-only render compilation with strict resource caps."""
from collections import defaultdict
import argparse,hashlib,json,math,resource,sys,time
from pathlib import Path
import author as a
import seam_adapter as seam
import active_composition
sys.path.insert(0,str(a.ROOT/'voxel_character/tools'))
import mesh
HERE=a.HERE;OUT=HERE/'compiled';CAP_BYTES=20*1024*1024;CAP_KB=256*1024;CAP_SECONDS=600

def checkpoint(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name('.tmp.'+path.name);a.write(tmp,value);tmp.replace(path)
def size():return sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
def guard(start):
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<CAP_KB,'memory cap reached'
    assert size()<CAP_BYTES,'20MB output cap reached'
    assert time.monotonic()-start<CAP_SECONDS,'600 second execution window reached; checkpoint retained'
def owned_surface(compiled,owned):
    pitch=compiled['pitch'];origin=compiled['grid_origin'];groups=defaultdict(list)
    for q,material in mesh.greedy_faces([(*r[:3],r[5]) for r in compiled['cells']]):
        axis,t,plane,sign,rect=a.quad_info(q);lo,hi=owned['min'],owned['max']
        if plane<lo[axis] or plane>hi[axis] or (plane==lo[axis] and sign>0) or (plane==hi[axis] and sign<0):continue
        clip=[max(rect[0],lo[t[0]]),max(rect[1],lo[t[1]]),min(rect[2],hi[t[0]]),min(rect[3],hi[t[1]])]
        if a.rect_area(clip)<=0:continue
        quad=a.rect_quad(clip,axis,t,plane,sign);groups[material].append([[origin[j]+v[j]*pitch for j in range(3)] for v in quad])
    return {'groups':[{'material':m,'quads':q} for m,q in sorted(groups.items())]}
def merge_groups(groups):
    result=defaultdict(list)
    for g in groups:result[g['material']]+=g['quads']
    return [{'material':m,'quads':q} for m,q in sorted(result.items())]

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--asset');parser.add_argument('--output-dir',type=Path);parser.add_argument('--patch',action='append',help='Bounded subset QA; same signature/checkpoints support later full resume.');parser.add_argument('--catalog',type=Path,default=HERE/'generated/catalog.json');parser.add_argument('--cost-plan',type=Path,default=HERE/'generated/cost_plan.json');args=parser.parse_args()
    if args.output_dir:OUT=args.output_dir
    start=time.monotonic();OUT.mkdir(exist_ok=True);catalog=a.load(args.catalog);cost=a.load(args.cost_plan);rules=a.load(HERE/'rules.v1.json');plans={x['asset_key']:x for x in cost['assets']}
    tool_signature={'core_sha256':a.sha(a.core.__file__),'seam_sha256':a.sha(seam.__file__),'runner_sha256':a.sha(__file__),'active_composition_sha256':a.sha(active_composition.__file__)}
    requested=[x for x in catalog['assets'] if not args.asset or x['asset_key']==args.asset];assert requested;goal=sum(x['window_count'] for x in requested)
    state_path=OUT/'run_state.json';state=a.load(state_path) if state_path.exists() else {'schema':'riverstone.facility_openings.run_state.v1','asset_signatures':{},'completed_windows':{},'status':'running','resume_count':0}
    state['resume_count']+=1;state['status']='running';checkpoint(state_path,state);processed=0;newcalls=0;totalcandidates=0;totalcommon=0;assets=[]
    try:
        for item in requested:
            key=item['asset_key'];signature=a.core.digest({'asset':item,'tools':tool_signature,'plans':plans[key]})
            assert key not in state['asset_signatures'] or state['asset_signatures'][key]==signature,'Inputs changed for this asset; do not mix checkpoint generations'
            state['asset_signatures'][key]=signature
            source=a.load(a.ROOT/item['source_master_path']);master=a.load(a.ROOT/item['emitted_master_path']);contract=a.load(a.ROOT/item['replacement_contract_path']);render=a.load(a.ROOT/contract['source_render_path']);assert a.sha(a.ROOT/item['source_master_path'])==item['source_sha256'];assert a.sha(a.ROOT/item['emitted_master_path'])==item['emitted_master_sha256'];occupancy=seam.CacheOccupancy(render);entries=source.get('assembly_cuts',[])+contract['protected_component_entry_cuts'];windows=[]
            active_roof=item.get('active_outside_roof_materials',[]);active_regions=[p['replacement_volume_master_m'] for p in contract['patches']];planmap={p['patch_id']:p for p in plans[key]['plans']}
            for patch in contract['patches']:
                if args.patch and patch['id'] not in args.patch:continue
                guard(start);wid=key+'/'+patch['id'];target=OUT/key/(patch['id']+'.window.json.gz')
                if wid in state['completed_windows']:
                    assert a.sha(target)==state['completed_windows'][wid]['sha256'];windows.append(state['completed_windows'][wid]);processed+=1;continue
                finegroups=[];seamgroups=[];chunks=[];pixels=defaultdict(int);entryviolations=0;window_start=time.monotonic()
                for i,cp in enumerate(planmap[patch['id']]['chunks']):
                    guard(start);path=OUT/'chunks'/key/(patch['id']+f'_{i:03d}.json.gz')
                    if path.exists():
                        result=a.load(path);assert result['input_signature']==signature and result['sample_cell_bounds']==cp['sample_cell_bounds_with_one_cell_halo']
                    else:
                        t0=time.monotonic();coarse=None
                        if active_roof:
                            cb=cp['sample_cell_bounds_with_one_cell_halo'];coarse_bounds={'min':[math.floor(v/10)-1 for v in cb['min']],'max':[math.ceil(v/10)+1 for v in cb['max']]};coarse=a.core.compile_master(source,{'pitch':.5},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=coarse_bounds)
                        compiled=a.core.compile_master(master,{'pitch':.05},max_candidate_cells=200000,max_output_cells=200000,cell_bounds=cp['sample_cell_bounds_with_one_cell_halo']);seconds=time.monotonic()-t0;assert compiled['candidate_cells']==cp['candidate_visits'];guard(start)
                        outside=active_composition.OutsideOccupancy(compiled,coarse,active_regions,active_roof) if active_roof else occupancy
                        owned=owned_surface(compiled,cp['owned_cell_bounds']);adapter=seam.build(render,compiled,owned,patch,entries,owned_bounds=cp['owned_cell_bounds'],validate_edges=False,occupancy=outside)
                        result={'schema':'riverstone.facility_openings.chunk.v1','input_signature':signature,'asset_key':key,'patch_id':patch['id'],'chunk_index':i,'sample_cell_bounds':cp['sample_cell_bounds_with_one_cell_halo'],'owned_cell_bounds':cp['owned_cell_bounds'],'common_payload_hash':compiled['payload_hash'],'common_candidate_cells':compiled['candidate_cells'],'common_output_cells':len(compiled['cells']),'common_seconds':seconds,'global_constraints_evaluated':False,'fine_exterior_groups':adapter['fine_exterior_groups'],'transition_groups':adapter['transition_groups'],'interface_pixel_counts':adapter['interface_pixel_counts'],'entry_interface_violations':adapter['protected_entry_interface_violations'],'transition_quads':adapter['transition_quads'],'source_shapes_cropped':False}
                        newcalls+=1;totalcommon+=seconds;totalcandidates+=compiled['candidate_cells'];del compiled,owned,adapter,outside,coarse;guard(start);checkpoint(path,result)
                    finegroups+=result['fine_exterior_groups'];seamgroups+=result['transition_groups'];entryviolations+=result['entry_interface_violations']
                    for k,v in result['interface_pixel_counts'].items():pixels[k]+=v
                    chunks.append({'path':str(path.relative_to(a.ROOT)),'sha256':a.sha(path),'candidate_cells':result['common_candidate_cells'],'output_cells':result['common_output_cells'],'common_seconds':result['common_seconds']})
                    checkpoint(OUT/'progress.json',{'asset_key':key,'window':patch['id'],'source_window':patch['source_glass']['operation'],'chunk_completed':i+1,'chunks_in_window':len(planmap[patch['id']]['chunks']),'windows_completed':processed,'elapsed_seconds':round(time.monotonic()-start,2),'max_rss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'status':'running'})
                finegroups=merge_groups(finegroups);seamgroups=merge_groups(seamgroups);closed=({'unit_interface_edge_count':None,'unpaired_interface_edges':None,'active_outside_occupancy_proven':True,'final_render_boundary_qa_pending':True} if active_roof else seam.closure(render,patch,finegroups,seamgroups,.05,master['grid_origin']));assert entryviolations==0
                # Each outer interface pixel must be covered once, including
                # chunks meeting at replacement-volume corners and edges.
                spans=[patch['fine_cell_bounds']['max'][j]-patch['fine_cell_bounds']['min'][j] for j in range(3)];expected=2*sum(spans[i]*spans[j] for i,j in [(0,1),(1,2),(0,2)]);assert sum(pixels.values())==expected
                groups=merge_groups(finegroups+seamgroups);window={'schema':'riverstone.facility_openings.window_render.v1','asset_key':key,'patch_id':patch['id'],'source_glass':patch['source_glass'],'input_signature':signature,'replacement_volume_master_m':patch['replacement_volume_master_m'],'fine_pitch_m':.05,'materials':master['materials'],'groups':groups,'quad_count':sum(len(g['quads']) for g in groups),'chunks':chunks,'transition_quads':sum(len(g['quads']) for g in seamgroups),'interface_pixel_counts':dict(pixels),**closed,'protected_entry_interface_violations':0,'source_geometry_deformed':False,'source_authored_outward_protrusion_m':0,'coarse_outer_envelope_growth':False,'collider_changed':False,'runtime_activated':False}
                checkpoint(target,window);record={'patch_id':patch['id'],'source_window':patch['source_glass']['operation'],'path':str(target.relative_to(a.ROOT)),'sha256':a.sha(target),'quad_count':window['quad_count'],'transition_quads':window['transition_quads'],'chunk_count':len(chunks),'unpaired_interface_edges':closed['unpaired_interface_edges'],'protected_entry_interface_violations':0};state['completed_windows'][wid]=record;windows.append(record);processed+=1;checkpoint(state_path,state);guard(start)
                print(json.dumps({'window_complete':wid,'source_window':record['source_window'],'window_seconds':round(time.monotonic()-window_start,2),'windows_completed':processed,'windows_total':goal,'elapsed_seconds':round(time.monotonic()-start,2),'max_rss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'disk_bytes':size()}),flush=True)
            assets.append({'asset_key':key,'source_master_path':item['source_master_path'],'source_sha256':item['source_sha256'],'source_render_path':contract['source_render_path'],'source_render_sha256':contract['source_render_sha256'],'replacement_contract_path':item['replacement_contract_path'],'replacement_contract_sha256':item['replacement_contract_sha256'],'windows':windows,'activation_unit':'all windows of this asset, old finite quad edits plus fine and seam together','roof_overlap_original_quad_count':sum(1 for e in contract['cache_quad_edits'] if 'slate' in e['material']),'collider_changed':False,'runtime_activated':False})
        state['status']='complete' if len(state['completed_windows'])==sum(x['window_count'] for x in catalog['assets']) else 'asset_subset_complete';state['last_run_seconds']=round(time.monotonic()-start,2);checkpoint(state_path,state)
        final={'schema':'riverstone.facility_openings.compiled_set.v1','asset_signatures':{x['asset_key']:state['asset_signatures'][x['asset_key']] for x in assets},'assets':assets,'window_count':processed,'new_common_compile_calls_this_run':newcalls,'new_candidate_cells_this_run':totalcandidates,'new_common_seconds_this_run':totalcommon,'elapsed_seconds':state['last_run_seconds'],'max_rss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'output_directory_bytes':size(),'source_geometry_deformed':False,'unpaired_interface_edges':None if any(x.get('active_outside_roof_materials') for x in requested) else 0,'protected_entry_interface_violations':0,'collider_changed':False,'runtime_activated':False,'roof_detail_composition_required':True,'subset_only':bool(args.patch),'provenance':'Only bounded common requests; render-only chunks and combined window surfaces. No full-world/full-building fine cells persisted.'};name=(args.asset or 'all')+('.subset_'+'_'.join(args.patch) if args.patch else '')+'.catalog.json';checkpoint(OUT/name,final);print(json.dumps({'complete':True,'windows':processed,'elapsed_seconds':final['elapsed_seconds'],'max_rss_kb':final['max_rss_kb'],'bytes':size()}),flush=True)
    except Exception as e:
        state['status']='paused';state['error']=str(e);state['elapsed_seconds']=round(time.monotonic()-start,2);checkpoint(state_path,state);print(json.dumps({'paused':True,'error':str(e),'windows_completed':processed}),flush=True);raise
if __name__=='__main__':main()
