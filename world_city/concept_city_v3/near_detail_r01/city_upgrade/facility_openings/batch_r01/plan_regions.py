"""Conservative finite source-contact domains; never crop or change source geometry.

AABB broad phase over exact source roof and nonroof paint operations covers all
possible contact including gables, ceiling caps, upper framing and chimneys.
The union is packed into disjoint coarse-grid boxes, then the common engine is
budgeted at native .05 cell_bounds. No occupancy evaluation occurs here.
"""
import argparse,itertools,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import author as a
import estimate_run as b
KEYS=['c3_property_ordinary_r2_b10bcfbba43136a4','working_r01_bank_loft_store']
ROOFS=a.HERE.parent/'facility_roofs/activation_plan/all_72_layered_compile_catalog.v6.json'

def union_boxes(boxes,pitch=.5):
    occupied=set()
    for r in boxes:
        lo=[round(v/pitch) for v in r['min']];hi=[round(v/pitch) for v in r['max']]
        occupied.update(itertools.product(*(range(lo[j],hi[j]) for j in range(3))))
    assert len(occupied)<100000,'finite contact grid budget exceeded'
    total=len(occupied);out=[]
    while occupied:
        lo=min(occupied);hi=[v+1 for v in lo]
        # Deterministic Z then X then Y rectangular packing of the exact union.
        for axis in [2,0,1]:
            while True:
                slab=itertools.product(*(range(lo[j],hi[j]) if j!=axis else [hi[j]] for j in range(3)))
                if all(p in occupied for p in slab):hi[axis]+=1
                else:break
        cells=set(itertools.product(*(range(lo[j],hi[j]) for j in range(3))))
        assert cells<=occupied;occupied-=cells
        out.append({'min':[v*pitch for v in lo],'max':[v*pitch for v in hi]})
    assert sum(math.prod(round((r['max'][j]-r['min'][j])/pitch) for j in range(3)) for r in out)==total
    return out,total

def contacts(source,roof):
    identities={c['metadata']['shared_row_source']['instance_metadata']['source_identity']['instance'] for c in roof['components']}
    inv=a.source_inventory(source);rs=[(c,i,o,t,bb) for c,i,o,t,bb in inv if i in identities and o['action']=='paint'];non=[x for x in inv if x[1] not in identities and x[2]['action']=='paint']
    candidates=[]
    for rc,ri,ro,rt,(rlo,rhi) in rs:
        for nc,ni,no,nt,(nlo,nhi) in non:
            low=[max(rlo[j],nlo[j]) for j in range(3)];high=[min(rhi[j],nhi[j]) for j in range(3)]
            if any(high[j]<low[j]-.05 for j in range(3)):continue
            # One retained-cache cell around every broad-phase contact restores
            # coarse/fine transition support without changing source operands.
            lo=[math.floor((v-.5)*2+1e-8)/2 for v in low];hi=[math.ceil((v+.5)*2-1e-8)/2 for v in high]
            candidates.append({'roof':{'component':rc,'instance':ri,'operation':ro['id']},'nonroof':{'component':nc,'instance':ni,'operation':no['id'],'material':no['material']},'exact_operation_aabb_intersection':{'min':low,'max':high},'min':lo,'max':hi})
    packed,n=union_boxes(candidates)
    return [{'id':f'contact_{i:03d}','kind':'source_contact','source_shape_change':False,**r} for i,r in enumerate(packed)],candidates,n

def make(key,canonical_catalog=None):
    rr=next(x for x in a.load(ROOFS)['assets'] if x['asset_key']==key)
    src=a.load(a.ROOT/rr['source_master_path']);roof=a.load(a.ROOT/rr['emitted_master_path'])
    assert a.sha(a.ROOT/rr['source_master_path'])==rr['source_sha256'] and a.sha(a.ROOT/rr['emitted_master_path'])==rr['emitted_master_sha256']
    regions,evidence,n=contacts(src,roof)
    out=HERE/'contact_plan';out.mkdir(exist_ok=True)
    result={'schema':'riverstone.facility.finite_regions.v1','asset_key':key,'source_master_path':rr['source_master_path'],'source_sha256':rr['source_sha256'],'roof_master_path':rr['emitted_master_path'],'roof_master_sha256':rr['emitted_master_sha256'],'source_shapes_cropped':False,'new_occupancy_authored':False,'coarse_contact_domain_cell_count':n,'contact_union_volume_m3':n/8,'contact_regions':regions,'contact_broad_phase_evidence':evidence,'algorithm_sha256':a.sha(__file__),'limitations':'Conservative original-operation AABB coverage, not evidence of actual solid contact or sealing. Exact canonical occupancy and final face-domain QA are required. Source-empty gaps stay empty.'}
    if canonical_catalog:
        row=next(x for x in a.load(canonical_catalog)['assets'] if x['asset_key']==key)
        master=a.load(a.ROOT/row['emitted_master_path']);wc=a.load(a.ROOT/row['replacement_contract_path']);bs=b.bounds_list(master,.05);rb=b.bounds_list(roof,.05)
        windows=[{'id':p['id'],'kind':'window','source_glass':p['source_glass'],**p['replacement_volume_master_m']} for p in wc['patches']]
        ordered=windows+regions;plans=[]
        for region in ordered:
            cb={k:[round(v*20) for v in region[k]] for k in ['min','max']};outer={'min':[v-1 for v in cb['min']],'max':[v+1 for v in cb['max']]}
            chunks=b.split(bs,cb,outer,140000)
            for chunk in chunks:
                chunk['roof_only_candidate_visits']=b.cost(rb,chunk['sample_cell_bounds_with_one_cell_halo']);assert chunk['roof_only_candidate_visits']<=140000
            plans.append({'region':region,'fine_cell_bounds':cb,'chunks':chunks})
        result.update(canonical_catalog_path=str(Path(canonical_catalog).resolve().relative_to(a.ROOT)),canonical_catalog_sha256=a.sha(canonical_catalog),canonical_master_path=row['emitted_master_path'],canonical_master_sha256=row['emitted_master_sha256'],window_contract_path=row['replacement_contract_path'],window_contract_sha256=row['replacement_contract_sha256'],ordered_regions=ordered,plans=plans,chunk_count=sum(len(p['chunks']) for p in plans),fine_candidates=sum(c['candidate_visits'] for p in plans for c in p['chunks']),roof_candidates=sum(c['roof_only_candidate_visits'] for p in plans for c in p['chunks']))
    target=out/(key+'.plan.json');a.write(target,result)
    print({k:v for k,v in result.items() if k in ['asset_key','coarse_contact_domain_cell_count','contact_union_volume_m3','chunk_count','fine_candidates','roof_candidates']},'contact_regions',len(regions),'broad_pairs',len(evidence),flush=True)
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--asset',action='append');p.add_argument('--canonical-catalog',type=Path);args=p.parse_args()
    for key in args.asset or KEYS:make(key,args.canonical_catalog)
