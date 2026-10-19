"""Read-only active-city inventory and authoring estimates, no full compilation.

Default writes reports only. --emit accepts explicit asset keys and writes their
independent masters below this directory. Unreferenced catalog assets are excluded.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import adapter as a




def classified_estimate(master,pitch,selectors):
    role_by_category=selectors["analysis_roles_by_category"]
    result=a.estimate_candidates(master,pitch)
    grouped=Counter()
    for row in result['by_component']:
        row['role']=next((role_by_category[c] for c in row['source_categories'] if c in role_by_category),'retained_other')
        grouped[row['role']]+=row['candidate_cells']
    result['by_role_candidate_cells']=dict(grouped)
    result['window_candidate_cells']=sum(row['by_part'].get('windows',0) for row in result['by_component'])
    result['door_candidate_cells']=sum(row['by_part'].get('door',0)+row['by_part'].get('door_frame',0) for row in result['by_component'])
    return result


def preflight(index_path,output,rules_path,selectors_path,emit=(),budget=20*1024*1024):
    index_path=Path(index_path)
    index=a.load(index_path)
    usages=defaultdict(dict)
    tile_sources=[]
    for tile_id,tile in index['tiles'].items():
        path=a.ROOT/tile['instances_path']
        actual=a.sha(path)
        a.fail(actual==tile['instances_sha256'],'tile_source_hash_mismatch',{'tile':tile_id})
        tile_sources.append({'tile_id':tile_id,'path':tile['instances_path'],'sha256':actual})
        for inst in a.load(path)['common_instances']:
            key=inst['asset_key']
            if key.startswith('ordinary_'):
                old=usages[key].get(inst['id'])
                a.fail(old is None or old==inst,'inconsistent_duplicate_city_instance',{'id':inst['id']})
                usages[key][inst['id']]=inst
    rules,selectors=a.load(rules_path),a.load(selectors_path)
    a.fail(set(emit)<=set(usages),'emit_asset_not_in_active_city',{'unknown':sorted(set(emit)-set(usages))})
    output=Path(output)
    records=[]
    running_bytes=0
    for key,instances in sorted(usages.items()):
        asset=index['common_assets'][key]
        source_path=a.ROOT/asset['master_path']
        a.fail(a.sha(source_path)==asset['master_sha256'],'master_source_hash_mismatch',{'key':key})
        source=a.load(source_path)
        info={'source_path':asset['master_path'],'source_sha256':asset['master_sha256'],
              'rules_path':str(rules_path.relative_to(a.ROOT) if rules_path.is_absolute() else rules_path),
              'rules_file_sha256':a.sha(rules_path),
              'selectors_path':str(selectors_path.relative_to(a.ROOT) if selectors_path.is_absolute() else selectors_path),
              'selectors_file_sha256':a.sha(selectors_path)}
        record={'asset_key':key,'source_master_path':asset['master_path'],'source_sha256':asset['master_sha256'],
                'source_render_sha256':asset['render_sha256'],'instance_count':len(instances),
                'instance_ids':sorted(instances),'source_metadata':source.get('metadata',{}),
                'seed':rules['seed'],'emitted_master_path':None}
        try:
            master,provenance,report=a.author(source,rules,selectors,info)
            record.update({'status':report['status'],'counts':report['counts'],
                           'pending_features':report['pending_features'],'preservation':report['preservation'],
                           'near_005':classified_estimate(master,.05,selectors),'coarse_010_cost_only':classified_estimate(master,.1,selectors),
                           'output_id':master['id'],'master_json_bytes':len(json.dumps(master,separators=(',',':'),ensure_ascii=False).encode())+1})
            if key in emit:
                size=record['master_json_bytes']
                a.fail(running_bytes+size<=budget,'emission_disk_budget_exceeded',{'requested':running_bytes+size,'budget':budget})
                path=output/'masters'/(key+'.master.json')
                a.write(path,master)
                a.write(path.with_name(key+'.provenance.json'),provenance)
                a.write(path.with_name(key+'.validation.json'),report)
                running_bytes+=size
                record['emitted_master_path']=str(path.relative_to(a.ROOT))
                record['emitted_master_sha256']=a.sha(path)
        except a.UnsupportedSurface as error:
            record.update(error.report)
            record['source_005_cost_only']=classified_estimate(source,.05,selectors)
            record['source_010_cost_only']=classified_estimate(source,.1,selectors)
        records.append(record)
    supported=[r for r in records if r['status']!='coverage_pending']
    pending=[r for r in records if r['status']=='coverage_pending']
    summary={'active_ordinary_assets':len(records),'active_ordinary_unique_instances':sum(r['instance_count'] for r in records),
             'authored_supported_assets':len(supported),'authored_supported_instances':sum(r['instance_count'] for r in supported),
             'unsupported_pending_assets':len(pending),'unsupported_pending_instances':sum(r['instance_count'] for r in pending),
             'pending_reasons':dict(Counter(r['reason'] for r in pending)),
             'feature_pending_assets':sum(bool(r.get('pending_features')) for r in supported),
             'source_operations':sum(r['counts']['source_operations'] for r in supported),
             'authored_operations':sum(r['counts']['output_operations'] for r in supported),
             'roof_tiles':sum(r['counts']['roof_tiles'] for r in supported),
             'windows':sum(r['counts']['windows'] for r in supported),
             'full_005_candidate_cells_unique_assets':sum(r['near_005']['operation_aabb_candidate_cells'] for r in supported),
             'full_010_candidate_cells_unique_assets_cost_only':sum(r['coarse_010_cost_only']['operation_aabb_candidate_cells'] for r in supported),
             'all_supported_master_json_bytes':sum(r['master_json_bytes'] for r in supported),
             'emitted_master_count':sum(r['emitted_master_path'] is not None for r in records),'emitted_master_bytes':running_bytes,
             'full_compilation_count':0}
    result={'schema':'riverstone.house_detail.active_catalog.v1','engine':a.VERSION,'engine_sha256':a.sha(a.__file__),
            'index_path':str(index_path.relative_to(a.ROOT)),'index_sha256':a.sha(index_path),
            'rules_sha256':a.sha(rules_path),'selectors_sha256':a.sha(selectors_path),'seed':rules['seed'],
            'tile_sources':tile_sources,'summary':summary,'assets':records,
            'limits':['Reports and emitted masters do not modify city runtime or approved r04.',
                      '0.10m statistics are cost comparisons, not approval to coarsen detail.',
                      'Separate structural/detail compilation must preserve shared grid origin, ordered cuts and same-instance overrides.',
                      'AABB candidate counts are not occupied-cell, memory, face or quad predictions.',
                      'No terrain support, public access, collision or visual integration approval.']}
    a.write(output/'active_catalog.json',result)
    a.write(output/'summary.json',summary)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',type=Path,default=a.ROOT/'world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json')
    p.add_argument('--output',type=Path,default=HERE/'generated')
    p.add_argument('--rules',type=Path,default=HERE/'rules.r04.v1.json')
    p.add_argument('--selectors',type=Path,default=HERE/'selectors.ordinary_r2.v1.json')
    p.add_argument('--emit',nargs='*',default=[])
    p.add_argument('--budget-bytes',type=int,default=20*1024*1024)
    args=p.parse_args()
    print(json.dumps(preflight(args.index,args.output,args.rules,args.selectors,args.emit,args.budget_bytes),indent=2))
