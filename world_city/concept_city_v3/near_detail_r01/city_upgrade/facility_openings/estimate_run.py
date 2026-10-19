"""Exact AABB-visit budgeting only. No occupancy compile or full cell files."""
import json,math
import author as a
HERE=a.HERE

def bounds_list(master,pitch):
    origin=master.get('grid_origin',[0,0,0]);items=[b for c,i,o,t,b in a.source_inventory(master)]
    items += [a.bounds(c['shape'],a.core.transform(c.get('transform'))) for c in master.get('assembly_cuts',[])]
    items += [a.bounds(c['shape'],a.core.transform(c.get('transform'))) for c in master.get('constraints',[]) if c['kind']=='empty_region']
    return [([math.floor((lo[j]-origin[j])/pitch+a.core.EPS) for j in range(3)],[math.ceil((hi[j]-origin[j])/pitch-a.core.EPS) for j in range(3)]) for lo,hi in items]
def cost(bounds,cb):return sum(math.prod(max(0,min(hi[j],cb['max'][j])-max(lo[j],cb['min'][j])) for j in range(3)) for lo,hi in bounds)
def halo(cb,outer):return {'min':[max(outer['min'][j],cb['min'][j]-1) for j in range(3)],'max':[min(outer['max'][j],cb['max'][j]+1) for j in range(3)]}
def split(bounds,cb,outer,cap):
    sampled=halo(cb,outer);n=cost(bounds,sampled)
    if n<=cap:return [{'owned_cell_bounds':cb,'sample_cell_bounds_with_one_cell_halo':sampled,'candidate_visits':n}]
    axis=max(range(3),key=lambda j:cb['max'][j]-cb['min'][j]);mid=((cb['max'][axis]+cb['min'][axis])//20)*10
    if mid<=cb['min'][axis] or mid>=cb['max'][axis]:mid=(cb['max'][axis]+cb['min'][axis])//2
    assert cb['min'][axis]<mid<cb['max'][axis]
    one={k:list(v) for k,v in cb.items()};two={k:list(v) for k,v in cb.items()};one['max'][axis]=mid;two['min'][axis]=mid
    return split(bounds,one,outer,cap)+split(bounds,two,outer,cap)

def main():
    verified=a.load(HERE/'tests/verification.json');rate=[r['detail_compile_seconds']/r['detail_candidate_cells'] for r in verified['roi_probes']];rows=[];total=0;cap=200000
    for asset in a.load(HERE/'generated/catalog.json')['assets']:
        master=a.load(a.ROOT/asset['emitted_master_path']);contract=a.load(a.ROOT/asset['replacement_contract_path']);bs=bounds_list(master,.05);plans=[]
        for p in contract['patches']:
            full=cost(bs,p['fine_cell_bounds']);chunks=split(bs,p['fine_cell_bounds'],p['fine_cell_bounds'],cap);plans.append({'patch_id':p['id'],'source_glass_operation':p['source_glass']['operation'],'whole_patch_candidate_visits':full,'chunks':chunks})
        for r in verified['roi_probes']:
            if r['asset_key']==asset['asset_key']:assert cost(bs,r['cell_bounds'])==r['detail_candidate_cells']
        n=sum(c['candidate_visits'] for p in plans for c in p['chunks']);total+=n;rows.append({'asset_key':asset['asset_key'],'windows':len(plans),'chunk_count':sum(len(p['chunks']) for p in plans),'max_whole_patch_candidates':max(p['whole_patch_candidate_visits'] for p in plans),'max_chunk_candidates':max(c['candidate_visits'] for p in plans for c in p['chunks']),'total_candidates_with_halos':n,'plans':plans})
    result={'schema':'riverstone.facility_openings.cost_plan.v1','mode':'estimate_only_no_full_compile','exact_candidate_estimator_matches_measured_probes':4,'assets':rows,'total_candidates_with_halos':total,'measured_common_fine_seconds_per_million_candidates_range':[min(rate)*1e6,max(rate)*1e6],'estimated_common_compile_seconds_range':[round(total*min(rate)),round(total*max(rate))],'proposed_wall_clock_cap_seconds':600,'proposed_candidate_visits_cap_per_call':cap,'proposed_retained_output_cells_cap_per_call':cap,'proposed_memory_guard_mib':256,'measured_roi_peak_rss_mib':round(verified['max_rss_kb']/1024,2),'additional_output_disk_cap_bytes':20*1024*1024,'output_policy':'Render-only gzip chunks and seams. Never persist full compiled occupancy. Keep only one chunk and halo transiently.','required_chunk_adapter':'Internal chunk edges use fine halo occupancy, never original coarse occupancy; only the outer replacement-volume boundary uses coarse/fine XOR seams. Merge or deduplicate chunk-owned surfaces by integer cell ownership.','approval_state':'Parent authorized one serial bounded run with 256MiB memory and 20MB output caps; no parallel/full-world compile.','limits':'Compile-time extrapolation is measured, not a completion promise; meshing/seam/IO costs and current CPU contention are additional. Stop on any cap or structural failure; never fall back to full-building compile.'}
    a.write(HERE/'generated/cost_plan.json',result);print(json.dumps({k:v for k,v in result.items() if k!='assets'},indent=2));print(json.dumps([{k:v for k,v in r.items() if k!='plans'} for r in rows],indent=2))
if __name__=='__main__':main()
