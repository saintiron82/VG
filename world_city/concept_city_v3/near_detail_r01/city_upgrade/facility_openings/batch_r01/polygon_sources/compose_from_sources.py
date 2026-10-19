"""Append-only opening-layer support around the frozen native roof composer.

Only the source-preserving appended common opening layer is admitted. Original
component/instance prefixes, constraints and operation bytes must be exact;
roof replacement proof remains the same inverse rigid-transform contract.
"""
import copy,importlib.util,json,resource,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent.parent))
import author as a
spec=importlib.util.spec_from_file_location('canonical_roof_shared',HERE.parent/'canonical_adapter/compose.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

def run():
    wc=a.load(HERE/'generated/catalog.json');rc=a.load(a.HERE.parent/'facility_roofs/activation_plan/all_72_layered_compile_catalog.v6.json');rm={r['asset_key']:r for r in rc['assets']};out=HERE/'canonical';out.mkdir(exist_ok=True);items=[]
    policy={'fine_pitch_m':.05,'transform_tolerance_m':1e-12,'roof_part_categories':['roof'],'roof_materials':['slate','slate_light','slate_dark','slate_worn']}
    for w in wc['assets']:
        r=rm[w['asset_key']];assert w['source_sha256']==r['source_sha256'];source=c.checked_load(a.ROOT/w['source_master_path'],w['source_sha256']);window=c.checked_load(a.ROOT/w['emitted_master_path'],w['emitted_master_sha256']);roof=c.checked_load(a.ROOT/r['emitted_master_path'],r['emitted_master_sha256'])
        assert window['components'][:len(source['components'])]==source['components'] and window['instances'][:len(source['instances'])]==source['instances'];assert window['constraints']==source['constraints'];extras=window['components'][len(source['components']):];exinst=window['instances'][len(source['instances']):];assert [x['id'] for x in extras]==['opening_details'] and [x['id'] for x in exinst]==['opening_details'];assert all(o['action']=='paint' for x in extras for o in x['operations'])
        native,proof=c.compose_master(source,source,roof,policy);nmap={x['id']:x for x in native['components']};combined=copy.deepcopy(window)
        for i,x in enumerate(source['components']):combined['components'][i]=nmap[x['id']]
        combined.setdefault('provenance',{})['canonical_roof_openings']=native['provenance']['canonical_roof_openings'];combined['provenance']['append_only_window_layer']={'window_master_path':w['emitted_master_path'],'window_master_sha256':w['emitted_master_sha256'],'extra_components':['opening_details'],'source_prefix_unchanged':True,'window_cuts_unchanged':True,'wrapper_sha256':a.sha(__file__)}
        assert combined['instances']==window['instances'] and combined['constraints']==window['constraints'] and combined['assembly_cuts']==window['assembly_cuts'];a.core.validate_master(combined,.05)
        contract=c.checked_load(a.ROOT/w['replacement_contract_path'],w['replacement_contract_sha256']);render=c.checked_load(a.ROOT/contract['source_render_path'],contract['source_render_sha256']);scope=c.replacement_scope(source,render,proof,policy)
        mp=out/(w['asset_key']+'.canonical.master.json.gz');a.write(mp,combined);pp=out/(w['asset_key']+'.proof.json.gz');a.write(pp,{**proof,'source_master_sha256':w['source_sha256'],'roof_master_sha256':r['emitted_master_sha256'],'window_master_sha256':w['emitted_master_sha256'],'canonical_master_sha256':a.sha(mp),'append_only_window_components':True,'full_compile':False})
        contract.update(authored_master_path=str(mp.relative_to(a.ROOT)),authored_master_sha256=a.sha(mp),roof_replacement_scope=scope,roof_composition={'composition_proof_path':str(pp.relative_to(a.ROOT)),'composition_proof_sha256':a.sha(pp),'canonical_master_path':str(mp.relative_to(a.ROOT)),'canonical_master_sha256':a.sha(mp),'roof_master_path':r['emitted_master_path'],'roof_master_sha256':r['emitted_master_sha256'],'native_instances_and_constraints_preserved':True,'source_prefix_exact':True,'full_compile':False});cp=out/(w['asset_key']+'.replacement.json.gz');a.write(cp,contract)
        items.append({**w,'emitted_master_path':str(mp.relative_to(a.ROOT)),'emitted_master_sha256':a.sha(mp),'replacement_contract_path':str(cp.relative_to(a.ROOT)),'replacement_contract_sha256':a.sha(cp),'roof_master_path':r['emitted_master_path'],'roof_master_sha256':r['emitted_master_sha256']})
    a.write(out/'catalog.json',{'schema':'riverstone.canonical_roof_openings.catalog.v1','assets':items,'shared_composer_sha256':a.sha(c.__file__),'wrapper_sha256':a.sha(__file__),'source_window_catalog_sha256':a.sha(HERE/'generated/catalog.json'),'compile_calls':0,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'runtime_ready':False});print({'source_assets':len(items),'windows':sum(x['window_count'] for x in items),'compile_calls':0,'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
if __name__=='__main__':run()
