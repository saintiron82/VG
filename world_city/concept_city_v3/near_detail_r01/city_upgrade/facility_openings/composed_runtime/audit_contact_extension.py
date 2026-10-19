"""Extend an immutable compiler-input closure with one bounded contact catalog."""
import argparse,time,resource
from pathlib import Path
import compose as c
import compile_source_contacts as runner
import seam_adapter as seam
a=c.a

def audit(catalog_path,previous_report,output):
    start=time.monotonic();prior=a.load(previous_report);assert prior['all_pass']
    files={item['path']:item for item in prior['source_inputs']}
    for item in files.values():assert a.sha(a.ROOT/item['path'])==item['sha256']
    def bind(path,role,expected=None,load=True):
        path=Path(path);path=path if path.is_absolute() else a.ROOT/path
        digest=a.sha(path)
        if expected:assert expected==digest,(path,'hash mismatch')
        files[str(path.relative_to(a.ROOT))]={'path':str(path.relative_to(a.ROOT)),'sha256':digest,'role':role}
        return a.load(path) if load else None
    bind(previous_report,'immutable prior compiler dependency closure',load=False)
    cat=bind(catalog_path,'additional contact catalog');extension=cat['source_contact_restoration']
    bind(extension['previous_catalog_path'],'previous immutable interface catalog',extension['previous_catalog_sha256'])
    spec=bind(extension['spec_path'],'additional bounded contact specification',extension['spec_sha256'])
    plan=bind(extension['cost_plan_path'],'additional contact cost plan',extension['cost_plan_sha256'])
    bind(cat['canonical_master_path'],'unchanged canonical source',cat['canonical_master_sha256'],False)
    bind(spec['roof_master_path'],'exact independent roof occupancy source',spec['roof_master_sha256'],False)
    assert extension['canonical_master_sha256_unchanged']==cat['canonical_master_sha256']
    signature=a.core.digest({'plan':plan,'runner_sha256':a.sha(runner.__file__),'common_sha256':a.sha(a.core.__file__),'seam_sha256':a.sha(seam.__file__)})
    count=0;regions=[]
    for entry in cat['outputs']:
        if Path(entry['path']).parent!=Path(spec['output_directory']):continue
        render=bind(entry['path'],'additional fine contact and seam geometry',entry['sha256']);regions.append(entry['region']['id'])
        for item in render['chunks']:
            chunk=bind(item['path'],'additional native common contact chunk',item['sha256'])
            assert chunk['signature']==signature and chunk['protected_entry_violations']==0 and chunk['source_shape_change']==False
            count+=1
    assert count==plan['chunks'] and sorted(regions)==sorted(r['id'] for r in spec['regions'])
    bind(__file__,'dependency extension verification tool',load=False)
    result={**prior,'previous_closure_sha256':a.sha(previous_report),'all_pass':True,'checks':prior['checks']+[{'scope':'unchanged-source upper gable contact extension','regions':regions,'all_input_and_tool_signatures_match':True,'fine_common_calls':count,'original_coarse_common_calls':count,'roof_only_common_calls':count,'protected_entry_violations':0}], 'verified_file_count':len(files),'source_inputs':list(files.values()),'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    a.write(output,result);print({k:result[k] for k in ['all_pass','verified_file_count','elapsed_seconds','max_rss_kib']})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('previous',type=Path);p.add_argument('output',type=Path);args=p.parse_args();audit(args.catalog.resolve(),args.previous.resolve(),args.output.resolve())
