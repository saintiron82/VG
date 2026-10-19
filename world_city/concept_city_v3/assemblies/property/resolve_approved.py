"""Resolve the explicitly approved seven noble plots; never compiles assets."""
from pathlib import Path
import hashlib,json
from .resolver import PropertyResolver,read_source_plan
HERE=Path(__file__).parent
APPROVED_NOBLES=['P_NOBLE_'+s for s in ('01','02','03','04','06','07','08')]


def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def verified_cache(path):
    if not path.exists():return {}
    manifest=json.loads(path.read_text());verified={}
    for key,r in manifest.get('assets',{}).items():
        if Path(r['compiled_asset_ref']).exists() and file_sha(r['compiled_asset_ref'])==r['render_sha256'] and file_sha(r['master_path'])==r['master_file_sha256']:verified[key]=r
    return verified


def run():
    plan_path=HERE.parents[1]/'source/plan.json';terrain_path=HERE.parents[1]/'topography/contract.json';plan,h=read_source_plan(plan_path);terrain=json.loads(terrain_path.read_text());resolver=PropertyResolver();cache=verified_cache(HERE/'cache/manifest.json');pack=resolver.resolve(plan,terrain,APPROVED_NOBLES,h,cache)
    failed=[p for p in pack['unresolved'] if p['source_plot_id'] in APPROVED_NOBLES]
    if failed:raise ValueError('Approved noble resolution failed: '+str(failed))
    pack['approval_scope']='Parent authorized these seven noble parcels after contour blockout review; other compound types remain unapproved for active placement.'
    pack['terrain_contract_file_sha256']=file_sha(terrain_path);pack['runtime_ready']=False;pack['pending_acceptance']=['visible terrain cut/fill/retaining support','common runtime integration and actual scene visual review']
    missing=[k for k,v in pack['asset_manifest'].items() if v['cache_status']!='reuse_verified_compiled_asset']
    pack['cache_binding_status']='all_required_render_files_verified' if not missing else 'source_bindings_resolved; compiled_render_cache_pending';pack['missing_compiled_asset_keys']=missing
    pack['deferred_recipe_compounds']=[{'source_plot_id':p['id'],'property_type':p['property_type'],'reason':'awaiting_accepted_whole_compound_terrain_contract; original source preserved'} for p in plan['plots'] if p['property_type'] in ('poor_block','merchant_court')]
    for key,asset in pack['asset_manifest'].items():
        if key in cache:asset['verified_runtime_asset']=cache[key]
    target=HERE/'resolved_placements.json'
    if target.exists() and file_sha(target)!=hashlib.sha256((json.dumps(pack,indent=2)+'\n').encode()).hexdigest():
        archive=HERE/'generated/resolver'/('resolved_placements.'+file_sha(target)[:12]+'.json')
        if not archive.exists():archive.write_bytes(target.read_bytes())
    write(target,pack);return pack,resolver
if __name__=='__main__':
    p,_=run();print(json.dumps({**p['summary'],'cache_binding_status':p['cache_binding_status'],'deferred_recipe_compounds':len(p['deferred_recipe_compounds'])},indent=2))
