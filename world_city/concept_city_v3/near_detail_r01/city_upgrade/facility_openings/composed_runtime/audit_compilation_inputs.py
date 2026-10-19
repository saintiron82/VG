"""Verify bounded window/contact chunk hashes and current frozen tool signatures."""
from pathlib import Path
import resource,time
import compose as c
a=c.a
import compile_set,active_composition,seam_adapter

def main():
    start=time.monotonic();files={};checks=[]
    def bind(path,role,expected=None,load=True):
        p=Path(path);p=p if p.is_absolute() else a.ROOT/p;digest=a.sha(p)
        if expected:assert digest==expected,(str(p),'hash mismatch')
        files[str(p.relative_to(a.ROOT))]={'path':str(p.relative_to(a.ROOT)),'sha256':digest,'role':role}
        return a.load(p) if load else None
    for p in [a.core.__file__,a.__file__,compile_set.__file__,active_composition.__file__,seam_adapter.__file__,__file__,Path(__file__).with_name('compile_authored_interfaces.py'),Path(__file__).with_name('compile_source_contacts.py')]:bind(p,'bounded author/compiler tool',load=False)
    authored=bind(a.HERE/'composed/active_boundary_r02.catalog.json','window source catalog')['assets'][0]
    plan=bind(a.HERE/'composed/active_boundary_r02.cost_plan.json','window cost plan')['assets'][0]
    tools={'core_sha256':a.sha(a.core.__file__),'seam_sha256':a.sha(seam_adapter.__file__),'runner_sha256':a.sha(compile_set.__file__),'active_composition_sha256':a.sha(active_composition.__file__)}
    signature=a.core.digest({'asset':authored,'tools':tools,'plans':plan});catalog=bind(a.HERE/'compiled_active_r02/registered_cathedral_nave_aisles_transept.catalog.json','complete compiled window catalog');assert catalog['asset_signatures'][authored['asset_key']]==signature
    chunks=0
    for w in catalog['assets'][0]['windows']:
        window=bind(w['path'],'complete window geometry',w['sha256']);assert window['input_signature']==signature
        for item in window['chunks']:
            chunk=bind(item['path'],'bounded native common window chunk',item['sha256']);assert chunk['input_signature']==signature and chunk['source_shapes_cropped']==False;chunks+=1
    assert chunks==128;checks.append({'scope':'33 windows / 128 chunks','all_input_and_tool_signatures_match':True,'fine_common_calls':128,'original_coarse_common_calls':128})
    for folder,version in [('cathedral_authored_interfaces_r01','authored'),('cathedral_gable_contacts_r02','source_contact')]:
        directory=Path(__file__).parent/folder;plan=bind(directory/'cost_plan.json',version+' cost plan');cat=bind(directory/'catalog.json',version+' catalog')
        if version=='authored':
            sig=a.core.digest({'plan':plan,'runner_sha':a.sha(Path(__file__).with_name('compile_authored_interfaces.py')),'common_sha':a.sha(a.core.__file__),'seam_sha':a.sha(seam_adapter.__file__),'active_composition_sha':a.sha(active_composition.__file__)})
            outputs=cat['outputs'];expected_chunks=50
        else:
            sig=a.core.digest({'plan':plan,'runner_sha256':a.sha(Path(__file__).with_name('compile_source_contacts.py')),'common_sha256':a.sha(a.core.__file__),'seam_sha256':a.sha(seam_adapter.__file__)})
            outputs=[o for o in cat['outputs'] if Path(o['path']).parent.name==folder];expected_chunks=16
        count=0
        for output in outputs:
            geometry=bind(output['path'],version+' region geometry',output['sha256'])
            for item in geometry['chunks']:
                chunk=bind(item['path'],version+' native common chunk',item['sha256']);assert chunk['signature']==sig and chunk.get('protected_entry_violations',0)==0;count+=1
        assert count==expected_chunks
        checks.append({'scope':version,'all_input_and_tool_signatures_match':True,'fine_common_calls':count,'original_coarse_common_calls':count,'roof_only_common_calls':count if version=='source_contact' else 0})
    result={'schema':'riverstone.bounded_compilation.input_closure.v1','all_pass':True,'checks':checks,'verified_file_count':len(files),'source_inputs':list(files.values()),'comparison_common_calls_separate':12,'whole_building_fine_compile':False,'source_shape_crop':False,'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};a.write(a.HERE/'composed/cathedral_compilation_input_closure.json',result);print({k:result[k] for k in ['all_pass','verified_file_count','elapsed_seconds','max_rss_kib']})

if __name__=='__main__':main()
