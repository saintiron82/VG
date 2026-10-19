"""Add explicit runtime schema bindings without changing sealed geometry."""
import argparse,copy,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import author as a

def run(key):
    out=HERE/'composed'/key;path=out/(key+'.manifest.json');manifest=a.load(path);cat=a.load(HERE/'compiled'/key/'catalog.json');old_render=manifest['render_sha256']
    before=out/(key+'.pre_runtime_fields.manifest.json')
    if not before.exists():before.write_bytes(path.read_bytes())
    original=a.load(before);assert original['render_sha256']==old_render
    manifest['surface_exclusion_regions']=[{k:r[k] for k in ['id','min','max']} for r in cat['ordered_regions']]
    manifest['replacement_contract_path']=cat['window_contract_path'];manifest['replacement_contract_sha256']=cat['window_contract_sha256'];manifest['window_contract_sha256']=cat['window_contract_sha256']
    manifest['composition_contract_sha256']=a.core.digest({'original_master':manifest['source_master_sha256'],'original_render':manifest['source_render_sha256'],'canonical':cat['canonical_master_sha256'],'roof':cat['roof_master_sha256'],'window_contract':cat['window_contract_sha256'],'plan':cat['plan_sha256']})
    manifest['runtime_contract_revision']={'prior_manifest_path':str(before.relative_to(a.ROOT)),'prior_manifest_sha256':a.sha(before),'geometry_changed':False,'added_fields':['surface_exclusion_regions','replacement_contract_path','replacement_contract_sha256','window_contract_sha256','composition_contract_sha256'],'window_identification':'Exact window_regions ID set, not an opening_ string prefix. Existing-aperture patches use aperture_ IDs; source_features is an array of original frame/sill/mullion/shutter operations.'}
    paths={i['path']:i for i in manifest['source_inputs']}
    for p,role in [(before,'prior geometry-identical manifest before runtime binding fields'),(Path(__file__),'runtime field schema adapter')]:paths[str(p.resolve().relative_to(a.ROOT))]={'path':str(p.resolve().relative_to(a.ROOT)),'sha256':a.sha(p),'role':role}
    manifest['source_inputs']=list(paths.values());assert a.sha(a.ROOT/manifest['render_path'])==old_render
    for row in manifest['source_inputs']:assert a.sha(a.ROOT/row['path'])==row['sha256'],row
    a.write(path,manifest);files=manifest['source_inputs']+[{'path':manifest['render_path'],'sha256':old_render,'role':'composed render output'},{'path':str(path.relative_to(a.ROOT)),'sha256':a.sha(path),'role':'runtime schema-complete composition manifest'}]
    a.write(out/'file_closure.json',{'schema':'riverstone.facility.composition_file_closure.v1','asset_key':key,'files':files,'file_count':len(files),'hash_mismatches':0,'catalog_revision_resolution':manifest.get('catalog_revision_resolution'),'geometry_changed':False});print(json.dumps({'manifest':str(path.relative_to(a.ROOT)),'sha256':a.sha(path),'surface_exclusion_regions':len(manifest['surface_exclusion_regions']),'replacement_contract_path':manifest['replacement_contract_path'],'closure_files':len(files),'render_unchanged':True}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('asset');run(p.parse_args().asset)
